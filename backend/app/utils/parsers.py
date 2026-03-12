"""
Common parsing utilities used across the codebase.
Ensures consistency in how amounts, dates, and other fields are parsed.
"""
import re
from typing import Optional
from datetime import datetime


def parse_amount(text: str) -> Optional[float]:
    """
    Parse amount from text. 
    
    Standard logic:
    1. Remove all commas, dots, and spaces
    2. Keep only numbers
    3. Treat as bani (cents) and divide by 100 to get lei
    
    Examples:
        "12345" -> 123.45
        "123.45" -> 123.45
        "123,45" -> 123.45
        "1.234,56" -> 1234.56 (treated as 123456 bani = 1234.56 lei)
        "1 234,56" -> 1234.56
    
    Args:
        text: String containing amount
        
    Returns:
        Float amount in lei, or None if parsing fails
    """
    if not text:
        return None
    
    try:
        raw_text = str(text).strip()
        # Preserve negative values (e.g. "-123,45", "123,45-", "(123,45)")
        is_negative = bool(
            re.search(r'[-−]\s*\d', raw_text)
            or re.search(r'\d\s*[-−]', raw_text)
            or re.search(r'\(\s*[\d.,\s]+\)', raw_text)
        )

        # Strip all commas, dots, and spaces - assume value is in bani
        cleaned = raw_text.replace(',', '').replace('.', '').replace(' ', '')
        # Remove any non-digit characters
        cleaned = re.sub(r'[^\d]', '', cleaned)
        if not cleaned:
            return None
        # Convert to int (bani) then divide by 100 to get lei
        amount_bani = int(cleaned)
        amount = amount_bani / 100.0
        return -amount if is_negative and amount > 0 else amount
    except (ValueError, AttributeError):
        return None


def coerce_amount(value) -> float:
    """
    Coerce a raw amount value (int, float, or formatted string) to float.
    Preserves negative sign for credit/refund amounts.

    Raises ValueError if the value cannot be parsed.
    """
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        return float(text)
    except (ValueError, TypeError):
        result = parse_amount(text)
        if result is None:
            raise ValueError(f"Cannot parse amount: {value!r}")
        return result

