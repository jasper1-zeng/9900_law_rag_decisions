"""
Test package for SAT Decisions RAG system.
"""
import sys
import os

# Add the parent directory to the path so we can import the backend modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir) 