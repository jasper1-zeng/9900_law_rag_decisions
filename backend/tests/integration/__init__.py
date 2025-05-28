"""Integration tests for the RAG system."""
import sys
import os

# Ensure the backend modules can be imported
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir) 