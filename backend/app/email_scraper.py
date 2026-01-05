import re
from typing import Optional
from dataclasses import dataclass

from app.utils.parsers import parse_amount as parse_amount_utility


@dataclass
class ExtractedBillInfo:
    iban: Optional[str] = None
    bill_number: Optional[str] = None
    amount: Optional[float] = None
    address: Optional[str] = None
    consumption_location: Optional[str] = None
    all_addresses: list[str] = None

    def __post_init__(self):
        if self.all_addresses is None:
            self.all_addresses = []


IBAN_PATTERN = re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b')
BILL_NUMBER_PATTERNS = [
    re.compile(r'(?:factura|invoice|bill)\s*(?:nr\.?|no\.?|#)?\s*[:.]?\s*(\w+[-/]?\w*)', re.I),
    re.compile(r'(?:nr\.?|no\.?)\s*(?:factura|invoice|bill)\s*[:.]?\s*(\w+[-/]?\w*)', re.I),
    re.compile(r'(?:reference|ref)\s*[:.]?\s*(\w+[-/]?\w*)', re.I),
]
AMOUNT_PATTERNS = [
    re.compile(r'(?:total|suma|amount|de plata)\s*[:.]?\s*(\d+[.,]?\d*)\s*(?:lei|ron|eur)?', re.I),
    re.compile(r'(\d+[.,]\d{2})\s*(?:lei|ron|eur)', re.I),
]
CONSUMPTION_LOCATION_PATTERNS = [
    re.compile(r'(?:loc\.?\s*consum|loc\.?\s*de\s*consum|locul\s*de\s*consum)\s*[:.]?\s*([^\n]+)', re.I),
    re.compile(r'(?:punct\s*consum|punct\s*de\s*consum)\s*[:.]?\s*([^\n]+)', re.I),
    re.compile(r'(?:adresa\s*consum|adresa\s*de\s*consum)\s*[:.]?\s*([^\n]+)', re.I),
]
ADDRESS_PATTERNS = [
    re.compile(r'(?:str\.?|strada)\s+([^,\n]+(?:,\s*(?:nr\.?|no\.?)\s*\d+)?)', re.I),
    re.compile(r'(?:adresa|address)\s*[:.]?\s*([^\n]+)', re.I),
]


def extract_iban(text: str) -> Optional[str]:
    match = IBAN_PATTERN.search(text.upper())
    return match.group(0) if match else None


def extract_bill_number(text: str) -> Optional[str]:
    for pattern in BILL_NUMBER_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def extract_amount(text: str) -> Optional[float]:
    """Extract amount from text using standard utility."""
    for pattern in AMOUNT_PATTERNS:
        match = pattern.search(text)
        if match:
            parsed = parse_amount_utility(match.group(1))
            if parsed is not None:
                return parsed
    return None


def extract_address(text: str) -> Optional[str]:
    for pattern in ADDRESS_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def extract_consumption_location(text: str) -> Optional[str]:
    for pattern in CONSUMPTION_LOCATION_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def extract_all_addresses(text: str) -> list[str]:
    addresses = []
    for pattern in CONSUMPTION_LOCATION_PATTERNS + ADDRESS_PATTERNS:
        for match in pattern.finditer(text):
            addr = match.group(1).strip()
            if addr and addr not in addresses:
                addresses.append(addr)
    return addresses


def extract_bill_info(email_body: str, email_subject: str = "") -> ExtractedBillInfo:
    combined_text = f"{email_subject}\n{email_body}"
    consumption_loc = extract_consumption_location(combined_text)
    all_addrs = extract_all_addresses(combined_text)
    return ExtractedBillInfo(
        iban=extract_iban(combined_text),
        bill_number=extract_bill_number(combined_text),
        amount=extract_amount(combined_text),
        address=extract_address(combined_text),
        consumption_location=consumption_loc,
        all_addresses=all_addrs,
    )


def match_address_to_property(extracted_address: Optional[str], properties: list) -> Optional[str]:
    if not extracted_address:
        return None
    extracted_lower = extracted_address.lower()
    for prop in properties:
        if prop.address.lower() in extracted_lower or extracted_lower in prop.address.lower():
            return prop.id
    return None
