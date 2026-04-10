#!/bin/bash
# Dev script to start both FastAPI backend and Vite frontend

set -e

echo "🚀 Starting MeowAI Home development environment..."

# Start backend in background
echo "📡 Starting FastAPI backend on http://localhost:8000..."
python3 -m uvicorn src.web.app:create_app --factory --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "🎨 Starting Vite frontend on http://localhost:5173..."
cd web && npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Both servers started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
