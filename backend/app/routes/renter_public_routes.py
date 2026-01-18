"""Public renter routes (token-based access)."""
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.models import Payment, PaymentCreate, PaymentMethod, PaymentStatus, BillStatus, TokenData, Bill
from app.database import db
from app.utils.currency import get_exchange_rates, convert_currency
from app.paths import get_bill_pdf_path, bill_pdf_exists

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
    
    # Get landlord preferences for date format and payment info
    landlord_preferences = None
    date_format = "DD/MM/YYYY"  # Default
    landlord_iban = None
    landlord_name = None
    if prop:
        landlord_preferences = db.get_user_preferences(prop.landlord_id)
        if landlord_preferences:
            if landlord_preferences.date_format:
                date_format = landlord_preferences.date_format
            landlord_iban = landlord_preferences.iban
            landlord_name = landlord_preferences.landlord_name
    
    return {
        "renter": {"id": renter.id, "name": renter.name},
        "property": {"id": prop.id, "name": prop.name, "address": prop.address} if prop else None,
        "date_format": date_format,
        "landlord_iban": landlord_iban,
        "landlord_name": landlord_name,
    }


@router.get("/{token}/bills")
async def renter_bills(token: str):
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    all_bills = db.list_bills(property_id=renter.property_id)
    
    # Filter bills: include if renter_id is None, 'all', or matches this renter
    # Only filter out bills with a specific renter_id that doesn't match
    bills = [b for b in all_bills if b.renter_id is None or b.renter_id == 'all' or b.renter_id == renter.id]
    
    # Get property to find landlord_id for PDF path lookup
    prop = db.get_property(renter.property_id)
    landlord_id = prop.landlord_id if prop else None
    
    # Get property suppliers to check direct_debit status (keyed by PropertySupplier.id)
    property_suppliers = db.list_property_suppliers(renter.property_id)
    direct_debit_by_property_supplier = {ps.id: ps.direct_debit for ps in property_suppliers}
    
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
        
        # Check if this bill's property supplier has direct_debit enabled
        is_direct_debit = False
        if bill.property_supplier_id and bill.property_supplier_id in direct_debit_by_property_supplier:
            is_direct_debit = direct_debit_by_property_supplier[bill.property_supplier_id]
        
        # Check if PDF is available for this bill
        has_pdf = False
        if landlord_id:
            has_pdf = bill_pdf_exists(landlord_id, bill.id)
        
        result.append({
            "bill": bill,
            "paid_amount": paid_amount,
            "remaining": bill.amount - paid_amount,
            "is_direct_debit": is_direct_debit,
            "has_pdf": has_pdf,
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
    
    # Filter bills: include if renter_id is None, 'all', or matches this renter
    bills = [b for b in all_bills if b.renter_id is None or b.renter_id == 'all' or b.renter_id == renter.id]
    
    # Get property suppliers to check direct_debit status
    property_suppliers = db.list_property_suppliers(renter.property_id)
    direct_debit_suppliers = {ps.supplier_id: ps.direct_debit for ps in property_suppliers}
    
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
        bill_payments = payments_by_bill.get(bill.id, [])
        paid_for_this_bill = sum(p.amount for p in bill_payments if p.status == PaymentStatus.COMPLETED)
        
        # Include all unpaid/pending bills in the balance (including direct debit)
        if bill.status != BillStatus.PAID:
            bill_currency_original = bill.currency if bill.currency else "RON"
            bill_amount_converted = convert_currency(bill.amount, bill_currency_original, bill_currency, exchange_rates)
            paid_amount_converted = convert_currency(paid_for_this_bill, bill_currency_original, bill_currency, exchange_rates)
            
            total_due_original += bill_amount_converted
            total_paid_original += paid_amount_converted
    
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


@router.get("/{token}/bill/{bill_id}/pdf")
async def download_bill_pdf(token: str, bill_id: str):
    """
    Download PDF file for a bill.
    
    Renters can download PDFs for bills that belong to their property.
    """
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    # Get the bill and verify it belongs to the renter's property
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    if bill.property_id != renter.property_id:
        raise HTTPException(status_code=403, detail="Bill does not belong to this renter's property")
    
    # Check if renter has access to this bill (renter_id is None, 'all', or matches)
    if bill.renter_id is not None and bill.renter_id != 'all' and bill.renter_id != renter.id:
        raise HTTPException(status_code=403, detail="Access denied to this bill")
    
    # Get the property to find the landlord (user_id for the PDF path)
    prop = db.get_property(bill.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Check if PDF exists
    if not bill_pdf_exists(prop.landlord_id, bill_id):
        raise HTTPException(status_code=404, detail="PDF not available for this bill")
    
    pdf_path = get_bill_pdf_path(prop.landlord_id, bill_id)
    
    # Generate a filename for download
    filename = f"bill_{bill.bill_number or bill_id}.pdf"
    
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename
    )
