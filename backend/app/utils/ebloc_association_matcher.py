"""Utility for matching e-bloc associations from login HTML"""
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


async def find_matching_associations(html: str, property_name: str) -> List[dict]:
    """Find matching associations by comparing address fields from gInfoAsoc with property name.
    
    Returns list of matches with id, apartment_index, apartment_id, and score.
    """
    try:
        # Parse gInfoAsoc to find matching associations
        gInfoAsoc_block_match = re.search(
            r'gInfoAsoc\s*\[\s*\d+\s*\]\s*=.*?(?=gInfoAp|gContAsoc|</script>|$)',
            html,
            re.DOTALL
        )
        
        if not gInfoAsoc_block_match:
            logger.warning("[E-Bloc] Could not find gInfoAsoc block")
            return []
        
        gInfoAsoc_block = gInfoAsoc_block_match.group(0)
        
        # Also parse gInfoAp to find apartment indices
        gInfoAp_block_match = re.search(
            r'gInfoAp\s*\[\s*\d+\s*\]\s*=.*?(?=gContAsoc|</script>|$)',
            html,
            re.DOTALL
        )
        
        # Build a map of association_id -> (apartment_index, apartment_id) from gInfoAp
        apartment_map = {}  # association_id -> {"apt_index": int, "id_ap": str}
        if gInfoAp_block_match:
            gInfoAp_block = gInfoAp_block_match.group(0)
            apt_indices = set(re.findall(r'gInfoAp\s*\[\s*(\d+)\s*\]', gInfoAp_block))
            
            for apt_index in sorted(apt_indices):
                kv_pattern = re.compile(
                    r'gInfoAp\s*\[\s*' + re.escape(apt_index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                    re.DOTALL
                )
                apt_data = {}
                for kv_match in kv_pattern.finditer(gInfoAp_block):
                    key = kv_match.group(1)
                    value = kv_match.group(2)
                    apt_data[key] = value
                
                apt_id_asoc = apt_data.get("id_asoc", "")
                apt_id_ap = apt_data.get("id_ap", "")
                if apt_id_asoc and apt_id_ap:
                    apartment_map[apt_id_asoc] = {
                        "apt_index": int(apt_index),
                        "id_ap": apt_id_ap
                    }
        
        # Find all association indices
        asoc_indices = set(re.findall(r'gInfoAsoc\s*\[\s*(\d+)\s*\]', gInfoAsoc_block))
        
        matches = []
        property_name_lower = property_name.lower()
        
        # Normalize property name - remove common prefixes and normalize
        normalized_prop = property_name_lower
        normalized_prop = re.sub(r'^(strada|str\.?|st\.?)\s+', '', normalized_prop, flags=re.I)
        normalized_prop = re.sub(r'\s+nr\.?\s*', ' ', normalized_prop, flags=re.I)
        normalized_prop = normalized_prop.strip()
        
        for asoc_index in sorted(asoc_indices):
            # Extract all assignments for this association
            kv_pattern = re.compile(
                r'gInfoAsoc\s*\[\s*' + re.escape(asoc_index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                re.DOTALL
            )
            asoc_data = {}
            for kv_match in kv_pattern.finditer(gInfoAsoc_block):
                key = kv_match.group(1)
                value = kv_match.group(2)
                asoc_data[key] = value
            
            if "id" not in asoc_data:
                continue
            
            asoc_id = asoc_data["id"]
            
            # Build address components for matching
            adr_strada = asoc_data.get("adr_strada", "").lower().strip()
            adr_nr = asoc_data.get("adr_nr", "").lower().strip()
            adr_bloc = asoc_data.get("adr_bloc", "").lower().strip()
            
            # Normalize street name
            normalized_street = re.sub(r'^(strada|str\.?|st\.?)\s+', '', adr_strada, flags=re.I).strip()
            
            # Check for matches using multiple criteria
            match_score = 0
            match_reasons = []
            
            # Word-by-word matching for better abbreviation handling
            prop_words = set(normalized_prop.split())
            street_words = set(normalized_street.split())
            
            # Remove common words that don't help matching
            common_words = {'nr', 'nr.', 'bloc', 'bl', 'sc', 'scara', 'ap', 'sector', 'str', 'str.', 'strada', 'st'}
            prop_words = {w for w in prop_words if w.lower() not in common_words and len(w) > 2}
            street_words = {w for w in street_words if w.lower() not in common_words and len(w) > 2}
            
            # Count matching words
            matching_words = 0
            for prop_word in prop_words:
                for street_word in street_words:
                    if prop_word.lower() == street_word.lower():
                        matching_words += 1
                        break
                    elif prop_word.lower() in street_word.lower() or street_word.lower() in prop_word.lower():
                        min_len = min(len(prop_word), len(street_word))
                        if min_len >= 3:
                            matching_words += 1
                            break
            
            if matching_words > 0:
                match_score += matching_words * 8
                match_reasons.append(f"words: {matching_words} matching")
            
            # Match street name
            if normalized_street and normalized_street in normalized_prop:
                match_score += 10
                match_reasons.append(f"street: '{adr_strada}'")
            
            if normalized_street and normalized_prop in normalized_street:
                match_score += 10
                match_reasons.append(f"street: '{adr_strada}'")
            
            # Match number
            if adr_nr and adr_nr in normalized_prop:
                match_score += 5
                match_reasons.append(f"number: '{adr_nr}'")
            
            # Match bloc
            asoc_name = asoc_data.get("nume", "").lower()
            if adr_bloc:
                if adr_bloc in normalized_prop:
                    match_score += 3
                    match_reasons.append(f"bloc: '{adr_bloc}'")
                elif adr_bloc in asoc_name:
                    match_score += 2
                    match_reasons.append(f"bloc in name: '{adr_bloc}'")
            
            # Match association name
            if property_name_lower in asoc_name or asoc_name in property_name_lower:
                match_score += 2
                match_reasons.append(f"name: '{asoc_data.get('nume', '')}'")
            
            # Only include matches with score > 5
            if match_score > 5:
                apt_info = apartment_map.get(asoc_id, {})
                apt_id_ap = apt_info.get("id_ap", "")
                apartment_index = int(asoc_index)
                
                matches.append({
                    "id": asoc_id,
                    "nume": asoc_data.get("nume", ""),
                    "adr_strada": adr_strada,
                    "adr_nr": adr_nr,
                    "adr_bloc": adr_bloc,
                    "score": match_score,
                    "reasons": match_reasons,
                    "apartment_index": apartment_index,
                    "apartment_id": apt_id_ap
                })
        
        # Sort by score (highest first)
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        if not matches:
            logger.warning(f"[E-Bloc] Could not match property name '{property_name}' with any association, returning all as fallback")
            for asoc_index in sorted(asoc_indices):
                kv_pattern = re.compile(
                    r'gInfoAsoc\s*\[\s*' + re.escape(asoc_index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                    re.DOTALL
                )
                asoc_data = {}
                for kv_match in kv_pattern.finditer(gInfoAsoc_block):
                    key = kv_match.group(1)
                    value = kv_match.group(2)
                    asoc_data[key] = value
                
                if "id" not in asoc_data:
                    continue
                
                asoc_id = asoc_data["id"]
                apt_info = apartment_map.get(asoc_id, {})
                apt_id_ap = apt_info.get("id_ap", "")
                
                matches.append({
                    "id": asoc_id,
                    "nume": asoc_data.get("nume", ""),
                    "adr_strada": asoc_data.get("adr_strada", ""),
                    "adr_nr": asoc_data.get("adr_nr", ""),
                    "adr_bloc": asoc_data.get("adr_bloc", ""),
                    "score": 0,
                    "reasons": ["fallback: no match found"],
                    "apartment_index": int(asoc_index),
                    "apartment_id": apt_id_ap
                })
        
        return matches
    except Exception as e:
        logger.error(f"[E-Bloc] Error finding matching associations: {e}", exc_info=True)
        return []

