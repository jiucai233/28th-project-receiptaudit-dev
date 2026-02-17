#!/bin/bash

# --- Configuration ---
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Check if we are in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the project root directory."
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' is not installed. Please install it first (https://github.com/astral-sh/uv)."
    exit 1
fi

echo "🚀 Starting Transparent-Audit with 'uv' for Performance Testing..."

# 1. Setup Backend Environment with uv
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment with uv..."
    uv venv
fi

echo "🛠 Syncing backend dependencies with uv..."
uv pip install -r requirements.txt > /dev/null 2>&1

# 2. Setup Frontend Environment
echo "🛠 Checking frontend dependencies..."
if [ -d "web-react" ]; then
    cd web-react
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing frontend packages..."
        npm install
    fi
    cd ..
else
    echo "❌ Error: web-react directory not found."
    exit 1
fi

# 3. Start Backend (Background) using uv run
echo "🔥 Starting Backend FastAPI (Port: $BACKEND_PORT)..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
# Using 'uv run' ensures we use the correct venv and dependencies
uv run uvicorn server.routes.app:app --host 0.0.0.0 --port $BACKEND_PORT > backend.log 2>&1 &
BACKEND_PID=$!

# 4. Start Frontend (Background)
echo "🌐 Starting Frontend React (Port: $FRONTEND_PORT)..."
cd web-react
npm run dev -- --port $FRONTEND_PORT > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Handle Exit
trap "echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT

echo "------------------------------------------------"
echo "✅ Services are running (Powered by uv)!"
echo "👉 Frontend: http://localhost:$FRONTEND_PORT"
echo "👉 Backend:  http://localhost:$BACKEND_PORT"
echo "📝 Backend Logs:  tail -f backend.log"
echo "📝 Frontend Logs: tail -f frontend.log"
echo "------------------------------------------------"
echo "Press Ctrl+C to stop all services."

# Keep script alive
wait
