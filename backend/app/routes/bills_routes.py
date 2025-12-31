"""Bill and payment management routes."""
import os
import re
import logging
import sys
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Query
from app.models import (
    Bill, BillCreate, BillUpdate, TokenData, UserRole, BillType, BillStatus
)
from app.auth import require_landlord
from app.database import db
from app.pdf_parser import parse_pdf_with_patterns
from app.utils.suppliers import initialize_suppliers

router = APIRouter(prefix="/bills", tags=["bills"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_bills(current_user: TokenData = Depends(require_landlord)):
    if current_user.role == UserRole.ADMIN:
        return db.list_bills()
    landlord_properties = {prop.id for prop in db.list_properties(landlord_id=current_user.user_id)}
    return [b for b in db.list_bills() if b.property_id in landlord_properties]


@router.post("", status_code=status.HTTP_201_CREATED)
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


@router.get("/{bill_id}")
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


@router.delete("/{bill_id}")
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


@router.post("/parse-pdf")
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
    
    # Auto-add supplier to property if matched pattern has a supplier
    supplier_added = False
    supplier_message = None
    if result.matched_pattern_supplier:
        # Initialize suppliers to ensure they exist in database
        initialize_suppliers()
        
        # Find supplier by name (case-insensitive match)
        all_suppliers = db.list_suppliers()
        matched_supplier = None
        for supplier in all_suppliers:
            # Match on supplier name or extraction_pattern_supplier field
            if (supplier.name and supplier.name.lower() == result.matched_pattern_supplier.lower()) or \
               (supplier.extraction_pattern_supplier and supplier.extraction_pattern_supplier.lower() == result.matched_pattern_supplier.lower()):
                matched_supplier = supplier
                break
        
        if matched_supplier:
            # Check if supplier is already added to property
            from app.models import PropertySupplier
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
        **result.model_dump(),
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
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
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


@router.get("/payments")
async def list_payments(current_user: TokenData = Depends(require_landlord)):
    if current_user.role == UserRole.ADMIN:
        return db.list_payments()
    landlord_bills = set()
    for prop in db.list_properties(landlord_id=current_user.user_id):
        for bill in db.list_bills(property_id=prop.id):
            landlord_bills.add(bill.id)
    return [p for p in db.list_payments() if p.bill_id in landlord_bills]



