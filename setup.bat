@echo off
REM Setup script for Windows

echo 🚀 Setting up Tiered Email Filtering Web App...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is required but not installed.
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is required but not installed.
    exit /b 1
)

echo ✅ Python and Node.js found

REM Setup backend
echo.
echo 📦 Setting up backend...
cd backend
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo ✅ Backend dependencies installed
cd ..

REM Setup frontend
echo.
echo 📦 Setting up frontend...
cd frontend
if not exist "node_modules" (
    echo Installing Node.js dependencies...
    call npm install
)
echo ✅ Frontend dependencies installed
cd ..

echo.
echo ✅ Setup complete!
echo.
echo To run the app:
echo   1. Start backend: run-backend.bat
echo   2. Start frontend: run-frontend.bat

