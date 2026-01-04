"""Public renter routes (token-based access)."""
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.models import Payment, PaymentCreate, PaymentMethod, PaymentStatus, BillStatus, TokenData, Bill
from app.database import db
from app.utils.currency import get_exchange_rates, convert_currency

router = APIRouter(prefix="/renter", tags=["renter-public"])

PAYMENT_SERVICE_COMMISSION = float(os.getenv("PAYMENT_SERVICE_COMMISSION", "0.02"))


def calculate_bill_status(bill: Bill) -> Bill:
    """Calculate and update bill status based on due date. Returns bill with updated status."""
    # Only update status if bill is not paid
    if bill.status != BillStatus.PAID:
        now = datetime.utcnow()
        # Compare dates (ignore time component for due date comparison)
        # Convert both to date objects for comparison
        if isinstance(bill.due_date, datetime):
            due_date_only = bill.due_date.date()
        else:
            # If it's already a date string or date object, handle accordingly
            due_date_only = bill.due_date
        
        now_date_only = now.date()
        
        if due_date_only < now_date_only:
            # Due date has passed, mark as overdue
            if bill.status != BillStatus.OVERDUE:
                bill.status = BillStatus.OVERDUE
                # Save the updated status to database
                db.save_bill(bill)
        elif due_date_only >= now_date_only and bill.status == BillStatus.OVERDUE:
            # Due date is in the future, but status is overdue (shouldn't happen, but fix it)
            bill.status = BillStatus.PENDING
            db.save_bill(bill)
    return bill


@router.get("/{token}")
async def renter_info(token: str):
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    prop = db.get_property(renter.property_id)
    return {
        "renter": {"id": renter.id, "name": renter.name},
        "property": {"id": prop.id, "name": prop.name, "address": prop.address} if prop else None,
    }


@router.get("/{token}/bills")
async def renter_bills(token: str):
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    all_bills = db.list_bills(property_id=renter.property_id)
    bills = [b for b in all_bills if b.renter_id is None or b.renter_id == renter.id]
    
    bill_ids = [bill.id for bill in bills]
    all_payments = db.list_payments_for_bills(bill_ids)
    payments_by_bill = {}
    for payment in all_payments:
        if payment.bill_id not in payments_by_bill:
            payments_by_bill[payment.bill_id] = []
        payments_by_bill[payment.bill_id].append(payment)
    
    result = []
    for bill in bills:
        bill = calculate_bill_status(bill)
        payments = payments_by_bill.get(bill.id, [])
        paid_amount = sum(p.amount for p in payments if p.status == PaymentStatus.COMPLETED)
        result.append({
            "bill": bill,
            "paid_amount": paid_amount,
            "remaining": bill.amount - paid_amount,
        })
    
    return result


@router.get("/{token}/balance")
async def renter_balance(token: str):
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    prop = db.get_property(renter.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    preferences = db.get_user_preferences(prop.landlord_id)
    bill_currency = preferences.bill_currency if preferences and preferences.bill_currency else "RON"
    
    exchange_rates = await get_exchange_rates()
    
    all_bills = db.list_bills(property_id=renter.property_id)
    bills = [b for b in all_bills if b.renter_id is None or b.renter_id == renter.id]
    
    bill_ids = [bill.id for bill in bills]
    all_payments = db.list_payments_for_bills(bill_ids)
    payments_by_bill = {}
    for payment in all_payments:
        if payment.bill_id not in payments_by_bill:
            payments_by_bill[payment.bill_id] = []
        payments_by_bill[payment.bill_id].append(payment)
    
    total_due_original = 0.0
    total_paid_original = 0.0
    
    for bill in bills:
        if bill.status != BillStatus.PAID:
            bill_currency_original = bill.currency if bill.currency else "RON"
            total_due_original += convert_currency(bill.amount, bill_currency_original, bill_currency, exchange_rates)
        
        bill_payments = payments_by_bill.get(bill.id, [])
        for payment in bill_payments:
            if payment.status == PaymentStatus.COMPLETED:
                payment_currency_original = bill.currency if bill.currency else "RON"
                total_paid_original += convert_currency(payment.amount, payment_currency_original, bill_currency, exchange_rates)
    
    balance_original = total_due_original - total_paid_original
    
    response = {
        "total_due": total_due_original,
        "total_paid": total_paid_original,
        "balance": balance_original,
        "currency": bill_currency,
        "exchange_rates": exchange_rates,
    }
    
    if bill_currency == "EUR":
        response["total_due_ron"] = convert_currency(total_due_original, "EUR", "RON", exchange_rates)
        response["total_paid_ron"] = convert_currency(total_paid_original, "EUR", "RON", exchange_rates)
        response["balance_ron"] = convert_currency(balance_original, "EUR", "RON", exchange_rates)
        response["eur_to_ron_rate"] = exchange_rates.get("RON", 4.97)
    
    return response


@router.post("/{token}/pay")
async def renter_pay(token: str, data: PaymentCreate):
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    bill = db.get_bill(data.bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if bill.property_id != renter.property_id:
        raise HTTPException(status_code=403, detail="Bill does not belong to this renter's property")
    commission = 0.0
    if data.method == PaymentMethod.PAYMENT_SERVICE:
        commission = data.amount * PAYMENT_SERVICE_COMMISSION
    payment = Payment(
        bill_id=data.bill_id,
        amount=data.amount,
        method=data.method,
        commission=commission,
    )
    db.save_payment(payment)
    existing_payments = db.list_payments(bill_id=bill.id)
    total_paid = sum(p.amount for p in existing_payments if p.status == PaymentStatus.COMPLETED)
    total_paid += data.amount
    if total_paid >= bill.amount:
        bill.status = BillStatus.PAID
        db.save_bill(bill)
    response = {
        "payment": payment,
        "commission": commission,
        "total_with_commission": data.amount + commission,
    }
    if data.method == PaymentMethod.BANK_TRANSFER and bill.iban:
        response["bank_transfer_info"] = {
            "iban": bill.iban,
            "bill_number": bill.bill_number,
            "amount": data.amount,
            "reference": f"Bill {bill.bill_number or bill.id}",
        }
    return response
