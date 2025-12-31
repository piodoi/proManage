"""Sync routes for supplier and ebloc synchronization with progress tracking."""
import logging
import asyncio
import platform
from datetime import datetime
from typing import Optional, List, Callable, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
import json
import httpx

from app.models import (
    Supplier, ExtractionPattern, Bill, BillType, BillStatus,
    Payment, PaymentMethod, PaymentStatus, TokenData, UserRole
)
from app.auth import require_landlord
from app.database import db
from app.utils.encryption import decrypt_password

router = APIRouter(tags=["sync"])
logger = logging.getLogger(__name__)


async def _send_progress_update(supplier_name: str, status: str, bills_found: int = 0, bills_created: int = 0, error: Optional[str] = None):
    """Helper to format progress updates for SSE"""
    return {
        "supplier_name": supplier_name,
        "status": status,  # "starting", "processing", "completed", "error"
        "bills_found": bills_found,
        "bills_created": bills_created,
        "error": error
    }


def _run_sync_supplier_scraper_in_thread(
    property_id: str,
    username: str,
    password: str,
    supplier: Supplier,
    patterns: List[ExtractionPattern],
    property_supplier_id: str,
    save_html_dumps: bool = False,
    progress_callback: Optional[Callable] = None
) -> tuple[int, int]:  # Returns (bills_found, bills_created)
    """Run scraper sync using Playwright sync API in a thread (for Windows compatibility)"""
    from app.web_scraper_sync import WebScraperSync
    from app.web_scraper import load_scraper_config
    from app.pdf_parser import parse_pdf_with_patterns
    
    log = logging.getLogger(__name__)
    log.info(f"[{supplier.name} Scraper] Starting sync (sync API) for property {property_id}")
    
    if progress_callback:
        progress_callback(supplier.name, "starting", 0, 0)
    
    # Load scraper configuration
    config = load_scraper_config(supplier.name)
    if not config:
        log.warning(f"[{supplier.name} Scraper] No scraper configuration found for {supplier.name}, skipping")
        if progress_callback:
            progress_callback(supplier.name, "error", 0, 0, "No scraper configuration found")
        return 0, 0
    
    # Find extraction pattern
    supplier_pattern = None
    for pattern in patterns:
        if pattern.supplier and pattern.supplier.lower() == supplier.name.lower():
            supplier_pattern = pattern
            break
    
    scraper = WebScraperSync(config, save_html_dumps=save_html_dumps)
    bills_created = 0
    bills_found = 0
    
    # Get property supplier to check/update contract_id
    property_supplier = db.get_property_supplier(property_supplier_id)
    contract_id_filter = property_supplier.contract_id if property_supplier else None
    contract_id_to_save = None
    
    try:
        # Login (sync version)
        logged_in = scraper.login(username, password)
        if not logged_in:
            error_msg = f"Failed to login to {supplier.name}"
            if progress_callback:
                progress_callback(supplier.name, "error", 0, 0, error_msg)
            raise Exception(error_msg)
        
        # Get bills (sync version)
        scraped_bills = scraper.get_bills()
        bills_found = len(scraped_bills)
        log.info(f"[{supplier.name} Scraper] Found {bills_found} bill(s)")
        
        if progress_callback:
            progress_callback(supplier.name, "processing", bills_found, 0)
        
        existing_bills = db.list_bills(property_id=property_id)
        
        for scraped_bill in scraped_bills:
            # Check if bill already exists
            existing = None
            if scraped_bill.bill_number:
                existing = next(
                    (b for b in existing_bills 
                     if b.bill_number == scraped_bill.bill_number 
                     and b.bill_type == supplier.bill_type),
                    None
                )
            
            if not existing and scraped_bill.due_date and scraped_bill.amount:
                for b in existing_bills:
                    if (b.bill_type == supplier.bill_type and 
                        b.description == supplier.name and
                        abs(b.amount - scraped_bill.amount) < 0.01):
                        if b.due_date:
                            days_diff = abs((b.due_date - scraped_bill.due_date).days)
                            if days_diff <= 5:
                                existing = b
                                break
            
            if existing:
                log.debug(f"[{supplier.name} Scraper] Bill {scraped_bill.bill_number} already exists, skipping")
                continue
            
            # Extract data from scraped bill
            iban = scraped_bill.raw_data.get("iban") if scraped_bill.raw_data else None
            bill_number = scraped_bill.bill_number
            amount = scraped_bill.amount
            due_date = scraped_bill.due_date if scraped_bill.due_date else datetime.utcnow()
            extracted_contract_id = scraped_bill.contract_id
            
            # Parse PDF if available
            if scraped_bill.pdf_content and supplier_pattern:
                try:
                    pdf_result = parse_pdf_with_patterns(
                        scraped_bill.pdf_content,
                        patterns=[supplier_pattern],
                        property_id=property_id
                    )
                    
                    if pdf_result.iban:
                        iban = pdf_result.iban
                    if pdf_result.bill_number:
                        bill_number = pdf_result.bill_number
                    if pdf_result.amount:
                        amount = pdf_result.amount
                    if pdf_result.contract_id and not extracted_contract_id:
                        extracted_contract_id = pdf_result.contract_id
                    if pdf_result.due_date:
                        try:
                            if '/' in pdf_result.due_date:
                                parts = pdf_result.due_date.split('/')
                                if len(parts) == 3:
                                    due_date = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                            elif '.' in pdf_result.due_date:
                                parts = pdf_result.due_date.split('.')
                                if len(parts) == 3:
                                    due_date = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                        except:
                            pass
                except Exception as e:
                    log.warning(f"[{supplier.name} Scraper] Error parsing PDF: {e}")
            
            # Filter by contract_id if specified
            if contract_id_filter and extracted_contract_id:
                if extracted_contract_id != contract_id_filter:
                    log.debug(f"[{supplier.name} Scraper] Skipping bill - contract_id mismatch")
                    continue
            
            # Save contract_id if we extracted it and it's not set yet
            if extracted_contract_id and not contract_id_to_save:
                contract_id_to_save = extracted_contract_id
            
            # Determine bill status
            bill_status = BillStatus.PENDING
            if due_date < datetime.utcnow():
                bill_status = BillStatus.OVERDUE
            
            # Create bill
            bill = Bill(
                property_id=property_id,
                renter_id=None,
                bill_type=supplier.bill_type,
                description=supplier.name,
                amount=amount or 0.0,
                due_date=due_date,
                iban=iban,
                bill_number=bill_number,
                extraction_pattern_id=supplier_pattern.id if supplier_pattern else None,
                contract_id=extracted_contract_id,
                status=bill_status
            )
            db.save_bill(bill)
            bills_created += 1
            log.info(f"[{supplier.name} Scraper] Created bill {bill.id}: {supplier.name} - {amount} RON")
        
        # Save contract_id if we extracted it and property_supplier doesn't have it yet
        if contract_id_to_save and property_supplier and not property_supplier.contract_id:
            property_supplier.contract_id = contract_id_to_save
            db.save_property_supplier(property_supplier)
            log.info(f"[{supplier.name} Scraper] Saved contract_id {contract_id_to_save} to property supplier")
        
        if progress_callback:
            progress_callback(supplier.name, "completed", bills_found, bills_created)
        
        return bills_found, bills_created
    
    except Exception as e:
        error_msg = str(e)
        log.error(f"[{supplier.name} Scraper] Error during sync: {error_msg}", exc_info=True)
        if progress_callback:
            progress_callback(supplier.name, "error", bills_found, bills_created, error_msg)
        raise Exception(error_msg)
    finally:
        scraper.close()


