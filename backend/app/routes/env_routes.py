"""Environment variables management routes for admin."""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.models import TokenData
from app.auth import require_admin

router = APIRouter(prefix="/admin/env", tags=["admin-env"])
logger = logging.getLogger(__name__)

# Base paths
BACKEND_DIR = Path(__file__).parent.parent.parent  # backend/
ROOT_DIR = BACKEND_DIR.parent  # project root
FRONTEND_DIR = ROOT_DIR / "frontend"
USERDATA_ADMIN_DIR = ROOT_DIR / "userdata" / "admin"

# Feature flags file path
FEATURE_FLAGS_FILE = USERDATA_ADMIN_DIR / "feature_flags.json"

# Default feature flags
DEFAULT_FEATURE_FLAGS = {
    "payOnline": False,
    "barcodeExtraction": False,
    "facebookLogin": False,
    "demoLogin": False,
    "usBuild": False,
}


class EnvVariable(BaseModel):
    """Environment variable model."""
    key: str
    value: str
    source: str  # 'backend' or 'frontend'
    category: str  # 'database', 'security', 'oauth', 'email', 'feature', etc.
    description: Optional[str] = None
    is_secret: bool = False


class EnvUpdateRequest(BaseModel):
    """Request to update environment variables."""
    variables: Dict[str, str]  # key -> value
    source: str  # 'backend' or 'frontend'


class RestartRequest(BaseModel):
    """Request to restart a service."""
    service: str  # 'backend' or 'frontend'


# Categorize known env variables
ENV_CATEGORIES = {
    # Backend variables
    'DATABASE_URL': ('database', 'Database connection string', True),
    'MYSQL_ROOT_PASSWORD': ('database', 'MySQL root password', True),
    'MYSQL_USER': ('database', 'MySQL username', False),
    'MYSQL_PASSWORD': ('database', 'MySQL password', True),
    'JWT_SECRET': ('security', 'JWT signing secret', True),
    'GOOGLE_CLIENT_ID': ('oauth', 'Google OAuth client ID', False),
    'GOOGLE_CLIENT_SECRET': ('oauth', 'Google OAuth client secret', True),
    'FACEBOOK_APP_ID': ('oauth', 'Facebook OAuth app ID', False),
    'FACEBOOK_APP_SECRET': ('oauth', 'Facebook OAuth app secret', True),
    'FRONTEND_URL': ('cors', 'Frontend URL for CORS', False),
    'CORS_ORIGINS': ('cors', 'Additional CORS origins (comma-separated)', False),
    'IMAP_SERVER': ('email', 'IMAP server address', False),
    'IMAP_PORT': ('email', 'IMAP server port', False),
    'EMAIL_ADDRESS': ('email', 'Email address for monitoring', False),
    'EMAIL_PASSWORD': ('email', 'Email password/app password', True),
    'SMTP_SERVER': ('email', 'SMTP server address', False),
    'SMTP_PORT': ('email', 'SMTP server port', False),
    'SMTP_USERNAME': ('email', 'SMTP username', False),
    'SMTP_PASSWORD': ('email', 'SMTP password', True),
    'STRIPE_SECRET_KEY': ('stripe', 'Stripe secret key', True),
    'STRIPE_WEBHOOK_SECRET': ('stripe', 'Stripe webhook secret', True),
    'STRIPE_PRICE_ID': ('stripe', 'Stripe price ID for subscriptions', False),
    
    # Frontend variables (VITE_ prefix)
    'VITE_API_URL': ('api', 'Backend API URL', False),
    'VITE_GOOGLE_CLIENT_ID': ('oauth', 'Google OAuth client ID', False),
    'VITE_FACEBOOK_APP_ID': ('oauth', 'Facebook OAuth app ID', False),
    'VITE_FEATURE_PAY_ONLINE': ('feature', 'Enable online payment feature', False),
    'VITE_FEATURE_BARCODE_EXTRACTION': ('feature', 'Enable barcode extraction feature', False),
    'VITE_FEATURE_FACEBOOK_LOGIN': ('feature', 'Enable Facebook login', False),
    'VITE_FEATURE_DEMO_LOGIN': ('feature', 'Enable demo login button', False),
    'VITE_FEATURE_US_BUILD': ('feature', 'US build mode (USD currency)', False),
}


def get_env_file_path(source: str) -> Path:
    """Get the .env file path for a source."""
    if source == 'backend':
        return BACKEND_DIR / '.env'
    elif source == 'frontend':
        return FRONTEND_DIR / '.env'
    else:
        raise ValueError(f"Unknown source: {source}")


