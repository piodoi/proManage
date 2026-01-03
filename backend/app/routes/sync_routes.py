"""Sync routes for supplier and ebloc synchronization with progress tracking."""
import logging
import asyncio
import platform
from datetime import datetime
from typing import Optional, List, Callable, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
import json
import httpx
import uuid

from app.models import (
    Supplier, ExtractionPattern, Bill, BillType, BillStatus,
    Payment, PaymentMethod, PaymentStatus, TokenData, UserRole
)
from app.auth import require_landlord
from app.database import db
from app.utils.encryption import decrypt_password


def get_default_bill_currency(user_id: str) -> str:
    """Get default bill currency from user preferences, or return 'RON' as fallback."""
    preferences = db.get_user_preferences(user_id)
    if preferences and preferences.bill_currency:
        return preferences.bill_currency
    return "RON"

router = APIRouter(tags=["sync"])
logger = logging.getLogger(__name__)

# Store cancellation flags for active sync operations
_cancellation_flags: Dict[str, bool] = {}


async def _send_progress_update(supplier_name: str, status: str, bills_found: int = 0, bills_created: int = 0, error: Optional[str] = None):
    """Helper to format progress updates for SSE"""
    return {
        "supplier_name": supplier_name,
        "status": status,  # "starting", "processing", "completed", "error"
        "bills_found": bills_found,
        "bills_created": bills_created,
        "error": error
    }


