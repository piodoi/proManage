import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from dotenv import load_dotenv

from app.models import (
    User, Property, Unit, Renter, Bill, Payment, EmailConfig, EblocConfig,
    UserRole, OAuthProvider, BillStatus, BillType, PaymentMethod, PaymentStatus,
    EmailConfigType, SubscriptionStatus,
    UserCreate, UserUpdate, PropertyCreate, PropertyUpdate, UnitCreate, UnitUpdate,
    RenterCreate, RenterUpdate, BillCreate, BillUpdate, PaymentCreate,
    EmailConfigCreate, EblocConfigCreate, TokenData,
)
from app.auth import (
    create_access_token, require_auth, require_admin, require_landlord,
    get_current_user,
)
from app import database as db
from app.email_scraper import extract_bill_info, match_address_to_property
from app.ebloc_scraper import EblocScraper

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


@app.post("/auth/google")
async def auth_google(token: str):
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        data = resp.json()
    email = data.get("email")
    name = data.get("name", email)
    oauth_id = data.get("sub")
    user = next(
        (u for u in db.users.values() if u.oauth_id == oauth_id and u.oauth_provider == OAuthProvider.GOOGLE),
        None,
    )
    if not user:
        user = User(
            email=email,
            name=name,
            role=UserRole.LANDLORD,
            oauth_provider=OAuthProvider.GOOGLE,
            oauth_id=oauth_id,
        )
        db.users[user.id] = user
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
        (u for u in db.users.values() if u.oauth_id == oauth_id and u.oauth_provider == OAuthProvider.FACEBOOK),
        None,
    )
    if not user:
        user = User(
            email=email,
            name=name,
            role=UserRole.LANDLORD,
            oauth_provider=OAuthProvider.FACEBOOK,
            oauth_id=oauth_id,
        )
        db.users[user.id] = user
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@app.get("/auth/me")
async def get_me(current_user: TokenData = Depends(require_auth)):
    user = db.users.get(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/admin/users")
async def list_users(_: TokenData = Depends(require_admin)):
    return list(db.users.values())


@app.post("/admin/users", status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, _: TokenData = Depends(require_admin)):
    if any(u.email == data.email for u in db.users.values()):
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(email=data.email, name=data.name, role=data.role)
    db.users[user.id] = user
    return user


@app.get("/admin/users/{user_id}")
async def get_user(user_id: str, _: TokenData = Depends(require_admin)):
    user = db.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/admin/users/{user_id}")
async def update_user(user_id: str, data: UserUpdate, _: TokenData = Depends(require_admin)):
    user = db.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.email is not None:
        user.email = data.email
    if data.name is not None:
        user.name = data.name
    if data.role is not None:
        user.role = data.role
    db.users[user_id] = user
    return user


@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, _: TokenData = Depends(require_admin)):
    if user_id not in db.users:
        raise HTTPException(status_code=404, detail="User not found")
    del db.users[user_id]
    return {"status": "deleted"}


@app.put("/admin/users/{user_id}/subscription")
async def update_subscription(
    user_id: str,
    status: SubscriptionStatus,
    expires: Optional[datetime] = None,
    _: TokenData = Depends(require_admin),
):
    user = db.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.subscription_status = status
    user.subscription_expires = expires
    db.users[user_id] = user
    return user


def check_subscription(user_id: str) -> bool:
    user = db.users.get(user_id)
    if not user:
        return False
    property_count = sum(1 for p in db.properties.values() if p.landlord_id == user_id)
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
        return list(db.properties.values())
    return [p for p in db.properties.values() if p.landlord_id == current_user.user_id]


@app.post("/properties", status_code=status.HTTP_201_CREATED)
async def create_property(data: PropertyCreate, current_user: TokenData = Depends(require_landlord)):
    existing_count = sum(1 for p in db.properties.values() if p.landlord_id == current_user.user_id)
    if existing_count >= 1 and not check_subscription(current_user.user_id):
        raise HTTPException(
            status_code=403,
            detail="Active subscription required to add more than one property",
        )
    prop = Property(landlord_id=current_user.user_id, address=data.address, name=data.name)
    db.properties[prop.id] = prop
    return prop


