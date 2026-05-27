# RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot using FastAPI, LangChain, FAISS, and Gemini LLMs.

## Features
- Upload PDF, DOCX, and TXT files
- Process and chunk documents using LangChain
- Vector store with FAISS
- Conversations powered by Google's Gemini models (`gemini-2.5-pro` and `text-embedding-004`)
- Clean UI for uploading and chatting

## Prerequisites
- Python 3.8+
- Gemini API Key

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd RAG
   ```

2. **Set up a Virtual Environment (Optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Make sure you have a `.env` file in the root of the project with your Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

5. **Run the Application:**
   ```bash
   uvicorn main:app --reload
   ```

6. **Access the UI:**
   Open your browser and navigate to:
   http://localhost:8000/

## Usage
1. Click **Choose Files** to select one or multiple documents.
2. Click **Upload** and wait for the backend to process and index them.
3. Start asking questions in the chat interface! The chatbot will use the uploaded context to answer you accurately.
