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
        # Strip all commas, dots, and spaces - assume value is in bani
        cleaned = str(text).replace(',', '').replace('.', '').replace(' ', '').strip()
        # Remove any non-digit characters
        cleaned = re.sub(r'[^\d]', '', cleaned)
        if not cleaned:
            return None
        # Convert to int (bani) then divide by 100 to get lei
        amount_bani = int(cleaned)
        return amount_bani / 100.0
    except (ValueError, AttributeError):
        return None

