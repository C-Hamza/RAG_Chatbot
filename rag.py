import os
import sqlite3
import json
import shutil
from typing import List, Dict
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from docx2txt import process as extract_docx_text
from langchain_core.documents import Document
import uuid
from datetime import datetime


class Session:
    """A single conversation session with its own documents and history."""

    def __init__(self, session_id: str, title: str = "New Chat"):
        self.id = session_id
        self.title = title
        self.created_at = datetime.now().isoformat()
        self.vector_store = None
        self.chat_history: List = []  # LangChain message objects
        self.history_log: List[Dict] = []  # For the /history endpoint
        self.documents: List[str] = []  # filenames uploaded

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "document_count": len(self.documents),
            "message_count": len(self.history_log),
        }


class RAGPipeline:
    def __init__(self, api_key: str):
        self.api_key = api_key
        os.environ["GOOGLE_API_KEY"] = api_key

        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)

        self.sessions: Dict[str, Session] = {}
        self.active_session_id: str = None

        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a helpful assistant that answers questions based ONLY on the provided document context. "
             "If the answer is not in the context, say so. Be concise and accurate.\n\n"
             "Context from uploaded documents:\n{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ])

        # Initialize SQLite database and load saved sessions
        self._init_db()
        self._load_sessions_from_db()

        # Create a default session if no sessions exist
        if not self.sessions:
            self._create_session("Welcome")
        else:
            # Set active session to the most recently created session
            sorted_sessions = sorted(self.sessions.values(), key=lambda x: x.created_at, reverse=True)
            self.active_session_id = sorted_sessions[0].id

    def _init_db(self):
        db_path = os.path.join(os.path.dirname(__file__), "rag_store.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                documents TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        conn.close()

    def _get_db_conn(self):
        db_path = os.path.join(os.path.dirname(__file__), "rag_store.db")
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _load_sessions_from_db(self):
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, created_at, documents FROM sessions")
        rows = cursor.fetchall()
        for row in rows:
            session_id, title, created_at, docs_json = row
            session = Session(session_id, title)
            session.created_at = created_at
            try:
                session.documents = json.loads(docs_json) if docs_json else []
            except Exception:
                session.documents = []
            
            # Load messages
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", 
                (session_id,)
            )
            msg_rows = cursor.fetchall()
            for role, content in msg_rows:
                session.history_log.append({"role": role, "content": content})
                if role == "user":
                    session.chat_history.append(HumanMessage(content=content))
                else:
                    session.chat_history.append(AIMessage(content=content))
            
            session.vector_store = None
            self.sessions[session_id] = session
        conn.close()

    def _update_session_db(self, session: Session):
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET title = ?, documents = ? WHERE id = ?",
            (session.title, json.dumps(session.documents), session.id)
        )
        conn.commit()
        conn.close()

    def _save_message_db(self, session_id: str, role: str, content: str):
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def _load_vector_store_if_needed(self, session: Session) -> bool:
        if session.vector_store is not None:
            return True
        vs_path = os.path.join(os.path.dirname(__file__), "vector_stores", session.id)
        if os.path.exists(vs_path):
            try:
                session.vector_store = FAISS.load_local(
                    vs_path, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
                return True
            except Exception as e:
                print(f"Error loading vector store for session {session.id}: {e}")
        return False

    def _create_session(self, title: str = "New Chat") -> Session:
        session_id = str(uuid.uuid4())[:8]
        session = Session(session_id, title)
        self.sessions[session_id] = session
        self.active_session_id = session_id
        
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, title, created_at, documents) VALUES (?, ?, ?, ?)",
            (session.id, session.title, session.created_at, json.dumps(session.documents))
        )
        conn.commit()
        conn.close()
        return session

    def _active_session(self) -> Session:
        if self.active_session_id and self.active_session_id in self.sessions:
            return self.sessions[self.active_session_id]
        return None

    def create_new_session(self, title: str = "New Chat") -> Dict:
        session = self._create_session(title)
        return session.to_dict()

    def switch_session(self, session_id: str) -> Dict:
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        self.active_session_id = session_id
        return self.sessions[session_id].to_dict()

    def get_sessions(self) -> List[Dict]:
        return [s.to_dict() for s in sorted(self.sessions.values(), key=lambda x: x.created_at, reverse=True)]

    def delete_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]
            
        vs_path = os.path.join(os.path.dirname(__file__), "vector_stores", session_id)
        if os.path.exists(vs_path):
            try:
                shutil.rmtree(vs_path)
            except Exception as e:
                print(f"Error removing vector directory: {e}")
                
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()

        if self.active_session_id == session_id:
            if self.sessions:
                sorted_sessions = sorted(self.sessions.values(), key=lambda x: x.created_at, reverse=True)
                self.active_session_id = sorted_sessions[0].id
            else:
                self._create_session("New Chat")

    def _load_file(self, path: str) -> List[Document]:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            return PyPDFLoader(path).load()
        elif ext == ".txt":
            return TextLoader(path, encoding="utf-8").load()
        elif ext == ".docx":
            text = extract_docx_text(path)
            return [Document(page_content=text, metadata={"source": path})]
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def process_and_add_documents(self, file_paths: List[str], filenames: List[str] = None) -> Dict:
        session = self._active_session()
        if not session:
            raise ValueError("No active session")

        # Load existing vector store from disk if any
        self._load_vector_store_if_needed(session)

        all_docs: List[Document] = []
        for p in file_paths:
            try:
                all_docs.extend(self._load_file(p))
            except Exception as e:
                print(f"Error loading {p}: {e}")

        if not all_docs:
            raise ValueError("No text could be extracted from the uploaded files.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(all_docs)

        if session.vector_store is None:
            session.vector_store = FAISS.from_documents(chunks, self.embeddings)
        else:
            session.vector_store.add_documents(chunks)

        # Save vector store to disk
        vs_dir = os.path.join(os.path.dirname(__file__), "vector_stores")
        os.makedirs(vs_dir, exist_ok=True)
        vs_path = os.path.join(vs_dir, session.id)
        session.vector_store.save_local(vs_path)

        if filenames:
            session.documents.extend(filenames)
            # Auto-title the session based on first uploaded file
            if session.title == "New Chat" or session.title == "Welcome":
                session.title = filenames[0].rsplit(".", 1)[0][:30]

        # Save session changes to SQLite
        self._update_session_db(session)

        return {"files_processed": len(file_paths), "total_chunks": len(chunks)}

    def answer_question(self, query: str) -> Dict:
        session = self._active_session()
        if not session:
            raise ValueError("No active session")

        # Load vector store from disk if not in memory
        has_vectors = self._load_vector_store_if_needed(session)
        if not has_vectors:
            raise ValueError("No documents uploaded yet. Please upload documents first.")

        docs = session.vector_store.similarity_search(query, k=5)
        context = "\n\n".join(d.page_content for d in docs)

        messages = self.prompt.format_messages(
            context=context,
            chat_history=session.chat_history,
            question=query,
        )

        response = self.llm.invoke(messages)
        answer = response.content

        session.chat_history.append(HumanMessage(content=query))
        session.chat_history.append(AIMessage(content=answer))
        if len(session.chat_history) > 20:
            session.chat_history = session.chat_history[-20:]

        session.history_log.append({"role": "user", "content": query})
        session.history_log.append({"role": "assistant", "content": answer})

        # Save user and assistant messages to SQLite
        self._save_message_db(session.id, "user", query)
        self._save_message_db(session.id, "assistant", answer)

        # Auto-title from first question
        if session.title in ["New Chat", "Welcome"] and len(session.history_log) == 2:
            session.title = query[:40]
            self._update_session_db(session)

        return {"response": answer, "context_used": len(docs)}

    def get_history(self, session_id: str = None) -> List[Dict]:
        sid = session_id or self.active_session_id
        if sid and sid in self.sessions:
            return self.sessions[sid].history_log
        return []

    def clear_session(self, session_id: str = None):
        sid = session_id or self.active_session_id
        if sid and sid in self.sessions:
            s = self.sessions[sid]
            s.vector_store = None
            s.chat_history = []
            s.history_log = []
            s.documents = []

            # Delete vectors from disk
            vs_path = os.path.join(os.path.dirname(__file__), "vector_stores", sid)
            if os.path.exists(vs_path):
                try:
                    shutil.rmtree(vs_path)
                except Exception as e:
                    print(f"Error removing vector directory: {e}")

            # Clear DB entries
            conn = self._get_db_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
            cursor.execute("UPDATE sessions SET documents = ?, title = ? WHERE id = ?", ("[]", "New Chat", sid))
            conn.commit()
            conn.close()
            s.title = "New Chat"
