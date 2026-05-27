@echo off
REM RAG Chatbot Setup Script for Windows

echo.
echo ====================================
echo RAG Chatbot - Setup Script
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [✓] Python found
python --version

REM Check if virtual environment exists
if not exist "venv\" (
    echo.
    echo [*] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [✓] Virtual environment created
)

REM Activate virtual environment
echo.
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo [*] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [✓] Dependencies installed successfully

REM Check for .env file
if not exist ".env" (
    echo.
    echo [WARNING] .env file not found
    echo [*] Creating .env from .env.example...
    copy .env.example .env
    echo [!] Please edit .env and add your GEMINI_API_KEY
)

echo.
echo ====================================
echo Setup Complete!
echo ====================================
echo.
echo Next steps:
echo 1. Edit .env and add your GEMINI_API_KEY (if not already done)
echo 2. Run: python main.py
echo 3. Open index.html in your browser
echo.
pause
