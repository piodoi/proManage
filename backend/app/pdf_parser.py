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


def apply_pattern(text: str, pattern: Optional[str]) -> Optional[str]:
    if not pattern:
        return None
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            result = match.group(1) if match.groups() else match.group(0)
            # Clean up the result
            if result:
                result = result.strip()
                # For bill numbers, filter out very short results that are likely false matches
                if len(result) < 3:
                    return None
            return result
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
            # Clean up the result - remove leading/trailing whitespace and ensure it's meaningful
            cleaned = result.strip()
            # Filter out very short results that are likely false matches (like "re", "nr", etc.)
            if len(cleaned) >= 3:  # At least 3 characters for a valid bill number
                return cleaned
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
        if new_accounts:
            print(f"[Bank Sync] Found {len(new_accounts)} new IBANs in PDF (no existing pattern)", flush=True)
            logger.info(f"[Bank Sync] Found {len(new_accounts)} new IBANs in PDF")
        return (True, new_accounts)
    
    # Normalize IBANs for comparison (remove spaces)
    text_ibans = set()
    iban_matches = re.findall(r'RO\d{2}\s*[A-Z0-9]{4,30}', text, re.IGNORECASE)
    for iban in iban_matches:
        normalized = re.sub(r'\s+', '', iban.upper())
        text_ibans.add(normalized)
    
    print(f"[Bank Sync] Found {len(text_ibans)} IBANs in PDF", flush=True)
    logger.info(f"[Bank Sync] Found {len(text_ibans)} IBANs in PDF")
    
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
                removed_accounts.append(f"{account.get('bank', 'Unknown')}: {normalized}")
    
    # Add new IBANs from PDF that aren't in the pattern
    new_accounts = []
    for iban in text_ibans:
        if iban not in iban_to_account:
            # Try to extract bank name from context around the IBAN
            bank_name = "Unknown"
            # Look for bank name before the IBAN (common pattern: "Bank Name\nIBAN")
            iban_pos = text.upper().find(iban)
            if iban_pos > 0:
                # Look backwards for bank name (common Romanian banks)
                context_before = text[max(0, iban_pos-100):iban_pos].upper()
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
                    # Also check if bank name appears in context
                    if name.upper().replace(' ', '') in context_before or name.upper() in context_before:
                        bank_name = name
                        break
            
            new_accounts.append({"bank": bank_name, "iban": iban})
    
    # Combine kept and new accounts
    final_accounts = updated_accounts + new_accounts
    
    if removed_accounts:
        print(f"[Bank Sync] Removed {len(removed_accounts)} IBANs not found in PDF: {removed_accounts[:3]}...", flush=True)
        logger.info(f"[Bank Sync] Removed {len(removed_accounts)} IBANs not found in PDF")
    
    if new_accounts:
        print(f"[Bank Sync] Added {len(new_accounts)} new IBANs from PDF", flush=True)
        logger.info(f"[Bank Sync] Added {len(new_accounts)} new IBANs from PDF")
    
    if not removed_accounts and not new_accounts:
        print(f"[Bank Sync] ✓ All {len(expected_bank_accounts)} IBANs match, no changes needed", flush=True)
        logger.info(f"[Bank Sync] ✓ All {len(expected_bank_accounts)} IBANs match, no changes needed")
    
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
    
    # Log for debugging (using print and logger)
    print(f"[Vendor Hint Check] Looking for '{vendor_hint}' in text (first 200 chars: {text[:200]})", flush=True)
    logger.info(f"[Vendor Hint Check] Looking for '{vendor_hint}' in text (first 200 chars: {text[:200]})")
    
    # First try simple substring match (most common case)
    if vendor_hint_lower in text_lower:
        print(f"[Vendor Hint Check] ✓ Found '{vendor_hint}' in text (substring match)", flush=True)
        logger.info(f"[Vendor Hint Check] ✓ Found '{vendor_hint}' in text (substring match)")
        return True
    
    # Fallback to regex if vendor_hint contains special characters
    try:
        match = bool(re.search(re.escape(vendor_hint), text, re.IGNORECASE))
        if match:
            print(f"[Vendor Hint Check] ✓ Found '{vendor_hint}' in text (regex match)", flush=True)
            logger.info(f"[Vendor Hint Check] ✓ Found '{vendor_hint}' in text (regex match)")
        else:
            print(f"[Vendor Hint Check] ✗ Did not find '{vendor_hint}' in text", flush=True)
            logger.info(f"[Vendor Hint Check] ✗ Did not find '{vendor_hint}' in text")
        return match
    except re.error:
        print(f"[Vendor Hint Check] ✗ Regex error for '{vendor_hint}'", flush=True)
        logger.info(f"[Vendor Hint Check] ✗ Regex error for '{vendor_hint}'")
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
    print(f"[PDF Parser] Checking {len(sorted_patterns)} patterns for vendor hints", flush=True)
    logger.info(f"[PDF Parser] Checking {len(sorted_patterns)} patterns for vendor hints")
    print(f"[PDF Parser] Text preview (first 500 chars): {text[:500]}", flush=True)
    logger.info(f"[PDF Parser] Text preview (first 500 chars): {text[:500]}")
    for pattern in sorted_patterns:
        print(f"[PDF Parser] Checking pattern: {pattern.name} (vendor_hint: '{pattern.vendor_hint}', supplier: '{pattern.supplier}')", flush=True)
        logger.info(f"[PDF Parser] Checking pattern: {pattern.name} (vendor_hint: '{pattern.vendor_hint}', supplier: '{pattern.supplier}')")
        if check_vendor_hint(text, pattern.vendor_hint):
            matched_pattern = pattern
            print(f"[PDF Parser] ✓ Matched pattern: {pattern.name} (supplier: {pattern.supplier})", flush=True)
            logger.info(f"[PDF Parser] ✓ Matched pattern: {pattern.name} (supplier: {pattern.supplier})")
            break
        else:
            print(f"[PDF Parser] ✗ Pattern '{pattern.name}' did not match", flush=True)
            logger.info(f"[PDF Parser] ✗ Pattern '{pattern.name}' did not match")
    if not matched_pattern:
        print(f"[PDF Parser] ✗ No pattern matched. Text preview (first 500 chars): {text[:500]}", flush=True)
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
    
    # Sync bank accounts if pattern has them defined
    is_valid = True
    bank_accounts_list = []
    pattern_needs_update = False
    if matched_pattern and matched_pattern.bank_accounts:
        print(f"[PDF Parser] Syncing bank accounts for pattern '{matched_pattern.name}'", flush=True)
        logger.info(f"[PDF Parser] Syncing bank accounts for pattern '{matched_pattern.name}'")
        is_valid, bank_accounts_list = sync_bank_accounts(text, matched_pattern.bank_accounts)
        print(f"[PDF Parser] Bank sync result: {is_valid}, {len(bank_accounts_list)} accounts", flush=True)
        logger.info(f"[PDF Parser] Bank sync result: {is_valid}, {len(bank_accounts_list)} accounts")
        
        # Check if bank_accounts_list differs from pattern's bank_accounts
        if bank_accounts_list != matched_pattern.bank_accounts:
            pattern_needs_update = True
            print(f"[PDF Parser] Pattern bank accounts need update (was {len(matched_pattern.bank_accounts)}, now {len(bank_accounts_list)})", flush=True)
            logger.info(f"[PDF Parser] Pattern bank accounts need update")
    elif matched_pattern:
        # No bank accounts in pattern, but we found some in PDF - add them
        is_valid, bank_accounts_list = sync_bank_accounts(text, [])
        if bank_accounts_list:
            pattern_needs_update = True
            print(f"[PDF Parser] Adding {len(bank_accounts_list)} new bank accounts to pattern", flush=True)
            logger.info(f"[PDF Parser] Adding {len(bank_accounts_list)} new bank accounts to pattern")
    
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
