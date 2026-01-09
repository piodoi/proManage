"""Bill and payment management routes."""
import os
import re
import logging
import sys
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Query
from app.models import (
    Bill, BillCreate, BillUpdate, TokenData, UserRole, BillType, BillStatus, PropertySupplier
)
from app.auth import require_landlord
from app.database import db
from app.text_pattern_extractor import extract_bill_from_pdf_auto
from app.utils.suppliers import initialize_suppliers
from app.routes.sync_routes import resolve_supplier_id

router = APIRouter(prefix="/bills", tags=["bills"])
logger = logging.getLogger(__name__)


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


@router.get("")
async def list_bills(current_user: TokenData = Depends(require_landlord)):
    # User isolation: all users (including admins) only see bills for their own properties
    landlord_properties = {prop.id for prop in db.list_properties(landlord_id=current_user.user_id)}
    bills = [b for b in db.list_bills() if b.property_id in landlord_properties]
    
    # Calculate and update status for all bills
    return [calculate_bill_status(bill) for bill in bills]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_bill(data: BillCreate, current_user: TokenData = Depends(require_landlord)):
    prop = db.get_property(data.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
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
        currency=data.currency or "RON",
        due_date=data.due_date,
        iban=data.iban,
        bill_number=data.bill_number,
    )
    db.save_bill(bill)
    return bill


