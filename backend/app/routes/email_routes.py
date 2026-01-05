"""Email processing routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.models import Bill, BillType, TokenData
from app.auth import require_landlord
from app.database import db
from app.email_scraper import extract_bill_info, match_address_to_property
from app.email_monitor import email_monitor

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/process")
async def process_email(
    subject: str, body: str, sender: str, current_user: TokenData = Depends(require_landlord)
):
    info = extract_bill_info(body, subject)
    landlord_properties = db.list_properties(landlord_id=current_user.user_id)
    property_id = match_address_to_property(info.address, landlord_properties)
    if not property_id:
        return {"status": "no_match", "extracted": info, "message": "Could not match to property"}
    # Create bill for the property (applies to all renters)
    bill = Bill(
        property_id=property_id,
        renter_id=None,  # Applies to all renters in the property
        bill_type=BillType.UTILITIES,
        description=f"Bill from {sender}: {subject}",
        amount=info.amount or 0,
        due_date=datetime.utcnow(),
        iban=info.iban,
        bill_number=info.bill_number,
    )
    db.save_bill(bill)
    return {"status": "created", "bill": bill, "extracted": info}


@router.post("/sync")
async def sync_email_bills(current_user: TokenData = Depends(require_landlord)):
    """
    Sync bills from email inbox.
    
    Fetches unread emails sent to proManage.bill+{user_id}@gmail.com,
    extracts PDF attachments, matches them against text patterns,
    and creates bills automatically.
    """
    if not email_monitor.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Email monitoring not configured. Set EMAIL_MONITOR_* environment variables."
        )
    
    # Process emails for the current user
    result = email_monitor.process_email_bills(user_id=current_user.user_id)
    
    return result


@router.post("/sync-all")
async def sync_all_email_bills(current_user: TokenData = Depends(require_landlord)):
    """
    Sync bills from email inbox for all users.
    
    Admin endpoint - processes unread emails for all users.
    """
    from app.models import UserRole
    
    # Only admins can sync all
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not email_monitor.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Email monitoring not configured. Set EMAIL_MONITOR_* environment variables."
        )
    
    # Process all emails (no user filter)
    result = email_monitor.process_email_bills(user_id=None)
    
    return result

