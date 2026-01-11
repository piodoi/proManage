"""
Centralized path configuration for the application.

All paths that reference userdata, configs, or other shared directories
should be defined here for consistency and ease of maintenance.
"""
from pathlib import Path

# Project root - backend folder is at project_root/backend/
# This file is at backend/app/paths.py
# .parent = backend/app
# .parent.parent = backend
# .parent.parent.parent = project root (proManage)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Backend folder (backend/)
BACKEND_DIR = PROJECT_ROOT / "backend"

# User data directory (project_root/userdata/)
USERDATA_DIR = PROJECT_ROOT / "userdata"

# Admin directory within userdata (project_root/userdata/admin/)
ADMIN_DATA_DIR = USERDATA_DIR / "admin"

# Text patterns directory for bill extraction
TEXT_PATTERNS_DIR = ADMIN_DATA_DIR / "text_patterns"

# Suppliers configuration file
SUPPLIERS_FILE = ADMIN_DATA_DIR / "suppliers.json"

# Scraper configs directory (kept in backend for debug purposes)
SCRAPER_DUMPS_DIR = BACKEND_DIR / "scraper_dumps"

# Environment file (in backend folder)
ENV_FILE = BACKEND_DIR / ".env"


def ensure_directories():
    """Create required directories if they don't exist."""
    TEXT_PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    ADMIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCRAPER_DUMPS_DIR.mkdir(parents=True, exist_ok=True)

