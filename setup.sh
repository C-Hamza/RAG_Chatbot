#!/bin/bash
# RAG Chatbot Setup Script for macOS/Linux

echo ""
echo "===================================="
echo "RAG Chatbot - Setup Script"
echo "===================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

echo "[✓] Python found"
python3 --version

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    fi
    echo "[✓] Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "[*] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "[*] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi
echo "[✓] Dependencies installed successfully"

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "[WARNING] .env file not found"
    echo "[*] Creating .env from .env.example..."
    cp .env.example .env
    echo "[!] Please edit .env and add your GEMINI_API_KEY"
fi

echo ""
echo "===================================="
echo "Setup Complete!"
echo "===================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your GEMINI_API_KEY (if not already done)"
echo "2. Run: python main.py"
echo "3. Open index.html in your browser"
echo ""
