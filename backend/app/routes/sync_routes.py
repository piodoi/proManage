"""Sync routes for supplier and ebloc synchronization with progress tracking."""
import logging
import asyncio
import platform
import re
from datetime import datetime
from typing import Optional, List, Callable, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import httpx
import uuid

from app.models import (
    Supplier, ExtractionPattern, Bill, BillType, BillStatus,
    Payment, PaymentMethod, PaymentStatus, TokenData, UserRole, Property, Renter
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
    bills_callback: Optional[Callable] = None,
    contract_ids_to_accept: Optional[List[str]] = None  # If None or empty, don't filter by contract_id
) -> tuple[int, int]:  # Returns (bills_found, bills_created)
    """Sync bills from supplier using web scraper"""
    from app.web_scraper import WebScraper, load_scraper_config
    from app.pdf_parser import parse_pdf_with_patterns
    
    # If contract_ids_to_accept is provided, log accordingly; otherwise log single property
    if contract_ids_to_accept is not None:
        logger.info(f"[{supplier.name} Scraper] Starting sync for multiple properties (contract IDs: {contract_ids_to_accept or 'all'})")
    else:
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
    
    # Get property supplier to check/update contract_id (only used if contract_ids_to_accept is None)
    property_supplier = db.get_property_supplier(property_supplier_id)
    contract_id_filter = property_supplier.contract_id if property_supplier and contract_ids_to_accept is None else None
    contract_id_to_save = None
    
    try:
        logged_in = await scraper.login(username, password)
        if not logged_in:
            error_msg = f"Failed to login to {supplier.name}"
            if progress_callback:
                progress_callback(supplier.name, "error", 0, 0, error_msg)
            raise Exception(error_msg)
        
        # Get bills
        # For E-bloc with multiple contract_ids (association IDs), fetch bills for each association
        scraped_bills = []
        if supplier.name.lower() == "e-bloc" and contract_ids_to_accept and len(contract_ids_to_accept) > 0:
            # For E-bloc, contract_ids are association IDs - fetch bills for each one
            # Note: apartment_id is not stored in contract_id, so we pass None
            association_ids = [(cid, None) for cid in contract_ids_to_accept]
            scraped_bills = await scraper.get_bills(association_ids=association_ids)
        else:
            # Regular flow - single association or non-E-bloc supplier
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
            # If contract_ids_to_accept is provided, use that list; otherwise use single contract_id_filter
            if contract_ids_to_accept is not None and len(contract_ids_to_accept) > 0:
                # Multi-property sync: filter by list of contract IDs
                extracted_str = str(extracted_contract_id).strip() if extracted_contract_id else None
                if not extracted_str or extracted_str not in [str(cid).strip() for cid in contract_ids_to_accept]:
                    continue  # Skip bills that don't match any of the accepted contract IDs
            elif contract_id_filter:
                # Single-property sync: filter by single contract ID
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
            landlord_id = prop.landlord_id if prop else None
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


class PropertyContractMapping(BaseModel):
    property_id: str
    contract_id: Optional[str] = None

class SupplierGroup(BaseModel):
    supplier_id: str
    properties: List[PropertyContractMapping]  # Changed from property_ids + contract_id to list of property+contract mappings


class SyncAllRequest(BaseModel):
    sync_id: str
    supplier_groups: List[SupplierGroup]
    discover_only: bool = True


