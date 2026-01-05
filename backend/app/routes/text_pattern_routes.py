"""Text-based pattern tool routes for PDF bill extraction."""
import logging
import sys
import json
import os
import re
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from datetime import datetime

from app.models import TokenData, BillType
from app.auth import require_landlord
from app.utils.text_pattern_utils import (
    TEXT_PATTERNS_DIR,
    extract_text_from_pdf,
    extract_iban,
    clean_bill_number,
    parse_date_with_month_names,
    create_flexible_label_regex,
    extract_field_value,
    extract_with_pattern,
    match_pattern_to_pdf,
)

router = APIRouter(prefix="/text-patterns", tags=["text-patterns"])
logger = logging.getLogger(__name__)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Ensure text patterns directory exists
os.makedirs(TEXT_PATTERNS_DIR, exist_ok=True)


class FieldPattern(BaseModel):
    """Represents a field pattern with label and line offset."""
    field_name: str
    label_text: str  # Label text to search for
    line_offset: int  # Number of lines between label and value (0 if on same line)
    value_text: Optional[str] = None  # Value text (optional, not used in extraction)
    value_regex: Optional[str] = None  # Value regex (optional, not used in extraction)


class TextPattern(BaseModel):
    """Text-based extraction pattern."""
    id: str
    name: str
    bill_type: BillType
    supplier: Optional[str] = None
    field_patterns: List[FieldPattern]
    created_at: str
    updated_at: str


class TextPatternCreate(BaseModel):
    """Create a text-based extraction pattern."""
    name: str
    bill_type: BillType
    supplier: Optional[str] = None
    field_patterns: List[FieldPattern]


# ========================================================================
# NOTE: All extraction utilities are now in app.utils.text_pattern_utils
# This ensures unity between pattern creation and extraction.
# ========================================================================


