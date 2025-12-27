import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64

import bcrypt

from app.models import (
    User, Property, Renter, Bill, Payment, EmailConfig,
    ExtractionPattern,
    UserRole, BillStatus, BillType, PaymentMethod, PaymentStatus,
    SubscriptionStatus,
    UserCreate, UserUpdate, PropertyCreate, PropertyUpdate,
    RenterCreate, RenterUpdate, BillCreate, BillUpdate, PaymentCreate,
    EmailConfigCreate, EblocConfigCreate, TokenData,
    ExtractionPatternCreate, ExtractionPatternUpdate,
)
from app.auth import (
    require_auth, require_admin, require_landlord,
)
from app.database import db
from app.email_scraper import extract_bill_info, match_address_to_property
from app.pdf_parser import parse_pdf_with_patterns
from app.routes import auth_router

load_dotenv()

# Encryption key for e-bloc passwords (in production, use a secure key from env)
# Fernet keys must be 32 bytes when base64-decoded (44 characters when base64-encoded)
EBLOC_ENCRYPTION_KEY = os.getenv("EBLOC_ENCRYPTION_KEY")
if EBLOC_ENCRYPTION_KEY:
    try:
        # Validate the key format
        decoded_key = base64.urlsafe_b64decode(EBLOC_ENCRYPTION_KEY)
        if len(decoded_key) != 32:
            raise ValueError(f"Invalid key length: {len(decoded_key)} bytes (expected 32)")
        fernet = Fernet(EBLOC_ENCRYPTION_KEY.encode())
        import logging
        logger = logging.getLogger(__name__)
        logger.info("[E-Bloc] Using encryption key from environment")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[E-Bloc] Invalid encryption key in environment: {e}. Generating new key.")
        # If key is invalid, generate a new one
        EBLOC_ENCRYPTION_KEY = Fernet.generate_key().decode()
        fernet = Fernet(EBLOC_ENCRYPTION_KEY.encode())
        logger.warning(f"[E-Bloc] Generated new encryption key. Save this to .env: EBLOC_ENCRYPTION_KEY={EBLOC_ENCRYPTION_KEY}")
else:
    # No key in environment, generate a new one
    EBLOC_ENCRYPTION_KEY = Fernet.generate_key().decode()
    fernet = Fernet(EBLOC_ENCRYPTION_KEY.encode())
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"[E-Bloc] No encryption key in environment. Generated new key. Save this to .env: EBLOC_ENCRYPTION_KEY={EBLOC_ENCRYPTION_KEY}")

