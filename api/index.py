"""
Vercel serverless entry point for FastAPI application.

Vercel's Python runtime automatically handles ASGI applications.
Simply export the FastAPI app and Vercel will manage it.
"""

import sys
from pathlib import Path

# Add project root to Python path so modules can be imported
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.app.main import app

# Export the app for Vercel
# Vercel's Python runtime recognizes this as an ASGI application
__all__ = ["app"]
