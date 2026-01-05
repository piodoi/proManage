"""
Utility for matching addresses between extracted bills and properties.
Reuses the logic from bills_routes.py to ensure consistency.
"""
import re
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


def normalize_address(addr: str) -> str:
    """Normalize address for comparison (remove common words, normalize whitespace)."""
    # Remove common words
    addr = re.sub(r'\b(nr\.?|număr|numar|bloc|bl\.?|scara|sc\.?|ap\.?|apartament|sector|sect\.?)\b', '', addr, flags=re.IGNORECASE)
    # Normalize whitespace
    addr = re.sub(r'\s+', ' ', addr).strip()
    return addr


def extract_all_tokens(addr: str) -> set:
    """Extract all words and numbers from address."""
    tokens = set()
    # Get all words (including short ones)
    words = re.findall(r'\b[a-zăâîșț]+\b', addr, re.IGNORECASE)
    tokens.update(w.lower() for w in words if w)
    # Get all numbers
    numbers = re.findall(r'\d+', addr)
    tokens.update(numbers)
    return tokens


def extract_key_components(addr: str) -> Dict[str, str]:
    """Extract key address components (street, number, block, etc.)."""
    components = {}
    # Street name (first significant word, usually after common prefixes)
    street_match = re.search(r'\b(strada|str|aleea|alee|bd|bulevardul|calea)\s+([a-zăâîșț]+)', addr, re.IGNORECASE)
    if street_match:
        components['street'] = street_match.group(2).lower()
    # Number
    nr_match = re.search(r'(?:nr|număr|numar)[\s\.:]*(\d+)', addr, re.IGNORECASE)
    if nr_match:
        components['number'] = nr_match.group(1)
    # Block/Building
    bl_match = re.search(r'\b(bl|bloc)[\s\.:]*([a-z0-9/]+)', addr, re.IGNORECASE)
    if bl_match:
        components['block'] = re.sub(r'[^a-z0-9]', '', bl_match.group(2).lower())
    # Staircase/Scara
    sc_match = re.search(r'\b(sc|scara|scara)[\s\.:]*([a-z0-9/]+)', addr, re.IGNORECASE)
    if sc_match:
        components['staircase'] = re.sub(r'[^a-z0-9]', '', sc_match.group(2).lower())
    # Apartment
    ap_match = re.search(r'\b(ap|apartament)[\s\.:]*(\d+)', addr, re.IGNORECASE)
    if ap_match:
        components['apartment'] = ap_match.group(2)
    return components


def calculate_address_confidence(extracted_address: str, property_address: str) -> Tuple[int, Dict[str, any]]:
    """
    Calculate confidence score for address matching.
    
    Args:
        extracted_address: Address extracted from bill
        property_address: Property address to match against
        
    Returns:
        Tuple of (confidence_score, debug_info)
        confidence_score: 0-100 integer
        debug_info: Dict with matching details for logging
    """
    if not extracted_address or not property_address:
        return 100, {}  # Default to 100% if no address to compare
    
    extracted_lower = extracted_address.lower()
    property_lower = property_address.lower()
    
    normalized_extracted = normalize_address(extracted_lower)
    normalized_property = normalize_address(property_lower)
    
    extracted_tokens = extract_all_tokens(normalized_extracted)
    property_tokens = extract_all_tokens(normalized_property)
    common_tokens = extracted_tokens & property_tokens
    
    extracted_components = extract_key_components(extracted_lower)
    property_components = extract_key_components(property_lower)
    
    # Count matching components
    matching_components = 0
    total_components = 0
    for key in ['street', 'number', 'block', 'staircase', 'apartment']:
        if key in extracted_components or key in property_components:
            total_components += 1
            if key in extracted_components and key in property_components:
                if extracted_components[key] == property_components[key]:
                    matching_components += 1
    
    # Calculate confidence based on both token overlap and component matching
    if not extracted_tokens or not property_tokens:
        # If no tokens, check exact match
        if normalized_extracted == normalized_property:
            confidence = 100
        else:
            confidence = 0
    else:
        # Improved token scoring: give more weight to multiple matching tokens
        num_common = len(common_tokens)
        num_extracted = len(extracted_tokens)
        num_property = len(property_tokens)
        
        # Base token score using Jaccard similarity, but with progressive bonus
        total_tokens = len(extracted_tokens | property_tokens)
        if total_tokens > 0:
            base_ratio = len(common_tokens) / total_tokens
            # Progressive bonus: more common tokens = exponentially better
            # 1 token: ~10-15%, 2 tokens: ~25-35%, 3 tokens: ~45-55%, 4+ tokens: 65%+
            token_multiplier = 1.0 + (num_common * 0.3)  # Bonus increases with matches
            token_score = min(50, base_ratio * 50 * token_multiplier)
        else:
            token_score = 0
        
        # Component matching score (50% weight instead of 60%)
        component_score = 0
        if total_components > 0:
            component_score = (matching_components / total_components) * 50
        else:
            # If no components found, use token score with higher weight
            component_score = token_score * 1.2
        
        # Bonus for substring match
        substring_bonus = 0
        if normalized_extracted in normalized_property or normalized_property in normalized_extracted:
            substring_bonus = 10
        
        confidence = min(100, int(token_score + component_score + substring_bonus))
    
    debug_info = {
        'extracted_address': extracted_address,
        'property_address': property_address,
        'common_tokens': common_tokens,
        'extracted_components': extracted_components,
        'property_components': property_components,
        'matching_components': matching_components,
        'total_components': total_components,
        'confidence': confidence
    }
    
    return confidence, debug_info