async def _sync_supplier_scraper(
    property_id: str,
    username: str,
    password: str,
    supplier: Supplier,
    patterns: List[ExtractionPattern],
    logger: logging.Logger,
    property_supplier_id: str,
    save_html_dumps: bool = False,
    progress_callback: Optional[Callable] = None
) -> tuple[int, int]:  # Returns (bills_found, bills_created)
    """Sync bills from supplier using web scraper"""
    from app.web_scraper import WebScraper, load_scraper_config
    from app.pdf_parser import parse_pdf_with_patterns
    
    logger.info(f"[{supplier.name} Scraper] Starting sync for property {property_id}")
    
    if progress_callback:
        progress_callback(supplier.name, "starting", 0, 0)
    
    # Load scraper configuration
    config = load_scraper_config(supplier.name)
    if not config:
        logger.warning(f"[{supplier.name} Scraper] No scraper configuration found for {supplier.name}, skipping")
        if progress_callback:
            progress_callback(supplier.name, "error", 0, 0, "No scraper configuration found")
        return 0, 0
    
    # Find extraction pattern
    supplier_pattern = None
    for pattern in patterns:
        if pattern.supplier and pattern.supplier.lower() == supplier.name.lower():
            supplier_pattern = pattern
            break
    
    scraper = WebScraper(config, save_html_dumps=save_html_dumps)
    bills_created = 0
    bills_found = 0
    
    # Get property supplier to check/update contract_id
    property_supplier = db.get_property_supplier(property_supplier_id)
    contract_id_filter = property_supplier.contract_id if property_supplier else None
    contract_id_to_save = None
    
    try:
        logged_in = await scraper.login(username, password)
        if not logged_in:
            error_msg = f"Failed to login to {supplier.name}"
            if progress_callback:
                progress_callback(supplier.name, "error", 0, 0, error_msg)
            raise Exception(error_msg)
        
        # Get bills
        scraped_bills = await scraper.get_bills()
        bills_found = len(scraped_bills)
        logger.info(f"[{supplier.name} Scraper] Found {bills_found} bill(s)")
        
        if progress_callback:
            progress_callback(supplier.name, "processing", bills_found, 0)
        
        existing_bills = db.list_bills(property_id=property_id)
        
        for scraped_bill in scraped_bills:
            # Check if bill already exists
            existing = None
            if scraped_bill.bill_number:
                existing = next(
                    (b for b in existing_bills 
                     if b.bill_number == scraped_bill.bill_number 
                     and b.bill_type == supplier.bill_type),
                    None
                )
            
            if not existing and scraped_bill.due_date and scraped_bill.amount:
                for b in existing_bills:
                    if (b.bill_type == supplier.bill_type and 
                        b.description == supplier.name and
                        abs(b.amount - scraped_bill.amount) < 0.01):
                        if b.due_date:
                            days_diff = abs((b.due_date - scraped_bill.due_date).days)
                            if days_diff <= 5:
                                existing = b
                                break
            
            if existing:
                logger.debug(f"[{supplier.name} Scraper] Bill {scraped_bill.bill_number} already exists, skipping")
                continue
            
            iban = scraped_bill.raw_data.get("iban") if scraped_bill.raw_data else None
            bill_number = scraped_bill.bill_number
            amount = scraped_bill.amount
            due_date = scraped_bill.due_date if scraped_bill.due_date else datetime.utcnow()
            extracted_contract_id = scraped_bill.contract_id
            
            if scraped_bill.pdf_content and supplier_pattern:
                try:
                    pdf_result = parse_pdf_with_patterns(
                        scraped_bill.pdf_content,
                        patterns=[supplier_pattern],
                        property_id=property_id
                    )
                    
                    if pdf_result.iban:
                        iban = pdf_result.iban
                    if pdf_result.bill_number:
                        bill_number = pdf_result.bill_number
                    if pdf_result.amount:
                        amount = pdf_result.amount
                    if pdf_result.contract_id and not extracted_contract_id:
                        extracted_contract_id = pdf_result.contract_id
                    if pdf_result.due_date:
                        try:
                            if '/' in pdf_result.due_date:
                                parts = pdf_result.due_date.split('/')
                                if len(parts) == 3:
                                    due_date = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                            elif '.' in pdf_result.due_date:
                                parts = pdf_result.due_date.split('.')
                                if len(parts) == 3:
                                    due_date = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                        except:
                            pass
                except Exception as e:
                    logger.warning(f"[{supplier.name} Scraper] Error parsing PDF: {e}")
            
            if contract_id_filter and extracted_contract_id:
                if extracted_contract_id != contract_id_filter:
                    logger.debug(f"[{supplier.name} Scraper] Skipping bill - contract_id mismatch")
                    continue
            
            if extracted_contract_id and not contract_id_to_save:
                contract_id_to_save = extracted_contract_id
            
            bill_status = BillStatus.PENDING
            if due_date < datetime.utcnow():
                bill_status = BillStatus.OVERDUE
            
            bill = Bill(
                property_id=property_id,
                renter_id=None,
                bill_type=supplier.bill_type,
                description=supplier.name,
                amount=amount or 0.0,
                due_date=due_date,
                iban=iban,
                bill_number=bill_number,
                extraction_pattern_id=supplier_pattern.id if supplier_pattern else None,
                contract_id=extracted_contract_id,
                status=bill_status
            )
            db.save_bill(bill)
            bills_created += 1
            logger.info(f"[{supplier.name} Scraper] Created bill {bill.id}: {supplier.name} - {amount} RON")
        
        if contract_id_to_save and property_supplier and not property_supplier.contract_id:
            property_supplier.contract_id = contract_id_to_save
            db.save_property_supplier(property_supplier)
            logger.info(f"[{supplier.name} Scraper] Saved contract_id {contract_id_to_save} to property supplier")
        
        if progress_callback:
            progress_callback(supplier.name, "completed", bills_found, bills_created)
        
        return bills_found, bills_created
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{supplier.name} Scraper] Error during sync: {error_msg}", exc_info=True)
        if progress_callback:
            progress_callback(supplier.name, "error", bills_found, bills_created, error_msg)
        raise Exception(error_msg)
    finally:
        await scraper.close()


