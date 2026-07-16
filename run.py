#!/usr/bin/env python
"""
CrapsIQ - All-in-one startup script

Runs the complete CrapsIQ application:
- Backend API server
- Frontend web server
- Automatic browser open
"""

import subprocess
import sys
import time
import webbrowser
import os

def run_server():
    """
    Start the FastAPI server that serves both API and frontend.
    """
    print("🎲 Starting CrapsIQ...\n")
    
    # Check if requirements are installed
    try:
        import fastapi
        import cv2
    except ImportError:
        print("❌ Missing dependencies. Install with:")
        print("   cd backend && pip install -r requirements.txt")
        sys.exit(1)
    
    # Start the server
    os.chdir('backend')
    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'main:app',
        '--host', '0.0.0.0',
        '--port', '8000',
        '--reload'
    ])

if __name__ == '__main__':
    # Give user time to read startup message
    print("�� CrapsIQ - Live Dealer AI Assistant\n")
    print("Starting server...")
    print("  🎲 Frontend: http://localhost:8000")
    print("  📋 API Docs: http://localhost:8000/docs")
    print("  ⚠️  Press Ctrl+C to stop\n")
    
    time.sleep(2)
    
    # Try to open browser
    try:
        webbrowser.open('http://localhost:8000')
    except:
        pass
    
    # Start the server
    run_server()
