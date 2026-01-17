"""Email processing routes."""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.models import Bill, BillType, TokenData, UserRole
from app.auth import require_landlord
from app.database import db
from app.email_scraper import extract_bill_info, match_address_to_property
from app.email_monitor import email_monitor
from app.limits import check_email_sync_allowed
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])


class MarkEmailsReadRequest(BaseModel):
    email_ids: List[str]  # List of email IDs to mark as read


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
    
    Requires paid subscription.
    """
    # Check subscription for email sync feature (admins bypass)
    if current_user.role != UserRole.ADMIN:
        user = db.get_user(current_user.user_id)
        if user:
            can_sync, message = check_email_sync_allowed(user.subscription_tier)
            if not can_sync:
                raise HTTPException(status_code=403, detail=message)
    
    if not email_monitor.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Email monitoring not configured. Set EMAIL_MONITOR_* environment variables."
        )
    
    # Process emails for the current user (discover only, don't create bills yet)
    result = email_monitor.process_email_bills(user_id=current_user.user_id, create_bills=False)
    
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


@router.post("/mark-read")
async def mark_emails_read(
    request: MarkEmailsReadRequest,
    current_user: TokenData = Depends(require_landlord)
):
    """
    Mark emails as read after user has processed them.
    
    Called when user closes the sync dialog, regardless of whether
    they imported bills or not.
    """
    if not email_monitor.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Email monitoring not configured."
        )
    
    try:
        for email_id in request.email_ids:
            email_monitor.mark_as_read(email_id)
        
        return {
            "status": "success",
            "message": f"Marked {len(request.email_ids)} emails as read",
            "email_ids": request.email_ids
        }
    except Exception as e:
        logger.error(f"[Email] Error marking emails as read: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to mark emails as read: {e}")


@router.post("/delete")
async def delete_emails(
    request: MarkEmailsReadRequest,
    current_user: TokenData = Depends(require_landlord)
):
    """
    Delete emails after user has processed them.
    
    Fire-and-forget: Returns immediately, deletion happens in background.
    Called when user closes the sync dialog.
    """
    if not email_monitor.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Email monitoring not configured."
        )
    
    # Schedule deletion as background task - don't wait for it
    import asyncio
    
    async def delete_in_background():
        """Delete emails in background thread (non-blocking)"""
        try:
            # Run blocking IMAP operations in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            for email_id in request.email_ids:
                await loop.run_in_executor(None, email_monitor.delete_email, email_id)
        except Exception as e:
            logger.error(f"[Email] Background deletion failed: {e}", exc_info=True)
    
    # Fire and forget - create task but don't await
    asyncio.create_task(delete_in_background())
    
    # Return immediately
    return {
        "status": "success",
        "message": f"Deletion scheduled for {len(request.email_ids)} emails",
        "email_ids": request.email_ids
    }

