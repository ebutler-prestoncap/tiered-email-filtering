@echo off
REM Run frontend development server on Windows

cd frontend

if not exist "node_modules" (
    echo ❌ Node modules not found. Run setup.bat first.
    pause
    exit /b 1
)

call npm run dev