@router.post("/upload-pdf")
async def upload_pdf_for_text_selection(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(require_landlord),
):
    """Upload a PDF and return plain text for selection."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    pdf_bytes = await file.read()
    
    try:
        # Extract text using same method as pdf2txt
        text = extract_text_from_pdf(pdf_bytes)
        
        return {
            "text": text,
            "line_count": len(text.splitlines()),
        }
    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post("/save-pattern")
async def save_text_pattern(
    pattern: TextPatternCreate,
    current_user: TokenData = Depends(require_landlord),
):
    """Save a text-based extraction pattern to file."""
    pattern_id = f"text_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{pattern.name.replace(' ', '_')}"
    
    # Save only field_name, label_text, and line_offset (no value_text, value_regex)
    processed_patterns = []
    for field_pattern in pattern.field_patterns:
        processed_patterns.append({
            "field_name": field_pattern.field_name,
            "label_text": field_pattern.label_text,
            "line_offset": field_pattern.line_offset,
        })
    
    # Build pattern dict manually to ensure no value_text/value_regex fields
    pattern_dict = {
        "id": pattern_id,
        "name": pattern.name,
        "bill_type": pattern.bill_type,
        "supplier": pattern.supplier,
        "field_patterns": processed_patterns,  # Already cleaned, only has field_name, label_text, line_offset
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    # Save to file (manually constructed to avoid Pydantic adding optional fields)
    pattern_file = os.path.join(TEXT_PATTERNS_DIR, f"{pattern_id}.json")
    with open(pattern_file, 'w', encoding='utf-8') as f:
        json.dump(pattern_dict, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved text pattern to {pattern_file}")
    
    return {"pattern_id": pattern_id, "message": "Pattern saved successfully"}


@router.get("/list-patterns")
async def list_text_patterns(
    current_user: TokenData = Depends(require_landlord),
):
    """List all text patterns with their metadata."""
    patterns = []
    if os.path.exists(TEXT_PATTERNS_DIR):
        for filename in os.listdir(TEXT_PATTERNS_DIR):
            if filename.endswith('.json'):
                try:
                    pattern_file = os.path.join(TEXT_PATTERNS_DIR, filename)
                    with open(pattern_file, 'r', encoding='utf-8') as f:
                        pattern = json.load(f)
                        filename_base = filename[:-5]  # Remove .json extension
                        patterns.append({
                            "pattern_id": filename_base,
                            "name": pattern.get('name', ''),
                            "supplier": pattern.get('supplier', ''),
                            "bill_type": pattern.get('bill_type', 'utilities'),
                            "field_count": len(pattern.get('field_patterns', [])),
                            "created_at": pattern.get('created_at', ''),
                            "updated_at": pattern.get('updated_at', ''),
                        })
                except Exception as e:
                    logger.warning(f"Error loading pattern {filename}: {e}")
    
    # Sort by name
    patterns.sort(key=lambda p: p['name'].lower())
    return {"patterns": patterns}


@router.get("/get-pattern/{pattern_id}")
async def get_text_pattern(
    pattern_id: str,
    current_user: TokenData = Depends(require_landlord),
):
    """Get a specific text pattern by ID."""
    pattern_file = os.path.join(TEXT_PATTERNS_DIR, f"{pattern_id}.json")
    if not os.path.exists(pattern_file):
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    with open(pattern_file, 'r', encoding='utf-8') as f:
        pattern = json.load(f)
    
    return pattern


@router.post("/match-pdf")
async def match_text_pattern(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(require_landlord),
):
    """Match a PDF against saved text patterns."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    pdf_bytes = await file.read()
    pdf_text = extract_text_from_pdf(pdf_bytes)
    pdf_lines = pdf_text.splitlines()
    
    # Load all patterns from text_patterns folder
    patterns = []
    if os.path.exists(TEXT_PATTERNS_DIR):
        for filename in os.listdir(TEXT_PATTERNS_DIR):
            if filename.endswith('.json'):
                try:
                    pattern_file = os.path.join(TEXT_PATTERNS_DIR, filename)
                    with open(pattern_file, 'r', encoding='utf-8') as f:
                        pattern = json.load(f)
                        filename_base = filename[:-5]  # Remove .json extension
                        # Use filename as pattern_id (not the ID field in JSON)
                        patterns.append({
                            'pattern': pattern,
                            'pattern_id': filename_base  # Use filename as pattern_id
                        })
                except Exception as e:
                    logger.warning(f"Error loading pattern {filename}: {e}")
    
    matches = []
    for pattern_data in patterns:
        pattern = pattern_data['pattern']
        pattern_id = pattern_data['pattern_id']  # Use filename-based pattern_id
        
        # Calculate confidence based on how many field patterns match
        matched_fields = 0
        total_fields = len(pattern.get('field_patterns', []))
        
        if total_fields == 0:
            continue  # Skip patterns with no fields
        
        for field_pattern in pattern.get('field_patterns', []):
            label_text = field_pattern.get('label_text', '')
            if label_text:
                # Try to find label in text (case-sensitive, flexible)
                label_regex = re.escape(label_text)
                label_regex = label_regex.replace(r'\ ', r'\s+')  # Allow flexible spacing
                if re.search(label_regex, pdf_text):
                    matched_fields += 1
        
        # Include all patterns, even with 0 confidence (for unknown PDFs)
        confidence = matched_fields / total_fields if total_fields > 0 else 0
        matches.append({
            "pattern_id": pattern_id,  # Use filename-based pattern_id
            "pattern_name": pattern.get('name', filename_base),
            "supplier": pattern.get('supplier'),
            "confidence": confidence,
            "matched_fields": matched_fields,
            "total_fields": total_fields,
        })
    
    # Sort by confidence (highest first), but include all patterns
    matches.sort(key=lambda m: m['confidence'], reverse=True)
    
    return {
        "matches": matches,
        "best_match": matches[0] if matches else None,
    }


