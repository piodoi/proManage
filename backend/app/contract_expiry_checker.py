"""
Contract Expiry Checker - Cron job to notify landlords about expiring contracts

This module checks for renters whose contracts are about to expire and:
- For admin users: sends email notifications
- For other users: creates payment notifications (using the existing notification system)

The check uses the user's rent_warning_days preference as the number of days before
contract expiry to send notifications.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import asyncio

from app.database import db
from app.models import (
    User, Property, Renter, PaymentNotification, PaymentNotificationStatus,
    UserPreferences, UserRole, gen_id
)
from app.email_sender import send_email, is_email_configured

logger = logging.getLogger(__name__)

# Track which notifications have been sent to avoid duplicates
# Key: f"{renter_id}_{year}_{month}" to track per-month notifications
_sent_notifications: set = set()


async def send_contract_expiry_email(
    to_email: str,
    landlord_name: str,
    renter_name: str,
    property_name: str,
    property_address: str,
    expiry_date: date,
    days_until_expiry: int
) -> bool:
    """Send email notification about expiring contract to admin."""
    subject = f"Contract Expiring: {renter_name} at {property_name}"
    
    expiry_str = expiry_date.strftime("%B %d, %Y")
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .alert {{ 
                background-color: #fef3c7; 
                border: 1px solid #f59e0b; 
                border-radius: 6px;
                padding: 15px;
                margin: 20px 0;
            }}
            .details {{ 
                background-color: #f3f4f6; 
                border-radius: 6px;
                padding: 15px;
                margin: 20px 0;
            }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Contract Expiry Notice</h2>
            <div class="alert">
                <strong>⚠️ Contract expiring in {days_until_expiry} day(s)</strong>
            </div>
            <div class="details">
                <p><strong>Renter:</strong> {renter_name}</p>
                <p><strong>Property:</strong> {property_name}</p>
                <p><strong>Address:</strong> {property_address}</p>
                <p><strong>Contract Expires:</strong> {expiry_str}</p>
            </div>
            <p>Please take action to renew or terminate the contract as needed.</p>
            <div class="footer">
                <p>ProManage - Property & Rent Management</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Contract Expiry Notice

⚠️ Contract expiring in {days_until_expiry} day(s)

Renter: {renter_name}
Property: {property_name}
Address: {property_address}
Contract Expires: {expiry_str}

Please take action to renew or terminate the contract as needed.

ProManage - Property & Rent Management
    """
    
    return await send_email(to_email, subject, html_body, text_body)


def create_contract_expiry_notification(
    landlord_id: str,
    renter: Renter,
    property_obj: Property,
    expiry_date: date,
    days_until_expiry: int
) -> PaymentNotification:
    """Create a payment notification for contract expiry (for non-admin users)."""
    # Use renter_note for the expiry message
    renter_note = f"Contract expires on {expiry_date.strftime('%Y-%m-%d')} ({days_until_expiry} days)"
    
    notification = PaymentNotification(
        id=gen_id(),
        bill_id="",  # No bill associated - empty string for contract expiry
        renter_id=renter.id,
        landlord_id=landlord_id,
        amount=0,  # No amount for contract expiry
        currency="EUR",
        status=PaymentNotificationStatus.PENDING,
        renter_note=renter_note,
        landlord_note=property_obj.address,  # Just the address since property name is shown in the Property column
        created_at=datetime.utcnow()
    )
    
    return db.save_payment_notification(notification)