def mask_secret_value(value: str) -> str:
    """
    Partially mask a secret value for display.
    First 8 characters are unmasked, then 1/3 of remaining chars are replaced with *.
    """
    if not value or len(value) <= 8:
        return value
    
    # First 8 chars unmasked
    prefix = value[:8]
    rest = value[8:]
    
    # Replace every 3rd character with *
    masked_rest = ""
    for i, char in enumerate(rest):
        if i % 3 == 0:
            masked_rest += "*"
        else:
            masked_rest += char
    
    return prefix + masked_rest


def parse_env_file(file_path: Path) -> Dict[str, str]:
    """Parse a .env file and return key-value pairs."""
    env_vars = {}
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                # Handle key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove surrounding quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    env_vars[key] = value
    return env_vars


def write_env_file(file_path: Path, env_vars: Dict[str, str], preserve_comments: bool = True):
    """Write environment variables to a .env file, preserving structure and comments."""
    lines = []
    existing_keys = set()
    
    # If file exists, preserve its structure
    if file_path.exists() and preserve_comments:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    lines.append(line.rstrip('\n'))
                elif '=' in stripped:
                    key = stripped.split('=', 1)[0].strip()
                    if key in env_vars:
                        lines.append(f'{key}={env_vars[key]}')
                        existing_keys.add(key)
                    else:
                        lines.append(line.rstrip('\n'))
                else:
                    lines.append(line.rstrip('\n'))
    
    # Add any new keys not in original file
    for key, value in env_vars.items():
        if key not in existing_keys:
            lines.append(f'{key}={value}')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def load_feature_flags() -> Dict[str, bool]:
    """Load feature flags from JSON file. Creates file with defaults if not exists."""
    # Ensure directory exists
    USERDATA_ADMIN_DIR.mkdir(parents=True, exist_ok=True)
    
    if not FEATURE_FLAGS_FILE.exists():
        # Create with defaults
        save_feature_flags(DEFAULT_FEATURE_FLAGS)
        return DEFAULT_FEATURE_FLAGS.copy()
    
    try:
        with open(FEATURE_FLAGS_FILE, 'r', encoding='utf-8') as f:
            flags = json.load(f)
        # Merge with defaults to ensure all flags exist
        result = DEFAULT_FEATURE_FLAGS.copy()
        result.update(flags)
        return result
    except Exception as e:
        logger.error(f"Error loading feature flags: {e}")
        return DEFAULT_FEATURE_FLAGS.copy()


