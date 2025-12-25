import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from dotenv import load_dotenv

from app.models import (
    User, Property, Unit, Renter, Bill, Payment, EmailConfig, EblocConfig, AddressMapping,
    ExtractionPattern,
    UserRole, OAuthProvider, BillStatus, BillType, PaymentMethod, PaymentStatus,
    SubscriptionStatus,
    UserCreate, UserUpdate, PropertyCreate, PropertyUpdate, UnitCreate, UnitUpdate,
    RenterCreate, RenterUpdate, BillCreate, BillUpdate, PaymentCreate,
    EmailConfigCreate, EblocConfigCreate, AddressMappingCreate, TokenData,
    ExtractionPatternCreate, ExtractionPatternUpdate,
)
from app.auth import (
    create_access_token, require_auth, require_admin, require_landlord,
)
from app.database import db, has_any_admin
from app.email_scraper import extract_bill_info, match_address_to_property
from app.pdf_parser import parse_pdf_with_patterns

load_dotenv()

app = FastAPI(title="ProManage API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
PAYMENT_SERVICE_COMMISSION = float(os.getenv("PAYMENT_SERVICE_COMMISSION", "0.02"))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth/has-admin")
async def check_has_admin():
    """Check if any admin user exists. Used by frontend to hide demo mode."""
    return {"has_admin": has_any_admin()}


@app.post("/auth/google")
async def auth_google(token: str):
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        data = resp.json()
    email = data.get("email")
    name = data.get("name", email)
    oauth_id = data.get("sub")
    user = next(
        (u for u in db.list_users() if u.oauth_id == oauth_id and u.oauth_provider == OAuthProvider.GOOGLE),
        None,
    )
    if not user:
        role = UserRole.ADMIN if not has_any_admin() else UserRole.LANDLORD
        user = User(
            email=email,
            name=name,
            role=role,
            oauth_provider=OAuthProvider.GOOGLE,
            oauth_id=oauth_id,
        )
        db.save_user(user)
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@app.post("/auth/facebook")
async def auth_facebook(token: str):
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}"
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Facebook token")
        data = resp.json()
    email = data.get("email", f"{data.get('id')}@facebook.local")
    name = data.get("name", email)
    oauth_id = data.get("id")
    user = next(
        (u for u in db.list_users() if u.oauth_id == oauth_id and u.oauth_provider == OAuthProvider.FACEBOOK),
        None,
    )
    if not user:
        role = UserRole.ADMIN if not has_any_admin() else UserRole.LANDLORD
        user = User(
            email=email,
            name=name,
            role=role,
            oauth_provider=OAuthProvider.FACEBOOK,
            oauth_id=oauth_id,
        )
        db.save_user(user)
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@app.get("/auth/me")
async def get_me(current_user: TokenData = Depends(require_auth)):
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/admin/users")
async def list_users(_: TokenData = Depends(require_admin)):
    return db.list_users()


@app.post("/admin/users", status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, _: TokenData = Depends(require_admin)):
    if db.get_user_by_email(data.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(email=data.email, name=data.name, role=data.role)
    db.save_user(user)
    return user


@app.get("/admin/users/{user_id}")
async def get_user(user_id: str, _: TokenData = Depends(require_admin)):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/admin/users/{user_id}")
async def update_user(user_id: str, data: UserUpdate, _: TokenData = Depends(require_admin)):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.email is not None:
        user.email = data.email
    if data.name is not None:
        user.name = data.name
    if data.role is not None:
        user.role = data.role
    db.save_user(user)
    return user


@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, _: TokenData = Depends(require_admin)):
    if not db.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    db.delete_user(user_id)
    return {"status": "deleted"}


@app.put("/admin/users/{user_id}/subscription")
async def update_subscription(
    user_id: str,
    status: SubscriptionStatus,
    expires: Optional[datetime] = None,
    _: TokenData = Depends(require_admin),
):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.subscription_status = status
    user.subscription_expires = expires
    db.save_user(user)
    return user


