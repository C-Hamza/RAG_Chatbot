import os
import tempfile
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Optional

from rag import RAGPipeline

load_dotenv()

app = FastAPI(title="RAG Chatbot", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

rag = RAGPipeline(API_KEY)


class ChatRequest(BaseModel):
    query: str


class SessionRequest(BaseModel):
    title: Optional[str] = "New Chat"


# ── Health ──
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ── Sessions ──
@app.get("/sessions")
async def list_sessions():
    return {"sessions": rag.get_sessions(), "active": rag.active_session_id}


@app.post("/sessions")
async def create_session(req: SessionRequest):
    session = rag.create_new_session(req.title)
    return {"session": session}


@app.post("/sessions/{session_id}/switch")
async def switch_session(session_id: str):
    try:
        session = rag.switch_session(session_id)
        return {"session": session}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    rag.delete_session(session_id)
    return {"status": "deleted", "active": rag.active_session_id}


@app.get("/sessions/{session_id}/history")
async def session_history(session_id: str):
    history = rag.get_history(session_id)
    return {"history": history}


# ── Upload ──
@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    try:
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        filenames = []
        try:
            for file in files:
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in [".pdf", ".docx", ".txt"]:
                    raise ValueError(f"Unsupported file type: {ext}")
                temp_path = os.path.join(temp_dir, file.filename)
                with open(temp_path, "wb") as f:
                    f.write(await file.read())
                file_paths.append(temp_path)
                filenames.append(file.filename)
            result = rag.process_and_add_documents(file_paths, filenames)
            return {
                "status": "success",
                "files_processed": result["files_processed"],
                "total_chunks": result["total_chunks"],
                "message": f"Processed {result['files_processed']} file(s)",
            }
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Chat ──
@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        result = rag.answer_question(request.query)
        return {"response": result["response"], "context_used": result["context_used"], "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── History ──
@app.get("/history")
async def get_history():
    return {"history": rag.get_history()}


# ── Clear ──
@app.post("/clear")
async def clear_session():
    rag.clear_session()
    return {"status": "success", "message": "Session cleared"}


# ── Serve frontend ──
@app.get("/")
async def serve_index():
    return FileResponse("index.html")

app.mount("/static", StaticFiles(directory="."), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
