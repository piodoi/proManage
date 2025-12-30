"""Public renter routes (token-based access)."""
import os
from fastapi import APIRouter, HTTPException
from app.models import Payment, PaymentCreate, PaymentMethod, PaymentStatus, BillStatus, TokenData
from app.database import db

router = APIRouter(prefix="/renter", tags=["renter-public"])

PAYMENT_SERVICE_COMMISSION = float(os.getenv("PAYMENT_SERVICE_COMMISSION", "0.02"))


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
    # Get bills for this property that either apply to all renters (renter_id is None) or to this specific renter
    all_bills = db.list_bills(property_id=renter.property_id)
    bills = [b for b in all_bills if b.renter_id is None or b.renter_id == renter.id]
    total_due = sum(b.amount for b in bills if b.status != BillStatus.PAID)
    total_paid = 0.0
    for bill in bills:
        payments = db.list_payments(bill_id=bill.id)
        total_paid += sum(p.amount for p in payments if p.status == PaymentStatus.COMPLETED)
    return {"total_due": total_due, "total_paid": total_paid, "balance": total_due - total_paid}


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