@router.post("/suppliers/sync/{property_id}")
async def sync_supplier_bills(property_id: str, current_user: TokenData = Depends(require_landlord)):
    """
    Sync bills from all suppliers with credentials configured for this property.
    Returns progress information including supplier status and bill counts.
    """
    try:
        logger.info(f"[Suppliers Sync] Starting sync for property {property_id}, user {current_user.user_id}")
        
        prop = db.get_property(property_id)
        if not prop:
            logger.error(f"[Suppliers Sync] Property {property_id} not found")
            raise HTTPException(status_code=404, detail="Property not found")
        if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
            logger.error(f"[Suppliers Sync] Access denied for property {property_id}, user {current_user.user_id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get all property suppliers with credentials
        logger.info(f"[Suppliers Sync] Getting property suppliers for property {property_id}")
        property_suppliers = db.list_property_suppliers(property_id)
        logger.info(f"[Suppliers Sync] Found {len(property_suppliers)} property supplier(s)")
        
        suppliers_to_sync = []
        for ps in property_suppliers:
            supplier = db.get_supplier(ps.supplier_id)
            if supplier and ps.username and ps.password_hash:
                logger.debug(f"[Suppliers Sync] Checking supplier {supplier.name}: has_api={supplier.has_api}, has_username={bool(ps.username)}, has_password={bool(ps.password_hash)}")
                suppliers_to_sync.append((supplier, ps))
        
        logger.info(f"[Suppliers Sync] {len(suppliers_to_sync)} supplier(s) ready to sync")
        
        if not suppliers_to_sync:
            logger.warning(f"[Suppliers Sync] No suppliers with credentials configured for property {property_id}")
            return {
                "status": "no_suppliers",
                "message": "No suppliers with credentials configured for this property",
                "progress": []
            }
        
        # Find extraction pattern for supplier matching
        all_patterns = db.list_extraction_patterns()
        logger.debug(f"[Suppliers Sync] Loaded {len(all_patterns)} extraction patterns")
        
        bills_created = 0
        errors = []
        progress = []  # Track progress for each supplier
        
        # Progress callback to update progress list
        def update_progress(supplier_name: str, status: str, bills_found: int = 0, bills_created: int = 0, error: Optional[str] = None):
            # Find existing progress entry or create new one
            existing = next((p for p in progress if p["supplier_name"] == supplier_name), None)
            if existing:
                existing["status"] = status
                existing["bills_found"] = bills_found
                existing["bills_created"] = bills_created
                if error:
                    existing["error"] = error
            else:
                progress.append({
                    "supplier_name": supplier_name,
                    "status": status,
                    "bills_found": bills_found,
                    "bills_created": bills_created,
                    "error": error
                })
        
        for idx, (supplier, property_supplier) in enumerate(suppliers_to_sync, 1):
            # Get credentials from user-supplier credential
            username = None
            password = None
            if property_supplier.credential_id:
                credential = db.get_user_supplier_credential(property_supplier.credential_id)
                if credential:
                    username = decrypt_password(credential.username) if credential.username else None
                    password = decrypt_password(credential.password_hash) if credential.password_hash else None
                    logger.debug(f"[Suppliers Sync] Credentials decrypted for {supplier.name}")
            
            try:
                logger.info(f"[Suppliers Sync] Syncing {supplier.name} ({idx}/{len(suppliers_to_sync)}) for property {property_id}")
                
                # Sync based on supplier capabilities
                if supplier.has_api:
                    logger.warning(f"[Suppliers Sync] Supplier {supplier.name} has API flag but API integration not implemented")
                    error_msg = f"{supplier.name}: API integration not yet implemented"
                    errors.append(error_msg)
                    update_progress(supplier.name, "error", 0, 0, error_msg)
                else:
                    # Use web scraper for suppliers without API
                    logger.info(f"[Suppliers Sync] Starting {supplier.name} scraper sync")
                    
                    from app.web_scraper import load_scraper_config
                    config = load_scraper_config(supplier.name)
                    if config and config.requires_js:
                        # On Windows, use sync API in thread executor
                        if platform.system() == 'Windows':
                            logger.info(f"[Suppliers Sync] Using sync API scraper for {supplier.name} (Windows + requires_js=True)")
                            bills_found, bills_count = await asyncio.to_thread(
                                _run_sync_supplier_scraper_in_thread,
                                property_id=property_id,
                                username=username,
                                password=password,
                                supplier=supplier,
                                patterns=all_patterns,
                                property_supplier_id=property_supplier.id,
                                save_html_dumps=False,
                                progress_callback=update_progress
                            )
                        else:
                            bills_found, bills_count = await _sync_supplier_scraper(
                                property_id=property_id,
                                username=username,
                                password=password,
                                supplier=supplier,
                                patterns=all_patterns,
                                logger=logger,
                                property_supplier_id=property_supplier.id,
                                save_html_dumps=False,
                                progress_callback=update_progress
                            )
                    else:
                        bills_found, bills_count = await _sync_supplier_scraper(
                            property_id=property_id,
                            username=username,
                            password=password,
                            supplier=supplier,
                            patterns=all_patterns,
                            logger=logger,
                            property_supplier_id=property_supplier.id,
                            save_html_dumps=False,
                            progress_callback=update_progress
                        )
                    bills_created += bills_count
                    logger.info(f"[Suppliers Sync] {supplier.name} sync completed: {bills_count} bill(s) created from {bills_found} found")
            
            except Exception as e:
                error_msg = str(e)
                if "Hidroelectrica" not in error_msg or "Sync" not in error_msg:
                    logger.error(f"[Suppliers Sync] Error syncing {supplier.name}: {error_msg}")
                errors.append(f"{supplier.name}: {error_msg}")
                update_progress(supplier.name, "error", 0, 0, error_msg)
        
        # Check if any supplier has multiple contracts (after sync)
        from app.web_scraper import load_scraper_config
        multiple_contracts_info = {}
        for supplier, property_supplier in suppliers_to_sync:
            config = load_scraper_config(supplier.name)
            if config and config.multiple_contracts_possible:
                supplier_bills = db.list_bills(property_id=property_id)
                supplier_contracts = {}
                for bill in supplier_bills:
                    if bill.contract_id and bill.description == supplier.name:
                        if bill.contract_id not in supplier_contracts:
                            supplier_contracts[bill.contract_id] = {
                                "contract_id": bill.contract_id,
                                "address": None
                            }
                
                if len(supplier_contracts) > 1:
                    multiple_contracts_info[supplier.id] = {
                        "supplier_name": supplier.name,
                        "contracts": list(supplier_contracts.values())
                    }
        
        result = {
            "status": "success",
            "property_id": property_id,
            "bills_created": bills_created,
            "errors": errors if errors else None,
            "multiple_contracts": multiple_contracts_info if multiple_contracts_info else None,
            "progress": progress  # Include progress information
        }
        logger.info(f"[Suppliers Sync] Sync completed for property {property_id}: {bills_created} bill(s) created, {len(errors)} error(s)")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Suppliers Sync] Unexpected error in sync endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error syncing suppliers: {str(e)}")


