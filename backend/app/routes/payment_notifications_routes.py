"""Payment notification routes for landlords."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.models import PaymentNotificationStatus, PaymentNotificationUpdate, BillStatus
from app.database import db
from app.auth import get_current_user

router = APIRouter(prefix="/payment-notifications", tags=["payment-notifications"])


class NotificationActionRequest(BaseModel):
    """Request body for confirming/rejecting a payment notification"""
    landlord_note: Optional[str] = None


@router.get("/")
async def list_notifications(
    status: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Get all payment notifications for the current landlord.
    Optionally filter by status: 'pending', 'confirmed', 'rejected'
    """
    notifications = db.list_payment_notifications_by_landlord(current_user.user_id, status)
    
    # Enrich notifications with bill and renter info
    result = []
    for notification in notifications:
        bill = db.get_bill(notification.bill_id)
        renter = db.get_renter(notification.renter_id)
        prop = db.get_property(bill.property_id) if bill else None
        
        result.append({
            "notification": notification,
            "bill": {
                "id": bill.id,
                "description": bill.description,
                "amount": bill.amount,
                "currency": bill.currency,
                "due_date": bill.due_date,
                "status": bill.status,
                "bill_number": bill.bill_number
            } if bill else None,
            "renter": {
                "id": renter.id,
                "name": renter.name,
                "email": renter.email
            } if renter else None,
            "property": {
                "id": prop.id,
                "name": prop.name,
                "address": prop.address
            } if prop else None
        })
    
    return result


@router.get("/count")
async def get_notification_count(current_user = Depends(get_current_user)):
    """Get count of pending payment notifications for the current landlord."""
    count = db.get_pending_notification_count(current_user.user_id)
    return {"count": count}


@router.get("/{notification_id}")
async def get_notification(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific payment notification."""
    notification = db.get_payment_notification(notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    bill = db.get_bill(notification.bill_id)
    renter = db.get_renter(notification.renter_id)
    prop = db.get_property(bill.property_id) if bill else None
    
    return {
        "notification": notification,
        "bill": {
            "id": bill.id,
            "description": bill.description,
            "amount": bill.amount,
            "currency": bill.currency,
            "due_date": bill.due_date,
            "status": bill.status,
            "bill_number": bill.bill_number,
            "iban": bill.iban
        } if bill else None,
        "renter": {
            "id": renter.id,
            "name": renter.name,
            "email": renter.email,
            "phone": renter.phone
        } if renter else None,
        "property": {
            "id": prop.id,
            "name": prop.name,
            "address": prop.address
        } if prop else None
    }


@router.post("/{notification_id}/confirm")
async def confirm_notification(
    notification_id: str,
    data: NotificationActionRequest,
    current_user = Depends(get_current_user)
):
    """
    Confirm a payment notification.
    This marks the associated bill as paid.
    """
    notification = db.get_payment_notification(notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if notification.status != PaymentNotificationStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Notification is already {notification.status}"
        )
    
    # Update the notification status
    updates = {
        "status": PaymentNotificationStatus.CONFIRMED,
        "landlord_note": data.landlord_note,
        "confirmed_at": datetime.utcnow().isoformat()
    }
    
    updated_notification = db.update_payment_notification(notification_id, updates)
    
    # Mark the bill as paid
    bill = db.get_bill(notification.bill_id)
    if bill:
        bill.status = BillStatus.PAID
        db.save_bill(bill)
    
    return {
        "notification": updated_notification,
        "message": "Payment confirmed. Bill has been marked as paid.",
        "bill_status": BillStatus.PAID
    }


@router.post("/{notification_id}/reject")
async def reject_notification(
    notification_id: str,
    data: NotificationActionRequest,
    current_user = Depends(get_current_user)
):
    """
    Reject a payment notification.
    The bill status remains unchanged.
    """
    notification = db.get_payment_notification(notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if notification.status != PaymentNotificationStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Notification is already {notification.status}"
        )
    
    # Update the notification status
    updates = {
        "status": PaymentNotificationStatus.REJECTED,
        "landlord_note": data.landlord_note,
        "confirmed_at": datetime.utcnow().isoformat()
    }
    
    updated_notification = db.update_payment_notification(notification_id, updates)
    
    return {
        "notification": updated_notification,
        "message": "Payment notification rejected."
    }
