"""Admin management routes."""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pathlib import Path
from app.models import (
    User, UserCreate, UserUpdate, TokenData, SubscriptionStatus,
    ExtractionPattern, ExtractionPatternCreate, ExtractionPatternUpdate
)
from app.auth import require_admin
from app.database import db
from app.routes.auth_routes import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


def load_extraction_patterns_from_json(force_update: bool = False):
    """Load extraction patterns from JSON files in the extraction_patterns directory."""
    from app.models import ExtractionPatternCreate, ExtractionPatternUpdate, BillType
    import json
    import os
    
    patterns_dir = Path(__file__).parent.parent.parent / "extraction_patterns"
    if not patterns_dir.exists():
        return []
    
    results = []
    
    for json_file in patterns_dir.glob("*.json"):
        # Skip suppliers.json - it's not an extraction pattern
        if json_file.name == "suppliers.json":
            continue
            
        try:
            # Get file modification time
            file_mtime = datetime.fromtimestamp(os.path.getmtime(json_file))
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Skip if data is a list (not a pattern object)
            if isinstance(data, list):
                logger.debug(f"Skipping {json_file.name} - file contains a list, not a pattern object")
                continue
            
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


@router.post("/refresh-patterns")
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


@router.post("/test-scraper")
async def test_scraper_endpoint(
    supplier_name: str = Query(...),
    username: str = Query(...),
    password: str = Query(...),
    login_only: bool = Query(False),
    current_user: TokenData = Depends(require_admin)
):
    """
    Test scraper configuration for a supplier (admin only).
    Useful for debugging scraper configs before integrating them.
    """
    from app.web_scraper import WebScraper, load_scraper_config
    
    logger.info(f"[Test Scraper] Testing {supplier_name} scraper")
    
    config = load_scraper_config(supplier_name)
    if not config:
        raise HTTPException(status_code=404, detail=f"Scraper config not found for {supplier_name}")
    
    scraper = WebScraper(config, save_html_dumps=True)  # Enable HTML dumps for debugging
    result = {
        "supplier_name": supplier_name,
        "config_loaded": True,
        "login_success": False,
        "bills_found": 0,
        "bills": [],
        "error": None
    }
    
    try:
        # Test login
        logged_in = await scraper.login(username, password)
        result["login_success"] = logged_in
        
        if not logged_in:
            result["error"] = "Login failed - check credentials and login_success_indicator in config"
            return result
        
        if login_only:
            return result
        
        # Test getting bills
        bills = await scraper.get_bills()
        result["bills_found"] = len(bills)
        
        for bill in bills:
            result["bills"].append({
                "bill_number": bill.bill_number,
                "amount": bill.amount,
                "due_date": bill.due_date.isoformat() if bill.due_date else None,
                "pdf_url": bill.pdf_url,
                "has_pdf": bool(bill.pdf_content),
                "pdf_size": len(bill.pdf_content) if bill.pdf_content else 0,
            })
        
    except Exception as e:
        logger.error(f"[Test Scraper] Error: {e}", exc_info=True)
        result["error"] = str(e)
    
    finally:
        await scraper.close()
    
    return result


@router.get("/users")
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


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, _: TokenData = Depends(require_admin)):
    if db.get_user_by_email(data.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    password_hash = None
    if data.password:
        password_hash = hash_password(data.password)
    user = User(email=data.email, name=data.name, role=data.role, password_hash=password_hash)
    db.save_user(user)
    return user


@router.get("/users/{user_id}")
async def get_user(user_id: str, _: TokenData = Depends(require_admin)):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}")
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


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, _: TokenData = Depends(require_admin)):
    if not db.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    db.delete_user(user_id)
    return {"status": "deleted"}


@router.put("/users/{user_id}/subscription")
async def update_subscription(
    user_id: str,
    tier: int = 0,  # 0 = off, 1 = on
    expires: datetime = None,
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


@router.get("/extraction-patterns")
async def list_extraction_patterns(_: TokenData = Depends(require_admin)):
    return db.list_extraction_patterns()


@router.post("/extraction-patterns", status_code=status.HTTP_201_CREATED)
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


@router.get("/extraction-patterns/{pattern_id}")
async def get_extraction_pattern(pattern_id: str, _: TokenData = Depends(require_admin)):
    pattern = db.get_extraction_pattern(pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern


@router.put("/extraction-patterns/{pattern_id}")
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


@router.delete("/extraction-patterns/{pattern_id}")
async def delete_extraction_pattern(pattern_id: str, _: TokenData = Depends(require_admin)):
    if not db.get_extraction_pattern(pattern_id):
        raise HTTPException(status_code=404, detail="Pattern not found")
    db.delete_extraction_pattern(pattern_id)
    return {"status": "deleted"}