@router.post("/extract-with-pattern")
async def extract_with_text_pattern(
    file: UploadFile = File(...),
    pattern_id: str = Form(...),
    current_user: TokenData = Depends(require_landlord),
):
    """Extract bill data from PDF using a text pattern."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    pdf_bytes = await file.read()
    
    # Load pattern
    pattern_file = os.path.join(TEXT_PATTERNS_DIR, f"{pattern_id}.json")
    if not os.path.exists(pattern_file):
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    with open(pattern_file, 'r', encoding='utf-8') as f:
        pattern = json.load(f)
    
    # Use shared extraction utility (same as email extraction)
    extracted_data = extract_with_pattern(pdf_bytes, pattern)
    
    return {"extracted_data": extracted_data}


@router.post("/extract-with-pattern-OLD-INLINE")
async def extract_with_text_pattern_old_inline(
    file: UploadFile = File(...),
    pattern_id: str = Form(...),
    current_user: TokenData = Depends(require_landlord),
):
    """OLD INLINE EXTRACTION - KEPT FOR REFERENCE IF UTILITY DOESN'T WORK"""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    pdf_bytes = await file.read()
    pdf_text = extract_text_from_pdf(pdf_bytes)
    pdf_lines = pdf_text.splitlines()
    
    # Load pattern
    pattern_file = os.path.join(TEXT_PATTERNS_DIR, f"{pattern_id}.json")
    if not os.path.exists(pattern_file):
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    with open(pattern_file, 'r', encoding='utf-8') as f:
        pattern = json.load(f)
    
    extracted_data = {}
    
    for field_pattern in pattern.get('field_patterns', []):
        field_name = field_pattern.get('field_name')
        label_text = field_pattern.get('label_text', '')
        line_offset = field_pattern.get('line_offset', 0)
        
        if not label_text:
            continue
        
        # Create flexible regex for label (allow extra chars, special chars)
        # Split into words and allow flexible spacing and extra characters between words
        label_words = label_text.split()
        if len(label_words) > 0:
            # Allow flexible matching: words can have extra chars, flexible spacing
            # Match each word, allowing extra characters after each character
            label_regex_parts = []
            for word in label_words:
                # Escape each character but allow extra chars after
                word_pattern = r'\s*'.join(re.escape(char) + r'[^\s]*' for char in word)
                label_regex_parts.append(word_pattern)
            label_regex = r'\s+'.join(label_regex_parts)
            # Case-sensitive matching
        else:
            label_regex = re.escape(label_text)
            label_regex = label_regex.replace(r'\ ', r'\s+')
        
        # Find label in text (case-sensitive)
        label_match = re.search(label_regex, pdf_text)
        
        if label_match:
            # Find the line where label appears
            label_pos = label_match.start()
            label_line_num = pdf_text[:label_pos].count('\n')
            
            # Look for value at label_line_num + line_offset
            target_line_num = label_line_num + line_offset
            
            if 0 <= target_line_num < len(pdf_lines):
                # Get the text from the target line
                target_line = pdf_lines[target_line_num].strip()
                if target_line:
                    # If offset is 0 (same line), remove label from extracted value
                    if line_offset == 0:
                        # Find label position in the line
                        label_in_line = target_line.find(label_text)
                        if label_in_line >= 0:
                            # Extract text after the label
                            after_label = target_line[label_in_line + len(label_text):].strip()
                            # Remove common separators (colon, dash, etc.)
                            after_label = re.sub(r'^[:;\-\s]+', '', after_label).strip()
                            extracted_value = after_label
                        else:
                            # Label not found in line, use whole line
                            extracted_value = re.sub(r'\s+', ' ', target_line).strip()
                    else:
                        # Offset > 0, use whole line
                        extracted_value = re.sub(r'\s+', ' ', target_line).strip()
                    
                    # Special handling for amount field
                    if field_name == 'amount' and extracted_value:
                        # Extract number and convert from bani
                        amount_match = re.search(r'\d+[,\.]?\d*', extracted_value)
                        if amount_match:
                            amount_str = amount_match.group(0).strip()
                            cleaned = amount_str.replace(',', '').replace('.', '').replace(' ', '').strip()
                            try:
                                amount_bani = int(cleaned)
                                extracted_data[field_name] = str(amount_bani / 100.0)
                            except (ValueError, TypeError):
                                extracted_data[field_name] = amount_str
                        else:
                            extracted_data[field_name] = extracted_value
                    # Special handling for currency - default to RON if not filled
                    elif field_name == 'currency':
                        if extracted_value:
                            # Extract 3-letter currency code
                            currency_match = re.search(r'[A-Z]{3}', extracted_value.upper())
                            if currency_match:
                                currency = currency_match.group(0)
                                if currency in ['LEI', 'RON']:
                                    extracted_data[field_name] = 'RON'
                                else:
                                    extracted_data[field_name] = currency
                            else:
                                extracted_data[field_name] = 'RON'  # Default
                        else:
                            extracted_data[field_name] = 'RON'  # Default if not filled
                    # Special handling for IBAN - remove spaces and extract only IBAN
                    elif field_name == 'iban' and extracted_value:
                        extracted_data[field_name] = extract_iban(extracted_value)
                    # Special handling for dates (due_date, bill_date) - extract date pattern
                    elif field_name in ['due_date', 'bill_date'] and extracted_value:
                        # Try parsing with month names first, then fallback to numeric
                        parsed_date = parse_date_with_month_names(extracted_value)
                        if parsed_date:
                            extracted_data[field_name] = parsed_date
                        else:
                            # Fallback to original value if parsing fails
                            extracted_data[field_name] = extracted_value
                    # Special handling for bill_number - smart prefix removal
                    elif field_name == 'bill_number' and extracted_value:
                        extracted_data[field_name] = clean_bill_number(extracted_value)
                    else:
                        # For other fields, use the extracted value (already cleaned)
                        extracted_data[field_name] = extracted_value
    
    # Load pattern metadata
    pattern_metadata = pattern.get('name', '')
    pattern_supplier = pattern.get('supplier', '')
    
    # Add description (pattern name) if not already extracted
    if 'description' not in extracted_data:
        extracted_data['description'] = pattern_metadata
    
    # Add legal_name from supplier if payment_details not selected
    if 'payment_details' not in extracted_data and pattern_supplier:
        extracted_data['legal_name'] = pattern_supplier
    
    return {"extracted_data": extracted_data}


