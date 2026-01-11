"""Admin management routes."""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from app.models import (
    User, UserCreate, UserUpdate, TokenData, SubscriptionStatus
)
from app.auth import require_admin
from app.database import db
from app.routes.auth_routes import hash_password

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
