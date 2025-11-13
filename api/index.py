"""Vercel serverless entry point for FastAPI application."""

import sys
from pathlib import Path

# Ensure vendored dependencies are discoverable at runtime
vendor_root = Path(__file__).resolve().parent.parent / ".python_packages"
if vendor_root.exists():
    for site_packages in sorted(vendor_root.glob("lib/python*/site-packages")):
        site_path = str(site_packages)
        if site_path not in sys.path:
            sys.path.insert(0, site_path)

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import and expose the FastAPI app
from src.app.main import app

# Vercel requires the app to be exported at module level
__all__ = ["app"]

