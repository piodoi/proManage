"""Stripe subscription management routes."""
import os
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel
from typing import Optional

from app.models import TokenData
from app.auth import require_auth
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["stripe"])

# Stripe configuration from environment
STRIPE_SECRET_KEY = os.environ.get("STRIPE_PRIVATE_KEY", "")
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")  # Monthly price for 1 property

# Initialize Stripe
stripe = None
if STRIPE_SECRET_KEY:
    try:
        import stripe as stripe_module
        stripe_module.api_key = STRIPE_SECRET_KEY
        stripe = stripe_module
        logger.info("[Stripe] Stripe initialized successfully")
    except ImportError:
        logger.warning("[Stripe] stripe package not installed - run: pip install stripe")
else:
    logger.warning("[Stripe] STRIPE_PRIVATE_KEY not set - Stripe integration disabled")


class CheckoutRequest(BaseModel):
    quantity: int  # Number of property subscriptions to purchase
    success_url: str
    cancel_url: str


class PortalOrCheckoutRequest(BaseModel):
    return_url: str
    checkout_quantity: Optional[int] = 1  # Used if we need to create a new subscription


@router.get("/config")
async def get_stripe_config(current_user: TokenData = Depends(require_auth)):
    """Get Stripe public configuration for frontend."""
    return {
        "public_key": STRIPE_PUBLIC_KEY,
        "enabled": bool(stripe and STRIPE_SECRET_KEY and STRIPE_PRICE_ID),
        "price_id": STRIPE_PRICE_ID,
    }