def encrypt_password(password: str) -> str:
    """Encrypt password for e-bloc (needs to be retrievable)"""
    return fernet.encrypt(password.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    """Decrypt password for e-bloc"""
    try:
        return fernet.decrypt(encrypted.encode()).decode()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[E-Bloc] Error decrypting password: {e}", exc_info=True)
        # If decryption fails, it might be because the encryption key changed
        # This can happen if the server restarted and EBLOC_ENCRYPTION_KEY wasn't set in env
        raise ValueError(f"Failed to decrypt password. The encryption key may have changed. Please reconfigure your E-bloc credentials. Error: {str(e)}")

app = FastAPI(title="ProManage API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

PAYMENT_SERVICE_COMMISSION = float(os.getenv("PAYMENT_SERVICE_COMMISSION", "0.02"))


def load_extraction_patterns_from_json(force_update: bool = False) -> list[dict]:
    """Load extraction patterns from JSON files in the extraction_patterns directory.
    
    Returns:
        List of dictionaries with 'action' ('created' or 'updated'), 'pattern_name', and 'file_name'
    """
    patterns_dir = Path(__file__).parent.parent / "extraction_patterns"
    if not patterns_dir.exists():
        return []
    
    import logging
    import os
    logger = logging.getLogger(__name__)
    results = []
    
    for json_file in patterns_dir.glob("*.json"):
        try:
            # Get file modification time
            file_mtime = datetime.fromtimestamp(os.path.getmtime(json_file))
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if pattern already exists (by supplier or name)
            supplier = data.get('supplier')
            name = data.get('name')
            existing_patterns = db.list_extraction_patterns()
            existing = None
            for pattern in existing_patterns:
                if (supplier and pattern.supplier == supplier) or (name and pattern.name == name):
                    existing = pattern
                    break
            
            # Check if JSON file is newer than existing pattern
            should_update = True
            if existing and existing.updated_at and not force_update:
                # Only update if JSON file is newer than the pattern's updated_at
                if file_mtime <= existing.updated_at:
                    should_update = False
                    logger.debug(f"Skipping {json_file.name} - JSON file is not newer than existing pattern")
            
            if not should_update:
                continue
            
            # Create or update pattern
            pattern_data = ExtractionPatternCreate(
                name=data.get('name', ''),
                bill_type=BillType(data.get('bill_type', 'utilities')),
                supplier=data.get('supplier'),
                vendor_hint=data.get('vendor_hint'),
                iban_pattern=data.get('iban_pattern'),
                amount_pattern=data.get('amount_pattern'),
                address_pattern=data.get('address_pattern'),
                bill_number_pattern=data.get('bill_number_pattern'),
                contract_id_pattern=data.get('contract_id_pattern'),
                due_date_pattern=data.get('due_date_pattern'),
                business_name_pattern=data.get('business_name_pattern'),
                bank_accounts=data.get('bank_accounts'),
                priority=data.get('priority', 0),
            )
            
            if existing:
                # Update existing pattern
                update_data = ExtractionPatternUpdate(
                    supplier=pattern_data.supplier,
                    vendor_hint=pattern_data.vendor_hint,
                    iban_pattern=pattern_data.iban_pattern,
                    amount_pattern=pattern_data.amount_pattern,
                    address_pattern=pattern_data.address_pattern,
                    bill_number_pattern=pattern_data.bill_number_pattern,
                    contract_id_pattern=pattern_data.contract_id_pattern,
                    due_date_pattern=pattern_data.due_date_pattern,
                    business_name_pattern=pattern_data.business_name_pattern,
                    bank_accounts=pattern_data.bank_accounts,
                    priority=pattern_data.priority,
                    enabled=data.get('enabled', True),
                )
                pattern = db.get_extraction_pattern(existing.id)
                if pattern:
                    if update_data.supplier is not None:
                        pattern.supplier = update_data.supplier
                    if update_data.vendor_hint is not None:
                        pattern.vendor_hint = update_data.vendor_hint
                    if update_data.iban_pattern is not None:
                        pattern.iban_pattern = update_data.iban_pattern
                    if update_data.amount_pattern is not None:
                        pattern.amount_pattern = update_data.amount_pattern
                    if update_data.address_pattern is not None:
                        pattern.address_pattern = update_data.address_pattern
                    if update_data.bill_number_pattern is not None:
                        pattern.bill_number_pattern = update_data.bill_number_pattern
                    if update_data.contract_id_pattern is not None:
                        pattern.contract_id_pattern = update_data.contract_id_pattern
                    if update_data.due_date_pattern is not None:
                        pattern.due_date_pattern = update_data.due_date_pattern
                    if update_data.business_name_pattern is not None:
                        pattern.business_name_pattern = update_data.business_name_pattern
                    if update_data.bank_accounts is not None:
                        pattern.bank_accounts = update_data.bank_accounts
                    if update_data.priority is not None:
                        pattern.priority = update_data.priority
                    if update_data.enabled is not None:
                        pattern.enabled = update_data.enabled
                    # Set updated_at to file modification time
                    pattern.updated_at = file_mtime
                    db.save_extraction_pattern(pattern)
                    logger.info(f"Updated extraction pattern: {pattern.name} (from {json_file.name})")
                    results.append({
                        'action': 'updated',
                        'pattern_name': pattern.name,
                        'file_name': json_file.name,
                        'supplier': pattern.supplier,
                    })
            else:
                # Create new pattern
                pattern = ExtractionPattern(
                    name=pattern_data.name,
                    bill_type=pattern_data.bill_type,
                    supplier=pattern_data.supplier,
                    vendor_hint=pattern_data.vendor_hint,
                    iban_pattern=pattern_data.iban_pattern,
                    amount_pattern=pattern_data.amount_pattern,
                    address_pattern=pattern_data.address_pattern,
                    bill_number_pattern=pattern_data.bill_number_pattern,
                    contract_id_pattern=pattern_data.contract_id_pattern,
                    due_date_pattern=pattern_data.due_date_pattern,
                    business_name_pattern=pattern_data.business_name_pattern,
                    bank_accounts=pattern_data.bank_accounts,
                    priority=pattern_data.priority,
                    enabled=data.get('enabled', True),
                    updated_at=file_mtime,
                )
                db.save_extraction_pattern(pattern)
                logger.info(f"Loaded extraction pattern: {pattern.name} (from {json_file.name})")
                results.append({
                    'action': 'created',
                    'pattern_name': pattern.name,
                    'file_name': json_file.name,
                    'supplier': pattern.supplier,
                })
        except Exception as e:
            logger.error(f"Error loading pattern from {json_file}: {e}")
            results.append({
                'action': 'error',
                'pattern_name': data.get('name', 'Unknown'),
                'file_name': json_file.name,
                'error': str(e),
            })
    
    return results


@app.on_event("startup")
async def startup_event():
    """Load extraction patterns from JSON files on startup."""
    load_extraction_patterns_from_json()


@app.post("/admin/refresh-patterns")
async def refresh_extraction_patterns(
    force: bool = Query(False, description="Force update even if JSON is not newer"),
    _: TokenData = Depends(require_admin),
):
    """Manually refresh extraction patterns from JSON files."""
    results = load_extraction_patterns_from_json(force_update=force)
    return {
        "status": "success",
        "updated_count": len([r for r in results if r['action'] in ('created', 'updated')]),
        "results": results,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/admin/users")
async def list_users(
    page: int = 1,
    limit: int = 50,
    _: TokenData = Depends(require_admin)
):
    offset = (page - 1) * limit
    users = db.list_users(limit=limit, offset=offset)
    total = db.count_users()
    return {
        "users": users,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }


@app.post("/admin/users", status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, _: TokenData = Depends(require_admin)):
    if db.get_user_by_email(data.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    password_hash = None
    if data.password:
        from app.routes.auth_routes import hash_password
        password_hash = hash_password(data.password)
    user = User(email=data.email, name=data.name, role=data.role, password_hash=password_hash)
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
    tier: int = 0,  # 0 = off, 1 = on
    expires: Optional[datetime] = None,
    _: TokenData = Depends(require_admin),
):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.subscription_tier = tier
    # Keep subscription_status for backward compatibility
    user.subscription_status = SubscriptionStatus.ACTIVE if tier > 0 else SubscriptionStatus.NONE
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
    if user.subscription_tier == 0:
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
    # Admins have implied subscription - skip check for them
    if current_user.role != UserRole.ADMIN and existing_count >= 1 and not check_subscription(current_user.user_id):
        raise HTTPException(
            status_code=403,
            detail="Active subscription required to add more than one property",
        )
    prop = Property(landlord_id=current_user.user_id, address=data.address, name=data.name)
    db.save_property(prop)
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


@app.get("/properties/{property_id}/renters")
async def list_renters(property_id: str, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.list_renters(property_id=property_id)


@app.post("/properties/{property_id}/renters", status_code=status.HTTP_201_CREATED)
async def create_renter(
    property_id: str, data: RenterCreate, current_user: TokenData = Depends(require_landlord)
):
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    renter = Renter(
        property_id=property_id, 
        name=data.name, 
        email=data.email, 
        phone=data.phone,
        rent_day=data.rent_day,
        start_contract_date=data.start_contract_date,
        rent_amount_eur=data.rent_amount_eur
    )
    db.save_renter(renter)
    return renter


@app.get("/renters/{renter_id}")
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


@app.put("/renters/{renter_id}")
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
    if data.rent_amount_eur is not None:
        renter.rent_amount_eur = data.rent_amount_eur
    db.save_renter(renter)
    return renter


@app.delete("/renters/{renter_id}")
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


@app.get("/renters/{renter_id}/link")
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


@app.get("/bills")
async def list_bills(current_user: TokenData = Depends(require_landlord)):
    if current_user.role == UserRole.ADMIN:
        return db.list_bills()
    landlord_properties = {prop.id for prop in db.list_properties(landlord_id=current_user.user_id)}
    return [b for b in db.list_bills() if b.property_id in landlord_properties]


@app.post("/bills", status_code=status.HTTP_201_CREATED)
async def create_bill(data: BillCreate, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(data.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    # If renter_id is provided, verify it belongs to the property
    if data.renter_id:
        renter = db.get_renter(data.renter_id)
        if not renter or renter.property_id != data.property_id:
            raise HTTPException(status_code=404, detail="Renter not found in this property")
    bill = Bill(
        property_id=data.property_id,
        renter_id=data.renter_id,
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
    prop = db.get_property(bill.property_id)
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
    prop = db.get_property(bill.property_id)
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
    prop = db.get_property(bill.property_id)
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
    prop = db.get_property(renter.property_id)
    return {
        "renter": {"id": renter.id, "name": renter.name},
        "property": {"id": prop.id, "name": prop.name, "address": prop.address} if prop else None,
    }


@app.get("/renter/{token}/bills")
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


@app.get("/renter/{token}/balance")
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


@app.post("/renter/{token}/pay")
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


@app.post("/ebloc/discover")
async def discover_ebloc_properties(
    data: dict, current_user: TokenData = Depends(require_landlord)
):
    """Discover properties from e-bloc account"""
    import logging
    logger = logging.getLogger(__name__)
    
    username = data.get("username")
    password = data.get("password")
    logger.info(f"[E-Bloc] Discovery request from user {current_user.user_id}, username: {username}")
    
    if not username or not password:
        logger.warning("[E-Bloc] Missing username or password")
        raise HTTPException(status_code=400, detail="Username and password required")
    
    from app.ebloc_scraper import EblocScraper, EblocProperty
    
    # Enable debug mode to save HTML for inspection
    scraper = EblocScraper(debug=True)
    try:
        logger.info("[E-Bloc] Attempting login...")
        logged_in = await scraper.login(username, password)
        if not logged_in:
            logger.warning("[E-Bloc] Login failed - invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid e-bloc credentials")
        
        logger.info("[E-Bloc] Login successful, fetching properties...")
        properties = await scraper.get_available_properties()
        logger.info(f"[E-Bloc] Found {len(properties)} properties")
        
        result = {
            "status": "success",
            "properties": [
                {
                    "page_id": p.page_id,
                    "name": p.name,
                    "address": p.address or p.name,
                    "url": p.url  # Include the e-bloc URL
                }
                for p in properties
            ]
        }
        logger.info(f"[E-Bloc] Returning {len(result['properties'])} properties")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[E-Bloc] Error discovering properties: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error discovering properties: {str(e)}")
    finally:
        await scraper.close()


@app.post("/ebloc/configure")
async def configure_ebloc(
    data: EblocConfigCreate, current_user: TokenData = Depends(require_landlord)
):
    from app.ebloc_scraper import EblocScraper
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[E-Bloc] Configure request from user {current_user.user_id}")
    
    # Verify credentials by attempting login
    scraper = EblocScraper()
    try:
        logged_in = await scraper.login(data.username, data.password)
        if not logged_in:
            raise HTTPException(status_code=401, detail="Invalid e-bloc credentials")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[E-Bloc] Login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error verifying credentials: {str(e)}")
    finally:
        await scraper.close()
    
    # Get user and update ebloc credentials
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Encrypt password (not hash, since we need to retrieve it for scraping)
    try:
        password_encrypted = encrypt_password(data.password)
        user.ebloc_username = data.username
        user.ebloc_password_hash = password_encrypted
        db.save_user(user)
        logger.info(f"[E-Bloc] Credentials saved for user {current_user.user_id}")
        
        # Verify the password was saved correctly by trying to decrypt it
        try:
            test_decrypt = decrypt_password(password_encrypted)
            if test_decrypt != data.password:
                logger.error(f"[E-Bloc] Password encryption/decryption verification failed!")
                raise HTTPException(status_code=500, detail="Password encryption verification failed")
        except ValueError as ve:
            # Re-raise ValueError as HTTPException with better message
            raise HTTPException(status_code=500, detail=str(ve))
        except Exception as e:
            logger.error(f"[E-Bloc] Password verification error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Password encryption error: {str(e)}")
        
        return {"status": "configured", "message": "E-bloc credentials saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[E-Bloc] Error saving credentials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error saving credentials: {str(e)}")


@app.get("/ebloc/config")
async def get_ebloc_config(current_user: TokenData = Depends(require_landlord)):
    """Get e-bloc configuration for current user (including decrypted password for form)"""
    import logging
    logger = logging.getLogger(__name__)
    
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.ebloc_username:
        return {"username": None, "password": None, "configured": False}
    
    # Decrypt password for form (since it's encrypted, not hashed, we can retrieve it)
    password = None
    if user.ebloc_password_hash:
        try:
            password = decrypt_password(user.ebloc_password_hash)
        except Exception as e:
            logger.warning(f"[E-Bloc] Could not decrypt password for user {current_user.user_id}: {e}")
            # Password might be encrypted with a different key (e.g., server restarted with new key)
            # Return None for password - user will need to re-enter it
            password = None
    
    return {
        "username": user.ebloc_username,
        "password": password,
        "configured": True,
    }


@app.post("/ebloc/sync/{property_id}")
async def sync_ebloc(property_id: str, association_id: Optional[str] = Query(None), current_user: TokenData = Depends(require_landlord)):
    from app.ebloc_scraper import EblocScraper
    import logging
    logger = logging.getLogger(__name__)
    
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get user ebloc credentials
    user = db.get_user(current_user.user_id)
    if not user or not user.ebloc_username or not user.ebloc_password_hash:
        raise HTTPException(status_code=404, detail="E-bloc not configured. Please configure your E-bloc credentials first.")
    
    # Decrypt password and login
    if not user.ebloc_password_hash:
        raise HTTPException(status_code=404, detail="E-bloc password not configured. Please configure your E-bloc credentials first.")
    
    try:
        password = decrypt_password(user.ebloc_password_hash)
    except Exception as e:
        logger.error(f"[E-Bloc] Error decrypting password: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error decrypting E-bloc password. Please reconfigure your credentials.")
    
    scraper = EblocScraper()
    try:
        logged_in = await scraper.login(user.ebloc_username, password)
        if not logged_in:
            raise HTTPException(status_code=401, detail="Invalid e-bloc credentials")
        
        # Find matching associations by address fields
        matches = await scraper.find_matching_associations(prop.name)
        
        if not matches:
            raise HTTPException(status_code=404, detail=f"Could not find matching E-bloc association for property: {prop.name}")
        
        # Check if all matches have score 0 (fallback case - no matches found)
        all_fallback = all(m.get("score", 0) == 0 for m in matches)
        
        # If multiple matches and no association_id provided, return them for user selection
        # Also return if all matches are fallback (no match found)
        if (len(matches) > 1 and not association_id) or (all_fallback and not association_id):
            return {
                "status": "multiple_matches",
                "property_id": property_id,
                "property_name": prop.name,
                "matches": [
                    {
                        "id": m["id"],
                        "nume": m["nume"],
                        "address": f"{m['adr_strada']} {m['adr_nr']}".strip(),
                        "score": m["score"],
                        "apartment_index": m.get("apartment_index")
                    }
                    for m in matches
                ]
            }
        
        # Single match or association_id provided - proceed with sync
        selected_match = next((m for m in matches if m["id"] == association_id), matches[0]) if association_id else matches[0]
        selected_association_id = selected_match["id"]
        selected_apartment_index = selected_match.get("apartment_index")
        selected_apartment_id = selected_match.get("apartment_id")  # id_ap from gInfoAp for cookie
        
        # Navigate to Datorii page once and get the soup
        matched_asoc_id, soup = await scraper.ensure_cookies_and_navigate(
            property_name=prop.name, 
            association_id=selected_association_id, 
            apartment_index=selected_apartment_index, 
            apartment_id=selected_apartment_id
        )
        
        if soup is None:
            raise HTTPException(status_code=500, detail="Could not navigate to Datorii page")
        
        # Use the same soup for both balance and payments to avoid duplicate navigation
        balance = await scraper.get_balance(property_name=prop.name, association_id=selected_association_id, apartment_index=selected_apartment_index, apartment_id=selected_apartment_id, soup=soup)
        payments = await scraper.get_payments(property_name=prop.name, association_id=selected_association_id, apartment_index=selected_apartment_index, apartment_id=selected_apartment_id, soup=soup)
        
        # Create/update E-Bloc bill from outstanding balance
        # There can only be one E-Bloc bill per property
        # Always create a bill, even if balance is 0 (with PAID status)
        bills_created = []
        # Find and delete any existing E-Bloc bills for this property
        existing_bills = db.list_bills(property_id=property_id)
        existing_ebloc_bills = [b for b in existing_bills if b.bill_type == BillType.EBLOC and b.renter_id is None]
        
        for existing_bill in existing_ebloc_bills:
            db.delete_bill(existing_bill.id)
            logger.info(f"[E-Bloc] Deleted existing E-Bloc bill {existing_bill.id} for property {property_id}")
        
        # Determine amount and status
        outstanding_debt = balance.outstanding_debt if balance else 0.0
        if outstanding_debt > 0:
            bill_status = BillStatus.OVERDUE
        else:
            bill_status = BillStatus.PAID  # Green "paid" status for 0 balance
        
        # Create a new E-Bloc bill (always create, even if 0)
        bill = Bill(
            property_id=property_id,
            renter_id=None,  # Applies to all renters in the property
            bill_type=BillType.EBLOC,
            description="E-Bloc",  # Simple description as requested
            amount=outstanding_debt,
            due_date=balance.last_payment_date if balance and balance.last_payment_date else datetime.utcnow(),
            status=bill_status
        )
        db.save_bill(bill)
        bills_created.append(bill.id)
        logger.info(f"[E-Bloc] Created E-Bloc bill {bill.id} for property {property_id} with amount {outstanding_debt} Lei, status: {bill_status}")
        
        # Create payment records from receipts
        payments_created = []
        for payment in payments:
            # Find matching bill or create one
            matching_bills = [b for b in db.list_bills(property_id=property_id) 
                            if b.bill_type == BillType.EBLOC and b.renter_id is None and abs(b.amount - payment.amount) < 0.01]
            
            if matching_bills:
                bill = matching_bills[0]
            else:
                # Create a bill for this payment
                bill = Bill(
                    property_id=property_id,
                    renter_id=None,  # Applies to all renters in the property
                    bill_type=BillType.EBLOC,
                    description=f"E-bloc payment receipt {payment.receipt_number}",
                    amount=payment.amount,
                    due_date=payment.payment_date,
                    status=BillStatus.PAID,
                    bill_number=payment.receipt_number
                )
                db.save_bill(bill)
            
            # Create payment record
            existing_payment = next((p for p in db.list_payments() if p.bill_id == bill.id and abs(p.amount - payment.amount) < 0.01), None)
            if not existing_payment:
                payment_record = Payment(
                    bill_id=bill.id,
                    amount=payment.amount,
                    method=PaymentMethod.BANK_TRANSFER,
                    status=PaymentStatus.COMPLETED,
                    commission=0.0
                )
                db.save_payment(payment_record)
                payments_created.append(payment_record.id)
        
        return {
            "status": "success",
            "property_id": property_id,
            "property_name": prop.name,
            "balance": {
                "outstanding_debt": balance.outstanding_debt if balance else 0.0,
                "last_payment_date": balance.last_payment_date.isoformat() if balance and balance.last_payment_date else None,
                "oldest_debt_month": balance.oldest_debt_month if balance else None
            } if balance else None,
            "bills_created": len(bills_created),
            "payments_created": len(payments_created)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing e-bloc: {str(e)}")
    finally:
        await scraper.close()


@app.get("/payments")
async def list_payments(current_user: TokenData = Depends(require_landlord)):
    if current_user.role == UserRole.ADMIN:
        return db.list_payments()
    landlord_bills = set()
    for prop in db.list_properties(landlord_id=current_user.user_id):
        for bill in db.list_bills(property_id=prop.id):
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
        "can_add_property": not needs_subscription or user.subscription_tier > 0,
    }




@app.post("/bills/parse-pdf")
async def parse_bill_pdf(
    file: UploadFile = File(...),
    property_id: str = Query(...),
    current_user: TokenData = Depends(require_landlord),
):
    """Parse PDF bill and check if it matches any extraction patterns. Returns extraction result with address matching warning."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Verify property access
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    pdf_bytes = await file.read()
    patterns = db.list_extraction_patterns()
    import logging
    import sys
    logger = logging.getLogger(__name__)
    # Ensure logger has a handler and is set to INFO level
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info(f"[PDF Parse] Starting parse for property {property_id}, {len(patterns)} patterns")
    result, pattern_to_update = parse_pdf_with_patterns(pdf_bytes, patterns)
    
    # Update pattern in database if bank accounts changed
    if pattern_to_update:
        pattern_to_update.bank_accounts = result.bank_accounts
        db.save_extraction_pattern(pattern_to_update)
        logger.info(f"[PDF Parse] Updated pattern '{pattern_to_update.name}' bank accounts: {len(result.bank_accounts)}")
    
    logger.info(f"[PDF Parse] Result: pattern={result.matched_pattern_supplier}, amount={result.amount}, due_date={result.due_date}, bill_number={result.bill_number}")
    
    # Check if extracted address matches property address
    address_matches = True
    address_warning = None
    address_confidence = 100  # Default to 100% if no address to compare
    if result.address and prop.address:
        # Simple address matching - check if key parts match
        extracted_lower = result.address.lower()
        property_lower = prop.address.lower()
        
        # Normalize addresses for comparison (remove common words, normalize whitespace)
        import re
        def normalize_address(addr: str) -> str:
            # Remove common words
            addr = re.sub(r'\b(nr\.?|număr|numar|bloc|bl\.?|scara|sc\.?|ap\.?|apartament|sector|sect\.?)\b', '', addr, flags=re.IGNORECASE)
            # Normalize whitespace
            addr = re.sub(r'\s+', ' ', addr).strip()
            return addr
        
        normalized_extracted = normalize_address(extracted_lower)
        normalized_property = normalize_address(property_lower)
        
        # Calculate confidence score based on word matching
        # Extract all words (including short ones like "nr", "ap", "sc") and numbers
        def extract_all_tokens(addr: str) -> set:
            # Extract words and numbers
            tokens = set()
            # Get all words (including short ones)
            words = re.findall(r'\b[a-zăâîșț]+\b', addr, re.IGNORECASE)
            tokens.update(w.lower() for w in words if w)
            # Get all numbers
            numbers = re.findall(r'\d+', addr)
            tokens.update(numbers)
            return tokens
        
        extracted_tokens = extract_all_tokens(normalized_extracted)
        property_tokens = extract_all_tokens(normalized_property)
        common_tokens = extracted_tokens & property_tokens
        
        # Also check for key address components
        def extract_key_components(addr: str) -> dict:
            components = {}
            # Street name (first significant word, usually after common prefixes)
            street_match = re.search(r'\b(strada|str|aleea|alee|bd|bulevardul|calea)\s+([a-zăâîșț]+)', addr, re.IGNORECASE)
            if street_match:
                components['street'] = street_match.group(2).lower()
            # Number
            nr_match = re.search(r'(?:nr|număr|numar)[\s\.:]*(\d+)', addr, re.IGNORECASE)
            if nr_match:
                components['number'] = nr_match.group(1)
            # Block/Building
            bl_match = re.search(r'\b(bl|bloc)[\s\.:]*([a-z0-9/]+)', addr, re.IGNORECASE)
            if bl_match:
                components['block'] = re.sub(r'[^a-z0-9]', '', bl_match.group(2).lower())
            # Staircase/Scara
            sc_match = re.search(r'\b(sc|scara|scara)[\s\.:]*([a-z0-9/]+)', addr, re.IGNORECASE)
            if sc_match:
                components['staircase'] = re.sub(r'[^a-z0-9]', '', sc_match.group(2).lower())
            # Apartment
            ap_match = re.search(r'\b(ap|apartament)[\s\.:]*(\d+)', addr, re.IGNORECASE)
            if ap_match:
                components['apartment'] = ap_match.group(2)
            return components
        
        extracted_components = extract_key_components(extracted_lower)
        property_components = extract_key_components(property_lower)
        
        # Count matching components
        matching_components = 0
        total_components = 0
        for key in ['street', 'number', 'block', 'staircase', 'apartment']:
            if key in extracted_components or key in property_components:
                total_components += 1
                if key in extracted_components and key in property_components:
                    if extracted_components[key] == property_components[key]:
                        matching_components += 1
        
        # Calculate confidence based on both token overlap and component matching
        if not extracted_tokens or not property_tokens:
            # If no tokens, check exact match
            if normalized_extracted == normalized_property:
                address_confidence = 100
            else:
                address_confidence = 0
        else:
            # Token overlap score (40% weight)
            total_tokens = len(extracted_tokens | property_tokens)
            token_score = 0
            if total_tokens > 0:
                token_score = (len(common_tokens) / total_tokens) * 40
            
            # Component matching score (60% weight)
            component_score = 0
            if total_components > 0:
                component_score = (matching_components / total_components) * 60
            else:
                # If no components found, use token score with higher weight
                component_score = token_score * 1.5
            
            # Bonus for substring match
            substring_bonus = 0
            if normalized_extracted in normalized_property or normalized_property in normalized_extracted:
                substring_bonus = 10
            
            address_confidence = min(100, int(token_score + component_score + substring_bonus))
        
        # Log for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"[Address Match] Property: '{prop.address}'")
        logger.debug(f"[Address Match] Extracted: '{result.address}'")
        logger.debug(f"[Address Match] Common tokens: {common_tokens}")
        logger.debug(f"[Address Match] Extracted components: {extracted_components}")
        logger.debug(f"[Address Match] Property components: {property_components}")
        logger.debug(f"[Address Match] Matching components: {matching_components}/{total_components}")
        logger.debug(f"[Address Match] Confidence: {address_confidence}%")
        
        # Only show warning if confidence is below 90%
        if address_confidence < 90:
            address_matches = False
            address_warning = f"Address mismatch detected (confidence: {address_confidence}%). The extracted address may not match this property."
    
    return {
        **result.model_dump(),
        "address_matches": address_matches,
        "address_warning": address_warning,
        "address_confidence": address_confidence,
        "property_address": prop.address,
    }


@app.post("/bills/create-from-pdf")
async def create_bill_from_pdf(
    data: dict,
    current_user: TokenData = Depends(require_landlord),
):
    """Create a bill from parsed PDF data."""
    property_id = data.get("property_id")
    if not property_id:
        raise HTTPException(status_code=400, detail="property_id is required")
    
    # Verify property access
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Parse due date
    from datetime import datetime
    due_date_str = data.get("due_date")
    if not due_date_str:
        raise HTTPException(status_code=400, detail="due_date is required")
    
    try:
        # Try parsing different date formats
        due_date = None
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"]:
            try:
                due_date = datetime.strptime(due_date_str, fmt)
                break
            except ValueError:
                continue
        if not due_date:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {due_date_str}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing due_date: {str(e)}")
    
    # Create bill
    bill = Bill(
        property_id=property_id,
        renter_id=data.get("renter_id"),
        bill_type=BillType(data.get("bill_type", "utilities")),
        description=data.get("description", "Bill from PDF"),
        amount=float(data.get("amount", 0)),
        due_date=due_date,
        iban=data.get("iban"),
        bill_number=data.get("bill_number"),
        extraction_pattern_id=data.get("extraction_pattern_id"),
        contract_id=data.get("contract_id"),
        status=BillStatus.PENDING,
    )
    db.save_bill(bill)
    return bill


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
        supplier=data.supplier,
        vendor_hint=data.vendor_hint,
        iban_pattern=data.iban_pattern,
        amount_pattern=data.amount_pattern,
        address_pattern=data.address_pattern,
        bill_number_pattern=data.bill_number_pattern,
        contract_id_pattern=data.contract_id_pattern,
        due_date_pattern=data.due_date_pattern,
        business_name_pattern=data.business_name_pattern,
        bank_accounts=data.bank_accounts,
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
    if data.contract_id_pattern is not None:
        pattern.contract_id_pattern = data.contract_id_pattern
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
