"""Vercel serverless entry point for FastAPI application."""

import sys
import logging
from pathlib import Path

# Configure logging for Vercel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure vendored dependencies are discoverable at runtime
vendor_root = Path(__file__).resolve().parent.parent / ".python_packages"
if vendor_root.exists():
    for site_packages in sorted(vendor_root.glob("lib/python*/site-packages")):
        site_path = str(site_packages)
        if site_path not in sys.path:
            sys.path.insert(0, site_path)
            logger.info(f"Added to path: {site_path}")

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    logger.info(f"Added project root to path: {project_root}")

try:
    # Import and expose the FastAPI app
    from src.app.main import app
    logger.info("FastAPI app imported successfully")
    logger.info(f"Total routes registered: {len(app.routes)}")
except Exception as e:
    logger.error(f"Failed to import FastAPI app: {e}", exc_info=True)
    raise

# Vercel requires the app to be exported at module level
__all__ = ["app"]

