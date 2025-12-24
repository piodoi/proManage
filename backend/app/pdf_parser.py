import re
from typing import Optional
import fitz

from app.models import ExtractionPattern, ExtractionResult


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
    try:
        return bool(re.search(vendor_hint, text, re.IGNORECASE))
    except re.error:
        return vendor_hint.lower() in text.lower()


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
    for pattern in sorted_patterns:
        if check_vendor_hint(text, pattern.vendor_hint):
            matched_pattern = pattern
            break
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
    all_addresses = extract_addresses(
        text,
        matched_pattern.address_pattern if matched_pattern else None,
    )
    consumption_location = extract_consumption_location(text)
    address = consumption_location or (all_addresses[0] if all_addresses else None)
    return ExtractionResult(
        iban=iban,
        bill_number=bill_number,
        amount=amount,
        address=address,
        consumption_location=consumption_location,
        all_addresses=all_addresses,
        matched_pattern_id=matched_pattern.id if matched_pattern else None,
        matched_pattern_name=matched_pattern.name if matched_pattern else None,
        raw_text=text,
    )
