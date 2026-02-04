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
    
    # Count suppliers and renters across all user's properties
    # Track both totals and max on any single property
    properties = db.list_properties(current_user.user_id)
    total_suppliers = 0
    total_renters = 0
    max_suppliers_on_property = 0  # Max suppliers on any single property
    max_renters_on_property = 0    # Max renters on any single property
    
    for prop in properties:
        # Count suppliers linked to this property
        property_suppliers = db.list_property_suppliers(prop.id)
        supplier_count = len(property_suppliers)
        total_suppliers += supplier_count
        max_suppliers_on_property = max(max_suppliers_on_property, supplier_count)
        
        # Count renters for this property
        property_renters = db.list_renters(prop.id)
        renter_count = len(property_renters)
        total_renters += renter_count
        max_renters_on_property = max(max_renters_on_property, renter_count)
    
    # Get user limits based on subscription tier
    limits = get_user_limits(user.subscription_tier, property_count)
    
    # Determine if tier is free or paid
    is_free_tier = user.subscription_tier == 0
    
    # Supplier limit is now per property for both tiers
    # Check max suppliers on any single property
    if is_free_tier:
        can_add_supplier = max_suppliers_on_property < FREE_MAX_SUPPLIERS
        supplier_limit = FREE_MAX_SUPPLIERS
        can_add_pattern_supplier = False  # Pattern suppliers are premium only
    else:
        can_add_supplier = max_suppliers_on_property < PAID_MAX_SUPPLIERS_PER_PROPERTY
        supplier_limit = PAID_MAX_SUPPLIERS_PER_PROPERTY
        can_add_pattern_supplier = True  # Pattern suppliers available for paid users
    
    # Renter limit: FREE checks total, PAID checks per property
    if is_free_tier:
        can_add_renter = total_renters < FREE_MAX_RENTERS
        renter_limit = FREE_MAX_RENTERS
    else:
        can_add_renter = max_renters_on_property < PAID_MAX_RENTERS_PER_PROPERTY
        renter_limit = PAID_MAX_RENTERS_PER_PROPERTY
    
    # Property limit: can add if current count < subscription_tier (or FREE_MAX_PROPERTIES)
    can_add_property = property_count < (FREE_MAX_PROPERTIES if is_free_tier else user.subscription_tier)
    
    return {
        "status": user.subscription_status,
        "expires": user.subscription_expires,
        "subscription_tier": user.subscription_tier,
        "is_free_tier": is_free_tier,
        
        # Current usage
        "property_count": property_count,
        "supplier_count": total_suppliers,
        "renter_count": total_renters,
        "max_suppliers_on_property": max_suppliers_on_property,
        "max_renters_on_property": max_renters_on_property,
        
        # Limits based on tier
        "limits": {
            "max_properties": FREE_MAX_PROPERTIES if is_free_tier else user.subscription_tier,
            "max_suppliers": supplier_limit,
            "max_suppliers_per_property": supplier_limit,
            "max_renters": renter_limit,
            "max_renters_per_property": renter_limit,
            "email_sync_enabled": FREE_EMAIL_SYNC if is_free_tier else PAID_EMAIL_SYNC,
        },
        
        # Action permissions
        "can_add_property": can_add_property,
        "can_add_supplier": can_add_supplier,
        "can_add_renter": can_add_renter,
        "can_use_email_sync": not is_free_tier,
        "can_add_pattern_supplier": can_add_pattern_supplier,  # Pattern-based suppliers require premium
    }

