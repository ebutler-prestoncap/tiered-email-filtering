@echo off
REM Run backend server on Windows

cd backend

if not exist "venv" (
    echo ❌ Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python app.py

