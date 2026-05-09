"""Renter management routes."""
from fastapi import APIRouter, HTTPException, Depends, status
from app.models import (
    Renter, RenterCreate, RenterUpdate, RenterPaymentCreate, TokenData, UserRole
)
from app.auth import require_landlord
from app.routes.auth_routes import hash_password
from app.database import db
from app.limits import check_can_add_renter
from app.utils.currency import get_exchange_rates
from app.utils.renter_payments import allocate_payment_to_bills, get_credit_currency, round_money

router = APIRouter(tags=["renters"])


@router.get("/properties/{property_id}/renters")
async def list_renters(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.list_renters(property_id=property_id)


@router.post("/properties/{property_id}/renters", status_code=status.HTTP_201_CREATED)
async def create_renter(
    property_id: str, data: RenterCreate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check subscription limit for renters
    user = db.get_user(current_user.user_id)
    if user and current_user.role != UserRole.ADMIN:
        # Count total renters across all user's properties
        user_properties = db.list_properties(landlord_id=current_user.user_id)
        total_renters = sum(len(db.list_renters(p.id)) for p in user_properties)
        
        can_add, message = check_can_add_renter(user.subscription_tier, total_renters)
        if not can_add:
            raise HTTPException(status_code=403, detail=message)
    
    # Hash password if provided
    password_hash = None
    if data.password:
        password_hash = hash_password(data.password)
    
    renter = Renter(
        property_id=property_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        rent_day=data.rent_day,
        start_contract_date=data.start_contract_date,
        rent_amount=data.rent_amount,
        rent_currency=data.rent_currency or 'EUR',
        credit=0.0,
        credit_currency='RON',
        password_hash=password_hash,
        language=data.language or 'ro',
    )
    db.save_renter(renter)
    return renter


@router.get("/renters/{renter_id}")
async def get_renter(renter_id: str, current_user: TokenData = Depends(require_landlord)):
    renter = db.get_renter(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    prop = db.get_property(renter.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return renter


@router.put("/renters/{renter_id}")
async def update_renter(
    renter_id: str, data: RenterUpdate, current_user: TokenData = Depends(require_landlord)
):
    renter = db.get_renter(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    prop = db.get_property(renter.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if data.name is not None:
        renter.name = data.name
    if data.email is not None:
        renter.email = data.email
    if data.phone is not None:
        renter.phone = data.phone
    if data.rent_day is not None:
        renter.rent_day = data.rent_day
    if data.start_contract_date is not None:
        renter.start_contract_date = data.start_contract_date
    if data.rent_amount is not None:
        renter.rent_amount = data.rent_amount
    if data.rent_currency is not None:
        renter.rent_currency = data.rent_currency
    # Hash password if provided
    if data.password is not None:
        renter.password_hash = hash_password(data.password)
    # Update language if provided
    if data.language is not None:
        renter.language = data.language
    db.save_renter(renter)
    return renter


@router.post("/renters/{renter_id}/payments")
async def record_renter_payment(
    renter_id: str, data: RenterPaymentCreate, current_user: TokenData = Depends(require_landlord)
):
    renter = db.get_renter(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")

    prop = db.get_property(renter.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    amount = round_money(data.amount)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")

    exchange_rates = await get_exchange_rates()
    payment_currency = (data.currency or 'RON').upper()
    bills = db.list_bills(property_id=renter.property_id)
    applied, remaining_credit, credit_currency = allocate_payment_to_bills(renter, bills, amount, payment_currency, exchange_rates)

    for bill in bills:
        if any(item["bill_id"] == bill.id for item in applied):
            db.save_bill(bill)

    renter.credit = remaining_credit
    renter.credit_currency = credit_currency
    db.save_renter(renter)

    return {
        "renter": renter,
        "applied": applied,
        "unapplied_credit": remaining_credit,
        "credit_currency": credit_currency,
        "message": "Payment recorded successfully.",
    }


@router.delete("/renters/{renter_id}")
async def delete_renter(renter_id: str, current_user: TokenData = Depends(require_landlord)):
    renter = db.get_renter(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    prop = db.get_property(renter.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete_renter(renter_id)
    return {"status": "deleted"}


@router.get("/renters/{renter_id}/link")
async def get_renter_link(renter_id: str, current_user: TokenData = Depends(require_landlord)):
    renter = db.get_renter(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    prop = db.get_property(renter.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {"access_token": renter.access_token, "link": f"/renter/{renter.access_token}"}

