#!/usr/bin/env python3
"""
Startup script for the Hansard RAG API
"""

import uvicorn
import sys
import os

# Add the parent directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    print("Starting Hansard RAG API...")
    print("Access the API at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("Alternative docs: http://localhost:8000/redoc")
    print("\nPress Ctrl+C to stop the server\n")
    
    uvicorn.run(
        "rag.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )