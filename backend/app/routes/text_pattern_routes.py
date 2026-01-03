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
import fitz  # PyMuPDF

router = APIRouter(prefix="/text-patterns", tags=["text-patterns"])
logger = logging.getLogger(__name__)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Directory for storing text patterns
TEXT_PATTERNS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "text_patterns")
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


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF using the same method as pdf2txt."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    try:
        for page in doc:
            text += page.get_text()
    finally:
        doc.close()
    return text


def extract_iban(text: str) -> str:
    """Extract and clean IBAN from text - remove spaces and extract only IBAN (international format).
    IBAN format: [Country Code (2 letters)][Check Digits (2 digits)][BBAN (varies by country)]
    Uses country-specific lengths to extract exact IBAN and stop before extra text."""
    # IBAN lengths by country code (ISO 13616 standard)
    IBAN_LENGTHS = {
        'AD': 24, 'AE': 23, 'AL': 28, 'AT': 20, 'AZ': 28, 'BA': 20, 'BE': 16, 'BG': 22,
        'BH': 22, 'BR': 29, 'BY': 28, 'CH': 21, 'CR': 22, 'CY': 28, 'CZ': 24, 'DE': 22,
        'DK': 18, 'DO': 28, 'EE': 20, 'EG': 29, 'ES': 24, 'FI': 18, 'FO': 18, 'FR': 27,
        'GB': 22, 'GE': 22, 'GI': 23, 'GL': 18, 'GR': 27, 'GT': 28, 'HR': 21, 'HU': 28,
        'IE': 22, 'IL': 23, 'IS': 26, 'IT': 27, 'JO': 30, 'KW': 30, 'KZ': 20, 'LB': 28,
        'LC': 32, 'LI': 21, 'LT': 20, 'LU': 20, 'LV': 21, 'MC': 27, 'MD': 24, 'ME': 22,
        'MK': 19, 'MR': 27, 'MT': 31, 'MU': 30, 'NL': 18, 'NO': 15, 'PK': 24, 'PL': 28,
        'PS': 29, 'PT': 25, 'QA': 29, 'RO': 24, 'RS': 22, 'SA': 24, 'SE': 24, 'SI': 19,
        'SK': 24, 'SM': 27, 'TN': 24, 'TR': 26, 'UA': 29, 'VG': 24, 'XK': 20
    }
    
    # Remove all spaces and convert to uppercase
    cleaned = re.sub(r'\s+', '', text.upper())
    
    # Find IBAN start pattern: country code (2 letters) + check digits (2 digits)
    iban_start_match = re.search(r'[A-Z]{2}\d{2}', cleaned)
    if not iban_start_match:
        return cleaned
    
    start_pos = iban_start_match.start()
    country_code = iban_start_match.group(0)[:2]
    
    # Get expected IBAN length for this country, or use default range
    expected_length = IBAN_LENGTHS.get(country_code)
    
    if expected_length:
        # Extract exact length for known country
        if start_pos + expected_length <= len(cleaned):
            iban = cleaned[start_pos:start_pos + expected_length]
            # Verify it's all alphanumeric (IBAN should be)
            if re.match(r'^[A-Z0-9]+$', iban):
                return iban
    
    # Fallback: try to extract IBAN with common lengths (15-34)
    # Match pattern and extract up to 34 characters, then try to find natural boundary
    iban_match = re.search(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}', cleaned)
    if iban_match:
        iban = iban_match.group(0)
        # Try to find where IBAN naturally ends (before common bank name words or non-alphanumeric)
        # Common bank-related words that might follow IBAN
        bank_words = ['BANCA', 'BANK', 'BANQUE', 'BANCO', 'BANKI', 'BANKA']
        for word in bank_words:
            if word in cleaned and cleaned.find(word) > len(iban):
                # IBAN might be shorter, try common lengths
                for length in [15, 16, 18, 20, 22, 24, 27, 28, 34]:
                    if start_pos + length <= len(cleaned):
                        candidate = cleaned[start_pos:start_pos + length]
                        if re.match(r'^[A-Z0-9]+$', candidate):
                            # Check if next char would be start of bank word
                            if start_pos + length < len(cleaned):
                                next_chars = cleaned[start_pos + length:start_pos + length + 5]
                                if not any(next_chars.startswith(w) for w in bank_words):
                                    return candidate
                            else:
                                return candidate
        
        # If no bank word found, return the matched IBAN (but limit to 34 chars)
        if 15 <= len(iban) <= 34:
            return iban
    
    return cleaned