@router.post("/create-checkout-session")
async def create_checkout_session(
    data: CheckoutRequest,
    current_user: TokenData = Depends(require_auth)
):
    """Create a Stripe Checkout session for subscription."""
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    
    if not STRIPE_PRICE_ID:
        raise HTTPException(status_code=503, detail="Stripe price not configured")
    
    if data.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Check if user already has a Stripe customer ID
        # We'll store this in a separate field or use metadata
        customer_id = None
        
        # Search for existing customer by email
        customers = stripe.Customer.list(email=user.email, limit=1)
        if customers.data:
            customer_id = customers.data[0].id
        else:
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={"user_id": user.id}
            )
            customer_id = customer.id
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": data.quantity,
            }],
            mode="subscription",
            success_url=data.success_url,
            cancel_url=data.cancel_url,
            metadata={
                "user_id": user.id,
                "quantity": str(data.quantity),
            },
            subscription_data={
                "metadata": {
                    "user_id": user.id,
                }
            }
        )
        
        logger.info(f"[Stripe] Created checkout session for user {user.id}, quantity: {data.quantity}")
        
        return {
            "session_id": session.id,
            "url": session.url,
        }
        
    except Exception as e:
        logger.error(f"[Stripe] Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


@router.post("/create-portal-session")
async def create_portal_session(
    data: PortalOrCheckoutRequest,
    current_user: TokenData = Depends(require_auth)
):
    """Create a Stripe Customer Portal session to manage subscription.
    If no subscription exists, creates a checkout session instead."""
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Find customer by email
        customers = stripe.Customer.list(email=user.email, limit=1)
        if not customers.data:
            # No customer found - create a checkout session instead
            if not STRIPE_PRICE_ID:
                raise HTTPException(status_code=503, detail="Stripe price not configured")
            
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={"user_id": user.id}
            )
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=["card"],
                line_items=[{
                    "price": STRIPE_PRICE_ID,
                    "quantity": data.checkout_quantity or 1,
                }],
                mode="subscription",
                success_url=data.return_url + "?subscription_success=true",
                cancel_url=data.return_url + "?subscription_cancelled=true",
                metadata={
                    "user_id": user.id,
                    "quantity": str(data.checkout_quantity or 1),
                },
                subscription_data={
                    "metadata": {
                        "user_id": user.id,
                    }
                }
            )
            
            logger.info(f"[Stripe] Created checkout session for new user {user.id}")
            return {
                "url": session.url,
                "type": "checkout",
            }
        
        customer_id = customers.data[0].id
        
        # Check if customer has any subscriptions
        subscriptions = stripe.Subscription.list(customer=customer_id, limit=1)
        if not subscriptions.data:
            # Customer exists but no subscription - create checkout session
            if not STRIPE_PRICE_ID:
                raise HTTPException(status_code=503, detail="Stripe price not configured")
            
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": STRIPE_PRICE_ID,
                    "quantity": data.checkout_quantity or 1,
                }],
                mode="subscription",
                success_url=data.return_url + "?subscription_success=true",
                cancel_url=data.return_url + "?subscription_cancelled=true",
                metadata={
                    "user_id": user.id,
                    "quantity": str(data.checkout_quantity or 1),
                },
                subscription_data={
                    "metadata": {
                        "user_id": user.id,
                    }
                }
            )
            
            logger.info(f"[Stripe] Created checkout session for existing customer {user.id}")
            return {
                "url": session.url,
                "type": "checkout",
            }
        
        # Create portal session
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=data.return_url,
        )
        
        logger.info(f"[Stripe] Created portal session for user {user.id}")
        
        return {
            "url": session.url,
            "type": "portal",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Stripe] Error creating portal session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")
):
    """Handle Stripe webhook events."""
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    
    payload = await request.body()
    
    try:
        if STRIPE_WEBHOOK_SECRET and stripe_signature:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        else:
            # For development without webhook signature verification
            import json
            event = json.loads(payload)
            logger.warning("[Stripe] Webhook signature not verified (development mode)")
        
        event_type = event.get("type") if isinstance(event, dict) else event.type
        event_data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
        
        logger.info(f"[Stripe] Received webhook event: {event_type}")
        
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(event_data)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event_data)
        elif event_type == "invoice.paid":
            await handle_invoice_paid(event_data)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(event_data)
        
        return {"status": "success"}
        
    except ValueError as e:
        logger.error(f"[Stripe] Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        logger.error(f"[Stripe] Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def handle_checkout_completed(session):
    """Handle successful checkout - activate subscription."""
    user_id = session.get("metadata", {}).get("user_id")
    quantity = int(session.get("metadata", {}).get("quantity", 1))
    
    if not user_id:
        logger.error("[Stripe] No user_id in checkout session metadata")
        return
    
    user = db.get_user(user_id)
    if not user:
        logger.error(f"[Stripe] User not found: {user_id}")
        return
    
    # Update subscription tier to the quantity purchased
    user.subscription_tier = quantity
    user.subscription_expires = None  # Managed by Stripe, no manual expiry
    db.save_user(user)
    
    logger.info(f"[Stripe] Activated subscription for user {user_id}, tier: {quantity}")


async def handle_subscription_updated(subscription):
    """Handle subscription updates (quantity changes, etc.)."""
    customer_id = subscription.get("customer")
    
    if not customer_id:
        return
    
    try:
        # Get customer to find user
        customer = stripe.Customer.retrieve(customer_id)
        user_id = customer.get("metadata", {}).get("user_id")
        
        if not user_id:
            # Try to find user by email
            user = db.get_user_by_email(customer.get("email"))
            if user:
                user_id = user.id
        
        if not user_id:
            logger.error(f"[Stripe] Could not find user for customer {customer_id}")
            return
        
        user = db.get_user(user_id)
        if not user:
            return
        
        # Get the quantity from subscription items
        items = subscription.get("items", {}).get("data", [])
        quantity = sum(item.get("quantity", 1) for item in items)
        
        # Check if subscription is active
        status = subscription.get("status")
        if status in ["active", "trialing"]:
            user.subscription_tier = quantity
            user.subscription_expires = None
        elif status in ["canceled", "unpaid", "past_due"]:
            user.subscription_tier = 0
            user.subscription_expires = datetime.utcnow()
        
        db.save_user(user)
        logger.info(f"[Stripe] Updated subscription for user {user_id}, tier: {user.subscription_tier}, status: {status}")
        
    except Exception as e:
        logger.error(f"[Stripe] Error handling subscription update: {e}")


async def handle_subscription_deleted(subscription):
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")
    
    if not customer_id:
        return
    
    try:
        customer = stripe.Customer.retrieve(customer_id)
        user_id = customer.get("metadata", {}).get("user_id")
        
        if not user_id:
            user = db.get_user_by_email(customer.get("email"))
            if user:
                user_id = user.id
        
        if not user_id:
            return
        
        user = db.get_user(user_id)
        if not user:
            return
        
        # Subscription canceled - revert to free tier
        user.subscription_tier = 0
        user.subscription_expires = datetime.utcnow()
        db.save_user(user)
        
        logger.info(f"[Stripe] Subscription canceled for user {user_id}")
        
    except Exception as e:
        logger.error(f"[Stripe] Error handling subscription deletion: {e}")


async def handle_invoice_paid(invoice):
    """Handle successful invoice payment - keep subscription active."""
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    
    if not customer_id or not subscription_id:
        return
    
    logger.info(f"[Stripe] Invoice paid for customer {customer_id}")
    # Subscription stays active, no action needed


async def handle_payment_failed(invoice):
    """Handle failed payment - log warning."""
    customer_id = invoice.get("customer")
    
    logger.warning(f"[Stripe] Payment failed for customer {customer_id}")
    # Stripe will handle retry logic and eventual subscription cancellation


@router.get("/subscription")
async def get_subscription_details(current_user: TokenData = Depends(require_auth)):
    """Get current user's Stripe subscription details."""
    if not stripe:
        return {
            "has_subscription": False,
            "stripe_enabled": False,
        }
    
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Find customer by email
        customers = stripe.Customer.list(email=user.email, limit=1)
        if not customers.data:
            return {
                "has_subscription": False,
                "stripe_enabled": True,
                "subscription_tier": user.subscription_tier,
            }
        
        customer_id = customers.data[0].id
        
        # Get active subscriptions
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status="active",
            limit=10
        )
        
        if not subscriptions.data:
            # Check for other statuses
            all_subs = stripe.Subscription.list(customer=customer_id, limit=10)
            if all_subs.data:
                sub = all_subs.data[0]
                return {
                    "has_subscription": False,
                    "stripe_enabled": True,
                    "subscription_tier": user.subscription_tier,
                    "subscription_status": sub.status,
                    "cancel_at_period_end": sub.cancel_at_period_end,
                }
            return {
                "has_subscription": False,
                "stripe_enabled": True,
                "subscription_tier": user.subscription_tier,
            }
        
        # Get subscription details
        sub = subscriptions.data[0]
        quantity = sum(item.quantity for item in sub["items"]["data"])
        
        return {
            "has_subscription": True,
            "stripe_enabled": True,
            "subscription_tier": user.subscription_tier,
            "subscription_id": sub.id,
            "status": sub.status,
            "quantity": quantity,
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }
        
    except Exception as e:
        logger.error(f"[Stripe] Error getting subscription details: {e}")
        return {
            "has_subscription": user.subscription_tier > 0,
            "stripe_enabled": True,
            "subscription_tier": user.subscription_tier,
            "error": str(e),
        }

