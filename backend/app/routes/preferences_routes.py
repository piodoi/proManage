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
    bill_currency: Optional[str] = None
    phone_number: Optional[str] = None
    landlord_name: Optional[str] = None
    personal_email: Optional[str] = None
    iban: Optional[str] = None


@router.get("")
async def get_preferences(current_user: TokenData = Depends(require_auth)):
    """Get current user's preferences"""
    preferences = db.get_user_preferences(current_user.user_id)
    
    # Auto-import personal_email from user email if not set
    if preferences and not preferences.personal_email:
        user = db.get_user(current_user.user_id)
        if user:
            preferences.personal_email = user.email
            db.save_user_preferences(preferences)
            logger.info(f"[Preferences] Auto-imported personal_email from user email for user {current_user.user_id}")
    elif not preferences:
        # Create preferences with auto-imported email
        user = db.get_user(current_user.user_id)
        if user:
            preferences = UserPreferences(
                user_id=current_user.user_id,
                language="en",
                view_mode="list",
                rent_warning_days=5,
                rent_currency="EUR",
                bill_currency="RON",
                personal_email=user.email
            )
            db.save_user_preferences(preferences)
            logger.info(f"[Preferences] Created preferences with auto-imported personal_email for user {current_user.user_id}")
    
    if not preferences:
        # Return default preferences if none exist (fallback)
        return {
            "language": "en",
            "view_mode": "list",
            "rent_warning_days": 5,
            "rent_currency": "EUR",
            "bill_currency": "RON",
            "phone_number": None,
            "landlord_name": None,
            "personal_email": None,
            "iban": None
        }
    return {
        "language": preferences.language or "en",
        "view_mode": preferences.view_mode or "list",
        "rent_warning_days": preferences.rent_warning_days if preferences.rent_warning_days is not None else 5,
        "rent_currency": preferences.rent_currency if preferences.rent_currency else "EUR",
        "bill_currency": preferences.bill_currency if preferences.bill_currency else "EUR",
        "phone_number": preferences.phone_number,
        "landlord_name": preferences.landlord_name,
        "personal_email": preferences.personal_email,
        "iban": preferences.iban
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
        if data.bill_currency is not None:
            existing.bill_currency = data.bill_currency
        if data.phone_number is not None:
            existing.phone_number = data.phone_number
        if data.landlord_name is not None:
            existing.landlord_name = data.landlord_name
        if data.personal_email is not None:
            existing.personal_email = data.personal_email
        if data.iban is not None:
            existing.iban = data.iban
        preferences = existing
    else:
        # Create new preferences
        preferences = UserPreferences(
            user_id=current_user.user_id,
            language=data.language or "en",
            view_mode=data.view_mode or "list",
            rent_warning_days=data.rent_warning_days if data.rent_warning_days is not None else 5,
            rent_currency=data.rent_currency if data.rent_currency else "EUR",
            bill_currency=data.bill_currency if data.bill_currency else "EUR",
            phone_number=data.phone_number,
            landlord_name=data.landlord_name,
            personal_email=data.personal_email,
            iban=data.iban
        )
    
    db.save_user_preferences(preferences)
    logger.info(f"[Preferences] Saved preferences for user {current_user.user_id}: language={preferences.language}, view_mode={preferences.view_mode}, rent_warning_days={preferences.rent_warning_days}, rent_currency={preferences.rent_currency}, bill_currency={preferences.bill_currency}, phone_number={'*' * 4 if preferences.phone_number else None}, landlord_name={preferences.landlord_name}, personal_email={'*' * 4 if preferences.personal_email else None}, iban={'*' * 4 if preferences.iban else None}")
    
    return {
        "language": preferences.language,
        "view_mode": preferences.view_mode,
        "rent_warning_days": preferences.rent_warning_days if preferences.rent_warning_days is not None else 5,
        "rent_currency": preferences.rent_currency if preferences.rent_currency else "EUR",
        "bill_currency": preferences.bill_currency if preferences.bill_currency else "EUR",
        "phone_number": preferences.phone_number,
        "landlord_name": preferences.landlord_name,
        "personal_email": preferences.personal_email,
        "iban": preferences.iban
    }

