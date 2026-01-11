"""Admin management routes."""
import logging
import json
import os
import re
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from app.models import (
    User, UserCreate, UserUpdate, TokenData, SubscriptionStatus
)
from app.auth import require_admin
from app.database import db
from app.routes.auth_routes import hash_password
from app.paths import USERDATA_DIR, TEXT_PATTERNS_DIR

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.get("/users")
async def list_users(
    page: int = 1,
    limit: int = 50,
    _: TokenData = Depends(require_admin)
):
    offset = (page - 1) * limit
    users = db.list_users(limit=limit, offset=offset)
    total = db.count_users()
    return {
        "users": users,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, _: TokenData = Depends(require_admin)):
    if db.get_user_by_email(data.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    password_hash = None
    if data.password:
        password_hash = hash_password(data.password)
    user = User(email=data.email, name=data.name, role=data.role, password_hash=password_hash)
    db.save_user(user)
    return user


@router.get("/users/{user_id}")
async def get_user(user_id: str, _: TokenData = Depends(require_admin)):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}")
async def update_user(user_id: str, data: UserUpdate, _: TokenData = Depends(require_admin)):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.email is not None:
        user.email = data.email
    if data.name is not None:
        user.name = data.name
    if data.role is not None:
        user.role = data.role
    db.save_user(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, _: TokenData = Depends(require_admin)):
    if not db.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    db.delete_user(user_id)
    return {"status": "deleted"}


@router.put("/users/{user_id}/subscription")
async def update_subscription(
    user_id: str,
    tier: int = 0,  # 0 = off, 1 = on
    expires: datetime = None,
    _: TokenData = Depends(require_admin),
):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.subscription_tier = tier
    # Keep subscription_status for backward compatibility
    user.subscription_status = SubscriptionStatus.ACTIVE if tier > 0 else SubscriptionStatus.NONE
    user.subscription_expires = expires
    db.save_user(user)
    return user


# ========================================================================
# User Pattern Management Routes (for admin to add user patterns as suppliers)
# ========================================================================

class UserPatternInfo(BaseModel):
    """Information about a user-created pattern."""
    user_id: str
    user_email: str
    user_name: str
    subscription_tier: int
    pattern_id: str
    pattern_name: str
    supplier: Optional[str]
    bill_type: str
    field_count: int
    created_at: str
    filename: str


class CopyPatternRequest(BaseModel):
    """Request to copy a user pattern to admin folder."""
    user_id: str
    filename: str  # Original filename in user folder
    new_pattern_id: str  # New ID for admin pattern (used as filename)
    new_name: Optional[str] = None  # Optional new name


@router.get("/user-patterns")
async def list_user_patterns(_: TokenData = Depends(require_admin)) -> List[UserPatternInfo]:
    """
    List all text patterns created by users across all user folders.
    Ordered by subscription tier (active first), then by date in filename.
    """
    patterns = []
    
    # Iterate through all directories in userdata
    logger.info(f"Looking for user patterns in: {USERDATA_DIR}")
    if not USERDATA_DIR.exists():
        logger.warning(f"USERDATA_DIR does not exist: {USERDATA_DIR}")
        return []
    
    # List all directories
    all_dirs = list(USERDATA_DIR.iterdir())
    logger.info(f"Found {len(all_dirs)} items in userdata: {[d.name for d in all_dirs]}")
    
    for user_dir in all_dirs:
        # Skip admin folder and non-directories
        if not user_dir.is_dir() or user_dir.name == "admin":
            logger.debug(f"Skipping: {user_dir.name} (is_dir={user_dir.is_dir()})")
            continue
        
        user_id = user_dir.name
        logger.info(f"Scanning user directory: {user_id}")
        
        # Try to get user info from database
        user = db.get_user(user_id)
        user_email = user.email if user else "unknown"
        user_name = user.name if user else "Unknown User"
        subscription_tier = user.subscription_tier if user else 0
        
        # Look for ALL JSON files in user directory (no prefix filtering - user folder only has user patterns)
        files_in_dir = os.listdir(user_dir)
        logger.info(f"Files in {user_id}: {files_in_dir}")
        
        for filename in files_in_dir:
            if not filename.endswith('.json'):
                continue
            
            logger.info(f"Processing pattern file: {filename}")
            try:
                pattern_file = user_dir / filename
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    pattern = json.load(f)
                
                # Extract date from filename for sorting (text_YYYYMMDD_HHMMSS_name.json)
                date_match = re.search(r'text_(\d{8}_\d{6})', filename)
                created_at = pattern.get('created_at', '')
                if date_match and not created_at:
                    # Parse date from filename
                    date_str = date_match.group(1)
                    try:
                        dt = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                        created_at = dt.isoformat()
                    except ValueError:
                        pass
                
                patterns.append(UserPatternInfo(
                    user_id=user_id,
                    user_email=user_email,
                    user_name=user_name,
                    subscription_tier=subscription_tier,
                    pattern_id=pattern.get('id', filename[:-5]),
                    pattern_name=pattern.get('name', filename[:-5]),
                    supplier=pattern.get('supplier'),
                    bill_type=pattern.get('bill_type', 'utilities'),
                    field_count=len(pattern.get('field_patterns', [])),
                    created_at=created_at,
                    filename=filename,
                ))
            except Exception as e:
                logger.warning(f"Error loading pattern {filename} from {user_id}: {e}")
    
    # Sort: subscription_tier DESC (active users first), then created_at DESC (newest first)
    patterns.sort(key=lambda p: (-p.subscription_tier, p.created_at or ''), reverse=False)
    # Re-sort to get proper order: high tier first, then newest first within each tier
    patterns.sort(key=lambda p: (-p.subscription_tier, -(datetime.fromisoformat(p.created_at).timestamp() if p.created_at else 0)))
    
    logger.info(f"Returning {len(patterns)} user patterns")
    return patterns


@router.post("/copy-user-pattern")
async def copy_user_pattern_to_admin(
    request: CopyPatternRequest,
    _: TokenData = Depends(require_admin),
):
    """
    Copy a user pattern to the admin text_patterns folder.
    """
    # Validate the new pattern ID
    if not request.new_pattern_id or not request.new_pattern_id.strip():
        raise HTTPException(status_code=400, detail="New pattern ID is required")
    
    # Sanitize new pattern ID for use as filename
    safe_id = re.sub(r'[^\w\-.]', '_', request.new_pattern_id.strip())
    
    # Check if file already exists
    target_file = TEXT_PATTERNS_DIR / f"{safe_id}.json"
    if target_file.exists():
        raise HTTPException(
            status_code=409, 
            detail=f"Pattern with ID '{safe_id}' already exists. Please choose a different ID."
        )
    
    # Find and read the source pattern
    source_dir = USERDATA_DIR / request.user_id
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="User folder not found")
    
    source_file = source_dir / request.filename
    if not source_file.exists():
        raise HTTPException(status_code=404, detail="Pattern file not found")
    
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            pattern = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading pattern: {e}")
    
    # Update pattern with new ID and optionally new name
    pattern['id'] = safe_id
    if request.new_name:
        pattern['name'] = request.new_name
    pattern['updated_at'] = datetime.utcnow().isoformat()
    
    # Ensure admin patterns directory exists
    TEXT_PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save to admin folder
    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(pattern, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving pattern: {e}")
    
    logger.info(f"Copied user pattern {request.filename} from {request.user_id} to admin as {safe_id}")
    
    return {
        "status": "success",
        "pattern_id": safe_id,
        "message": f"Pattern copied successfully as '{safe_id}'"
    }
