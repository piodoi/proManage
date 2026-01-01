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
    rent_warning_days: Optional[int] = None
    rent_currency: Optional[str] = None


@router.get("")
async def get_preferences(current_user: TokenData = Depends(require_auth)):
    """Get current user's preferences"""
    preferences = db.get_user_preferences(current_user.user_id)
    if not preferences:
        # Return default preferences if none exist
        return {
            "language": "en",
            "view_mode": "list",
            "rent_warning_days": 5,
            "rent_currency": "EUR"
        }
    return {
        "language": preferences.language or "en",
        "view_mode": preferences.view_mode or "list",
        "rent_warning_days": preferences.rent_warning_days if preferences.rent_warning_days is not None else 5,
        "rent_currency": preferences.rent_currency if preferences.rent_currency else "EUR"
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
        if data.rent_warning_days is not None:
            existing.rent_warning_days = data.rent_warning_days
        if data.rent_currency is not None:
            existing.rent_currency = data.rent_currency
        preferences = existing
    else:
        # Create new preferences
        preferences = UserPreferences(
            user_id=current_user.user_id,
            language=data.language or "en",
            view_mode=data.view_mode or "list",
            rent_warning_days=data.rent_warning_days if data.rent_warning_days is not None else 5,
            rent_currency=data.rent_currency if data.rent_currency else "EUR"
        )
    
    db.save_user_preferences(preferences)
    logger.info(f"[Preferences] Saved preferences for user {current_user.user_id}: language={preferences.language}, view_mode={preferences.view_mode}, rent_warning_days={preferences.rent_warning_days}, rent_currency={preferences.rent_currency}")
    
    return {
        "language": preferences.language,
        "view_mode": preferences.view_mode,
        "rent_warning_days": preferences.rent_warning_days if preferences.rent_warning_days is not None else 5,
        "rent_currency": preferences.rent_currency if preferences.rent_currency else "EUR"
    }

