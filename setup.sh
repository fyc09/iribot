#!/bin/bash

# Quick start script for Agent Chat Application

echo ""
echo "================================"
echo "Agent Chat Application - Setup"
echo "================================"
echo ""

# Check if backend/.env exists
if [ ! -f "backend/.env" ]; then
    echo "[1/2] Creating backend .env file..."
    cp backend/.env.example backend/.env
    echo "Please edit backend/.env and add your OPENAI_API_KEY"
    echo ""
fi

# Install backend dependencies
echo "[2/2] Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..

echo ""
echo "================================"
echo "Setup complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your OpenAI API key"
echo "2. Run: python backend/main.py"
echo "3. In another terminal: cd frontend && npm install && npm run dev"
echo ""
