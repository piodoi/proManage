"""
Shared utilities for text pattern extraction.

This module contains the core extraction logic used by both:
- Pattern creation tool (text_pattern_routes.py)
- Email bill extraction (text_pattern_extractor.py)

IMPORTANT: Any changes to extraction logic must be made here to ensure
both features extract bills consistently.
"""
import os
import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import fitz  # PyMuPDF

from app.utils.parsers import parse_amount

logger = logging.getLogger(__name__)

# Directory for storing text patterns
TEXT_PATTERNS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "text_patterns")


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF using PyMuPDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        try:
            for page in doc:
                text += page.get_text()
        finally:
            doc.close()
        
        if not text or not text.strip():
            logger.warning(f"[PDF Extract] PDF appears to be empty or contains no extractable text ({len(pdf_bytes)} bytes)")
        else:
            logger.debug(f"[PDF Extract] Extracted {len(text)} characters from PDF ({len(pdf_bytes)} bytes)")
        
        return text
    except Exception as e:
        logger.error(f"[PDF Extract] Failed to extract text from PDF: {e}", exc_info=True)
        return ""


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
    iban_match = re.search(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}', cleaned)
    if iban_match:
        iban = iban_match.group(0)
        # Try to find where IBAN naturally ends
        bank_words = ['BANCA', 'BANK', 'BANQUE', 'BANCO', 'BANKI', 'BANKA']
        for word in bank_words:
            if word in cleaned and cleaned.find(word) > len(iban):
                for length in [15, 16, 18, 20, 22, 24, 27, 28, 34]:
                    if start_pos + length <= len(cleaned):
                        candidate = cleaned[start_pos:start_pos + length]
                        if re.match(r'^[A-Z0-9]+$', candidate):
                            if start_pos + length < len(cleaned):
                                next_chars = cleaned[start_pos + length:start_pos + length + 5]
                                if not any(next_chars.startswith(w) for w in bank_words):
                                    return candidate
                            else:
                                return candidate
        
        if 15 <= len(iban) <= 34:
            return iban
    
    return cleaned


