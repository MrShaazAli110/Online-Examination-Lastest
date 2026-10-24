import uvicorn
import os
import sys

# Ensure current directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.seed_data import seed_database

if __name__ == "__main__":
    print("=" * 60)
    print("ProctorCode: Secure Proctored Quiz & Coding Assessment Platform")
    print("=" * 60)
    print("Initializing Database & Seed Data...")
    seed_database()
    print("Starting Web Server at http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
