"""
Quick test script to verify all components work
Run this after installation to test the RAG system
"""

import os
import sys
from dotenv import load_dotenv

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    try:
        import fastapi
        print("  ✓ FastAPI")
        import uvicorn
        print("  ✓ Uvicorn")
        import PyPDF2
        print("  ✓ PyPDF2")
        import docx
        print("  ✓ python-docx")
        import faiss
        print("  ✓ FAISS")
        import google.generativeai
        print("  ✓ google-generativeai")
        import dotenv
        print("  ✓ python-dotenv")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_api_key():
    """Test if API key is configured"""
    print("\nTesting API key configuration...")
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        print(f"  ✓ GEMINI_API_KEY found (length: {len(api_key)})")
        return True
    else:
        print("  ✗ GEMINI_API_KEY not found in .env")
        return False

def test_modules():
    """Test custom modules"""
    print("\nTesting custom modules...")
    try:
        from document_processor import DocumentProcessor
        print("  ✓ DocumentProcessor")
        from embedding_manager import EmbeddingManager
        print("  ✓ EmbeddingManager")
        from rag_engine import RAGEngine
        print("  ✓ RAGEngine")
        return True
    except ImportError as e:
        print(f"  ✗ Module import failed: {e}")
        return False

def test_sample_document():
    """Test document processing"""
    print("\nTesting document processing...")
    try:
        from document_processor import DocumentProcessor
        if os.path.exists("sample_document.txt"):
            text = DocumentProcessor.extract_txt("sample_document.txt")
            print(f"  ✓ Extracted {len(text)} characters from sample_document.txt")
            
            chunks = DocumentProcessor.chunk_text(text)
            print(f"  ✓ Created {len(chunks)} chunks")
            return True
        else:
            print("  ⚠ sample_document.txt not found (skip)")
            return True
    except Exception as e:
        print(f"  ✗ Document processing failed: {e}")
        return False

def main():
    print("=" * 50)
    print("RAG Chatbot - Component Test")
    print("=" * 50)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("API Key", test_api_key()))
    results.append(("Modules", test_modules()))
    results.append(("Document Processing", test_sample_document()))
    
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Ready to run the application.")
        print("\nTo start the server, run:")
        print("  python main.py")
        print("\nThen open index.html in your browser.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\nCommon issues:")
        print("  - Missing dependencies: Run 'pip install -r requirements.txt'")
        print("  - Missing .env file: Copy .env.example to .env and add API key")
        print("  - Python path issues: Ensure Python 3.8+ is installed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