@router.post("/suppliers/sync-all")
async def sync_all_properties_supplier_bills(
    request: SyncAllRequest = Body(...),
    current_user: TokenData = Depends(require_landlord)
):
    """
    Sync bills from suppliers across all properties.
    Suppliers are synced only once per contract_id, then bills are distributed to properties.
    """
    cancel_key = f"all:{request.sync_id}"
    _cancellation_flags[cancel_key] = False
    
    async def stream_sync_progress():
        """Generator function that streams progress updates via SSE."""
        try:
            def is_cancelled():
                return _cancellation_flags.get(cancel_key, False)
            
            def send_event(event_type: str, data: dict):
                """Send SSE event"""
                return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            
            yield send_event("start", {"sync_id": request.sync_id, "status": "starting"})
            
            # Verify all properties belong to the user
            for group in request.supplier_groups:
                for prop_mapping in group.properties:
                    prop = db.get_property(prop_mapping.property_id)
                    if not prop:
                        yield send_event("error", {"error": f"Property {prop_mapping.property_id} not found"})
                        return
                    if prop.landlord_id != current_user.user_id:
                        yield send_event("error", {"error": "Access denied"})
                        return
            
            all_patterns = db.list_extraction_patterns()
            bills_discovered = []
            
            # Sync each supplier group once (grouped by supplier_id only)
            for group in request.supplier_groups:
                if is_cancelled():
                    yield send_event("cancelled", {"message": "Sync cancelled"})
                    return
                
                supplier = db.get_supplier(group.supplier_id)
                if not supplier:
                    property_ids = [p.property_id for p in group.properties]
                    yield send_event("progress", {
                        "supplier_name": "Unknown",
                        "contract_id": None,
                        "status": "error",
                        "bills_found": 0,
                        "bills_created": 0,
                        "error": f"Supplier {group.supplier_id} not found",
                        "properties_affected": property_ids
                    })
                    continue
                
                # Get credentials
                credential = db.get_user_supplier_credential_by_user_supplier(current_user.user_id, supplier.id)
                if not credential or not credential.username or not credential.password_hash:
                    property_ids = [p.property_id for p in group.properties]
                    yield send_event("progress", {
                        "supplier_name": supplier.name,
                        "contract_id": None,
                        "status": "error",
                        "bills_found": 0,
                        "bills_created": 0,
                        "error": "No credentials configured",
                        "properties_affected": property_ids
                    })
                    continue
                
                username = decrypt_password(credential.username)
                password = decrypt_password(credential.password_hash)
                
                property_ids = [p.property_id for p in group.properties]
                yield send_event("progress", {
                    "supplier_name": supplier.name,
                    "contract_id": None,
                    "status": "starting",
                    "bills_found": 0,
                    "bills_created": 0,
                    "properties_affected": property_ids
                })
                
                # Sync supplier once for all properties
                property_to_association = {}  # Map property_id -> (association_id, apartment_id) for E-bloc
                try:
                    # Special handling for E-bloc - use externalized helper with immediate bill sending
                    if supplier.name.lower() == "e-bloc":
                        from app.utils.ebloc_sync_helper import sync_ebloc_all_properties
                        import asyncio
                        
                        # Prepare properties list
                        properties_list = [(p.property_id, p.contract_id) for p in group.properties]
                        
                        # Use callback to send bills immediately as they're discovered
                        bills_queue = asyncio.Queue()
                        
                        def bills_callback(bill_data: Dict[str, Any]):
                            """Callback to queue bills for immediate sending"""
                            bills_queue.put_nowait(bill_data)
                        
                        # Start sync task
                        sync_task = asyncio.create_task(
                            sync_ebloc_all_properties(
                                properties_list,
                                username,
                                password,
                                bill_callback=bills_callback if request.discover_only else None
                            )
                        )
                        
                        # Process bills from queue and send immediately (only in discover mode)
                        property_to_association = {}
                        group_bills = []
                        
                        if request.discover_only:
                            while True:
                                try:
                                    # Wait for bill with short timeout to allow checking task status
                                    item = await asyncio.wait_for(bills_queue.get(), timeout=0.1)
                                    
                                    # Process bill and send immediately
                                    bill_data = item
                                    matched_property_id = match_bill_to_property(bill_data)
                                    
                                    if matched_property_id:
                                        bill_data["property_id"] = matched_property_id
                                        prop = db.get_property(matched_property_id)
                                        if prop:
                                            bill_with_property = {
                                                **bill_data,
                                                "supplier_name": supplier.name,
                                                "property_name": prop.name
                                            }
                                            bills_discovered.append(bill_with_property)
                                            logger.info(f"*** BILL sent: {bill_with_property.get('bill_number')} for property {prop.name}")
                                            # Send bill immediately via SSE
                                            yield send_event("bill_discovered", {
                                                "supplier_name": supplier.name,
                                                "bill": bill_with_property
                                            })
                                    
                                    group_bills.append(bill_data)
                                    bills_queue.task_done()
                                except asyncio.TimeoutError:
                                    # Check if sync task is done
                                    if sync_task.done():
                                        break
                                    continue
                        
                        # Wait for sync to complete and get results
                        group_bills_result, property_to_association = await sync_task
                        # Use result from task if queue didn't collect all bills
                        if not request.discover_only or len(group_bills) < len(group_bills_result):
                            group_bills = group_bills_result
                        
                        bills_found = len(group_bills)
                        bills_created = 0  # Will be set after distribution
                        
                        # For E-bloc, skip the discover_only section below since bills already sent incrementally
                        if request.discover_only and supplier.name.lower() == "e-bloc":
                            # Send final completion event for E-bloc
                            yield send_event("progress", {
                                "supplier_name": supplier.name,
                                "contract_id": None,
                                "status": "completed",
                                "bills_found": bills_found,
                                "bills_created": 0,
                                "properties_affected": property_ids,
                                "bills": None  # Don't send bills here, already sent incrementally
                            })
                            continue
                    else:
                        # Non-E-bloc suppliers - use regular sync
                        # Find property supplier for first property to get property_supplier_id
                        first_property_id = group.properties[0].property_id
                        first_property_suppliers = db.list_property_suppliers(first_property_id)
                        property_supplier = next((ps for ps in first_property_suppliers if ps.supplier_id == supplier.id), None)
                        if not property_supplier:
                            yield send_event("progress", {
                                "supplier_name": supplier.name,
                                "contract_id": None,
                                "status": "error",
                                "bills_found": 0,
                                "bills_created": 0,
                                "error": "Property supplier not found",
                                "properties_affected": property_ids
                            })
                            continue
                        
                        # Collect all contract IDs from properties in this group (for filtering)
                        # Only filter if there are multiple different contract_ids; otherwise get all bills
                        contract_ids = [p.contract_id for p in group.properties if p.contract_id]
                        unique_contract_ids = list(set(contract_ids)) if contract_ids else []
                        # If all properties have the same contract_id (or all are None), don't filter - get all bills
                        # Only filter if there are multiple different contract_ids
                        contract_ids_to_accept = unique_contract_ids if len(unique_contract_ids) > 1 else None
                        
                        group_bills = []  # Collect bills for this supplier group
                        
                        def bills_callback(bill_data: Dict[str, Any]):
                            """Callback to collect discovered bills - receives single bill dict"""
                            # No filtering here - we'll filter when distributing to properties
                            group_bills.append(bill_data)
                        
                        yield send_event("progress", {
                            "supplier_name": supplier.name,
                            "contract_id": None,
                            "status": "processing",
                            "bills_found": 0,
                            "bills_created": 0,
                            "properties_affected": property_ids
                        })
                        
                        bills_found, bills_created = await _sync_supplier_scraper(
                            property_id=first_property_id,  # Use first property for sync (just for reference)
                            username=username,
                            password=password,
                            supplier=supplier,
                            patterns=all_patterns,
                            logger=logger,
                            property_supplier_id=property_supplier.id,
                            save_html_dumps=False,
                            progress_callback=None,  # We handle progress manually
                            discover_only=request.discover_only,
                            bills_callback=bills_callback,
                            contract_ids_to_accept=contract_ids_to_accept  # Pass list of contract IDs to accept (or None for no filtering)
                        )
                    
                    # Match each bill to exactly one property
                    # Logic: 1) Match by contract_id if available, 2) Match by apartment number
                    def match_bill_to_property(bill_data: Dict[str, Any]) -> Optional[str]:
                        """Match a bill to exactly one property. Returns property_id or None."""
                        bill_contract_id = bill_data.get("contract_id")
                        
                        # Step 1: Try matching by contract_id
                        if bill_contract_id and str(bill_contract_id).strip().upper() != "A000000":
                            # For E-bloc, contract_id is actually association_id
                            if supplier.name.lower() == "e-bloc":
                                # Match by association_id
                                for prop_mapping in group.properties:
                                    if prop_mapping.property_id in property_to_association:
                                        assoc_id, _ = property_to_association[prop_mapping.property_id]
                                        if str(assoc_id).strip() == str(bill_contract_id).strip():
                                            return prop_mapping.property_id
                                # Also check property_supplier contract_id
                                for prop_mapping in group.properties:
                                    property_suppliers = db.list_property_suppliers(prop_mapping.property_id)
                                    property_supplier = next((ps for ps in property_suppliers if ps.supplier_id == supplier.id), None)
                                    if property_supplier and property_supplier.contract_id:
                                        if str(property_supplier.contract_id).strip() == str(bill_contract_id).strip():
                                            return prop_mapping.property_id
                            else:
                                # For non-E-bloc, match by contract_id
                                for prop_mapping in group.properties:
                                    # Check prop_mapping.contract_id first
                                    if prop_mapping.contract_id and str(prop_mapping.contract_id).strip() == str(bill_contract_id).strip():
                                        return prop_mapping.property_id
                                    # Check property_supplier.contract_id
                                    property_suppliers = db.list_property_suppliers(prop_mapping.property_id)
                                    property_supplier = next((ps for ps in property_suppliers if ps.supplier_id == supplier.id), None)
                                    if property_supplier and property_supplier.contract_id:
                                        if str(property_supplier.contract_id).strip() == str(bill_contract_id).strip():
                                            return prop_mapping.property_id
                        
                        # Step 2: Match by apartment number (for E-bloc)
                        if supplier.name.lower() == "e-bloc":
                            # Extract apartment number from bill_number (e.g., "Octombrie 2025 Ap.8")
                            bill_number = bill_data.get("bill_number", "")
                            apt_match = re.search(r'Ap\.\s*(\d+)', bill_number, re.I)
                            if apt_match:
                                bill_apt_number = apt_match.group(1).strip()
                                # Match with property address apartment number
                                for prop_mapping in group.properties:
                                    prop = db.get_property(prop_mapping.property_id)
                                    if prop and prop.address:
                                        from app.utils.ebloc_sync_helper import extract_apartment_number_from_address
                                        prop_apt_number = extract_apartment_number_from_address(prop.address)
                                        if prop_apt_number and prop_apt_number == bill_apt_number:
                                            return prop_mapping.property_id
                        
                        # No match found
                        return None
                    
                    if request.discover_only:
                        # Skip E-bloc here since it was already processed above with incremental sending
                        if supplier.name.lower() == "e-bloc":
                            continue  # E-bloc already handled, move to next supplier
                        
                        # In discover mode, assign each bill to exactly one property
                        all_bills_for_display = []
                        for bill_data in group_bills:
                            matched_property_id = match_bill_to_property(bill_data)
                            
                            if matched_property_id:
                                prop = db.get_property(matched_property_id)
                                bill_with_property = {
                                    **bill_data,
                                    "property_id": matched_property_id,
                                    "supplier_name": supplier.name,
                                }
                                all_bills_for_display.append(bill_with_property)
                                bills_discovered.append(bill_with_property)
                            else:
                                # No match found - still include bill but without property_id
                                logger.warning(f"[{supplier.name}] Could not match bill {bill_data.get('bill_number')} to any property")
                                bill_with_property = {
                                    **bill_data,
                                    "supplier_name": supplier.name,
                                }
                                all_bills_for_display.append(bill_with_property)
                                bills_discovered.append(bill_with_property)
                        
                        # Send bills incrementally as they're discovered
                        # First, send progress update without bills (for progress display)
                        yield send_event("progress", {
                            "supplier_name": supplier.name,
                            "contract_id": None,
                            "status": "processing",
                            "bills_found": len(group_bills),
                            "bills_created": 0,
                            "properties_affected": property_ids,
                            "bills": None  # Don't send bills in progress event
                        })
                        
                        # Send each bill individually as they're discovered
                        for bill_with_property in all_bills_for_display:
                            yield send_event("bill_discovered", {
                                "supplier_name": supplier.name,
                                "bill": bill_with_property
                            })
                        
                        # Final completion event
                        yield send_event("progress", {
                            "supplier_name": supplier.name,
                            "contract_id": None,
                            "status": "completed",
                            "bills_found": len(group_bills),
                            "bills_created": 0,
                            "properties_affected": property_ids,
                            "bills": None  # Don't send bills here, already sent incrementally
                        })
                    else:
                        # In save mode, match each bill to exactly one property and save it
                        bills_saved_count = 0
                        bills_saved_info = []  # List of (property_name, bill_count) for logging
                        
                        for bill_data in group_bills:
                            matched_property_id = match_bill_to_property(bill_data)
                            
                            if not matched_property_id:
                                logger.warning(f"[{supplier.name}] Could not match bill {bill_data.get('bill_number')} to any property, skipping")
                                continue
                            
                            prop = db.get_property(matched_property_id)
                            prop_name = prop.name if prop else matched_property_id
                            
                            # Save the bill to the matched property
                            try:
                                # Filter out A000000 contract_id - never save it
                                bill_contract_id = bill_data.get("contract_id")
                                bill_contract_id_to_save = bill_contract_id
                                if bill_contract_id_to_save and str(bill_contract_id_to_save).strip().upper() == "A000000":
                                    bill_contract_id_to_save = None
                                
                                # Convert bill_data to Bill object and save
                                due_date_str = bill_data["due_date"].replace('Z', '+00:00')
                                due_date = datetime.fromisoformat(due_date_str)
                                if due_date.tzinfo:
                                    due_date = due_date.replace(tzinfo=None)
                                
                                bill_type = BillType(bill_data["bill_type"])
                                bill_status = BillStatus(bill_data.get("status", "pending"))
                                
                                # Check if bill already exists
                                existing_bills = db.list_bills(property_id=matched_property_id)
                                existing = None
                                bill_number = bill_data.get("bill_number")
                                
                                if bill_number:
                                    existing = next(
                                        (b for b in existing_bills 
                                         if b.bill_number == bill_number 
                                         and b.bill_type == bill_type),
                                        None
                                    )
                                
                                if not existing and bill_data.get("amount"):
                                    for b in existing_bills:
                                        if (b.bill_type == bill_type and 
                                            b.description == bill_data.get("description", "") and
                                            abs(b.amount - bill_data["amount"]) < 0.01):
                                            if b.due_date:
                                                days_diff = abs((b.due_date - due_date).days)
                                                if days_diff <= 5:
                                                    existing = b
                                                    break
                                
                                if existing:
                                    # Update existing bill
                                    existing.amount = bill_data["amount"]
                                    existing.due_date = due_date
                                    if bill_data.get("iban"):
                                        existing.iban = bill_data["iban"]
                                    if bill_number:
                                        existing.bill_number = bill_number
                                    if bill_contract_id_to_save:
                                        existing.contract_id = bill_contract_id_to_save
                                    if bill_data.get("extraction_pattern_id"):
                                        existing.extraction_pattern_id = bill_data["extraction_pattern_id"]
                                    if due_date < datetime.utcnow() and existing.status == BillStatus.PENDING:
                                        existing.status = BillStatus.OVERDUE
                                    elif due_date >= datetime.utcnow() and existing.status == BillStatus.OVERDUE:
                                        existing.status = BillStatus.PENDING
                                    db.save_bill(existing)
                                else:
                                    # Create new bill
                                    bill = Bill(
                                        property_id=matched_property_id,
                                        renter_id=bill_data.get("renter_id"),
                                        bill_type=bill_type,
                                        description=bill_data.get("description", ""),
                                        amount=bill_data["amount"],
                                        due_date=due_date,
                                        iban=bill_data.get("iban"),
                                        bill_number=bill_number,
                                        extraction_pattern_id=bill_data.get("extraction_pattern_id"),
                                        contract_id=bill_contract_id_to_save,
                                        status=bill_status
                                    )
                                    db.save_bill(bill)
                                
                                bills_saved_count += 1
                                bills_discovered.append({
                                    **bill_data,
                                    "property_id": matched_property_id,
                                    "supplier_name": supplier.name,
                                    "contract_id": bill_contract_id_to_save,
                                })
                                
                                # Track property name for logging
                                found_info = next((info for info in bills_saved_info if info[0] == prop_name), None)
                                if found_info:
                                    found_info[1] += 1
                                else:
                                    bills_saved_info.append([prop_name, 1])
                                
                            except Exception as e:
                                logger.error(f"Error saving bill for property {prop_name}: {e}", exc_info=True)
                        
                        # Build property info string for logging
                        property_info = ", ".join([f"{name} ({count})" for name, count in bills_saved_info])
                        
                        yield send_event("progress", {
                            "supplier_name": f"{supplier.name} - {property_info}" if property_info else supplier.name,
                            "contract_id": None,
                            "status": "completed",
                            "bills_found": len(group_bills),
                            "bills_created": bills_saved_count,
                            "properties_affected": property_ids,
                            "bills": None
                        })
                except Exception as e:
                    logger.error(f"Error syncing supplier {supplier.name}: {e}", exc_info=True)
                    yield send_event("progress", {
                        "supplier_name": supplier.name,
                        "contract_id": None,
                        "status": "error",
                        "bills_found": 0,
                        "bills_created": 0,
                        "error": str(e),
                        "properties_affected": property_ids
                    })
            
            yield send_event("complete", {
                "status": "completed",
                "bills_discovered": len(bills_discovered)
            })
        except Exception as e:
            logger.error(f"Error in sync_all_properties_supplier_bills: {e}", exc_info=True)
            yield send_event("error", {"error": str(e)})
        finally:
            if cancel_key in _cancellation_flags:
                del _cancellation_flags[cancel_key]
    
    return StreamingResponse(
        stream_sync_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/suppliers/sync-all/cancel")
async def cancel_all_sync(sync_id: str = Query(...), current_user: TokenData = Depends(require_landlord)):
    """Cancel an ongoing all-properties sync operation."""
    cancel_key = f"all:{sync_id}"
    if cancel_key in _cancellation_flags:
        _cancellation_flags[cancel_key] = True
        logger.info(f"[Suppliers Sync All] Cancellation requested for {cancel_key}")
        return {"status": "cancelled"}
    return {"status": "not_found"}


@router.post("/suppliers/sync-all/save-bills")
async def save_all_discovered_bills(
    bills_data: Dict[str, Any] = Body(...),
    current_user: TokenData = Depends(require_landlord)
):
    """Save discovered bills from all properties sync to the database"""
    bills = bills_data.get("bills", [])
    if not bills:
        return {"status": "success", "bills_created": 0}
    
    bills_created = []
    bills_updated = []
    
    for bill_data in bills:
        try:
            property_id = bill_data.get("property_id")
            if not property_id:
                continue
                
            prop = db.get_property(property_id)
            if not prop:
                continue
            # User isolation: all users (including admins) can only access their own properties
            if prop.landlord_id != current_user.user_id:
                continue
            
            # Convert ISO string dates back to datetime
            due_date_str = bill_data["due_date"].replace('Z', '+00:00')
            due_date = datetime.fromisoformat(due_date_str)
            if due_date.tzinfo:
                due_date = due_date.replace(tzinfo=None)
            
            # Convert string enums back to enum types
            bill_type = BillType(bill_data["bill_type"])
            bill_status = BillStatus(bill_data.get("status", "pending"))
            
            # Check if bill already exists
            existing_bills = db.list_bills(property_id=property_id)
            existing = None
            bill_number = bill_data.get("bill_number")
            
            if bill_number:
                existing = next(
                    (b for b in existing_bills 
                     if b.bill_number == bill_number 
                     and b.bill_type == bill_type),
                    None
                )
            
            if not existing and bill_data.get("amount"):
                for b in existing_bills:
                    if (b.bill_type == bill_type and 
                        b.description == bill_data.get("description", "") and
                        abs(b.amount - bill_data["amount"]) < 0.01):
                        if b.due_date:
                            days_diff = abs((b.due_date - due_date).days)
                            if days_diff <= 5:
                                existing = b
                                break
            
            if existing:
                # Update existing bill
                existing.amount = bill_data["amount"]
                existing.due_date = due_date
                if bill_data.get("iban"):
                    existing.iban = bill_data["iban"]
                if bill_number:
                    existing.bill_number = bill_number
                contract_id_to_save = bill_data.get("contract_id")
                # Filter out A000000 contract_id - never save it
                if contract_id_to_save and str(contract_id_to_save).strip().upper() == "A000000":
                    contract_id_to_save = None
                if contract_id_to_save:
                    existing.contract_id = contract_id_to_save
                if bill_data.get("extraction_pattern_id"):
                    existing.extraction_pattern_id = bill_data["extraction_pattern_id"]
                if due_date < datetime.utcnow() and existing.status == BillStatus.PENDING:
                    existing.status = BillStatus.OVERDUE
                elif due_date >= datetime.utcnow() and existing.status == BillStatus.OVERDUE:
                    existing.status = BillStatus.PENDING
                
                db.save_bill(existing)
                bills_updated.append(existing.id)
            else:
                # Create new bill
                bill = Bill(
                    property_id=property_id,
                    renter_id=bill_data.get("renter_id"),
                    bill_type=bill_type,
                    description=bill_data.get("description", ""),
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
                
                # For E-bloc bills, save contract_id (association_id) to property_supplier if not already set
                if bill_type == BillType.EBLOC and bill_data.get("contract_id"):
                    contract_id = bill_data["contract_id"]
                    prop_suppliers = db.list_property_suppliers(property_id)
                    # Find E-bloc supplier
                    ebloc_supplier = next((s for s in db.list_suppliers() if s.name.lower() == "e-bloc"), None)
                    if ebloc_supplier:
                        prop_supplier = next((ps for ps in prop_suppliers if ps.supplier_id == ebloc_supplier.id), None)
                        if prop_supplier and not prop_supplier.contract_id:
                            prop_supplier.contract_id = contract_id
                            db.save_property_supplier(prop_supplier)
                            logger.info(f"[E-bloc] Saved contract_id {contract_id} to property supplier for property {property_id}")
        except Exception as e:
            logger.error(f"Error saving bill: {e}", exc_info=True)
            continue
    
    return {
        "status": "success",
        "bills_created": len(bills_created),
        "bills_updated": len(bills_updated)
    }