def clean_bill_number(text: str) -> str:
    """Clean bill number - only remove prefixes like 'NO.', 'NO ', 'nr.', etc. if followed by alphanumeric.
    Don't remove 'NO' if it's part of a word like 'NOvember'."""
    # Patterns to match: "NO." or "NO " or "nr." etc. followed by alphanumeric (not part of a word)
    # Use word boundaries to ensure we're not matching "NO" in "NOvember"
    patterns = [
        r'^Seria\s+ENG\s+nr\.?\s+',
        r'^Seria\s+[A-Z]+\s+nr\.?\s+',
        r'^nr\.?\s+',
        r'^No\.\s+',  # "No." with period
        r'^NO\s+',     # "NO " with space (not part of word)
        r'^No\s+',     # "No " with space
    ]
    
    for pattern in patterns:
        # Check if pattern matches and is followed by alphanumeric (not part of word)
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            remaining = text[match.end():].strip()
            # Only remove if followed by alphanumeric (likely a bill number)
            if remaining and re.match(r'^[A-Z0-9]', remaining, re.IGNORECASE):
                return remaining
    
    return text.strip()


def parse_date_with_month_names(text: str) -> Optional[str]:
    """Parse date with Romanian or English month names and convert to DD/MM/YYYY format."""
    # Romanian month names
    ro_months = {
        'ianuarie': 1, 'februarie': 2, 'martie': 3, 'aprilie': 4, 'mai': 5, 'iunie': 6,
        'iulie': 7, 'august': 8, 'septembrie': 9, 'octombrie': 10, 'noiembrie': 11, 'decembrie': 12
    }
    
    # English month names
    en_months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    # Try to match date patterns with month names
    # Pattern: "5 Decembrie 2025" or "5 December 2025"
    date_pattern = r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})'
    match = re.search(date_pattern, text, re.IGNORECASE)
    
    if match:
        day = int(match.group(1))
        month_name = match.group(2).lower()
        year = int(match.group(3))
        
        # Check Romanian months
        if month_name in ro_months:
            month = ro_months[month_name]
        # Check English months
        elif month_name in en_months:
            month = en_months[month_name]
        else:
            return None
        
        # Format as DD/MM/YYYY
        return f"{day:02d}/{month:02d}/{year}"
    
    # Fallback to numeric date pattern (DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY)
    numeric_match = re.search(r'(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{2,4})', text)
    if numeric_match:
        day = int(numeric_match.group(1))
        month = int(numeric_match.group(2))
        year_str = numeric_match.group(3)
        # Handle 2-digit years
        if len(year_str) == 2:
            year = int(year_str)
            if year < 50:
                year += 2000
            else:
                year += 1900
        else:
            year = int(year_str)
        
        return f"{day:02d}/{month:02d}/{year}"
    
    return None


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
    
    # Save only field_name, label_text, and line_offset (no regex generation)
    processed_patterns = []
    for field_pattern in pattern.field_patterns:
        processed_patterns.append({
            "field_name": field_pattern.field_name,
            "label_text": field_pattern.label_text,
            "line_offset": field_pattern.line_offset,
        })
    
    text_pattern = TextPattern(
        id=pattern_id,
        name=pattern.name,
        bill_type=pattern.bill_type,
        supplier=pattern.supplier,
        field_patterns=processed_patterns,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )
    
    # Save to file
    pattern_file = os.path.join(TEXT_PATTERNS_DIR, f"{pattern_id}.json")
    with open(pattern_file, 'w', encoding='utf-8') as f:
        json.dump(text_pattern.model_dump(), f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved text pattern to {pattern_file}")
    
    return {"pattern_id": pattern_id, "message": "Pattern saved successfully"}


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
    
    # Load all patterns
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
                            'pattern': pattern,
                            'filename_base': filename_base
                        })
                except Exception as e:
                    logger.warning(f"Error loading pattern {filename}: {e}")
    
    matches = []
    for pattern_data in patterns:
        pattern = pattern_data['pattern']
        filename_base = pattern_data['filename_base']
        
        # Calculate confidence based on how many field patterns match
        matched_fields = 0
        total_fields = len(pattern.get('field_patterns', []))
        
        for field_pattern in pattern.get('field_patterns', []):
            label_text = field_pattern.get('label_text', '')
            if label_text:
                # Try to find label in text (case-sensitive, flexible)
                label_regex = re.escape(label_text)
                label_regex = label_regex.replace(r'\ ', r'\s+')  # Allow flexible spacing
                if re.search(label_regex, pdf_text):
                    matched_fields += 1
        
        if matched_fields > 0:
            confidence = matched_fields / total_fields if total_fields > 0 else 0
            matches.append({
                "pattern_id": filename_base,  # Use filename as pattern_id
                "pattern_name": pattern['name'],
                "supplier": pattern.get('supplier'),
                "confidence": confidence,
                "matched_fields": matched_fields,
                "total_fields": total_fields,
            })
    
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

