import re
from typing import Optional
import fitz
import logging

from app.models import ExtractionPattern, ExtractionResult

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def apply_pattern(text: str, pattern: Optional[str]) -> Optional[str]:
    if not pattern:
        return None
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    except re.error:
        pass
    return None


def extract_iban(text: str, custom_pattern: Optional[str] = None) -> Optional[str]:
    if custom_pattern:
        result = apply_pattern(text, custom_pattern)
        if result:
            return result
    iban_pattern = r'\b([A-Z]{2}\d{2}[A-Z0-9]{4,30})\b'
    match = re.search(iban_pattern, text)
    return match.group(1) if match else None


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


def extract_bill_number(text: str, custom_pattern: Optional[str] = None) -> Optional[str]:
    if custom_pattern:
        result = apply_pattern(text, custom_pattern)
        if result:
            return result
    bill_patterns = [
        r'(?:nr\.?\s*factura|numar\s*factura|invoice\s*(?:no|number)|bill\s*(?:no|number))[\s:]*([A-Z0-9\-/]+)',
        r'(?:factura|invoice|bill)[\s#:]*([A-Z0-9\-/]+)',
    ]
    for pattern in bill_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_contract_id(text: str, custom_pattern: Optional[str] = None) -> Optional[str]:
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


def extract_due_date(text: str, custom_pattern: Optional[str] = None) -> Optional[str]:
    """Extract due date."""
    if custom_pattern:
        result = apply_pattern(text, custom_pattern)
        if result:
            return result.strip()
    # Default patterns for various date formats
    due_date_patterns = [
        r'(?:data\s+scadenței|data\s+scadentei|due\s+date|scadență|scadenta)[\s:]*([0-9]{2}/[0-9]{2}/[0-9]{4})',
        r'(?:data\s+scadenței|data\s+scadentei|due\s+date|scadență|scadenta)[\s:]*([0-9]{4}-[0-9]{2}-[0-9]{2})',
        r'(?:data\s+scadenței|data\s+scadentei|due\s+date|scadență|scadenta)[\s:]*([0-9]{2}\.[0-9]{2}\.[0-9]{4})',
    ]
    for pattern in due_date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_business_name(text: str, custom_pattern: Optional[str] = None) -> Optional[str]:
    """Extract business name for bank transfer."""
    if custom_pattern:
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


def validate_bank_accounts(text: str, expected_bank_accounts: list[dict[str, str]]) -> bool:
    """Validate that all expected bank accounts (IBANs) are present in the text."""
    if not expected_bank_accounts:
        return True  # No validation needed if no bank accounts specified
    
    # Normalize IBANs for comparison (remove spaces)
    text_ibans = set()
    iban_matches = re.findall(r'RO\d{2}\s*[A-Z0-9]{4,30}', text, re.IGNORECASE)
    for iban in iban_matches:
        normalized = re.sub(r'\s+', '', iban.upper())
        text_ibans.add(normalized)
    
    # Check if all expected IBANs are present
    for bank_account in expected_bank_accounts:
        expected_iban = bank_account.get('iban', '')
        if expected_iban:
            normalized_expected = re.sub(r'\s+', '', expected_iban.upper())
            if normalized_expected not in text_ibans:
                return False  # Missing expected IBAN
    
    return True  # All IBANs found


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
    
    # Log for debugging
    logger.debug(f"[Vendor Hint Check] Looking for '{vendor_hint}' in text (first 200 chars: {text[:200]})")
    
    # First try simple substring match (most common case)
    if vendor_hint_lower in text_lower:
        logger.debug(f"[Vendor Hint Check] ✓ Found '{vendor_hint}' in text (substring match)")
        return True
    
    # Fallback to regex if vendor_hint contains special characters
    try:
        match = bool(re.search(re.escape(vendor_hint), text, re.IGNORECASE))
        if match:
            logger.debug(f"[Vendor Hint Check] ✓ Found '{vendor_hint}' in text (regex match)")
        else:
            logger.debug(f"[Vendor Hint Check] ✗ Did not find '{vendor_hint}' in text")
        return match
    except re.error:
        logger.debug(f"[Vendor Hint Check] ✗ Regex error for '{vendor_hint}'")
        return False


def parse_pdf_with_patterns(
    pdf_bytes: bytes,
    patterns: list[ExtractionPattern],
) -> ExtractionResult:
    text = extract_text_from_pdf(pdf_bytes)
    sorted_patterns = sorted(
        [p for p in patterns if p.enabled],
        key=lambda p: p.priority,
        reverse=True,
    )
    matched_pattern: Optional[ExtractionPattern] = None
    logger.debug(f"[PDF Parser] Checking {len(sorted_patterns)} patterns for vendor hints")
    logger.debug(f"[PDF Parser] Text preview (first 500 chars): {text[:500]}")
    for pattern in sorted_patterns:
        logger.debug(f"[PDF Parser] Checking pattern: {pattern.name} (vendor_hint: '{pattern.vendor_hint}', supplier: '{pattern.supplier}')")
        if check_vendor_hint(text, pattern.vendor_hint):
            matched_pattern = pattern
            logger.info(f"[PDF Parser] ✓ Matched pattern: {pattern.name} (supplier: {pattern.supplier})")
            break
        else:
            logger.debug(f"[PDF Parser] ✗ Pattern '{pattern.name}' did not match")
    if not matched_pattern:
        logger.warning(f"[PDF Parser] ✗ No pattern matched. Text preview (first 500 chars): {text[:500]}")
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
    )
    contract_id = extract_contract_id(
        text,
        matched_pattern.contract_id_pattern if matched_pattern else None,
    )
    due_date = extract_due_date(
        text,
        matched_pattern.due_date_pattern if matched_pattern else None,
    )
    business_name = extract_business_name(
        text,
        matched_pattern.business_name_pattern if matched_pattern else None,
    )
    
    # Validate bank accounts if pattern has them defined
    is_valid = True
    bank_accounts_list = []
    if matched_pattern and matched_pattern.bank_accounts:
        is_valid = validate_bank_accounts(text, matched_pattern.bank_accounts)
        if is_valid:
            bank_accounts_list = matched_pattern.bank_accounts
        # If validation fails, matched_pattern_id and matched_pattern_name will be set to None
    
    all_addresses = extract_addresses(
        text,
        matched_pattern.address_pattern if matched_pattern else None,
    )
    consumption_location = extract_consumption_location(text)
    address = consumption_location or (all_addresses[0] if all_addresses else None)
    return ExtractionResult(
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
    )
