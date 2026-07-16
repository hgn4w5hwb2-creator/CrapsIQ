#!/bin/bash
# CrapsIQ startup script for macOS/Linux

echo "🎲 CrapsIQ - Live Dealer AI Assistant"
echo ""
echo "Starting server..."
echo "  🎲 Frontend: http://localhost:8000"
echo "  📋 API Docs: http://localhost:8000/docs"
echo "  ⚠️  Press Ctrl+C to stop"
echo ""

cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
