"""Public renter routes (token-based access)."""
import os
from datetime import datetime
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException
from app.models import Payment, PaymentCreate, PaymentMethod, PaymentStatus, BillStatus, TokenData, Bill
from app.database import db

router = APIRouter(prefix="/renter", tags=["renter-public"])

PAYMENT_SERVICE_COMMISSION = float(os.getenv("PAYMENT_SERVICE_COMMISSION", "0.02"))


async def get_exchange_rates() -> dict[str, float]:
    """Fetch current exchange rates from EUR to other currencies."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://api.exchangerate-api.com/v4/latest/EUR")
            if response.status_code == 200:
                data = response.json()
                return {
                    "EUR": 1.0,
                    "USD": data.get("rates", {}).get("USD", 1.1),
                    "RON": data.get("rates", {}).get("RON", 4.97),
                }
    except Exception:
        pass
    # Fallback to default rates
    return {"EUR": 1.0, "USD": 1.1, "RON": 4.97}


def convert_amount(amount: float, from_currency: str, to_currency: str, exchange_rates: dict[str, float]) -> float:
    """Convert amount from one currency to another using exchange rates."""
    if from_currency == to_currency:
        return amount
    
    from_upper = from_currency.upper()
    to_upper = to_currency.upper()
    
    # Convert to EUR first
    amount_in_eur = amount
    if from_upper == "USD":
        amount_in_eur = amount / exchange_rates.get("USD", 1.1)
    elif from_upper == "RON":
        amount_in_eur = amount / exchange_rates.get("RON", 4.97)
    elif from_upper != "EUR":
        # Unknown currency, assume RON
        amount_in_eur = amount / exchange_rates.get("RON", 4.97)
    
    # Convert from EUR to target currency
    if to_upper == "EUR":
        return amount_in_eur
    elif to_upper == "USD":
        return amount_in_eur * exchange_rates.get("USD", 1.1)
    elif to_upper == "RON":
        return amount_in_eur * exchange_rates.get("RON", 4.97)
    else:
        # Unknown currency, assume RON
        return amount_in_eur * exchange_rates.get("RON", 4.97)


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
    # Get bills for this property that either apply to all renters (renter_id is None) or to this specific renter
    all_bills = db.list_bills(property_id=renter.property_id)
    bills = [b for b in all_bills if b.renter_id is None or b.renter_id == renter.id]
    result = []
    for bill in bills:
        # Calculate and update status based on due date
        bill = calculate_bill_status(bill)
        payments = db.list_payments(bill_id=bill.id)
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
    
    # Get property to access landlord_id
    prop = db.get_property(renter.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get landlord's preferences to determine currency
    preferences = db.get_user_preferences(prop.landlord_id)
    bill_currency = preferences.bill_currency if preferences and preferences.bill_currency else "RON"
    
    # Get exchange rates
    exchange_rates = await get_exchange_rates()
    
    # Get bills for this property that either apply to all renters (renter_id is None) or to this specific renter
    all_bills = db.list_bills(property_id=renter.property_id)
    bills = [b for b in all_bills if b.renter_id is None or b.renter_id == renter.id]
    
    # Calculate totals in original currency (bills are stored in their original currency)
    total_due_original = 0.0
    total_paid_original = 0.0
    
    for bill in bills:
        if bill.status != BillStatus.PAID:
            # Convert bill amount from bill currency to target currency
            bill_currency_original = bill.currency if bill.currency else "RON"
            total_due_original += convert_amount(bill.amount, bill_currency_original, bill_currency, exchange_rates)
        
        payments = db.list_payments(bill_id=bill.id)
        for payment in payments:
            if payment.status == PaymentStatus.COMPLETED:
                # Payments are stored in the same currency as the bill
                payment_currency_original = bill.currency if bill.currency else "RON"
                total_paid_original += convert_amount(payment.amount, payment_currency_original, bill_currency, exchange_rates)
    
    balance_original = total_due_original - total_paid_original
    
    # Build response
    response = {
        "total_due": total_due_original,
        "total_paid": total_paid_original,
        "balance": balance_original,
        "currency": bill_currency,
        "exchange_rates": exchange_rates,
    }
    
    # If currency is EUR, also include RON conversion
    if bill_currency == "EUR":
        response["total_due_ron"] = convert_amount(total_due_original, "EUR", "RON", exchange_rates)
        response["total_paid_ron"] = convert_amount(total_paid_original, "EUR", "RON", exchange_rates)
        response["balance_ron"] = convert_amount(balance_original, "EUR", "RON", exchange_rates)
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