@app.get("/properties/{property_id}")
async def get_property(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.properties.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return prop


@app.put("/properties/{property_id}")
async def update_property(
    property_id: str, data: PropertyUpdate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.properties.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if data.address is not None:
        prop.address = data.address
    if data.name is not None:
        prop.name = data.name
    db.properties[property_id] = prop
    return prop


@app.delete("/properties/{property_id}")
async def delete_property(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.properties.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    del db.properties[property_id]
    return {"status": "deleted"}


@app.get("/properties/{property_id}/units")
async def list_units(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.properties.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return [u for u in db.units.values() if u.property_id == property_id]


@app.post("/properties/{property_id}/units", status_code=status.HTTP_201_CREATED)
async def create_unit(
    property_id: str, data: UnitCreate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.properties.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    unit = Unit(property_id=property_id, unit_number=data.unit_number)
    db.units[unit.id] = unit
    return unit


@app.get("/units/{unit_id}")
async def get_unit(unit_id: str, current_user: TokenData = Depends(require_landlord)):
    unit = db.units.get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return unit


@app.put("/units/{unit_id}")
async def update_unit(unit_id: str, data: UnitUpdate, current_user: TokenData = Depends(require_landlord)):
    unit = db.units.get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if data.unit_number is not None:
        unit.unit_number = data.unit_number
    db.units[unit_id] = unit
    return unit


@app.delete("/units/{unit_id}")
async def delete_unit(unit_id: str, current_user: TokenData = Depends(require_landlord)):
    unit = db.units.get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    del db.units[unit_id]
    return {"status": "deleted"}


@app.get("/units/{unit_id}/renters")
async def list_renters(unit_id: str, current_user: TokenData = Depends(require_landlord)):
    unit = db.units.get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return [r for r in db.renters.values() if r.unit_id == unit_id]


@app.post("/units/{unit_id}/renters", status_code=status.HTTP_201_CREATED)
async def create_renter(
    unit_id: str, data: RenterCreate, current_user: TokenData = Depends(require_landlord)
):
    unit = db.units.get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    renter = Renter(unit_id=unit_id, name=data.name, email=data.email, phone=data.phone)
    db.renters[renter.id] = renter
    db.renter_tokens[renter.access_token] = renter.id
    return renter


@app.get("/renters/{renter_id}")
async def get_renter(renter_id: str, current_user: TokenData = Depends(require_landlord)):
    renter = db.renters.get(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    unit = db.units.get(renter.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return renter


@app.put("/renters/{renter_id}")
async def update_renter(
    renter_id: str, data: RenterUpdate, current_user: TokenData = Depends(require_landlord)
):
    renter = db.renters.get(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    unit = db.units.get(renter.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
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
    db.renters[renter_id] = renter
    return renter


@app.delete("/renters/{renter_id}")
async def delete_renter(renter_id: str, current_user: TokenData = Depends(require_landlord)):
    renter = db.renters.get(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    unit = db.units.get(renter.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if renter.access_token in db.renter_tokens:
        del db.renter_tokens[renter.access_token]
    del db.renters[renter_id]
    return {"status": "deleted"}


@app.get("/renters/{renter_id}/link")
async def get_renter_link(renter_id: str, current_user: TokenData = Depends(require_landlord)):
    renter = db.renters.get(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    unit = db.units.get(renter.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {"access_token": renter.access_token, "link": f"/renter/{renter.access_token}"}


@app.get("/bills")
async def list_bills(current_user: TokenData = Depends(require_landlord)):
    if current_user.role == UserRole.ADMIN:
        return list(db.bills.values())
    landlord_units = set()
    for prop in db.properties.values():
        if prop.landlord_id == current_user.user_id:
            for unit in db.units.values():
                if unit.property_id == prop.id:
                    landlord_units.add(unit.id)
    return [b for b in db.bills.values() if b.unit_id in landlord_units]


@app.post("/bills", status_code=status.HTTP_201_CREATED)
async def create_bill(data: BillCreate, current_user: TokenData = Depends(require_landlord)):
    unit = db.units.get(data.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
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
    db.bills[bill.id] = bill
    return bill


@app.get("/bills/{bill_id}")
async def get_bill(bill_id: str, current_user: TokenData = Depends(require_landlord)):
    bill = db.bills.get(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    unit = db.units.get(bill.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return bill


@app.put("/bills/{bill_id}")
async def update_bill(
    bill_id: str, data: BillUpdate, current_user: TokenData = Depends(require_landlord)
):
    bill = db.bills.get(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    unit = db.units.get(bill.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
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
    db.bills[bill_id] = bill
    return bill


@app.delete("/bills/{bill_id}")
async def delete_bill(bill_id: str, current_user: TokenData = Depends(require_landlord)):
    bill = db.bills.get(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    unit = db.units.get(bill.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    prop = db.properties.get(unit.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    del db.bills[bill_id]
    return {"status": "deleted"}


@app.get("/renter/{token}")
async def renter_info(token: str):
    renter_id = db.renter_tokens.get(token)
    if not renter_id:
        raise HTTPException(status_code=404, detail="Invalid access token")
    renter = db.renters.get(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    unit = db.units.get(renter.unit_id)
    prop = db.properties.get(unit.property_id) if unit else None
    return {
        "renter": {"id": renter.id, "name": renter.name},
        "unit": {"id": unit.id, "unit_number": unit.unit_number} if unit else None,
        "property": {"id": prop.id, "name": prop.name, "address": prop.address} if prop else None,
    }


@app.get("/renter/{token}/bills")
async def renter_bills(token: str):
    renter_id = db.renter_tokens.get(token)
    if not renter_id:
        raise HTTPException(status_code=404, detail="Invalid access token")
    renter = db.renters.get(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    bills = [b for b in db.bills.values() if b.unit_id == renter.unit_id]
    result = []
    for bill in bills:
        payments = [p for p in db.payments.values() if p.bill_id == bill.id]
        paid_amount = sum(p.amount for p in payments if p.status == PaymentStatus.COMPLETED)
        result.append({
            "bill": bill,
            "paid_amount": paid_amount,
            "remaining": bill.amount - paid_amount,
        })
    return result


@app.get("/renter/{token}/balance")
async def renter_balance(token: str):
    renter_id = db.renter_tokens.get(token)
    if not renter_id:
        raise HTTPException(status_code=404, detail="Invalid access token")
    renter = db.renters.get(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    bills = [b for b in db.bills.values() if b.unit_id == renter.unit_id]
    total_due = sum(b.amount for b in bills if b.status != BillStatus.PAID)
    total_paid = sum(
        p.amount for p in db.payments.values()
        if p.bill_id in [b.id for b in bills] and p.status == PaymentStatus.COMPLETED
    )
    return {"total_due": total_due, "total_paid": total_paid, "balance": total_due - total_paid}


@app.post("/renter/{token}/pay")
async def renter_pay(token: str, data: PaymentCreate):
    renter_id = db.renter_tokens.get(token)
    if not renter_id:
        raise HTTPException(status_code=404, detail="Invalid access token")
    renter = db.renters.get(renter_id)
    if not renter:
        raise HTTPException(status_code=404, detail="Renter not found")
    bill = db.bills.get(data.bill_id)
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
    db.payments[payment.id] = payment
    existing_payments = [p for p in db.payments.values() if p.bill_id == bill.id]
    total_paid = sum(p.amount for p in existing_payments if p.status == PaymentStatus.COMPLETED)
    total_paid += data.amount
    if total_paid >= bill.amount:
        bill.status = BillStatus.PAID
        db.bills[bill.id] = bill
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
    existing = next(
        (c for c in db.email_configs.values() if c.landlord_id == current_user.user_id), None
    )
    if existing:
        existing.config_type = data.config_type
        existing.forwarding_email = data.forwarding_email
        db.email_configs[existing.id] = existing
        return existing
    config = EmailConfig(
        landlord_id=current_user.user_id,
        config_type=data.config_type,
        forwarding_email=data.forwarding_email,
    )
    db.email_configs[config.id] = config
    return config


@app.get("/email/config")
async def get_email_config(current_user: TokenData = Depends(require_landlord)):
    config = next(
        (c for c in db.email_configs.values() if c.landlord_id == current_user.user_id), None
    )
    if not config:
        raise HTTPException(status_code=404, detail="Email not configured")
    return config


@app.post("/email/process")
async def process_email(
    subject: str, body: str, sender: str, current_user: TokenData = Depends(require_landlord)
):
    info = extract_bill_info(body, subject)
    landlord_properties = [p for p in db.properties.values() if p.landlord_id == current_user.user_id]
    property_id = match_address_to_property(info.address, landlord_properties)
    if not property_id:
        return {"status": "no_match", "extracted": info, "message": "Could not match to property"}
    units = [u for u in db.units.values() if u.property_id == property_id]
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
    db.bills[bill.id] = bill
    return {"status": "created", "bill": bill, "extracted": info}


@app.post("/ebloc/configure")
async def configure_ebloc(
    data: EblocConfigCreate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.properties.get(data.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    password_hash = pwd_context.hash(data.password)
    existing = next(
        (c for c in db.ebloc_configs.values()
         if c.landlord_id == current_user.user_id and c.property_id == data.property_id),
        None,
    )
    if existing:
        existing.username = data.username
        existing.password_hash = password_hash
        db.ebloc_configs[existing.id] = existing
        return {"status": "updated", "config_id": existing.id}
    config = EblocConfig(
        landlord_id=current_user.user_id,
        property_id=data.property_id,
        username=data.username,
        password_hash=password_hash,
    )
    db.ebloc_configs[config.id] = config
    return {"status": "created", "config_id": config.id}


@app.post("/ebloc/sync/{property_id}")
async def sync_ebloc(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.properties.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    config = next(
        (c for c in db.ebloc_configs.values()
         if c.landlord_id == current_user.user_id and c.property_id == property_id),
        None,
    )
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
        return list(db.payments.values())
    landlord_bills = set()
    for prop in db.properties.values():
        if prop.landlord_id == current_user.user_id:
            for unit in db.units.values():
                if unit.property_id == prop.id:
                    for bill in db.bills.values():
                        if bill.unit_id == unit.id:
                            landlord_bills.add(bill.id)
    return [p for p in db.payments.values() if p.bill_id in landlord_bills]


@app.get("/subscription/status")
async def subscription_status(current_user: TokenData = Depends(require_auth)):
    user = db.users.get(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    property_count = sum(1 for p in db.properties.values() if p.landlord_id == current_user.user_id)
    needs_subscription = property_count >= 1
    return {
        "status": user.subscription_status,
        "expires": user.subscription_expires,
        "property_count": property_count,
        "needs_subscription": needs_subscription,
        "can_add_property": not needs_subscription or user.subscription_status == SubscriptionStatus.ACTIVE,
    }
