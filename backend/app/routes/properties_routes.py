"""Property management routes."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from app.models import (
    Property, PropertyCreate, PropertyUpdate, TokenData, UserRole, SubscriptionStatus
)
from app.auth import require_landlord
from app.database import db
from app.limits import check_can_add_property

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("")
async def list_properties(current_user: TokenData = Depends(require_landlord)):
    # User isolation: all users (including admins) only see their own properties
    return db.list_properties(landlord_id=current_user.user_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_property(data: PropertyCreate, current_user: TokenData = Depends(require_landlord)):
    existing_count = db.count_properties(current_user.user_id)
    
    # Check subscription limits for properties
    if current_user.role != UserRole.ADMIN:
        user = db.get_user(current_user.user_id)
        if user:
            can_add, message = check_can_add_property(user.subscription_tier, existing_count)
            if not can_add:
                raise HTTPException(status_code=403, detail=message)
    
    prop = Property(landlord_id=current_user.user_id, address=data.address, name=data.name)
    db.save_property(prop)
    return prop


@router.get("/{property_id}")
async def get_property(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return prop


@router.put("/{property_id}")
async def update_property(
    property_id: str, data: PropertyUpdate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only update their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if data.address is not None:
        prop.address = data.address
    if data.name is not None:
        prop.name = data.name
    db.save_property(prop)
    return prop


@router.delete("/{property_id}")
async def delete_property(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only delete their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete_property(property_id)
    return {"status": "deleted"}