def get_expiring_contracts(warning_days: int = 5) -> List[Dict[str, Any]]:
    """
    Find all renters with contracts expiring within the warning period.
    
    Returns a list of dicts with:
    - renter: Renter object
    - property: Property object
    - landlord: User object
    - expiry_date: date
    - days_until_expiry: int
    - preferences: UserPreferences
    """
    today = date.today()
    results = []
    
    # Get all renters with start_contract_date set
    all_renters = db.list_renters()
    
    for renter in all_renters:
        if not renter.start_contract_date:
            continue
        
        # Calculate contract expiry (1 year from start)
        # Note: This assumes 1-year contracts. Adjust if needed.
        start_date = renter.start_contract_date
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        
        # Calculate next expiry date (could be multiple years)
        expiry_date = start_date
        while expiry_date <= today:
            expiry_date = date(expiry_date.year + 1, expiry_date.month, expiry_date.day)
        
        days_until_expiry = (expiry_date - today).days
        
        # Get property and landlord
        property_obj = db.get_property(renter.property_id)
        if not property_obj:
            continue
        
        landlord = db.get_user(property_obj.landlord_id)
        if not landlord:
            continue
        
        # Get landlord preferences for warning days
        preferences = db.get_user_preferences(landlord.id)
        user_warning_days = (preferences.rent_warning_days if preferences and preferences.rent_warning_days else 5)
        
        # Check if within warning period
        if days_until_expiry <= user_warning_days:
            results.append({
                'renter': renter,
                'property': property_obj,
                'landlord': landlord,
                'expiry_date': expiry_date,
                'days_until_expiry': days_until_expiry,
                'preferences': preferences
            })
    
    return results


async def check_and_notify_expiring_contracts() -> Dict[str, int]:
    """
    Main function to check for expiring contracts and send notifications.
    
    Returns a dict with counts:
    - emails_sent: number of emails sent to admins
    - notifications_created: number of notifications created for non-admins
    - skipped: number of already-notified contracts
    """
    global _sent_notifications
    
    logger.info("[ContractExpiry] Starting contract expiry check...")
    
    emails_sent = 0
    notifications_created = 0
    skipped = 0
    
    expiring = get_expiring_contracts()
    logger.info(f"[ContractExpiry] Found {len(expiring)} expiring contracts")
    
    # Process in batches to avoid overwhelming the system
    batch_size = 10
    delay_between_batches = 1.0  # seconds
    
    for i, item in enumerate(expiring):
        renter = item['renter']
        property_obj = item['property']
        landlord = item['landlord']
        expiry_date = item['expiry_date']
        days_until_expiry = item['days_until_expiry']
        preferences = item['preferences']
        
        # Create unique key for this notification
        notification_key = f"{renter.id}_{expiry_date.year}_{expiry_date.month}"
        
        if notification_key in _sent_notifications:
            skipped += 1
            continue
        
        try:
            if landlord.role == UserRole.ADMIN:
                # Send email to admin
                if is_email_configured():
                    email = preferences.personal_email if preferences and preferences.personal_email else landlord.email
                    landlord_name = preferences.landlord_name if preferences and preferences.landlord_name else landlord.name
                    
                    create_contract_expiry_notification(
                        landlord_id=landlord.id,
                        renter=renter,
                        property_obj=property_obj,
                        expiry_date=expiry_date,
                        days_until_expiry=days_until_expiry
                    )                    

                    success = await send_contract_expiry_email(
                        to_email=email,
                        landlord_name=landlord_name,
                        renter_name=renter.name,
                        property_name=property_obj.name,
                        property_address=property_obj.address,
                        expiry_date=expiry_date,
                        days_until_expiry=days_until_expiry
                    )
                    
                    if success:
                        emails_sent += 1
                        _sent_notifications.add(notification_key)
                        logger.info(f"[ContractExpiry] Email sent to {email} for {renter.name}")
                else:
                    logger.warning("[ContractExpiry] Email not configured, skipping admin notification")
            else:
                # Create payment notification for non-admin
                create_contract_expiry_notification(
                    landlord_id=landlord.id,
                    renter=renter,
                    property_obj=property_obj,
                    expiry_date=expiry_date,
                    days_until_expiry=days_until_expiry
                )
                notifications_created += 1
                _sent_notifications.add(notification_key)
                logger.info(f"[ContractExpiry] Notification created for {landlord.email} about {renter.name}")
            
            # Add delay between batches
            if (i + 1) % batch_size == 0:
                await asyncio.sleep(delay_between_batches)
                
        except Exception as e:
            logger.error(f"[ContractExpiry] Error processing {renter.name}: {e}")
    
    logger.info(f"[ContractExpiry] Complete: {emails_sent} emails, {notifications_created} notifications, {skipped} skipped")
    
    return {
        'emails_sent': emails_sent,
        'notifications_created': notifications_created,
        'skipped': skipped
    }


def run_contract_expiry_check():
    """Synchronous wrapper for the async check function."""
    return asyncio.run(check_and_notify_expiring_contracts())
