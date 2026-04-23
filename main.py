"""
Main entry point for the Task Automation Engine
Run with: uvicorn main:app --reload
"""

import uvicorn
from src.api import app

if __name__ == "__main__":
    print("=" * 60)
    print("Task Automation Engine - Starting Server")
    print("=" * 60)
    print("\nAPI Documentation available at:")
    print("  http://localhost:8000/docs")
    print("\nQuick test commands:")
    print("  curl http://localhost:8000/health")
    print("  curl -X POST http://localhost:8000/tasks/execute \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"name": "test", "steps": [{"action": "wait", "seconds": 1}]}\'')
    print("\n" + "=" * 60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