@router.post("/ebloc/sync/{property_id}")
async def sync_ebloc(
    property_id: str, 
    association_id: Optional[str] = Query(None), 
    current_user: TokenData = Depends(require_landlord)
):
    """Sync E-bloc bills and payments for a property."""
    from app.ebloc_scraper import EblocScraper
    
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get user ebloc credentials
    user = db.get_user(current_user.user_id)
    if not user or not user.ebloc_username or not user.ebloc_password_hash:
        raise HTTPException(status_code=404, detail="E-bloc not configured. Please configure your E-bloc credentials first.")
    
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
        
        matches = await scraper.find_matching_associations(prop.name)
        
        if not matches:
            raise HTTPException(status_code=404, detail=f"Could not find matching E-bloc association for property: {prop.name}")
        
        all_fallback = all(m.get("score", 0) == 0 for m in matches)
        
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
        
        selected_match = next((m for m in matches if m["id"] == association_id), matches[0]) if association_id else matches[0]
        selected_association_id = selected_match["id"]
        selected_apartment_index = selected_match.get("apartment_index")
        selected_apartment_id = selected_match.get("apartment_id")
        
        matched_asoc_id, soup = await scraper.ensure_cookies_and_navigate(
            property_name=prop.name, 
            association_id=selected_association_id, 
            apartment_index=selected_apartment_index, 
            apartment_id=selected_apartment_id
        )
        
        if soup is None:
            raise HTTPException(status_code=500, detail="Could not navigate to Datorii page")
        
        balance = await scraper.get_balance(property_name=prop.name, association_id=selected_association_id, apartment_index=selected_apartment_index, apartment_id=selected_apartment_id, soup=soup)
        payments = await scraper.get_payments(property_name=prop.name, association_id=selected_association_id, apartment_index=selected_apartment_index, apartment_id=selected_apartment_id, soup=soup)
        
        bills_created = []
        existing_bills = db.list_bills(property_id=property_id)
        existing_ebloc_bills = [b for b in existing_bills if b.bill_type == BillType.EBLOC and b.renter_id is None]
        
        for existing_bill in existing_ebloc_bills:
            db.delete_bill(existing_bill.id)
            logger.info(f"[E-Bloc] Deleted existing E-Bloc bill {existing_bill.id} for property {property_id}")
        
        outstanding_debt = balance.outstanding_debt if balance else 0.0
        if outstanding_debt > 0:
            bill_status = BillStatus.OVERDUE
        else:
            bill_status = BillStatus.PAID
        
        bill = Bill(
            property_id=property_id,
            renter_id=None,
            bill_type=BillType.EBLOC,
            description="E-Bloc",
            amount=outstanding_debt,
            due_date=balance.last_payment_date if balance and balance.last_payment_date else datetime.utcnow(),
            status=bill_status
        )
        db.save_bill(bill)
        bills_created.append(bill.id)
        logger.info(f"[E-Bloc] Created E-Bloc bill {bill.id} for property {property_id} with amount {outstanding_debt} Lei, status: {bill_status}")
        
        payments_created = []
        for payment in payments:
            matching_bills = [b for b in db.list_bills(property_id=property_id) 
                            if b.bill_type == BillType.EBLOC and b.renter_id is None and abs(b.amount - payment.amount) < 0.01]
            
            if matching_bills:
                bill = matching_bills[0]
            else:
                bill = Bill(
                    property_id=property_id,
                    renter_id=None,
                    bill_type=BillType.EBLOC,
                    description=f"E-bloc payment receipt {payment.receipt_number}",
                    amount=payment.amount,
                    due_date=payment.payment_date,
                    status=BillStatus.PAID,
                    bill_number=payment.receipt_number
                )
                db.save_bill(bill)
            
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
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError) as e:
        logger.warning(f"[E-Bloc] Network error during sync: {e}")
        raise HTTPException(
            status_code=503,
            detail="Network connection error. Please check your internet connection and try again in a moment."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing e-bloc: {str(e)}")
    finally:
        await scraper.close()

