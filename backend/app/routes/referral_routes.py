"""Referral system routes for ProManage."""
import os
import logging
import secrets
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List

from app.models import TokenData, ReferralReward
from app.auth import require_auth
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/referrals", tags=["referrals"])

# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get("STRIPE_PRIVATE_KEY", "")
stripe = None
if STRIPE_SECRET_KEY:
    try:
        import stripe as stripe_module
        stripe_module.api_key = STRIPE_SECRET_KEY
        stripe = stripe_module
    except ImportError:
        logger.warning("[Referral] stripe package not installed")


class ReferralLinkResponse(BaseModel):
    referral_code: str
    referral_link: str
    total_referrals: int
    pending_rewards: int
    applied_rewards: int


class ReferralStatsResponse(BaseModel):
    total_referrals: int
    pending_subscriptions: int  # Signed up but not subscribed
    pending_rewards: int  # Subscribed but reward not applied
    applied_rewards: int  # Rewards already given
    referrals: List[dict]


def generate_referral_code(length: int = 8) -> str:
    """Generate a unique referral code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


@router.get("/link", response_model=ReferralLinkResponse)
async def get_referral_link(
    current_user: TokenData = Depends(require_auth),
    frontend_url: str = Query(None, description="Frontend base URL for link generation")
):
    """Get or create user's referral link."""
    try:
        user = db.get_user_by_id(current_user.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate referral code if user doesn't have one
        if not user.referral_code:
            # Generate unique code
            while True:
                code = generate_referral_code()
                # Check if code already exists
                existing = db.execute(
                    "SELECT id FROM users WHERE referral_code = ?",
                    (code,)
                ).fetchone()
                if not existing:
                    break
            
            # Update user with new code
            db.execute(
                "UPDATE users SET referral_code = ? WHERE id = ?",
                (code, user.id)
            )
            db.commit()
            user.referral_code = code
        
        # Get referral stats
        stats = db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN subscription_date IS NULL THEN 1 ELSE 0 END) as pending_sub,
                SUM(CASE WHEN subscription_date IS NOT NULL AND reward_applied = 0 THEN 1 ELSE 0 END) as pending_reward,
                SUM(CASE WHEN reward_applied = 1 THEN 1 ELSE 0 END) as applied
            FROM referral_rewards
            WHERE referrer_id = ?
        """, (user.id,)).fetchone()
        
        total = stats['total'] if stats else 0
        pending_rewards = stats['pending_reward'] if stats else 0
        applied_rewards = stats['applied'] if stats else 0
        
        # Build referral link
        base_url = frontend_url or os.environ.get("FRONTEND_URL", "http://localhost:5173")
        referral_link = f"{base_url}/login?ref={user.referral_code}"
        
        return ReferralLinkResponse(
            referral_code=user.referral_code,
            referral_link=referral_link,
            total_referrals=total,
            pending_rewards=pending_rewards,
            applied_rewards=applied_rewards
        )
    
    except Exception as e:
        logger.error(f"[Referral] Error getting referral link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(current_user: TokenData = Depends(require_auth)):
    """Get detailed referral statistics for the current user."""
    try:
        # Get all referrals
        referrals = db.execute("""
            SELECT 
                rr.*,
                u.name as referred_user_name,
                u.email as referred_user_email,
                u.subscription_tier
            FROM referral_rewards rr
            JOIN users u ON u.id = rr.referred_user_id
            WHERE rr.referrer_id = ?
            ORDER BY rr.signup_date DESC
        """, (current_user.user_id,)).fetchall()
        
        referral_list = []
        pending_subs = 0
        pending_rewards = 0
        applied_rewards = 0
        
        for ref in referrals:
            referral_list.append({
                'id': ref['id'],
                'user_name': ref['referred_user_name'],
                'user_email': ref['referred_user_email'],
                'signup_date': ref['signup_date'],
                'subscription_date': ref['subscription_date'],
                'has_subscription': ref['subscription_tier'] > 0,
                'reward_applied': bool(ref['reward_applied']),
                'reward_applied_date': ref['reward_applied_date']
            })
            
            if not ref['subscription_date']:
                pending_subs += 1
            elif ref['subscription_date'] and not ref['reward_applied']:
                pending_rewards += 1
            elif ref['reward_applied']:
                applied_rewards += 1
        
        return ReferralStatsResponse(
            total_referrals=len(referral_list),
            pending_subscriptions=pending_subs,
            pending_rewards=pending_rewards,
            applied_rewards=applied_rewards,
            referrals=referral_list
        )
    
    except Exception as e:
        logger.error(f"[Referral] Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def apply_referral_reward(referrer_id: str, referred_user_id: str):
    """
    Apply referral reward - extend subscription by 1 month for referrer.
    Called when a referred user successfully subscribes.
    """
    if not stripe:
        logger.warning("[Referral] Stripe not configured, cannot apply reward")
        return False
    
    try:
        # Get referrer
        referrer = db.get_user_by_id(referrer_id)
        if not referrer or referrer.subscription_tier == 0:
            logger.warning(f"[Referral] Referrer {referrer_id} not found or not subscribed")
            return False
        
        # Get Stripe customer ID
        customer_id = db.execute(
            "SELECT stripe_customer_id FROM users WHERE id = ?",
            (referrer_id,)
        ).fetchone()
        
        if not customer_id or not customer_id['stripe_customer_id']:
            logger.warning(f"[Referral] No Stripe customer ID for referrer {referrer_id}")
            return False
        
        # Get active subscription
        subscriptions = stripe.Subscription.list(
            customer=customer_id['stripe_customer_id'],
            status='active',
            limit=1
        )
        
        if not subscriptions.data:
            logger.warning(f"[Referral] No active subscription for referrer {referrer_id}")
            return False
        
        subscription = subscriptions.data[0]
        
        # Calculate new trial_end (current period end + 30 days)
        current_period_end = subscription.current_period_end
        new_trial_end = current_period_end + (30 * 24 * 60 * 60)  # Add 30 days in seconds
        
        # Update subscription to skip next billing
        stripe.Subscription.modify(
            subscription.id,
            trial_end=new_trial_end,
            proration_behavior='none'
        )
        
        logger.info(f"[Referral] Extended subscription for {referrer_id} by 30 days")
        
        # Mark reward as applied
        db.execute("""
            UPDATE referral_rewards 
            SET reward_applied = 1, reward_applied_date = ?
            WHERE referrer_id = ? AND referred_user_id = ?
        """, (datetime.utcnow(), referrer_id, referred_user_id))
        
        db.execute(
            "UPDATE users SET referral_reward_applied = 1 WHERE id = ?",
            (referred_user_id,)
        )
        db.commit()
        
        return True
    
    except Exception as e:
        logger.error(f"[Referral] Error applying reward: {e}")
        return False


# This function should be called from stripe_routes when a user subscribes
def check_and_apply_referral_reward(user_id: str):
    """
    Check if user was referred and apply reward to referrer if applicable.
    Call this when a user successfully subscribes.
    """
    try:
        user = db.get_user_by_id(user_id)
        if not user or not user.referred_by:
            return
        
        # Check if reward already applied
        if user.referral_reward_applied:
            logger.info(f"[Referral] Reward already applied for {user_id}")
            return
        
        # Record subscription date
        db.execute("""
            UPDATE referral_rewards 
            SET subscription_date = ?
            WHERE referred_user_id = ? AND subscription_date IS NULL
        """, (datetime.utcnow(), user_id))
        db.commit()
        
        # Apply reward to referrer
        logger.info(f"[Referral] Applying reward for referrer of {user_id}")
        apply_referral_reward(user.referred_by, user_id)
        
    except Exception as e:
        logger.error(f"[Referral] Error checking referral reward: {e}")
