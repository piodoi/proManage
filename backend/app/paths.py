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

# Text patterns directory for bill extraction (admin patterns)
TEXT_PATTERNS_DIR = ADMIN_DATA_DIR / "text_patterns"

# Suppliers configuration file
SUPPLIERS_FILE = ADMIN_DATA_DIR / "suppliers.json"

# Scraper configs directory (kept in backend for debug purposes)
SCRAPER_DUMPS_DIR = BACKEND_DIR / "scraper_dumps"

# Environment file (in backend folder)
ENV_FILE = BACKEND_DIR / ".env"


def get_user_data_dir(user_id: str) -> Path:
    """Get the data directory for a specific user."""
    return USERDATA_DIR / user_id


def ensure_directories():
    """Create required directories if they don't exist."""
    TEXT_PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    ADMIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCRAPER_DUMPS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_user_directory(user_id: str) -> Path:
    """Ensure user data directory exists and return path."""
    user_dir = get_user_data_dir(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_user_bills_dir(user_id: str) -> Path:
    """Get the bills directory for a specific user."""
    return get_user_data_dir(user_id) / "bills"


def ensure_user_bills_directory(user_id: str) -> Path:
    """Ensure user bills directory exists and return path."""
    bills_dir = get_user_bills_dir(user_id)
    bills_dir.mkdir(parents=True, exist_ok=True)
    return bills_dir


def get_bill_pdf_path(user_id: str, bill_id: str) -> Path:
    """Get the path for a bill's PDF file."""
    return get_user_bills_dir(user_id) / f"{bill_id}.pdf"


def save_bill_pdf(user_id: str, bill_id: str, pdf_data: bytes) -> Path:
    """Save PDF data for a bill and return the file path."""
    ensure_user_bills_directory(user_id)
    pdf_path = get_bill_pdf_path(user_id, bill_id)
    pdf_path.write_bytes(pdf_data)
    return pdf_path


def delete_bill_pdf(user_id: str, bill_id: str) -> bool:
    """Delete PDF file for a bill. Returns True if file was deleted, False if not found."""
    pdf_path = get_bill_pdf_path(user_id, bill_id)
    if pdf_path.exists():
        pdf_path.unlink()
        return True
    return False


def bill_pdf_exists(user_id: str, bill_id: str) -> bool:
    """Check if a PDF file exists for a bill."""
    return get_bill_pdf_path(user_id, bill_id).exists()

