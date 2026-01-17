"""Subscription and utility routes."""
from fastapi import APIRouter, HTTPException, Depends
from app.models import TokenData
from app.auth import require_auth
from app.database import db
from app.limits import (
    get_user_limits,
    FREE_MAX_PROPERTIES,
    FREE_MAX_SUPPLIERS,
    FREE_MAX_RENTERS,
    FREE_EMAIL_SYNC,
    PAID_MAX_SUPPLIERS_PER_PROPERTY,
    PAID_MAX_RENTERS_PER_PROPERTY,
    PAID_EMAIL_SYNC,
)

router = APIRouter(tags=["subscription"])


@router.get("/subscription/status")
async def subscription_status(current_user: TokenData = Depends(require_auth)):
    """Get detailed subscription status including limits and usage."""
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    property_count = db.count_properties(current_user.user_id)
    
    # Count total suppliers and renters across all user's properties
    properties = db.list_properties(current_user.user_id)
    total_suppliers = 0
    total_renters = 0
    
    for prop in properties:
        # Count suppliers linked to this property
        property_suppliers = db.list_property_suppliers(prop.id)
        total_suppliers += len(property_suppliers)
        # Count renters for this property
        property_renters = db.list_renters(prop.id)
        total_renters += len(property_renters)
    
    # Get user limits based on subscription tier
    limits = get_user_limits(user.subscription_tier, property_count)
    
    # Determine if tier is free or paid
    is_free_tier = user.subscription_tier == 0
    
    return {
        "status": user.subscription_status,
        "expires": user.subscription_expires,
        "subscription_tier": user.subscription_tier,
        "is_free_tier": is_free_tier,
        
        # Current usage
        "property_count": property_count,
        "supplier_count": total_suppliers,
        "renter_count": total_renters,
        
        # Limits based on tier
        "limits": {
            "max_properties": limits["max_properties"],
            "max_suppliers": FREE_MAX_SUPPLIERS if is_free_tier else PAID_MAX_SUPPLIERS_PER_PROPERTY * user.subscription_tier,
            "max_suppliers_per_property": FREE_MAX_SUPPLIERS if is_free_tier else PAID_MAX_SUPPLIERS_PER_PROPERTY,
            "max_renters": FREE_MAX_RENTERS if is_free_tier else PAID_MAX_RENTERS_PER_PROPERTY * user.subscription_tier,
            "max_renters_per_property": FREE_MAX_RENTERS if is_free_tier else PAID_MAX_RENTERS_PER_PROPERTY,
            "email_sync_enabled": FREE_EMAIL_SYNC if is_free_tier else PAID_EMAIL_SYNC,
        },
        
        # Action permissions
        "can_add_property": limits.get("can_add_property", False),
        "can_add_supplier": total_suppliers < (FREE_MAX_SUPPLIERS if is_free_tier else PAID_MAX_SUPPLIERS_PER_PROPERTY * user.subscription_tier),
        "can_add_renter": total_renters < (FREE_MAX_RENTERS if is_free_tier else PAID_MAX_RENTERS_PER_PROPERTY * user.subscription_tier),
        "can_use_email_sync": not is_free_tier,
    }

