import os
import shutil
import sqlite3
from dotenv import load_dotenv

# Ensure we load environment variables
load_dotenv()

# Check key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("[ERROR] GEMINI_API_KEY not found in .env")
    exit(1)

# Paths to verify
db_path = os.path.join(os.path.dirname(__file__), "rag_store.db")
vs_dir = os.path.join(os.path.dirname(__file__), "vector_stores")

print("--- Clean up past databases for a clean run ---")
if os.path.exists(db_path):
    os.remove(db_path)
    print("Removed old db")
if os.path.exists(vs_dir):
    shutil.rmtree(vs_dir)
    print("Removed old vector stores")

print("\n--- Test 1: Initializing RAGPipeline ---")
from rag import RAGPipeline
pipeline = RAGPipeline(api_key)

print(f"Created default session ID: {pipeline.active_session_id}")
session = pipeline._active_session()
print(f"Session title: {session.title}")

# Verify SQLite file was created
if os.path.exists(db_path):
    print("[SUCCESS] SQLite database file created successfully.")
else:
    print("[FAILURE] SQLite database file was not created.")
    exit(1)

# Verify table entries
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT id, title FROM sessions")
rows = c.fetchall()
print(f"Sessions in SQLite: {rows}")
conn.close()

if len(rows) != 1 or rows[0][0] != pipeline.active_session_id:
    print("[FAILURE] SQLite did not match in-memory session.")
    exit(1)
else:
    print("[SUCCESS] SQLite session matches in-memory session.")

print("\n--- Test 2: Uploading a mock file and generating vectors ---")
# Create mock file
mock_file_path = os.path.join(os.path.dirname(__file__), "mock_test_doc.txt")
with open(mock_file_path, "w", encoding="utf-8") as f:
    f.write("Google Antigravity is a secret project developed by the Google DeepMind team for pair programming with users.")

try:
    result = pipeline.process_and_add_documents([mock_file_path], ["mock_test_doc.txt"])
    print(f"File processed: {result}")
    
    # Verify local vector store dir exists
    sess_vs_path = os.path.join(vs_dir, pipeline.active_session_id)
    if os.path.exists(sess_vs_path):
        print(f"[SUCCESS] Vector store directory created for session at {sess_vs_path}")
    else:
        print("[FAILURE] Vector store directory was not created.")
        exit(1)
        
    # Verify document name stored in SQLite
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT documents FROM sessions WHERE id=?", (pipeline.active_session_id,))
    docs_json = c.fetchone()[0]
    print(f"Documents in SQLite: {docs_json}")
    conn.close()
    if "mock_test_doc.txt" in docs_json:
         print("[SUCCESS] SQLite contains uploaded filename.")
    else:
         print("[FAILURE] SQLite does not contain filename.")
         exit(1)
finally:
    if os.path.exists(mock_file_path):
        os.remove(mock_file_path)

print("\n--- Test 3: Chat conversation and history log ---")
question = "Who developed Google Antigravity?"
print(f"Question: {question}")
answer_res = pipeline.answer_question(question)
print(f"Response: {answer_res['response']}")

# Verify messages table has records
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT role, content FROM messages WHERE session_id=?", (pipeline.active_session_id,))
messages = c.fetchall()
print(f"Messages in SQLite: {messages}")
conn.close()

if len(messages) == 2:
    print("[SUCCESS] User question and chatbot answer saved to SQLite.")
else:
    print("[FAILURE] Chat message log not saved correctly.")
    exit(1)

print("\n--- Test 4: Reloading Server Simulation (reinitializing RAGPipeline) ---")
# Re-create pipeline instance (simulates server restart)
pipeline_restarted = RAGPipeline(api_key)

print(f"Active session ID after restart: {pipeline_restarted.active_session_id}")
re_session = pipeline_restarted._active_session()
print(f"Restored Session Title: {re_session.title}")
print(f"Restored Session Documents: {re_session.documents}")
print(f"Restored Session Messages Log: {re_session.history_log}")

if re_session.title == session.title and re_session.documents == session.documents and len(re_session.history_log) == 2:
    print("[SUCCESS] Session metadata, documents list, and messages restored perfectly on restart.")
else:
    print("[FAILURE] Verification failed during pipeline restart.")
    exit(1)

print("\n--- Test 5: Ask another question on restarted server using same context ---")
question_2 = "What team worked on this project?"
print(f"Question: {question_2}")
answer_res_2 = pipeline_restarted.answer_question(question_2)
print(f"Response: {answer_res_2['response']}")
if "deepmind" in answer_res_2['response'].lower():
    print("[SUCCESS] Context search from loaded FAISS vector store works post-restart!")
else:
    print("[FAILURE] Could not search from local vector index.")
    exit(1)

print("\nALL PERSISTENT DATABASE AND VECTOR STORE TESTS PASSED SUCCESSFULLY!")
