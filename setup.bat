@echo off
REM Quick start script for Agent Chat Application

echo.
echo ================================
echo Agent Chat Application - Setup
echo ================================
echo.

REM Check if backend/.env exists
if not exist "backend\.env" (
    echo [1/2] Creating backend .env file...
    copy backend\.env.example backend\.env
    echo Please edit backend\.env and add your OPENAI_API_KEY
    echo.
)

REM Install backend dependencies
echo [2/2] Installing backend dependencies...
cd backend
pip install -r requirements.txt
cd ..

echo.
echo ================================
echo Setup complete!
echo ================================
echo.
echo Next steps:
echo 1. Edit backend\.env with your OpenAI API key
echo 2. Run: python backend/main.py
echo 3. In another terminal: cd frontend && npm install && npm run dev
echo.
pause