@router.get("/{bill_id}")
async def get_bill(bill_id: str, current_user: TokenData = Depends(require_landlord)):
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    prop = db.get_property(bill.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    # Calculate and update status based on due date
    return calculate_bill_status(bill)


@router.put("/{bill_id}")
async def update_bill(
    bill_id: str, data: BillUpdate, current_user: TokenData = Depends(require_landlord)
):
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    prop = db.get_property(bill.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    # Handle renter_id update - check if it was provided in the request
    # We need to check the raw request data since Pydantic doesn't distinguish between
    # "field not provided" and "field is None" by default
    update_data = data.model_dump(exclude_unset=True)
    if "renter_id" in update_data:
        renter_id_value = update_data["renter_id"]
        if renter_id_value:  # Not None and not empty string
            renter = db.get_renter(renter_id_value)
            if not renter or renter.property_id != bill.property_id:
                raise HTTPException(status_code=404, detail="Renter not found in this property")
        bill.renter_id = renter_id_value  # Can be None for all/property
    if data.bill_type is not None:
        bill.bill_type = data.bill_type
    if data.description is not None:
        bill.description = data.description
    if data.amount is not None:
        bill.amount = data.amount
    if data.currency is not None:
        bill.currency = data.currency
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


@router.delete("/{bill_id}")
async def delete_bill(bill_id: str, current_user: TokenData = Depends(require_landlord)):
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    prop = db.get_property(bill.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete_bill(bill_id)
    return {"status": "deleted"}


@router.post("/parse-pdf")
async def parse_bill_pdf(
    file: UploadFile = File(...),
    property_id: str = Query(...),
    current_user: TokenData = Depends(require_landlord),
):
    """Parse PDF bill using text patterns. Returns extraction result with address matching warning."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Verify property access
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    pdf_bytes = await file.read()
    
    # Ensure logger has a handler and is set to INFO level
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info(f"[PDF Parse] Starting parse for property {property_id} using text patterns")
    
    # Use new text pattern extraction system
    extracted_data, pattern_id, pattern_name, pattern_bill_type = extract_bill_from_pdf_auto(pdf_bytes)
    
    if not extracted_data:
        raise HTTPException(status_code=400, detail="Could not extract bill data from PDF. Please ensure the PDF matches a known supplier format.")
    
    logger.info(f"[PDF Parse] Result: pattern={pattern_name}, bill_type={pattern_bill_type}, amount={extracted_data.get('amount')}, due_date={extracted_data.get('due_date')}, bill_number={extracted_data.get('bill_number')}")
    
    # Convert extracted_data to match old format for compatibility
    # Use pattern name as description (will be used as bill description)
    result = {
        "iban": extracted_data.get("iban"),
        "bill_number": extracted_data.get("bill_number"),
        "amount": extracted_data.get("amount"),
        "due_date": extracted_data.get("due_date"),  # Already in ISO format YYYY-MM-DD
        "contract_id": extracted_data.get("contract_id"),
        "address": extracted_data.get("address"),
        "business_name": extracted_data.get("legal_name") or extracted_data.get("description"),
        "matched_pattern_id": pattern_id,
        "matched_pattern_name": pattern_name,
        "matched_pattern_supplier": extracted_data.get("legal_name") or pattern_name,  # Supplier from pattern
        "matched_pattern_bill_type": pattern_bill_type,  # Bill type from pattern
    }
    
    # Check if extracted address matches property address
    address_matches = True
    address_warning = None
    address_confidence = 100  # Default to 100% if no address to compare
    if result.get("address") and prop.address:
        # Simple address matching - check if key parts match
        extracted_lower = result.get("address", "").lower()
        property_lower = prop.address.lower()
        
        # Normalize addresses for comparison (remove common words, normalize whitespace)
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
        logger.debug(f"[Address Match] Property: '{prop.address}'")
        logger.debug(f"[Address Match] Extracted: '{result.get('address')}'")
        logger.debug(f"[Address Match] Common tokens: {common_tokens}")
        logger.debug(f"[Address Match] Extracted components: {extracted_components}")
        logger.debug(f"[Address Match] Property components: {property_components}")
        logger.debug(f"[Address Match] Matching components: {matching_components}/{total_components}")
        logger.debug(f"[Address Match] Confidence: {address_confidence}%")
        
        # Only show warning if confidence is below 90%
        if address_confidence < 90:
            address_matches = False
            address_warning = f"Address mismatch detected (confidence: {address_confidence}%). The extracted address may not match this property."
    
    # Auto-add supplier to property if matched pattern has a supplier
    supplier_added = False
    supplier_message = None
    if result.get("matched_pattern_supplier"):
        # Initialize suppliers to ensure they exist in database
        initialize_suppliers()
        
        # Find supplier by name (case-insensitive match)
        all_suppliers = db.list_suppliers()
        matched_supplier = None
        for supplier in all_suppliers:
            # Match on supplier name or extraction_pattern_supplier field
            if (supplier.name and supplier.name.lower() == result.get("matched_pattern_supplier", "").lower()) or \
               (supplier.extraction_pattern_supplier and supplier.extraction_pattern_supplier.lower() == result.get("matched_pattern_supplier", "").lower()):
                matched_supplier = supplier
                break
        
        if matched_supplier:
            # Check if supplier is already added to property
            existing = db.get_property_supplier_by_supplier(property_id, matched_supplier.id)
            if not existing:
                # Auto-add supplier to property
                property_supplier = PropertySupplier(
                    property_id=property_id,
                    supplier_id=matched_supplier.id,
                    credential_id=None,
                )
                db.save_property_supplier(property_supplier)
                supplier_added = True
                logger.info(f"[PDF Parse] Auto-added supplier '{matched_supplier.name}' to property {property_id}")
            
            # Add message about API capability if supplier has API support
            if matched_supplier.has_api:
                supplier_message = f"Supplier '{matched_supplier.name}' has been added to this property. Since this supplier supports API integration, you can configure your login credentials in the property settings to enable automatic bill fetching."
            elif supplier_added:
                supplier_message = f"Supplier '{matched_supplier.name}' has been added to this property."
    
    return {
        **result,
        "address_matches": address_matches,
        "address_warning": address_warning,
        "address_confidence": address_confidence,
        "property_address": prop.address,
        "supplier_added": supplier_added,
        "supplier_message": supplier_message,
    }


@router.post("/create-from-pdf")
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
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Parse due date
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
    
    # Resolve supplier_id
    supplier_name = data.get("matched_pattern_supplier") or data.get("description")
    supplier_id = resolve_supplier_id(
        property_id=property_id,
        supplier_name=supplier_name,
        extraction_pattern_id=data.get("extraction_pattern_id"),
        contract_id=data.get("contract_id")
    )
    
    # Use pattern name as description (from matched_pattern_name)
    # This ensures consistent naming: "Engie", "Digi", "E-bloc" etc.
    bill_description = data.get("matched_pattern_name") or data.get("description", "Bill from PDF")
    
    # Resolve bill_type from pattern, matching against BillType enum case-insensitively
    def resolve_bill_type(bill_type_str: str) -> BillType:
        """Match bill_type string to BillType enum case-insensitively, default to OTHER."""
        if not bill_type_str:
            return BillType.OTHER
        bill_type_lower = bill_type_str.lower()
        for bt in BillType:
            if bt.value.lower() == bill_type_lower:
                return bt
        return BillType.OTHER
    
    pattern_bill_type = data.get("matched_pattern_bill_type") or data.get("bill_type", "utilities")
    resolved_bill_type = resolve_bill_type(pattern_bill_type)
    
    # Handle renter_id - convert 'all' to None
    renter_id = data.get("renter_id")
    if renter_id == "all" or not renter_id:
        renter_id = None
    
    # Create bill
    bill = Bill(
        property_id=property_id,
        renter_id=renter_id,
        bill_type=resolved_bill_type,
        description=bill_description,
        amount=float(data.get("amount", 0)),
        currency=data.get("currency", "RON"),
        due_date=due_date,
        iban=data.get("iban"),
        bill_number=data.get("bill_number"),
        extraction_pattern_id=data.get("extraction_pattern_id"),
        supplier_id=supplier_id,
        contract_id=data.get("contract_id"),
        status=BillStatus.PENDING,
    )
    db.save_bill(bill)
    
    # Save contract_id to PropertySupplier if supplier was resolved and contract_id exists
    contract_id_from_data = data.get("contract_id")
    if supplier_id and contract_id_from_data:
        # Get the PropertySupplier for this supplier
        property_supplier = db.get_property_supplier_by_supplier(property_id, supplier_id)
        if property_supplier and not property_supplier.contract_id:
            property_supplier.contract_id = contract_id_from_data
            db.save_property_supplier(property_supplier)
    
    return bill


@router.get("/payments")
async def list_payments(current_user: TokenData = Depends(require_landlord)):
    # User isolation: all users (including admins) only see payments for their own properties
    landlord_bills = set()
    for prop in db.list_properties(landlord_id=current_user.user_id):
        for bill in db.list_bills(property_id=prop.id):
            landlord_bills.add(bill.id)
    return [p for p in db.list_payments() if p.bill_id in landlord_bills]



