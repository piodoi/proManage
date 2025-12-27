import re
from typing import Optional, Tuple
import fitz
import logging
import sys

from app.models import ExtractionPattern, ExtractionResult

logger = logging.getLogger(__name__)
# Ensure logger has a handler
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def extract_value_by_label_position(pdf_bytes: bytes, label: str, max_distance: float = 200.0) -> Optional[str]:
    """
    Extract a value from PDF by finding a label and looking for its value to the right or below.
    Useful for tabular layouts where labels and values are in separate columns.
    
    Args:
        pdf_bytes: PDF file content
        label: Label text to search for (e.g., "Cont IBAN:", "Cod client:")
        max_distance: Maximum horizontal distance to search for value (in points)
    
    Returns:
        Extracted value string or None if not found
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Normalize label: remove extra spaces, colons, make lowercase for matching
    label_normalized = re.sub(r'[:\s]+', ' ', label).strip().lower()
    label_parts = label_normalized.split()
    
    for page in doc:
        # Get words with position: (x0, y0, x1, y1, "text", block_no, line_no, word_no)
        words = page.get_text("words")
        if not words:
            continue
        
        # Build list of (x0, y0, x1, y1, text) for easier searching
        word_list = [(w[0], w[1], w[2], w[3], w[4]) for w in words]
        
        # Find label in words
        for i in range(len(word_list)):
            # Try to match label starting at position i
            matched = True
            label_positions = []
            label_texts = []
            
            # Check if we can match the label starting from word i
            for j, part in enumerate(label_parts):
                if i + j >= len(word_list):
                    matched = False
                    break
                x0, y0, x1, y1, text = word_list[i + j]
                text_normalized = re.sub(r'[:\s]+', ' ', text).strip().lower()
                # Check if this word contains the label part
                if part not in text_normalized and text_normalized not in part:
                    matched = False
                    break
                label_positions.append((x0, y0, x1, y1))
                label_texts.append(text)
            
            if matched and label_positions:
                # Label found! Now find the value
                label_end_x = label_positions[-1][2]  # x1 of last label word
                label_start_x = label_positions[0][0]  # x0 of first label word
                label_y = label_positions[0][1]  # y0 of first label word
                label_bottom = max(y1 for _, _, _, y1 in label_positions)
                
                # Search for value after label position
                value_candidates = []
                search_start = i + len(label_parts)
                
                for k in range(search_start, len(word_list)):
                    vx0, vy0, vx1, vy1, vtext = word_list[k]
                    vtext_clean = vtext.strip()
                    
                    # Skip empty text, punctuation-only text, or labels
                    if not vtext_clean or re.match(r'^[:\.,;]+$', vtext_clean):
                        continue
                    
                    # Same line (y within 5 pixels tolerance) and to the right
                    if abs(vy0 - label_y) < 5 and vx0 > label_end_x:
                        # Value is on the same line to the right
                        distance = vx0 - label_end_x
                        if distance < max_distance:
                            value_candidates.append((vx0, vy0, vtext_clean, distance, 'same_line'))
                    # Next line (y below label but within reasonable distance)
                    elif vy0 > label_bottom and vy0 < label_bottom + 25:
                        # Value is on the line below, check if x is similar (within column alignment)
                        x_diff = abs(vx0 - label_start_x)
                        if x_diff < max_distance:
                            value_candidates.append((vx0, vy0, vtext_clean, x_diff, 'next_line'))
                
                if value_candidates:
                    # Sort by: prefer same_line, then by distance (closer is better)
                    value_candidates.sort(key=lambda v: (v[4] != 'same_line', v[3]))
                    
                    # Get the best candidate
                    best_candidate = value_candidates[0]
                    value = best_candidate[2]
                    
                    # For multi-word values on same line, collect adjacent words
                    if best_candidate[4] == 'same_line':
                        best_x, best_y, _, _, _ = best_candidate
                        # Look for additional words on the same line to the right
                        value_words = [value]
                        for k in range(search_start, len(word_list)):
                            vx0, vy0, vx1, vy1, vtext = word_list[k]
                            if abs(vy0 - best_y) < 5 and vx0 > best_x + 5:
                                # Check if this word is close (probably part of same value)
                                if vx0 < best_x + 150:  # Reasonable width for a value
                                    vtext_clean = vtext.strip()
                                    if vtext_clean and not re.match(r'^[:\.,;]+$', vtext_clean):
                                        value_words.append(vtext_clean)
                                    else:
                                        break
                                else:
                                    break
                        
                        value = ' '.join(value_words)
                    
                    if value:
                        logger.info(f"[Position-based] Found value for label '{label}': {value}")
                        doc.close()
                        return value.strip()
    
    doc.close()
    return None


def apply_pattern(text: str, pattern: Optional[str], debug_name: str = "") -> Optional[str]:
    if not pattern:
        return None
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            result = match.group(1) if match.groups() else match.group(0)
            # Clean up the result
            if result:
                result = result.strip()
                # Remove trailing period if present
                result = result.rstrip('.')
                # Don't filter short results here - let the calling function (extract_bill_number, etc.) decide
                # This allows apartment numbers (single digits) to pass through
                if len(result) < 1:
                    return None
            return result
        elif debug_name and "due_date" in debug_name:
            # Debug: show why pattern didn't match for due_date
            idx = text.lower().find('scaden')
            if idx >= 0:
                context = text[max(0, idx-10):min(len(text), idx+50)]
                logger.info(f"[Pattern Debug] Pattern: {pattern}")
                logger.info(f"[Pattern Debug] Context: {repr(context)}")
                # Try to see what newline characters are present
                newline_chars = [c for c in context if c in ['\n', '\r', '\r\n']]
                logger.info(f"[Pattern Debug] Newline chars in context: {repr(newline_chars)}")
    except re.error as e:
        if debug_name:
            logger.warning(f"[Pattern] Regex error for '{debug_name}': {e}")
    return None


def extract_iban(text: str, custom_pattern: Optional[str] = None) -> Optional[str]:
    if custom_pattern:
        # For IBAN patterns, we want to capture the full IBAN
        # If pattern has capturing group, use it, otherwise match the whole pattern
        try:
            match = re.search(custom_pattern, text, re.IGNORECASE)
            if match:
                # If there's a capturing group, use it, otherwise use the full match
                if match.groups():
                    result = match.group(1)
                else:
                    result = match.group(0)
                if result:
                    # Normalize IBAN: remove spaces, uppercase
                    normalized = re.sub(r'\s+', '', result.upper())
                    return normalized
        except re.error:
            pass
    iban_pattern = r'\b([A-Z]{2}\d{2}[A-Z0-9]{4,30})\b'
    match = re.search(iban_pattern, text, re.IGNORECASE)
    if match:
        normalized = re.sub(r'\s+', '', match.group(1).upper())
        return normalized
    return None


def extract_amount(text: str, custom_pattern: Optional[str] = None) -> Optional[float]:
    if custom_pattern:
        result = apply_pattern(text, custom_pattern)
        if result:
            try:
                cleaned = result.replace(',', '.').replace(' ', '')
                return float(cleaned)
            except ValueError:
                pass
    amount_patterns = [
        r'(?:total|suma|amount|de plata|plata)[\s:]*(\d+[.,]\d{2})\s*(?:lei|ron|eur)?',
        r'(\d+[.,]\d{2})\s*(?:lei|ron|eur)',
        r'(?:lei|ron|eur)\s*(\d+[.,]\d{2})',
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                cleaned = match.group(1).replace(',', '.')
                return float(cleaned)
            except ValueError:
                continue
    return None


def extract_bill_number(text: str, custom_pattern: Optional[str] = None, pdf_bytes: Optional[bytes] = None) -> Optional[str]:
    if custom_pattern:
        result = apply_pattern(text, custom_pattern)
        if result:
            # Clean up the result - remove leading/trailing whitespace and ensure it's meaningful
            cleaned = result.strip()
            # Remove trailing period if present (e.g., "Apartament 5." -> "Apartament 5")
            cleaned = cleaned.rstrip('.')
            # For apartment identifiers (like "Apartament 5", "Ap 1", "Ap: 2"), allow them
            # Check if pattern is for apartment (common patterns)
            is_apartment_pattern = 'apartament' in custom_pattern.lower() or '\\bap[\\s:]' in custom_pattern.lower()
            min_length = 3 if is_apartment_pattern else 3  # "Ap 1" is 4 chars, "Apartament 5" is ~13 chars
            if len(cleaned) >= min_length:
                return cleaned
        # If pattern failed and we have PDF bytes, try position-based extraction as fallback
        elif pdf_bytes:
            logger.info(f"[Bill Number] Trying position-based extraction as fallback...")
            # Try common bill number labels
            for label in ["Factură seria și nr.", "Factura seria si nr.", "Număr factură", "Numar factura"]:
                position_result = extract_value_by_label_position(pdf_bytes, label, max_distance=150.0)
                if position_result and len(position_result) >= 3:
                    return position_result
    bill_patterns = [
        r'(?:nr\.?\s*factura|numar\s*factura|invoice\s*(?:no|number)|bill\s*(?:no|number))[\s:]*([A-Z0-9\-/]+)',
        r'(?:factura|invoice|bill)[\s#:]*([A-Z0-9\-/]+)',
    ]
    for pattern in bill_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result = match.group(1).strip()
            # Filter out very short results
            if len(result) >= 3:
                return result
    return None


def extract_contract_id(text: str, custom_pattern: Optional[str] = None, pdf_bytes: Optional[bytes] = None) -> Optional[str]:
    """Extract contract/client ID."""
    if custom_pattern:
        # Try custom pattern first
        try:
            match = re.search(custom_pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                # Return first non-empty group, or the full match if no groups
                for i in range(1, len(match.groups()) + 1):
                    if match.group(i):
                        return match.group(i).strip()
                return match.group(0).strip()
        except re.error:
            pass
        # If pattern failed and we have PDF bytes, try position-based extraction as fallback
        if pdf_bytes:
            logger.info(f"[Contract ID] Trying position-based extraction as fallback...")
            position_result = extract_value_by_label_position(pdf_bytes, "Cod client", max_distance=150.0)
            if position_result:
                return position_result
    # Default patterns
    contract_patterns = [
        r'(?:cod\s+cont\s+contract|cont\s+contract|cod\s+contract)[\s:]*([0-9]+)',
        r'(?:cont\s+client|contract\s+id|client\s+id|client\s+number)[\s:]*([0-9]+)',
        r'CONT\s+CONTRACT[:\s]+([0-9]+)',
        r'([0-9]+)\s*\n?\s*Cod\s+Cont\s+Contract',  # Number before label
    ]
    for pattern in contract_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def convert_romanian_date_to_standard(romanian_date: str) -> Optional[str]:
    """
    Convert Romanian date format to standard format (DD/MM/YYYY).
    Example: "11 Ianuarie 2026" -> "11/01/2026"
    """
    # Romanian month names mapping
    month_map = {
        'ianuarie': '01', 'februarie': '02', 'martie': '03', 'aprilie': '04',
        'mai': '05', 'iunie': '06', 'iulie': '07', 'august': '08',
        'septembrie': '09', 'octombrie': '10', 'noiembrie': '11', 'decembrie': '12'
    }
    
    # Try to match Romanian date pattern: "DD Month YYYY" or "DD MonthName YYYY"
    # Pattern: day (1-2 digits), month name, year (4 digits)
    pattern = r'(\d{1,2})\s+([a-z]+)\s+(\d{4})'
    match = re.search(pattern, romanian_date.lower().strip(), re.IGNORECASE)
    
    if match:
        day, month_str, year = match.groups()
        month_lower = month_str.lower()
        
        # Check if it's a Romanian month name
        if month_lower in month_map:
            month_num = month_map[month_lower]
            day_padded = day.zfill(2)  # Ensure 2 digits
            return f"{day_padded}/{month_num}/{year}"
    
    return None


def extract_due_date(text: str, custom_pattern: Optional[str] = None, pdf_bytes: Optional[bytes] = None) -> Optional[str]:
    """Extract due date."""
    if custom_pattern:
        # Find context around "scaden" for debugging
        idx = text.lower().find('scaden')
        if idx >= 0:
            context = text[max(0, idx-10):min(len(text), idx+50)]
            # Show actual characters (including newlines)
            logger.info(f"[Due Date] Pattern: {custom_pattern}")
            logger.info(f"[Due Date] Text context: {repr(context)}")
            # Try the pattern
            result = apply_pattern(text, custom_pattern, "due_date")
            if result:
                logger.info(f"[Due Date] Extracted: {result}")
                # Check if result is in Romanian date format and convert it
                converted = convert_romanian_date_to_standard(result)
                if converted:
                    logger.info(f"[Due Date] Converted Romanian date '{result}' to '{converted}'")
                    return converted
                return result
            else:
                # Try to see what's actually there
                logger.warning(f"[Due Date] Pattern failed. Trying alternative...")
                # Try pattern without requiring colon
                alt_pattern = custom_pattern.replace(':', '[:\\s]*')
                alt_result = apply_pattern(text, alt_pattern, "due_date_alt")
                if alt_result:
                    logger.info(f"[Due Date] Extracted with alt pattern: {alt_result}")
                    # Check if result is in Romanian date format and convert it
                    converted = convert_romanian_date_to_standard(alt_result)
                    if converted:
                        logger.info(f"[Due Date] Converted Romanian date '{alt_result}' to '{converted}'")
                        return converted
                    return alt_result
                # If still no result and we have PDF bytes, try position-based extraction as fallback
                elif pdf_bytes:
                    logger.info(f"[Due Date] Trying position-based extraction as fallback...")
                    position_result = extract_value_by_label_position(pdf_bytes, "Ultima zi de plată", max_distance=150.0)
                    if position_result:
                        # Check if result is in Romanian date format and convert it
                        converted = convert_romanian_date_to_standard(position_result)
                        if converted:
                            logger.info(f"[Due Date] Converted Romanian date '{position_result}' to '{converted}'")
                            return converted
                        return position_result
        else:
            logger.warning(f"[Due Date] 'scaden' not found in text")
    # Default patterns for various date formats (handle newlines between label and date)
    # Note: [țţ] matches both t-comma (U+021B) and t-cedilla (U+0163) variants
    due_date_patterns = [
        r'(?:data\s+scaden[țţ]ei|data\s+scadentei|due\s+date|scaden[țţ]ă|scadenta):\s*\n\s*([0-9]{2}/[0-9]{2}/[0-9]{4})',
        r'(?:data\s+scaden[țţ]ei|data\s+scadentei|due\s+date|scaden[țţ]ă|scadenta):\s*\n\s*([0-9]{4}-[0-9]{2}-[0-9]{2})',
        r'(?:data\s+scaden[țţ]ei|data\s+scadentei|due\s+date|scaden[țţ]ă|scadenta):\s*\n\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})',
    ]
    for pattern in due_date_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            result = match.group(1).strip()
            logger.info(f"[Due Date] Extracted via default pattern: {result}")
            # Check if result is in Romanian date format and convert it
            converted = convert_romanian_date_to_standard(result)
            if converted:
                logger.info(f"[Due Date] Converted Romanian date '{result}' to '{converted}'")
                return converted
            return result
    logger.warning(f"[Due Date] No due date found")
    return None


def extract_business_name(text: str, custom_pattern: Optional[str] = None) -> Optional[str]:
    """Extract business name for bank transfer."""
    if custom_pattern:
        # Special handling for pattern that matches first line (^)
        if custom_pattern.startswith('^'):
            # Get first line of text
            first_line = text.split('\n')[0].strip()
            if first_line:
                return first_line
        else:
            result = apply_pattern(text, custom_pattern)
            if result:
                return result.strip()
    # Default patterns
    business_patterns = [
        r'(?:beneficiar|payee|business\s+name|nume\s+firma)[\s:]*([A-Z][A-Za-z\s&\.]+(?:SA|S\.A\.|SRL|LTD))',
    ]
    for pattern in business_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def sync_bank_accounts(text: str, expected_bank_accounts: list[dict[str, str]]) -> tuple[bool, list[dict[str, str]]]:
    """
    Sync bank accounts: keep IBANs found in PDF, remove missing ones, add new ones.
    Returns (is_valid, updated_bank_accounts_list)
    """
    if not expected_bank_accounts:
        # No existing bank accounts, extract all from PDF
        text_ibans = set()
        iban_matches = re.findall(r'RO\d{2}\s*[A-Z0-9]{4,30}', text, re.IGNORECASE)
        for iban in iban_matches:
            normalized = re.sub(r'\s+', '', iban.upper())
            text_ibans.add(normalized)
        
        new_accounts = [{"bank": "Unknown", "iban": iban} for iban in text_ibans]
        return (True, new_accounts)
    
    # Normalize IBANs for comparison (remove spaces)
    text_ibans = set()
    iban_matches = re.findall(r'RO\d{2}\s*[A-Z0-9]{4,30}', text, re.IGNORECASE)
    for iban in iban_matches:
        normalized = re.sub(r'\s+', '', iban.upper())
        text_ibans.add(normalized)
    
    # Create a map of normalized IBAN -> bank_account for quick lookup
    iban_to_account = {}
    for account in expected_bank_accounts:
        iban = account.get('iban', '')
        if iban:
            normalized = re.sub(r'\s+', '', iban.upper())
            iban_to_account[normalized] = account
    
    # Keep accounts whose IBANs are found in PDF
    updated_accounts = []
    removed_accounts = []
    for account in expected_bank_accounts:
        iban = account.get('iban', '')
        if iban:
            normalized = re.sub(r'\s+', '', iban.upper())
            if normalized in text_ibans:
                updated_accounts.append(account)
            else:
                removed_accounts.append(normalized)
    
    # Add new IBANs from PDF that aren't in the pattern
    new_accounts = []
    for iban in text_ibans:
        if iban not in iban_to_account:
            # Try to extract bank name from IBAN code
            bank_name = "Unknown"
            bank_keywords = {
                'CITI': 'Citibank',
                'INGB': 'ING Bank',
                'BRDE': 'BRD',
                'BTRL': 'Banca Transilvania',
                'RNCB': 'BCR',
                'BUCU': 'Alpha Bank',
                'BACX': 'UniCredit Bank',
                'RZBR': 'Raiffeisen Bank',
                'TREZ': 'Trezorerie',
                'PIRB': 'First Bank',
                'CECE': 'CEC Bank',
                'UGBI': 'Garanti Bank',
            }
            for code, name in bank_keywords.items():
                if code in iban:
                    bank_name = name
                    break
            
            new_accounts.append({"bank": bank_name, "iban": iban})
    
    # Combine kept and new accounts
    final_accounts = updated_accounts + new_accounts
    
    if removed_accounts or new_accounts:
        logger.info(f"[Bank Sync] Updated: {len(removed_accounts)} removed, {len(new_accounts)} added")
    
    # Valid if we have at least one account (either kept or new)
    is_valid = len(final_accounts) > 0
    return (is_valid, final_accounts)


def extract_addresses(text: str, custom_pattern: Optional[str] = None) -> list[str]:
    addresses = []
    if custom_pattern:
        try:
            matches = re.findall(custom_pattern, text, re.IGNORECASE | re.MULTILINE)
            addresses.extend([m if isinstance(m, str) else m[0] for m in matches])
        except re.error:
            pass
    address_patterns = [
        r'(?:loc\s*consum|adresa|address|strada|str\.)[\s:]*([^\n]{10,100})',
        r'(?:str\.|strada|bd\.|bulevardul|calea)\s+[A-Za-z\s]+(?:nr\.?\s*\d+)?(?:,\s*[A-Za-z\s]+)?',
    ]
    for pattern in address_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            addr = match.strip() if isinstance(match, str) else match[0].strip()
            if addr and len(addr) > 5 and addr not in addresses:
                addresses.append(addr)
    return addresses


def extract_consumption_location(text: str) -> Optional[str]:
    loc_patterns = [
        r'loc\s*(?:de\s*)?consum[\s:]*([^\n]{10,100})',
        r'punct\s*(?:de\s*)?consum[\s:]*([^\n]{10,100})',
        r'adresa\s*(?:de\s*)?consum[\s:]*([^\n]{10,100})',
    ]
    for pattern in loc_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def check_vendor_hint(text: str, vendor_hint: Optional[str]) -> bool:
    if not vendor_hint:
        return True
    # More relaxed matching: check if vendor_hint appears anywhere in text (case-insensitive)
    # This handles cases where vendor_hint is a simple word like "Vodafone"
    vendor_hint_lower = vendor_hint.lower().strip()
    text_lower = text.lower()
    
    # First try simple substring match (most common case)
    if vendor_hint_lower in text_lower:
        return True
    
    # Fallback to regex if vendor_hint contains special characters
    try:
        return bool(re.search(re.escape(vendor_hint), text, re.IGNORECASE))
    except re.error:
        return False


def parse_pdf_with_patterns(
    pdf_bytes: bytes,
    patterns: list[ExtractionPattern],
) -> Tuple[ExtractionResult, Optional[ExtractionPattern]]:
    text = extract_text_from_pdf(pdf_bytes)
    sorted_patterns = sorted(
        [p for p in patterns if p.enabled],
        key=lambda p: p.priority,
        reverse=True,
    )
    matched_pattern: Optional[ExtractionPattern] = None
    for pattern in sorted_patterns:
        if check_vendor_hint(text, pattern.vendor_hint):
            matched_pattern = pattern
            logger.info(f"[PDF Parser] Matched pattern: {pattern.name} (supplier: {pattern.supplier})")
            break
    if not matched_pattern:
        logger.warning(f"[PDF Parser] No pattern matched")
    iban = extract_iban(
        text,
        matched_pattern.iban_pattern if matched_pattern else None,
    )
    amount = extract_amount(
        text,
        matched_pattern.amount_pattern if matched_pattern else None,
    )
    bill_number = extract_bill_number(
        text,
        matched_pattern.bill_number_pattern if matched_pattern else None,
        pdf_bytes=pdf_bytes,  # Pass PDF bytes for position-based fallback
    )
    contract_id = extract_contract_id(
        text,
        matched_pattern.contract_id_pattern if matched_pattern else None,
        pdf_bytes=pdf_bytes,  # Pass PDF bytes for position-based fallback
    )
    due_date = extract_due_date(
        text,
        matched_pattern.due_date_pattern if matched_pattern else None,
        pdf_bytes=pdf_bytes,  # Pass PDF bytes for position-based fallback
    )
    if due_date:
        logger.info(f"[PDF Parser] Extracted due_date: {due_date}")
    else:
        logger.warning(f"[PDF Parser] No due_date extracted from PDF")
    business_name = extract_business_name(
        text,
        matched_pattern.business_name_pattern if matched_pattern else None,
    )
    
    # Sync bank accounts if pattern has them defined (only after pattern match)
    is_valid = True
    bank_accounts_list = []
    pattern_needs_update = False
    if matched_pattern and matched_pattern.bank_accounts:
        is_valid, bank_accounts_list = sync_bank_accounts(text, matched_pattern.bank_accounts)
        # Check if bank_accounts_list differs from pattern's bank_accounts
        if bank_accounts_list != matched_pattern.bank_accounts:
            pattern_needs_update = True
            logger.info(f"[PDF Parser] Bank accounts updated: {len(matched_pattern.bank_accounts)} -> {len(bank_accounts_list)}")
    elif matched_pattern:
        # No bank accounts in pattern, but we found some in PDF - add them
        is_valid, bank_accounts_list = sync_bank_accounts(text, [])
        if bank_accounts_list:
            pattern_needs_update = True
            logger.info(f"[PDF Parser] Added {len(bank_accounts_list)} new bank accounts to pattern")
    
    all_addresses = extract_addresses(
        text,
        matched_pattern.address_pattern if matched_pattern else None,
    )
    consumption_location = extract_consumption_location(text)
    address = consumption_location or (all_addresses[0] if all_addresses else None)
    
    # Return the pattern that needs updating (if bank accounts changed)
    pattern_to_update = None
    if pattern_needs_update and matched_pattern:
        pattern_to_update = matched_pattern
    
    return (
        ExtractionResult(
            iban=iban,
            contract_id=contract_id,
            bill_number=bill_number,
            amount=amount,
            due_date=due_date,
            address=address,
            consumption_location=consumption_location,
            business_name=business_name,
            all_addresses=all_addresses,
            bank_accounts=bank_accounts_list,
            matched_pattern_id=matched_pattern.id if matched_pattern and is_valid else None,
            matched_pattern_name=matched_pattern.name if matched_pattern and is_valid else None,
            matched_pattern_supplier=matched_pattern.supplier if matched_pattern and is_valid else None,
            raw_text=text,
        ),
        pattern_to_update
    )