def check_subscription(user_id: str) -> bool:
    user = db.get_user(user_id)
    if not user:
        return False
    property_count = db.count_properties(user_id)
    if property_count < 1:
        return True
    if user.subscription_status != SubscriptionStatus.ACTIVE:
        return False
    if user.subscription_expires and user.subscription_expires < datetime.utcnow():
        return False
    return True


@app.get("/properties")
async def list_properties(current_user: TokenData = Depends(require_landlord)):
    if current_user.role == UserRole.ADMIN:
        return db.list_properties()
    return db.list_properties(landlord_id=current_user.user_id)


@app.post("/properties", status_code=status.HTTP_201_CREATED)
async def create_property(data: PropertyCreate, current_user: TokenData = Depends(require_landlord)):
    existing_count = db.count_properties(current_user.user_id)
    if existing_count >= 1 and not check_subscription(current_user.user_id):
        raise HTTPException(
            status_code=403,
            detail="Active subscription required to add more than one property",
        )
    prop = Property(landlord_id=current_user.user_id, address=data.address, name=data.name)
    db.save_property(prop)
    default_unit = Unit(property_id=prop.id, unit_number="Main")
    db.save_unit(default_unit)
    return prop


@app.get("/properties/{property_id}")
async def get_property(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return prop


@app.put("/properties/{property_id}")
async def update_property(
    property_id: str, data: PropertyUpdate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if data.address is not None:
        prop.address = data.address
    if data.name is not None:
        prop.name = data.name
    db.save_property(prop)
    return prop


@app.delete("/properties/{property_id}")
async def delete_property(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete_property(property_id)
    return {"status": "deleted"}


@app.get("/properties/{property_id}/units")
async def list_units(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.list_units(property_id=property_id)


@app.post("/properties/{property_id}/units", status_code=status.HTTP_201_CREATED)
async def create_unit(
    property_id: str, data: UnitCreate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    unit = Unit(property_id=property_id, unit_number=data.unit_number)
    db.save_unit(unit)
    return unit


@app.get("/units/{unit_id}")
async def get_unit(unit_id: str, current_user: TokenData = Depends(require_landlord)):
    unit = db.get_unit(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return unit


@app.put("/units/{unit_id}")
async def update_unit(unit_id: str, data: UnitUpdate, current_user: TokenData = Depends(require_landlord)):
    unit = db.get_unit(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if data.unit_number is not None:
        unit.unit_number = data.unit_number
    db.save_unit(unit)
    return unit


@app.delete("/units/{unit_id}")
async def delete_unit(unit_id: str, current_user: TokenData = Depends(require_landlord)):
    unit = db.get_unit(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete_unit(unit_id)
    return {"status": "deleted"}


@app.get("/units/{unit_id}/renters")
async def list_renters(unit_id: str, current_user: TokenData = Depends(require_landlord)):
    unit = db.get_unit(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.list_renters(unit_id=unit_id)


@app.post("/units/{unit_id}/renters", status_code=status.HTTP_201_CREATED)
async def create_renter(
    unit_id: str, data: RenterCreate, current_user: TokenData = Depends(require_landlord)
):
    unit = db.get_unit(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    renter = Renter(unit_id=unit_id, name=data.name, email=data.email, phone=data.phone)
    db.save_renter(renter)
    return renter


@app.get("/renters/{renter_id}")
async def get_renter(renter_id: str, current_user: TokenData = Depends(require_landlord)):
    renter = db.get_renter(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    unit = db.get_unit(renter.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return renter


@app.put("/renters/{renter_id}")
async def update_renter(
    renter_id: str, data: RenterUpdate, current_user: TokenData = Depends(require_landlord)
):
    renter = db.get_renter(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    unit = db.get_unit(renter.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
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
    db.save_renter(renter)
    return renter


@app.delete("/renters/{renter_id}")
async def delete_renter(renter_id: str, current_user: TokenData = Depends(require_landlord)):
    renter = db.get_renter(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    unit = db.get_unit(renter.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete_renter(renter_id)
    return {"status": "deleted"}


@app.get("/renters/{renter_id}/link")
async def get_renter_link(renter_id: str, current_user: TokenData = Depends(require_landlord)):
    renter = db.get_renter(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    unit = db.get_unit(renter.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {"access_token": renter.access_token, "link": f"/renter/{renter.access_token}"}


@app.get("/bills")
async def list_bills(current_user: TokenData = Depends(require_landlord)):
    if current_user.role == UserRole.ADMIN:
        return db.list_bills()
    landlord_units = set()
    for prop in db.list_properties(landlord_id=current_user.user_id):
        for unit in db.list_units(property_id=prop.id):
            landlord_units.add(unit.id)
    return [b for b in db.list_bills() if b.unit_id in landlord_units]


@app.post("/bills", status_code=status.HTTP_201_CREATED)
async def create_bill(data: BillCreate, current_user: TokenData = Depends(require_landlord)):
    unit = db.get_unit(data.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    bill = Bill(
        unit_id=data.unit_id,
        bill_type=data.bill_type,
        description=data.description,
        amount=data.amount,
        due_date=data.due_date,
        iban=data.iban,
        bill_number=data.bill_number,
    )
    db.save_bill(bill)
    return bill


@app.get("/bills/{bill_id}")
async def get_bill(bill_id: str, current_user: TokenData = Depends(require_landlord)):
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    unit = db.get_unit(bill.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return bill


@app.put("/bills/{bill_id}")
async def update_bill(
    bill_id: str, data: BillUpdate, current_user: TokenData = Depends(require_landlord)
):
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    unit = db.get_unit(bill.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if data.description is not None:
        bill.description = data.description
    if data.amount is not None:
        bill.amount = data.amount
    if data.due_date is not None:
        bill.due_date = data.due_date
    if data.iban is not None:
        bill.iban = data.iban
    if data.bill_number is not None:
        bill.bill_number = data.bill_number
    if data.status is not None:
        bill.status = data.status
    db.save_bill(bill)
    return bill


@app.delete("/bills/{bill_id}")
async def delete_bill(bill_id: str, current_user: TokenData = Depends(require_landlord)):
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    unit = db.get_unit(bill.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.get_property(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete_bill(bill_id)
    return {"status": "deleted"}


@app.get("/renter/{token}")
async def renter_info(token: str):
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    unit = db.get_unit(renter.unit_id)
    prop = db.get_property(unit.property_id) if unit else None
    return {
        "renter": {"id": renter.id, "name": renter.name},
        "unit": {"id": unit.id, "unit_number": unit.unit_number} if unit else None,
        "property": {"id": prop.id, "name": prop.name, "address": prop.address} if prop else None,
    }


@app.get("/renter/{token}/bills")
async def renter_bills(token: str):
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    bills = db.list_bills(unit_id=renter.unit_id)
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


@app.get("/renter/{token}/balance")
async def renter_balance(token: str):
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    bills = db.list_bills(unit_id=renter.unit_id)
    total_due = sum(b.amount for b in bills if b.status != BillStatus.PAID)
    total_paid = 0.0
    for bill in bills:
        payments = db.list_payments(bill_id=bill.id)
        total_paid += sum(p.amount for p in payments if p.status == PaymentStatus.COMPLETED)
    return {"total_due": total_due, "total_paid": total_paid, "balance": total_due - total_paid}


@app.post("/renter/{token}/pay")
async def renter_pay(token: str, data: PaymentCreate):
    renter = db.get_renter_by_token(token)
    if not renter:
        raise HTTPException(status_code=404, detail="Invalid access token")
    bill = db.get_bill(data.bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if bill.unit_id != renter.unit_id:
        raise HTTPException(status_code=403, detail="Bill does not belong to this renter")
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


@app.post("/email/configure")
async def configure_email(
    data: EmailConfigCreate, current_user: TokenData = Depends(require_landlord)
):
    existing = db.get_email_config(current_user.user_id)
    if existing:
        existing.config_type = data.config_type
        existing.forwarding_email = data.forwarding_email
        db.save_email_config(existing)
        return existing
    config = EmailConfig(
        landlord_id=current_user.user_id,
        config_type=data.config_type,
        forwarding_email=data.forwarding_email,
    )
    db.save_email_config(config)
    return config


@app.get("/email/config")
async def get_email_config(current_user: TokenData = Depends(require_landlord)):
    config = db.get_email_config(current_user.user_id)
    if not config:
        raise HTTPException(status_code=404, detail="Email not configured")
    return config


@app.post("/email/process")
async def process_email(
    subject: str, body: str, sender: str, current_user: TokenData = Depends(require_landlord)
):
    info = extract_bill_info(body, subject)
    landlord_properties = db.list_properties(landlord_id=current_user.user_id)
    property_id = match_address_to_property(info.address, landlord_properties)
    if not property_id:
        return {"status": "no_match", "extracted": info, "message": "Could not match to property"}
    units = db.list_units(property_id=property_id)
    if not units:
        return {"status": "no_units", "extracted": info, "message": "Property has no units"}
    unit = units[0]
    bill = Bill(
        unit_id=unit.id,
        bill_type=BillType.UTILITIES,
        description=f"Bill from {sender}: {subject}",
        amount=info.amount or 0,
        due_date=datetime.utcnow(),
        iban=info.iban,
        bill_number=info.bill_number,
    )
    db.save_bill(bill)
    return {"status": "created", "bill": bill, "extracted": info}


@app.post("/ebloc/configure")
async def configure_ebloc(
    data: EblocConfigCreate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.get_property(data.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    password_hash = pwd_context.hash(data.password)
    existing = db.get_ebloc_config(current_user.user_id, data.property_id)
    if existing:
        existing.username = data.username
        existing.password_hash = password_hash
        db.save_ebloc_config(existing)
        return {"status": "updated", "config_id": existing.id}
    config = EblocConfig(
        landlord_id=current_user.user_id,
        property_id=data.property_id,
        username=data.username,
        password_hash=password_hash,
    )
    db.save_ebloc_config(config)
    return {"status": "created", "config_id": config.id}


@app.post("/ebloc/sync/{property_id}")
async def sync_ebloc(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    config = db.get_ebloc_config(current_user.user_id, property_id)
    if not config:
        raise HTTPException(status_code=404, detail="E-bloc not configured for this property")
    return {
        "status": "configured",
        "message": "E-bloc sync requires valid credentials. Bills will be fetched when credentials are verified.",
        "property_id": property_id,
    }


@app.get("/payments")
async def list_payments(current_user: TokenData = Depends(require_landlord)):
    if current_user.role == UserRole.ADMIN:
        return db.list_payments()
    landlord_bills = set()
    for prop in db.list_properties(landlord_id=current_user.user_id):
        for unit in db.list_units(property_id=prop.id):
            for bill in db.list_bills(unit_id=unit.id):
                landlord_bills.add(bill.id)
    return [p for p in db.list_payments() if p.bill_id in landlord_bills]


@app.get("/subscription/status")
async def subscription_status(current_user: TokenData = Depends(require_auth)):
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    property_count = db.count_properties(current_user.user_id)
    needs_subscription = property_count >= 1
    return {
        "status": user.subscription_status,
        "expires": user.subscription_expires,
        "property_count": property_count,
        "needs_subscription": needs_subscription,
        "can_add_property": not needs_subscription or user.subscription_status == SubscriptionStatus.ACTIVE,
    }


@app.get("/address-mappings")
async def list_address_mappings(current_user: TokenData = Depends(require_landlord)):
    if current_user.role == UserRole.ADMIN:
        return db.list_address_mappings()
    return db.list_address_mappings(landlord_id=current_user.user_id)


@app.post("/address-mappings", status_code=status.HTTP_201_CREATED)
async def create_address_mapping(
    data: AddressMappingCreate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.get_property(data.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    normalized = data.extracted_address.lower().strip()
    normalized = " ".join(normalized.split())
    existing = db.get_address_mapping_by_normalized(current_user.user_id, normalized)
    if existing:
        existing.property_id = data.property_id
        db.save_address_mapping(existing)
        return existing
    mapping = AddressMapping(
        landlord_id=current_user.user_id,
        property_id=data.property_id,
        extracted_address=data.extracted_address,
        normalized_address=normalized,
    )
    db.save_address_mapping(mapping)
    return mapping


@app.delete("/address-mappings/{mapping_id}")
async def delete_address_mapping(mapping_id: str, current_user: TokenData = Depends(require_landlord)):
    mapping = db.get_address_mapping(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    if current_user.role != UserRole.ADMIN and mapping.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete_address_mapping(mapping_id)
    return {"status": "deleted"}


@app.get("/address-mappings/lookup")
async def lookup_address_mapping(
    address: str, current_user: TokenData = Depends(require_landlord)
):
    normalized = address.lower().strip()
    normalized = " ".join(normalized.split())
    for mapping in db.list_address_mappings(landlord_id=current_user.user_id):
        if mapping.normalized_address in normalized or normalized in mapping.normalized_address:
            prop = db.get_property(mapping.property_id)
            return {"property_id": mapping.property_id, "property": prop, "mapping": mapping}
    return {"property_id": None, "property": None, "mapping": None}


@app.post("/admin/bills/parse")
async def parse_bill_pdf(
    file: UploadFile = File(...),
    _: TokenData = Depends(require_admin),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    pdf_bytes = await file.read()
    patterns = db.list_extraction_patterns()
    result = parse_pdf_with_patterns(pdf_bytes, patterns)
    return result


@app.get("/admin/extraction-patterns")
async def list_extraction_patterns(_: TokenData = Depends(require_admin)):
    return db.list_extraction_patterns()


@app.post("/admin/extraction-patterns", status_code=status.HTTP_201_CREATED)
async def create_extraction_pattern(
    data: ExtractionPatternCreate, _: TokenData = Depends(require_admin)
):
    pattern = ExtractionPattern(
        name=data.name,
        bill_type=data.bill_type,
        vendor_hint=data.vendor_hint,
        iban_pattern=data.iban_pattern,
        amount_pattern=data.amount_pattern,
        address_pattern=data.address_pattern,
        bill_number_pattern=data.bill_number_pattern,
        priority=data.priority,
    )
    db.save_extraction_pattern(pattern)
    return pattern


@app.get("/admin/extraction-patterns/{pattern_id}")
async def get_extraction_pattern(pattern_id: str, _: TokenData = Depends(require_admin)):
    pattern = db.get_extraction_pattern(pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern


@app.put("/admin/extraction-patterns/{pattern_id}")
async def update_extraction_pattern(
    pattern_id: str, data: ExtractionPatternUpdate, _: TokenData = Depends(require_admin)
):
    pattern = db.get_extraction_pattern(pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    if data.name is not None:
        pattern.name = data.name
    if data.bill_type is not None:
        pattern.bill_type = data.bill_type
    if data.vendor_hint is not None:
        pattern.vendor_hint = data.vendor_hint
    if data.iban_pattern is not None:
        pattern.iban_pattern = data.iban_pattern
    if data.amount_pattern is not None:
        pattern.amount_pattern = data.amount_pattern
    if data.address_pattern is not None:
        pattern.address_pattern = data.address_pattern
    if data.bill_number_pattern is not None:
        pattern.bill_number_pattern = data.bill_number_pattern
    if data.priority is not None:
        pattern.priority = data.priority
    if data.enabled is not None:
        pattern.enabled = data.enabled
    db.save_extraction_pattern(pattern)
    return pattern


@app.delete("/admin/extraction-patterns/{pattern_id}")
async def delete_extraction_pattern(pattern_id: str, _: TokenData = Depends(require_admin)):
    if not db.get_extraction_pattern(pattern_id):
        raise HTTPException(status_code=404, detail="Pattern not found")
    db.delete_extraction_pattern(pattern_id)
    return {"status": "deleted"}


@app.post("/auth/demo")
async def auth_demo(email: str, name: str):
    user = db.get_user_by_email(email)
    if not user:
        user = User(
            email=email,
            name=name,
            role=UserRole.LANDLORD,
        )
        db.save_user(user)
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "user": user}