def clean_bill_number(text: str) -> Optional[str]:
    """Clean bill number - remove prefixes like 'NO.', 'NO ', 'nr.', etc."""
    if not text:
        return None
    
    patterns = [
        r'^Seria\s+ENG\s+nr\.?\s+',
        r'^Seria\s+[A-Z]+\s+nr\.?\s+',
        r'^nr\.?\s+',
        r'^No\.\s+',
        r'^NO\s+',
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    cleaned = text.strip()
    return cleaned if cleaned else None


def parse_date_with_month_names(date_str: str) -> Optional[str]:
    """Parse date with Romanian/English month names and return ISO format (YYYY-MM-DD)."""
    if not date_str:
        return None
    
    # Romanian month names mapping
    month_names_ro = {
        'ianuarie': '01', 'ian': '01',
        'februarie': '02', 'feb': '02',
        'martie': '03', 'mar': '03',
        'aprilie': '04', 'apr': '04',
        'mai': '05',
        'iunie': '06', 'iun': '06',
        'iulie': '07', 'iul': '07',
        'august': '08', 'aug': '08',
        'septembrie': '09', 'sep': '09',
        'octombrie': '10', 'oct': '10',
        'noiembrie': '11', 'nov': '11',
        'decembrie': '12', 'dec': '12'
    }
    
    date_str_lower = date_str.lower().strip()
    
    # Try matching "DD month YYYY"
    for month_name, month_num in month_names_ro.items():
        if month_name in date_str_lower:
            parts = re.findall(r'\d+', date_str)
            if len(parts) >= 2:
                day = parts[0].zfill(2)
                year = parts[-1] if len(parts[-1]) == 4 else f"20{parts[-1]}"
                return f"{year}-{month_num}-{day}"
    
    # Try standard date formats
    date_patterns = [
        r'(\d{2})\.(\d{2})\.(\d{4})',
        r'(\d{2})/(\d{2})/(\d{4})',
        r'(\d{4})-(\d{2})-(\d{2})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_str)
        if match:
            if pattern.endswith(r'(\d{4})'):  # DD.MM.YYYY or DD/MM/YYYY
                day, month, year = match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:  # YYYY-MM-DD
                return match.group(0)
    
    return None


def create_flexible_label_regex(label_text: str) -> str:
    """
    Create a flexible regex pattern for label matching.
    
    Allows for:
    - Extra characters between words
    - Flexible spacing
    - Special character variations
    """
    label_words = label_text.split()
    if len(label_words) == 0:
        return ''
    
    label_regex_parts = []
    for word in label_words:
        # Escape each character but allow extra chars after
        word_pattern = r'\s*'.join(re.escape(char) + r'[^\s]*' for char in word)
        label_regex_parts.append(word_pattern)
    
    # Join words with flexible spacing
    label_pattern = r'\s+'.join(label_regex_parts)
    return label_pattern


def extract_field_value(pdf_lines: List[str], label_text: str, line_offset: int) -> Optional[str]:
    """
    Extract field value from PDF lines using label and offset.
    
    Uses the working Tool tab logic:
    - Search in full PDF text (not line-by-line)
    - Find line number where label appears  
    - Extract value from line + offset
    
    Args:
        pdf_lines: List of text lines from PDF
        label_text: Label text to search for
        line_offset: Offset from label line (0 = same line, 1 = next line, etc.)
        
    Returns:
        Extracted value or None if not found
    """
    if not label_text:
        return None
    
    # Reconstruct full PDF text
    pdf_text = '\n'.join(pdf_lines)
    
    # Create flexible regex for label (same as old working code)
    label_words = label_text.split()
    if len(label_words) > 0:
        # Allow flexible matching: words can have extra chars, flexible spacing
        label_regex_parts = []
        for word in label_words:
            # Escape each character but allow extra chars after
            word_pattern = r'\s*'.join(re.escape(char) + r'[^\s]*' for char in word)
            label_regex_parts.append(word_pattern)
        label_regex = r'\s+'.join(label_regex_parts)
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
                extracted_value = None
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
                
                if extracted_value:
                    return extracted_value
    
    return None


def extract_with_pattern(pdf_bytes: bytes, pattern: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract bill data from PDF using a text pattern.
    
    Args:
        pdf_bytes: PDF file as bytes
        pattern: Pattern dictionary from JSON
        
    Returns:
        Dictionary with extracted data
    """
    pdf_text = extract_text_from_pdf(pdf_bytes)
    pdf_lines = pdf_text.splitlines()
    
    extracted_data = {}
    
    for field_pattern in pattern.get('field_patterns', []):
        field_name = field_pattern.get('field_name')
        label_text = field_pattern.get('label_text', '')
        line_offset = field_pattern.get('line_offset', 0)
        
        if not label_text or not field_name:
            continue
        
        # Extract value
        extracted_value = extract_field_value(pdf_lines, label_text, line_offset)
        
        if extracted_value:
            # Apply truncation if size is specified (size > 0)
            size = field_pattern.get('size', 0)
            if size and size > 0:
                extracted_value = extracted_value[:size]
            
            # Apply field-specific processing
            if field_name == 'iban':
                extracted_data[field_name] = extract_iban(extracted_value)
            elif field_name == 'amount':
                parsed_amount = parse_amount(extracted_value)
                if parsed_amount is not None:
                    extracted_data[field_name] = parsed_amount
                else:
                    extracted_data[field_name] = extracted_value
            elif field_name in ['due_date', 'bill_date']:
                parsed_date = parse_date_with_month_names(extracted_value)
                if parsed_date:
                    extracted_data[field_name] = parsed_date
                else:
                    extracted_data[field_name] = extracted_value
            elif field_name == 'bill_number':
                cleaned = clean_bill_number(extracted_value)
                if cleaned:  # Only add if not None/empty
                    extracted_data[field_name] = cleaned
            else:
                extracted_data[field_name] = extracted_value
    
    # Add pattern metadata
    pattern_metadata = pattern.get('name', '')
    pattern_supplier = pattern.get('supplier', '')
    
    if 'description' not in extracted_data and pattern_metadata:
        extracted_data['description'] = pattern_metadata
    
    if 'legal_name' not in extracted_data and pattern_supplier:
        extracted_data['legal_name'] = pattern_supplier
    
    return extracted_data


def match_pattern_to_pdf(pdf_bytes: bytes, pattern: Dict[str, Any]) -> int:
    """
    Calculate how many fields from the pattern match in the PDF.
    
    Args:
        pdf_bytes: PDF file as bytes
        pattern: Pattern dictionary from JSON
        
    Returns:
        Number of matched fields
    """
    pdf_text = extract_text_from_pdf(pdf_bytes)
    pdf_lines = pdf_text.splitlines()
    
    matched_count = 0
    field_patterns = pattern.get('field_patterns', [])
    
    for field_pattern in field_patterns:
        label_text = field_pattern.get('label_text', '')
        if not label_text:
            continue
        
        # Check if label exists in PDF (case-sensitive for strict matching)
        label_pattern = create_flexible_label_regex(label_text)
        
        for line in pdf_lines:
            if re.search(label_pattern, line):
                matched_count += 1
                break
    
    return matched_count

