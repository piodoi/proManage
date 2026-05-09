"""Payment notification routes for landlords."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.models import PaymentNotificationStatus, PaymentNotificationUpdate, BillStatus
from app.database import db
from app.auth import get_current_user
from app.utils.currency import get_exchange_rates, convert_currency
from app.utils.renter_payments import get_credit_currency, merge_credit_amount, round_money

router = APIRouter(prefix="/payment-notifications", tags=["payment-notifications"])


def _get_notification_amount_in_bill_currency(notification, exchange_rates: dict[str, float]) -> float:
    if notification.amount_in_bill_currency is not None and notification.bill_currency:
        return round_money(notification.amount_in_bill_currency)

    notification_currency = (notification.currency or "RON").upper()
    bill_currency = (notification.bill_currency or "RON").upper()
    return round_money(convert_currency(notification.amount, notification_currency, bill_currency, exchange_rates))


def _calculate_remaining_bill_amount(bill, notifications, exchange_rates: dict[str, float], exclude_notification_id: Optional[str] = None) -> float:
    if bill.status == BillStatus.PAID and not any(n.status == PaymentNotificationStatus.CONFIRMED for n in notifications):
        return 0.0

    confirmed_paid = 0.0
    for existing_notification in notifications:
        if existing_notification.id == exclude_notification_id:
            continue
        if existing_notification.status != PaymentNotificationStatus.CONFIRMED:
            continue
        confirmed_paid += _get_notification_amount_in_bill_currency(existing_notification, exchange_rates)

    return max(0.0, round_money(bill.amount - confirmed_paid))


def _get_bill_status_for_remaining(bill, remaining_amount: float) -> BillStatus:
    if remaining_amount <= 0:
        return BillStatus.PAID

    due_date = bill.due_date
    if isinstance(due_date, str):
        try:
            due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except ValueError:
            return BillStatus.PENDING
    elif not isinstance(due_date, datetime):
        due_date = datetime.combine(due_date, datetime.min.time())

    return BillStatus.OVERDUE if due_date.date() < datetime.utcnow().date() else BillStatus.PENDING


class NotificationActionRequest(BaseModel):
    """Request body for confirming/rejecting a payment notification"""
    landlord_note: Optional[str] = None


class ClearSelectedRequest(BaseModel):
    """Request body for clearing selected notifications"""
    notification_ids: List[str]


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
    
    bill = db.get_bill(notification.bill_id)
    renter = db.get_renter(notification.renter_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")

    exchange_rates = await get_exchange_rates()
    existing_notifications = db.list_payment_notifications_by_bill(notification.bill_id)
    remaining_before_confirmation = _calculate_remaining_bill_amount(
        bill,
        existing_notifications,
        exchange_rates,
        exclude_notification_id=notification.id,
    )
    notification_amount_in_bill_currency = _get_notification_amount_in_bill_currency(notification, exchange_rates)
    applied_to_bill = min(remaining_before_confirmation, notification_amount_in_bill_currency)
    extra_in_bill_currency = max(0.0, round_money(notification_amount_in_bill_currency - applied_to_bill))

    # Update the notification status
    updates = {
        "status": PaymentNotificationStatus.CONFIRMED,
        "landlord_note": data.landlord_note,
        "confirmed_at": datetime.utcnow().isoformat()
    }
    
    updated_notification = db.update_payment_notification(notification_id, updates)
    
    remaining_after_confirmation = max(0.0, round_money(remaining_before_confirmation - applied_to_bill))
    bill.status = _get_bill_status_for_remaining(bill, remaining_after_confirmation)
    db.save_bill(bill)

    credited_amount = 0.0
    credited_currency = None
    if extra_in_bill_currency > 0:
        notification_currency = (notification.currency or "RON").upper()
        notification_bill_currency = (notification.bill_currency or bill.currency or "RON").upper()
        if notification_amount_in_bill_currency > 0:
            credited_amount = round_money(notification.amount * (extra_in_bill_currency / notification_amount_in_bill_currency))
        else:
            credited_amount = round_money(convert_currency(extra_in_bill_currency, notification_bill_currency, notification_currency, exchange_rates))

        merged_credit, merged_currency = merge_credit_amount(
            round_money(getattr(renter, 'credit', 0.0)),
            get_credit_currency(renter),
            credited_amount,
            notification_currency,
            exchange_rates,
        )
        renter.credit = merged_credit
        renter.credit_currency = merged_currency
        db.save_renter(renter)
        credited_currency = merged_currency
    
    return {
        "notification": updated_notification,
        "message": "Payment confirmed.",
        "bill_status": bill.status,
        "credited_amount": credited_amount,
        "credited_currency": credited_currency,
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


@router.delete("/clear-all")
async def clear_all_notifications(
    status: Optional[str] = None,
    property_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Delete all payment notifications for the current landlord.
    Optionally filter by status: 'pending', 'confirmed', 'rejected', or 'all' for all notifications.
    Optionally filter by property_id to only delete notifications for a specific property.
    """
    deleted_count = db.delete_all_payment_notifications(current_user.user_id, status, property_id)
    
    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} notification(s)"
    }


@router.post("/clear-selected")
async def clear_selected_notifications(
    data: ClearSelectedRequest,
    current_user = Depends(get_current_user)
):
    """
    Delete specific payment notifications by their IDs.
    Only deletes notifications that belong to the current landlord.
    """
    deleted_count = 0
    for notification_id in data.notification_ids:
        notification = db.get_payment_notification(notification_id)
        if notification and notification.landlord_id == current_user.user_id:
            db.delete_payment_notification(notification_id)
            deleted_count += 1
    
    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} notification(s)"
    }