async def _sync_supplier_scraper(
    property_id: str,
    username: str,
    password: str,
    supplier: Supplier,
    patterns: List[ExtractionPattern],
    logger: logging.Logger,
    property_supplier_id: str,
    save_html_dumps: bool = False,
    progress_callback: Optional[Callable] = None,
    discover_only: bool = False,
    bills_callback: Optional[Callable] = None
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
    
    # Get property to access landlord_id for currency preferences
    prop = db.get_property(property_id)
    if not prop:
        logger.error(f"[{supplier.name} Scraper] Property {property_id} not found")
        if progress_callback:
            progress_callback(supplier.name, "error", 0, 0, "Property not found")
        return 0, 0
    
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
        
        # Process all bills in a single pass
        for scraped_bill in scraped_bills:
            # Extract basic fields first
            iban = scraped_bill.raw_data.get("iban") if scraped_bill.raw_data else None
            bill_number = scraped_bill.bill_number
            amount = scraped_bill.amount
            due_date = scraped_bill.due_date if scraped_bill.due_date else datetime.utcnow()
            extracted_contract_id = scraped_bill.contract_id
            
            # Filter by contract_id EARLY - before expensive operations
            if contract_id_filter:
                filter_str = str(contract_id_filter).strip()
                extracted_str = str(extracted_contract_id).strip() if extracted_contract_id else None
                if not extracted_str or extracted_str != filter_str:
                    continue  # Skip early, no logging needed
            
            # Only parse PDF if we're missing critical information that might be in the PDF
            needs_pdf_parsing = (
                scraped_bill.pdf_content and 
                supplier_pattern and 
                (not bill_number or not amount or not extracted_contract_id)
            )
            
            if needs_pdf_parsing:
                try:
                    pdf_result, _ = parse_pdf_with_patterns(
                        scraped_bill.pdf_content,
                        patterns=[supplier_pattern]
                    )
                    
                    # Only use PDF data if we're missing it from the page
                    if pdf_result.iban and not iban:
                        iban = pdf_result.iban
                    if pdf_result.bill_number and not bill_number:
                        bill_number = pdf_result.bill_number
                    if pdf_result.amount and not amount:
                        amount = pdf_result.amount
                    if pdf_result.contract_id and not extracted_contract_id:
                        extracted_contract_id = pdf_result.contract_id
                    if pdf_result.due_date and not scraped_bill.due_date:
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
            
            # Check if bill already exists (only check after filtering by contract_id)
            existing = None
            if bill_number:
                existing = next(
                    (b for b in existing_bills 
                     if b.bill_number == bill_number 
                     and b.bill_type == supplier.bill_type),
                    None
                )
            
            if not existing and due_date and amount:
                for b in existing_bills:
                    if (b.bill_type == supplier.bill_type and 
                        b.description == supplier.name and
                        abs(b.amount - amount) < 0.01):
                        if b.due_date:
                            days_diff = abs((b.due_date - due_date).days)
                            if days_diff <= 5:
                                existing = b
                                break
            
            # In discover_only mode, show all bills even if they exist (user can decide)
            # In normal mode, skip duplicates to avoid creating duplicates
            if existing and not discover_only:
                continue  # Skip silently
            elif existing and discover_only:
                logger.debug(f"[{supplier.name} Scraper] Bill {bill_number} already exists in DB, but showing in discover mode")
            
            if extracted_contract_id and not contract_id_to_save:
                contract_id_to_save = extracted_contract_id
            
            bill_status = BillStatus.PENDING
            if due_date < datetime.utcnow():
                bill_status = BillStatus.OVERDUE
            
            # Get default currency from user preferences
            default_currency = get_default_bill_currency(landlord_id) if landlord_id else "RON"
            
            # Prepare bill data
            bill_data = {
                "property_id": property_id,
                "renter_id": None,
                "bill_type": supplier.bill_type.value if hasattr(supplier.bill_type, 'value') else str(supplier.bill_type),
                "description": supplier.name,
                "amount": amount or 0.0,
                "currency": default_currency,
                "due_date": due_date.isoformat() if isinstance(due_date, datetime) else due_date,
                "iban": iban,
                "bill_number": bill_number,
                "extraction_pattern_id": supplier_pattern.id if supplier_pattern else None,
                "contract_id": extracted_contract_id,
                "status": bill_status.value if hasattr(bill_status, 'value') else str(bill_status)
            }
            
            if discover_only:
                # Just collect the bill data, don't save
                if bills_callback:
                    bills_callback(bill_data)
                bills_created += 1
            else:
                # Create and save bill
                bill = Bill(**bill_data)
                db.save_bill(bill)
                bills_created += 1
        
        if contract_id_to_save and property_supplier and not property_supplier.contract_id:
            property_supplier.contract_id = contract_id_to_save
            db.save_property_supplier(property_supplier)
            logger.debug(f"[{supplier.name} Scraper] Saved contract_id {contract_id_to_save} to property supplier")
        
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


@router.post("/suppliers/sync/{property_id}/cancel")
async def cancel_sync(property_id: str, sync_id: str = Query(...), current_user: TokenData = Depends(require_landlord)):
    """Cancel an ongoing sync operation."""
    cancel_key = f"{property_id}:{sync_id}"
    if cancel_key in _cancellation_flags:
        _cancellation_flags[cancel_key] = True
        logger.info(f"[Suppliers Sync] Cancellation requested for {cancel_key}")
        return {"status": "cancelled"}
    return {"status": "not_found"}


@router.post("/suppliers/sync/{property_id}")
async def sync_supplier_bills(
    property_id: str,
    sync_id: Optional[str] = Query(None),
    supplier_ids: Optional[str] = Query(None, description="Comma-separated list of property supplier IDs to sync"),
    discover_only: bool = Query(False, description="If true, discover bills without saving them"),
    current_user: TokenData = Depends(require_landlord)
):
    """
    Sync bills from suppliers with credentials configured for this property.
    Returns progress information including supplier status and bill counts.
    If sync_id is provided, streams progress via Server-Sent Events.
    If discover_only is true, bills are discovered but not saved to the database.
    """
    # Generate sync_id if not provided
    if not sync_id:
        sync_id = str(uuid.uuid4())
    
    cancel_key = f"{property_id}:{sync_id}"
    _cancellation_flags[cancel_key] = False
    
    async def stream_sync_progress():
        """Generator function that streams progress updates via SSE."""
        try:
            def is_cancelled():
                return _cancellation_flags.get(cancel_key, False)
            
            def send_event(event_type: str, data: dict):
                """Send SSE event"""
                return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            
            # Send initial status
            yield send_event("start", {"sync_id": sync_id, "status": "starting"})
            
            prop = db.get_property(property_id)
            if not prop:
                yield send_event("error", {"error": "Property not found"})
                return
            # User isolation: all users (including admins) can only access their own properties
            if prop.landlord_id != current_user.user_id:
                yield send_event("error", {"error": "Access denied"})
                return
            
            # Get all property suppliers
            property_suppliers = db.list_property_suppliers(property_id)
            suppliers_to_sync = []
            suppliers_without_credentials = []
            
            # Filter by supplier_ids if provided
            selected_supplier_ids = set()
            if supplier_ids:
                selected_supplier_ids = set(supplier_ids.split(','))
            
            for ps in property_suppliers:
                # Filter by selected supplier IDs if provided
                if selected_supplier_ids and ps.id not in selected_supplier_ids:
                    continue
                    
                supplier = db.get_supplier(ps.supplier_id)
                if not supplier:
                    continue
                    
                # Check if credentials are configured - source of truth is user_supplier_credentials table
                # Check directly by user_id and supplier_id, not just by credential_id link
                credential = db.get_user_supplier_credential_by_user_supplier(current_user.user_id, ps.supplier_id)
                if credential and credential.username and credential.password_hash:
                    suppliers_to_sync.append((supplier, ps))
                else:
                    suppliers_without_credentials.append(supplier.name)
            
            # Send suppliers without credentials as errors
            for supplier_name in suppliers_without_credentials:
                if is_cancelled():
                    yield send_event("cancelled", {"message": "Sync cancelled"})
                    return
                yield send_event("progress", {
                    "supplier_name": supplier_name,
                    "status": "error",
                    "bills_found": 0,
                    "bills_created": 0,
                    "error": "No credentials configured. Please set credentials in Settings."
                })
            
            if not suppliers_to_sync:
                yield send_event("complete", {
                    "status": "no_suppliers",
                    "bills_created": 0,
                    "message": "No suppliers with credentials configured"
                })
                return
            
            all_patterns = db.list_extraction_patterns()
            bills_created_total = 0
            
            # Use a queue to receive progress updates from callbacks
            progress_queue = asyncio.Queue()
            
            async def progress_callback_wrapper(supplier_name: str, status: str, bills_found: int = 0, bills_created_count: int = 0, error: Optional[str] = None):
                """Progress callback that puts events in the queue"""
                await progress_queue.put({
                    "supplier_name": supplier_name,
                    "status": status,
                    "bills_found": bills_found,
                    "bills_created": bills_created_count,
                    "error": error
                })
            
            # Task to process progress queue and yield events
            async def process_progress_queue():
                """Process progress updates from queue and yield SSE events"""
                while True:
                    try:
                        # Get progress update with timeout to allow checking cancellation
                        try:
                            progress_update = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                            yield send_event("progress", progress_update)
                            if progress_update["status"] == "completed":
                                nonlocal bills_created_total
                                bills_created_total += progress_update.get("bills_created", 0)
                        except asyncio.TimeoutError:
                            # Check cancellation periodically
                            if is_cancelled():
                                break
                            continue
                    except Exception as e:
                        logger.error(f"[Suppliers Sync] Error processing progress queue: {e}")
                        break
            
            for idx, (supplier, property_supplier) in enumerate(suppliers_to_sync, 1):
                if is_cancelled():
                    yield send_event("cancelled", {"message": "Sync cancelled"})
                    return
                
                # Get credentials - source of truth is user_supplier_credentials table
                # Check directly by user_id and supplier_id
                username = None
                password = None
                try:
                    credential = db.get_user_supplier_credential_by_user_supplier(current_user.user_id, supplier.id)
                    if credential and credential.username and credential.password_hash:
                        username = decrypt_password(credential.username) if credential.username else None
                        password = decrypt_password(credential.password_hash) if credential.password_hash else None
                    else:
                        yield send_event("progress", {
                            "supplier_name": supplier.name,
                            "status": "error",
                            "bills_found": 0,
                            "bills_created": 0,
                            "error": "No credentials configured. Please set credentials in Settings."
                        })
                        continue
                except Exception as e:
                    yield send_event("progress", {
                        "supplier_name": supplier.name,
                        "status": "error",
                        "bills_found": 0,
                        "bills_created": 0,
                        "error": f"Error loading credentials: {str(e)}"
                    })
                    continue
                
                if not username or not password:
                    yield send_event("progress", {
                        "supplier_name": supplier.name,
                        "status": "error",
                        "bills_found": 0,
                        "bills_created": 0,
                        "error": "Missing username or password. Please configure credentials in Settings."
                    })
                    continue
                
                # Send starting status
                yield send_event("progress", {
                    "supplier_name": supplier.name,
                    "status": "starting",
                    "bills_found": 0,
                    "bills_created": 0
                })
                
                try:
                    # Sync based on supplier capabilities
                    if supplier.name.lower() == "e-bloc":
                        yield send_event("progress", {
                            "supplier_name": supplier.name,
                            "status": "processing",
                            "bills_found": 0,
                            "bills_created": 0
                        })
                        
                        # Use web_scraper for e-bloc
                        from app.web_scraper import WebScraper, load_scraper_config
                        from app.utils.ebloc_association_matcher import find_matching_associations
                        
                        config = load_scraper_config("e-bloc")
                        if not config:
                            yield send_event("progress", {
                                "supplier_name": supplier.name,
                                "status": "error",
                                "bills_found": 0,
                                "bills_created": 0,
                                "error": "E-bloc scraper config not found"
                            })
                            continue
                        
                        scraper = WebScraper(config, save_html_dumps=False)
                        logged_in = await scraper.login(username, password)
                        if not logged_in:
                            yield send_event("progress", {
                                "supplier_name": supplier.name,
                                "status": "error",
                                "bills_found": 0,
                                "bills_created": 0,
                                "error": "Invalid E-bloc credentials"
                            })
                            await scraper.close()
                            continue
                        
                        if is_cancelled():
                            await scraper.close()
                            yield send_event("cancelled", {"message": "Sync cancelled"})
                            return
                        
                        # Get login page HTML for association matching
                        login_html = await scraper.page.content()
                        matches = await find_matching_associations(login_html, prop.name)
                        if not matches:
                            yield send_event("progress", {
                                "supplier_name": supplier.name,
                                "status": "error",
                                "bills_found": 0,
                                "bills_created": 0,
                                "error": f"Could not find matching E-bloc association for property: {prop.name}"
                            })
                            await scraper.close()
                            continue
                        
                        selected_match = max(matches, key=lambda m: m.get("score", 0))
                        selected_association_id = selected_match["id"]
                        selected_apartment_id = selected_match.get("apartment_id")
                        
                        # Delete existing E-bloc bills
                        existing_bills = db.list_bills(property_id=property_id)
                        existing_ebloc_bills = [b for b in existing_bills if b.bill_type == BillType.EBLOC and b.renter_id is None]
                        for existing_bill in existing_ebloc_bills:
                            db.delete_bill(existing_bill.id)
                        
                        # Get bills with association/apartment cookies set
                        scraped_bills = await scraper.get_bills(selected_association_id, selected_apartment_id)
                        
                        if is_cancelled():
                            await scraper.close()
                            yield send_event("cancelled", {"message": "Sync cancelled"})
                            return
                        
                        bills_count = 0
                        discovered_bills_list = []
                        
                        for scraped_bill in scraped_bills:
                            if not scraped_bill.bill_number or scraped_bill.amount is None:
                                continue
                            
                            # Determine bill status based on amount
                            bill_status = BillStatus.OVERDUE if scraped_bill.amount > 0 else BillStatus.PAID
                            due_date = scraped_bill.due_date if scraped_bill.due_date else datetime.utcnow()
                            
                            # Get default currency from user preferences
                            default_currency = get_default_bill_currency(prop.landlord_id)
                            
                            if discover_only:
                                # Collect bill data without saving
                                bill_data = {
                                    "property_id": property_id,
                                    "renter_id": None,
                                    "bill_type": BillType.EBLOC,
                                    "description": "E-Bloc",
                                    "amount": scraped_bill.amount,
                                    "currency": default_currency,
                                    "due_date": due_date.isoformat(),
                                    "status": bill_status.value,
                                    "bill_number": scraped_bill.bill_number,
                                    "contract_id": scraped_bill.contract_id
                                }
                                discovered_bills_list.append(bill_data)
                            else:
                                bill = Bill(
                                    property_id=property_id,
                                    renter_id=None,
                                    bill_type=BillType.EBLOC,
                                    description="E-Bloc",
                                    amount=scraped_bill.amount,
                                    currency=default_currency,
                                    due_date=due_date,
                                    status=bill_status,
                                    bill_number=scraped_bill.bill_number,
                                    contract_id=scraped_bill.contract_id
                                )
                                db.save_bill(bill)
                                bills_count += 1
                        
                        if discover_only:
                            yield send_event("progress", {
                                "supplier_name": supplier.name,
                                "status": "processing",
                                "bills_found": len(discovered_bills_list),
                                "bills_created": 0,
                                "bills": discovered_bills_list
                            })
                        else:
                            yield send_event("progress", {
                                "supplier_name": supplier.name,
                                "status": "completed",
                                "bills_found": len(scraped_bills),
                                "bills_created": bills_count
                            })
                        
                        await scraper.close()
                        
                    elif supplier.has_api:
                        yield send_event("progress", {
                            "supplier_name": supplier.name,
                            "status": "error",
                            "bills_found": 0,
                            "bills_created": 0,
                            "error": f"{supplier.name}: API integration not yet implemented"
                        })
                    else:
                        # Use web scraper
                        yield send_event("progress", {
                            "supplier_name": supplier.name,
                            "status": "processing",
                            "bills_found": 0,
                            "bills_created": 0
                        })
                        
                        from app.web_scraper import load_scraper_config
                        config = load_scraper_config(supplier.name)
                        
                        # Use a list to collect progress updates (simpler than queue for now)
                        supplier_progress_updates = []
                        discovered_bills_list = []
                        
                        def sync_progress_callback(name: str, status: str, found: int = 0, created: int = 0, err: Optional[str] = None):
                            """Progress callback - stores updates to be sent via SSE"""
                            supplier_progress_updates.append({
                                "supplier_name": name,
                                "status": status,
                                "bills_found": found,
                                "bills_created": created,
                                "error": err
                            })
                        
                        def bills_collection_callback(bill_data: dict):
                            """Collect discovered bills"""
                            discovered_bills_list.append(bill_data)
                        
                        try:
                            bills_found, bills_count = await _sync_supplier_scraper(
                                property_id=property_id,
                                username=username,
                                password=password,
                                supplier=supplier,
                                patterns=all_patterns,
                                logger=logger,
                                property_supplier_id=property_supplier.id,
                                save_html_dumps=False,
                                progress_callback=sync_progress_callback,
                                discover_only=discover_only,
                                bills_callback=bills_collection_callback if discover_only else None
                            )
                            
                            # Send all progress updates collected during sync (without bills to avoid duplication)
                            for update in supplier_progress_updates:
                                yield send_event("progress", update)
                                await asyncio.sleep(0)  # Yield control to allow cancellation check
                            
                            if is_cancelled():
                                yield send_event("cancelled", {"message": "Sync cancelled"})
                                return
                            
                            # Send final completion event with discovered bills if discover_only
                            # Only include bills in the final completion event to avoid duplication
                            completion_data = {
                                "supplier_name": supplier.name,
                                "status": "completed",
                                "bills_found": bills_found,
                                "bills_created": bills_count
                            }
                            if discover_only and discovered_bills_list:
                                completion_data["bills"] = discovered_bills_list
                                logger.info(f"[{supplier.name} Scraper] Sending {len(discovered_bills_list)} discovered bills in completion event")
                            yield send_event("progress", completion_data)
                            bills_created_total += bills_count
                        except Exception as e:
                            error_msg = str(e)
                            yield send_event("progress", {
                                "supplier_name": supplier.name,
                                "status": "error",
                                "bills_found": 0,
                                "bills_created": 0,
                                "error": error_msg
                            })
                            raise
                
                except Exception as e:
                    error_msg = str(e)
                    yield send_event("progress", {
                        "supplier_name": supplier.name,
                        "status": "error",
                        "bills_found": 0,
                        "bills_created": 0,
                        "error": error_msg
                    })
            
            # Send completion event
            yield send_event("complete", {
                "status": "success",
                "bills_created": bills_created_total,
                "sync_id": sync_id
            })
        
        except Exception as e:
            logger.error(f"[Suppliers Sync] Error in stream: {e}", exc_info=True)
            yield send_event("error", {"error": str(e)})
        finally:
            # Clean up cancellation flag
            if cancel_key in _cancellation_flags:
                del _cancellation_flags[cancel_key]
    
    return StreamingResponse(stream_sync_progress(), media_type="text/event-stream")


@router.post("/suppliers/sync/{property_id}/save-bills")
async def save_discovered_bills(
    property_id: str,
    bills_data: Dict[str, Any],
    current_user: TokenData = Depends(require_landlord)
):
    """Save discovered bills to the database"""
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    bills = bills_data.get("bills", [])
    if not bills:
        return {"status": "success", "bills_created": 0}
    
    bills_created = []
    bills_updated = []
    existing_bills = db.list_bills(property_id=property_id)
    
    for bill_data in bills:
        try:
            # Convert ISO string dates back to datetime
            due_date_str = bill_data["due_date"].replace('Z', '+00:00')
            due_date = datetime.fromisoformat(due_date_str)
            if due_date.tzinfo:
                due_date = due_date.replace(tzinfo=None)
            
            # Convert string enums back to enum types
            bill_type = BillType(bill_data["bill_type"])
            bill_status = BillStatus(bill_data["status"])
            
            # Check if bill already exists (by bill_number and bill_type, or by amount/description/due_date)
            existing = None
            bill_number = bill_data.get("bill_number")
            
            if bill_number:
                existing = next(
                    (b for b in existing_bills 
                     if b.bill_number == bill_number 
                     and b.bill_type == bill_type),
                    None
                )
            
            # Fallback: check by amount, description, and due_date if no bill_number
            if not existing and bill_data.get("amount"):
                for b in existing_bills:
                    if (b.bill_type == bill_type and 
                        b.description == bill_data["description"] and
                        abs(b.amount - bill_data["amount"]) < 0.01):
                        if b.due_date:
                            days_diff = abs((b.due_date - due_date).days)
                            if days_diff <= 5:
                                existing = b
                                break
            
            if existing:
                # Update existing bill with new information
                existing.amount = bill_data["amount"]
                existing.due_date = due_date
                if bill_data.get("iban"):
                    existing.iban = bill_data["iban"]
                if bill_number:
                    existing.bill_number = bill_number
                if bill_data.get("contract_id"):
                    existing.contract_id = bill_data["contract_id"]
                if bill_data.get("extraction_pattern_id"):
                    existing.extraction_pattern_id = bill_data["extraction_pattern_id"]
                # Update status if bill is now overdue
                if due_date < datetime.utcnow() and existing.status == BillStatus.PENDING:
                    existing.status = BillStatus.OVERDUE
                elif due_date >= datetime.utcnow() and existing.status == BillStatus.OVERDUE:
                    existing.status = BillStatus.PENDING
                
                db.save_bill(existing)
                bills_updated.append(existing.id)
                logger.info(f"Updated existing bill {existing.id} (bill_number: {bill_number}, new amount: {bill_data['amount']})")
            else:
                # Create new bill
                bill = Bill(
                    property_id=bill_data["property_id"],
                    renter_id=bill_data.get("renter_id"),
                    bill_type=bill_type,
                    description=bill_data["description"],
                    amount=bill_data["amount"],
                    due_date=due_date,
                    iban=bill_data.get("iban"),
                    bill_number=bill_number,
                    extraction_pattern_id=bill_data.get("extraction_pattern_id"),
                    contract_id=bill_data.get("contract_id"),
                    status=bill_status
                )
                db.save_bill(bill)
                bills_created.append(bill.id)
                logger.info(f"Created new bill {bill.id} (bill_number: {bill_number})")
        except Exception as e:
            logger.error(f"Error saving bill: {e}", exc_info=True)
            continue
    
    return {"status": "success", "bills_created": len(bills_created), "bills_updated": len(bills_updated)}
    
    return {"status": "success", "bills_created": len(bills_created)}


@router.post("/ebloc/sync/{property_id}")
async def sync_ebloc(
    property_id: str, 
    association_id: Optional[str] = Query(None), 
    current_user: TokenData = Depends(require_landlord)
):
    """Sync E-bloc bills and payments for a property."""
    from app.web_scraper import WebScraper, load_scraper_config
    from app.utils.ebloc_association_matcher import find_matching_associations
    
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
    
    config = load_scraper_config("e-bloc")
    if not config:
        raise HTTPException(status_code=500, detail="E-bloc scraper config not found")
    
    scraper = WebScraper(config, save_html_dumps=False)
    try:
        logged_in = await scraper.login(user.ebloc_username, password)
        if not logged_in:
            raise HTTPException(status_code=401, detail="Invalid e-bloc credentials")
        
        # Get login page HTML for association matching
        login_html = await scraper.page.content()
        matches = await find_matching_associations(login_html, prop.name)
        
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
        selected_apartment_id = selected_match.get("apartment_id")
        
        # Delete existing E-bloc bills
        existing_bills = db.list_bills(property_id=property_id)
        existing_ebloc_bills = [b for b in existing_bills if b.bill_type == BillType.EBLOC and b.renter_id is None]
        
        for existing_bill in existing_ebloc_bills:
            db.delete_bill(existing_bill.id)
            logger.info(f"[E-Bloc] Deleted existing E-Bloc bill {existing_bill.id} for property {property_id}")
        
        # Get bills with association/apartment cookies set
        scraped_bills = await scraper.get_bills(selected_association_id, selected_apartment_id)
        
        bills_created = []
        outstanding_debt = 0.0
        last_payment_date = None
        
        for scraped_bill in scraped_bills:
            if not scraped_bill.bill_number or scraped_bill.amount is None:
                continue
            
            outstanding_debt += scraped_bill.amount if scraped_bill.amount > 0 else 0
            if scraped_bill.due_date and (not last_payment_date or scraped_bill.due_date > last_payment_date):
                last_payment_date = scraped_bill.due_date
            
            bill_status = BillStatus.OVERDUE if scraped_bill.amount > 0 else BillStatus.PAID
            due_date = scraped_bill.due_date if scraped_bill.due_date else datetime.utcnow()
            
            # Get default currency from user preferences
            default_currency = get_default_bill_currency(prop.landlord_id)
            
            bill = Bill(
                property_id=property_id,
                renter_id=None,
                bill_type=BillType.EBLOC,
                description="E-Bloc",
                amount=scraped_bill.amount,
                currency=default_currency,
                due_date=due_date,
                status=bill_status,
                bill_number=scraped_bill.bill_number,
                contract_id=scraped_bill.contract_id
            )
            db.save_bill(bill)
            bills_created.append(bill.id)
            logger.info(f"[E-Bloc] Created E-Bloc bill {bill.id} for property {property_id} with amount {scraped_bill.amount} Lei, status: {bill_status}")
        
        await scraper.close()
        
        return {
            "status": "success",
            "property_id": property_id,
            "property_name": prop.name,
            "bills_created": len(bills_created),
            "payments_created": 0,  # Payments not extracted with web_scraper
            "balance": {
                "outstanding_debt": outstanding_debt,
                "last_payment_date": last_payment_date.isoformat() if last_payment_date else None,
                "oldest_debt_month": None  # Not extracted with web_scraper
            }
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
