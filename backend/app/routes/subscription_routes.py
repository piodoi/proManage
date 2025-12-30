"""Subscription and utility routes."""
from fastapi import APIRouter, HTTPException, Depends
from app.models import TokenData
from app.auth import require_auth
from app.database import db

router = APIRouter(tags=["subscription"])


@router.get("/subscription/status")
async def subscription_status(current_user: TokenData = Depends(require_auth)):
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    property_count = db.count_properties(current_user.user_id)
    needs_subscription = property_count >= 1
    return {
        "status": user.subscription_status,
        "expires": user.subscription_expires,
        "property_count": property_count,
        "needs_subscription": needs_subscription,
        "can_add_property": not needs_subscription or user.subscription_tier > 0,
    }