@router.get("/list-patterns")
async def list_text_patterns(
    current_user: TokenData = Depends(require_landlord),
):
    """List all text patterns with their metadata."""
    patterns = []
    if os.path.exists(TEXT_PATTERNS_DIR):
        for filename in os.listdir(TEXT_PATTERNS_DIR):
            if filename.endswith('.json'):
                try:
                    pattern_file = os.path.join(TEXT_PATTERNS_DIR, filename)
                    with open(pattern_file, 'r', encoding='utf-8') as f:
                        pattern = json.load(f)
                        filename_base = filename[:-5]  # Remove .json extension
                        patterns.append({
                            "pattern_id": filename_base,
                            "name": pattern.get('name', ''),
                            "supplier": pattern.get('supplier', ''),
                            "bill_type": pattern.get('bill_type', 'utilities'),
                            "field_count": len(pattern.get('field_patterns', [])),
                            "created_at": pattern.get('created_at', ''),
                            "updated_at": pattern.get('updated_at', ''),
                        })
                except Exception as e:
                    logger.warning(f"Error loading pattern {filename}: {e}")
    
    # Sort by name
    patterns.sort(key=lambda p: p['name'].lower())
    return {"patterns": patterns}


@router.get("/get-pattern/{pattern_id}")
async def get_text_pattern(
    pattern_id: str,
    current_user: TokenData = Depends(require_landlord),
):
    """Get a specific text pattern by ID."""
    pattern_file = os.path.join(TEXT_PATTERNS_DIR, f"{pattern_id}.json")
    if not os.path.exists(pattern_file):
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    with open(pattern_file, 'r', encoding='utf-8') as f:
        pattern = json.load(f)
    
    return pattern


@router.put("/update-pattern/{pattern_id}")
async def update_text_pattern(
    pattern_id: str,
    pattern: TextPatternCreate,
    current_user: TokenData = Depends(require_landlord),
):
    """Update an existing text pattern - adds new fields, keeps existing ones."""
    pattern_file = os.path.join(TEXT_PATTERNS_DIR, f"{pattern_id}.json")
    if not os.path.exists(pattern_file):
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    # Load existing pattern
    with open(pattern_file, 'r', encoding='utf-8') as f:
        existing_pattern = json.load(f)
    
    # Create a map of existing field patterns by field_name
    # Clean up old fields (value_text, value_regex) from existing patterns
    existing_fields = {}
    for fp in existing_pattern.get('field_patterns', []):
        existing_fields[fp['field_name']] = {
            "field_name": fp['field_name'],
            "label_text": fp.get('label_text', ''),
            "line_offset": fp.get('line_offset', 0),
        }
    
    # Merge: keep existing fields, add/update new ones from the request
    for field_pattern in pattern.field_patterns:
        existing_fields[field_pattern.field_name] = {
            "field_name": field_pattern.field_name,
            "label_text": field_pattern.label_text,
            "line_offset": field_pattern.line_offset,
        }
    
    # Convert back to list (only field_name, label_text, line_offset)
    merged_field_patterns = list(existing_fields.values())
    
    # Update pattern metadata
    # Ensure field_patterns only contain field_name, label_text, line_offset (no value_text, value_regex)
    cleaned_field_patterns = []
    for fp in merged_field_patterns:
        cleaned_field_patterns.append({
            "field_name": fp.get('field_name', ''),
            "label_text": fp.get('label_text', ''),
            "line_offset": fp.get('line_offset', 0),
        })
    
    # Build pattern dict manually to ensure no value_text/value_regex fields
    pattern_dict = {
        "id": pattern_id,
        "name": pattern.name,
        "bill_type": pattern.bill_type,
        "supplier": pattern.supplier,
        "field_patterns": cleaned_field_patterns,  # Already cleaned, only has field_name, label_text, line_offset
        "created_at": existing_pattern.get('created_at', datetime.utcnow().isoformat()),
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    # Save updated pattern (manually constructed to avoid Pydantic adding optional fields)
    with open(pattern_file, 'w', encoding='utf-8') as f:
        json.dump(pattern_dict, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Updated text pattern {pattern_file}")
    
    return {"pattern_id": pattern_id, "message": "Pattern updated successfully"}

