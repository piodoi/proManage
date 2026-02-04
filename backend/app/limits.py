"""
App-wide subscription limits and tier definitions.
These constants define what users can do at each subscription tier.
"""

# ==================== TIER DEFINITIONS ====================
# subscription_tier in User model:
# 0 = Free tier
# 1+ = Number of properties subscribed (paid tier)

# ==================== FREE TIER LIMITS ====================
FREE_MAX_PROPERTIES = 1
FREE_MAX_SUPPLIERS = 5  # Max suppliers per property (not total)
FREE_MAX_RENTERS = 5    # Total renters across all properties
FREE_EMAIL_SYNC = False  # Email sync not available in free tier

# ==================== PAID TIER LIMITS (per property) ====================
PAID_MAX_SUPPLIERS_PER_PROPERTY = 10
PAID_MAX_RENTERS_PER_PROPERTY = 10
PAID_EMAIL_SYNC = True  # Email sync available in paid tier

# ==================== STRIPE CONFIGURATION ====================
# Product and price IDs should be set in environment variables
# STRIPE_PRICE_ID = monthly recurring price for 1 property subscription


def get_user_limits(subscription_tier: int, property_count: int = 0) -> dict:
    """
    Get the limits for a user based on their subscription tier.
    
    Args:
        subscription_tier: 0 for free, 1+ for number of paid properties
        property_count: Current number of properties the user has
    
    Returns:
        Dictionary with all applicable limits
    """
    if subscription_tier == 0:
        # Free tier
        return {
            "tier": "free",
            "max_properties": FREE_MAX_PROPERTIES,
            "max_suppliers_per_property": FREE_MAX_SUPPLIERS,  # Limit is per property
            "max_renters": FREE_MAX_RENTERS,
            "email_sync_enabled": FREE_EMAIL_SYNC,
            "can_add_property": property_count < FREE_MAX_PROPERTIES,
            "pattern_suppliers_enabled": False,  # Pattern-based suppliers require premium
        }
    else:
        # Paid tier - subscription_tier = number of properties paid for
        return {
            "tier": "paid",
            "max_properties": subscription_tier,
            "max_suppliers_per_property": PAID_MAX_SUPPLIERS_PER_PROPERTY,
            "max_renters_per_property": PAID_MAX_RENTERS_PER_PROPERTY,
            "email_sync_enabled": PAID_EMAIL_SYNC,
            "can_add_property": property_count < subscription_tier,
            "properties_paid": subscription_tier,
            "pattern_suppliers_enabled": True,  # Pattern-based suppliers available
        }


def check_can_add_property(subscription_tier: int, current_property_count: int) -> tuple[bool, str]:
    """Check if user can add another property."""
    if subscription_tier == 0:
        if current_property_count >= FREE_MAX_PROPERTIES:
            return False, f"Free tier allows only {FREE_MAX_PROPERTIES} property. Upgrade to add more."
        return True, ""
    else:
        if current_property_count >= subscription_tier:
            return False, f"You have {subscription_tier} property subscriptions. Add more subscriptions to add more properties."
        return True, ""


def check_can_add_supplier(subscription_tier: int, current_supplier_count: int, property_count: int = 1) -> tuple[bool, str]:
    """Check if user can add another supplier to a property. Limit is per property for both tiers."""
    if subscription_tier == 0:
        if current_supplier_count >= FREE_MAX_SUPPLIERS:
            return False, f"Free tier allows only {FREE_MAX_SUPPLIERS} suppliers per property. Upgrade to add more."
        return True, ""
    else:
        if current_supplier_count >= PAID_MAX_SUPPLIERS_PER_PROPERTY:
            return False, f"Maximum {PAID_MAX_SUPPLIERS_PER_PROPERTY} suppliers per property reached."
        return True, ""


def check_can_add_renter(subscription_tier: int, current_renter_count: int, property_id: str = None) -> tuple[bool, str]:
    """Check if user can add another renter."""
    if subscription_tier == 0:
        if current_renter_count >= FREE_MAX_RENTERS:
            return False, f"Free tier allows only {FREE_MAX_RENTERS} renters. Upgrade to add more."
        return True, ""
    else:
        if current_renter_count >= PAID_MAX_RENTERS_PER_PROPERTY:
            return False, f"Maximum {PAID_MAX_RENTERS_PER_PROPERTY} renters per property reached."
        return True, ""


def check_email_sync_allowed(subscription_tier: int) -> tuple[bool, str]:
    """Check if user can use email sync feature."""
    if subscription_tier == 0:
        return False, "Email sync is only available with a paid subscription. Upgrade to enable this feature."
    return True, ""

