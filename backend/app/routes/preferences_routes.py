import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.models import UserPreferences
from app.auth import require_auth, TokenData
from app.database import db

router = APIRouter(prefix="/preferences", tags=["preferences"])

logger = logging.getLogger(__name__)


class PreferencesUpdate(BaseModel):
    language: Optional[str] = None
    view_mode: Optional[str] = None


@router.get("")
async def get_preferences(current_user: TokenData = Depends(require_auth)):
    """Get current user's preferences"""
    preferences = db.get_user_preferences(current_user.user_id)
    if not preferences:
        # Return default preferences if none exist
        return {
            "language": "en",
            "view_mode": "list"
        }
    return {
        "language": preferences.language or "en",
        "view_mode": preferences.view_mode or "list"
    }


@router.post("")
async def save_preferences(
    data: PreferencesUpdate,
    current_user: TokenData = Depends(require_auth)
):
    """Save or update user preferences"""
    # Get existing preferences or create new
    existing = db.get_user_preferences(current_user.user_id)
    
    if existing:
        # Update existing preferences
        if data.language is not None:
            existing.language = data.language
        if data.view_mode is not None:
            existing.view_mode = data.view_mode
        preferences = existing
    else:
        # Create new preferences
        preferences = UserPreferences(
            user_id=current_user.user_id,
            language=data.language or "en",
            view_mode=data.view_mode or "list"
        )
    
    db.save_user_preferences(preferences)
    logger.info(f"[Preferences] Saved preferences for user {current_user.user_id}: language={preferences.language}, view_mode={preferences.view_mode}")
    
    return {
        "language": preferences.language,
        "view_mode": preferences.view_mode
    }