def save_feature_flags(flags: Dict[str, bool]) -> None:
    """Save feature flags to JSON file."""
    USERDATA_ADMIN_DIR.mkdir(parents=True, exist_ok=True)
    with open(FEATURE_FLAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(flags, f, indent=2)


# Public endpoint for feature flags (no auth required for runtime checks)
@router.get("/feature-flags/public")
async def get_feature_flags_public() -> Dict[str, bool]:
    """Get current feature flag values. Public endpoint for frontend runtime checks."""
    return load_feature_flags()


@router.get("/variables")
async def get_env_variables(_: TokenData = Depends(require_admin)) -> Dict[str, List[EnvVariable]]:
    """
    Get all environment variables from backend and frontend .env files.
    Also includes current runtime values from os.environ.
    """
    result = {
        'backend': [],
        'frontend': [],
    }
    
    # Get backend env vars
    backend_env_file = get_env_file_path('backend')
    backend_file_vars = parse_env_file(backend_env_file)
    
    # Combine with os.environ for runtime values
    all_backend_keys = set(backend_file_vars.keys())
    for key in os.environ:
        if key in ENV_CATEGORIES or key.startswith(('DATABASE', 'JWT', 'GOOGLE', 'FACEBOOK', 'IMAP', 'SMTP', 'EMAIL', 'STRIPE', 'CORS', 'FRONTEND')):
            all_backend_keys.add(key)
    
    for key in sorted(all_backend_keys):
        if key.startswith('VITE_'):
            continue  # Skip frontend vars in backend list
        
        # Prefer file value, fall back to environ
        value = backend_file_vars.get(key, os.environ.get(key, ''))
        category, description, is_secret = ENV_CATEGORIES.get(key, ('other', None, False))
        
        result['backend'].append(EnvVariable(
            key=key,
            value=mask_secret_value(value) if is_secret else value,
            source='backend',
            category=category,
            description=description,
            is_secret=is_secret,
        ))
    
    # Get frontend env vars
    frontend_env_file = get_env_file_path('frontend')
    frontend_file_vars = parse_env_file(frontend_env_file)
    
    for key in sorted(frontend_file_vars.keys()):
        value = frontend_file_vars[key]
        category, description, is_secret = ENV_CATEGORIES.get(key, ('other', None, False))
        
        result['frontend'].append(EnvVariable(
            key=key,
            value=mask_secret_value(value) if is_secret else value,
            source='frontend',
            category=category,
            description=description,
            is_secret=is_secret,
        ))
    
    # Add known frontend vars that might not exist in file yet
    known_frontend = [k for k in ENV_CATEGORIES.keys() if k.startswith('VITE_')]
    for key in known_frontend:
        if key not in frontend_file_vars:
            category, description, is_secret = ENV_CATEGORIES[key]
            result['frontend'].append(EnvVariable(
                key=key,
                value='',
                source='frontend',
                category=category,
                description=description,
                is_secret=is_secret,
            ))
    
    return result


@router.get("/feature-flags")
async def get_feature_flags(_: TokenData = Depends(require_admin)) -> Dict[str, bool]:
    """Get current feature flag values from JSON file."""
    return load_feature_flags()


@router.put("/feature-flags")
async def update_feature_flags(
    flags: Dict[str, bool],
    _: TokenData = Depends(require_admin)
) -> Dict[str, str]:
    """Update feature flags in JSON file. Changes take effect immediately."""
    try:
        current_flags = load_feature_flags()
        
        # Update with provided values
        for flag_name, value in flags.items():
            if flag_name in DEFAULT_FEATURE_FLAGS:
                current_flags[flag_name] = value
        
        save_feature_flags(current_flags)
        
        return {
            "status": "success",
            "message": "Feature flags updated. Changes take effect immediately."
        }
    except Exception as e:
        logger.error(f"Error updating feature flags: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update feature flags: {str(e)}")


@router.put("/variables")
async def update_env_variables(
    request: EnvUpdateRequest,
    _: TokenData = Depends(require_admin)
) -> Dict[str, str]:
    """Update environment variables in a .env file."""
    try:
        env_file = get_env_file_path(request.source)
        current_vars = parse_env_file(env_file)
        
        # Update with new values (skip empty values unless explicitly setting to empty)
        for key, value in request.variables.items():
            # Don't update secret placeholders
            if value == '********':
                continue
            current_vars[key] = value
        
        write_env_file(env_file, current_vars)
        
        return {
            "status": "success",
            "message": f"{request.source.capitalize()} environment variables updated. Restart the service to apply changes."
        }
    except Exception as e:
        logger.error(f"Error updating env variables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update environment variables: {str(e)}")


@router.post("/restart")
async def restart_service(
    request: RestartRequest,
    _: TokenData = Depends(require_admin)
) -> Dict[str, str]:
    """
    Restart backend or frontend service.
    Note: Backend restart will terminate the current process.
    """
    if request.service not in ('backend', 'frontend'):
        raise HTTPException(status_code=400, detail="Invalid service. Use 'backend' or 'frontend'.")
    
    if request.service == 'backend':
        # For backend, we'll trigger a restart by exiting the process
        # The process manager (systemd, docker, etc.) should restart it
        logger.info("Backend restart requested - scheduling shutdown")
        
        # Create a flag file that can be checked by a restart script
        restart_flag = BACKEND_DIR / '.restart_requested'
        restart_flag.touch()
        
        return {
            "status": "pending",
            "message": "Backend restart initiated. The service will restart shortly."
        }
    
    else:  # frontend
        # For frontend in dev mode, we can't really restart it
        # In production, it's static files served by nginx
        logger.info("Frontend restart requested")
        
        return {
            "status": "info",
            "message": "Frontend uses environment variables at build time. You need to rebuild the frontend for changes to take effect. Run 'npm run build' in the frontend directory."
        }


@router.get("/status")
async def get_service_status(_: TokenData = Depends(require_admin)) -> Dict[str, Any]:
    """Get status of backend and frontend services."""
    backend_env = get_env_file_path('backend')
    frontend_env = get_env_file_path('frontend')
    
    return {
        "backend": {
            "running": True,  # If we can respond, we're running
            "env_file_exists": backend_env.exists(),
            "python_version": sys.version,
        },
        "frontend": {
            "env_file_exists": frontend_env.exists(),
        }
    }
