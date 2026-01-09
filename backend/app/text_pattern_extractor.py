"""
Text pattern extraction using patterns from text_patterns folder.

This module provides extraction functionality for email bill processing,
using the JSON patterns from the text_patterns folder.

Uses shared utilities from app.utils.text_pattern_utils to ensure consistency
with pattern creation tool.
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple

from app.utils.text_pattern_utils import (
    TEXT_PATTERNS_DIR,
    extract_with_pattern,
    match_pattern_to_pdf,
)

logger = logging.getLogger(__name__)




def load_all_patterns() -> List[Dict[str, Any]]:
    """Load all patterns from text_patterns folder."""
    patterns = []
    if os.path.exists(TEXT_PATTERNS_DIR):
        for filename in os.listdir(TEXT_PATTERNS_DIR):
            if filename.endswith('.json'):
                try:
                    pattern_file = os.path.join(TEXT_PATTERNS_DIR, filename)
                    with open(pattern_file, 'r', encoding='utf-8') as f:
                        pattern = json.load(f)
                        filename_base = filename[:-5]  # Remove .json extension
                        patterns.append({
                            'pattern': pattern,
                            'pattern_id': filename_base
                        })
                except Exception as e:
                    logger.warning(f"[Text Pattern] Error loading pattern {filename}: {e}")
    return patterns


def match_text_patterns(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Match PDF against all text patterns and return matching patterns with scores.
    
    Returns:
        List of dicts with 'pattern', 'pattern_id', and 'matched_fields' count
    """
    patterns = load_all_patterns()
    logger.info(f"[Text Pattern] Checking {len(patterns)} patterns against PDF")
    
    matches = []
    for pattern_data in patterns:
        pattern = pattern_data['pattern']
        pattern_name = pattern.get('name', pattern_data['pattern_id'])
        field_patterns = pattern.get('field_patterns', [])
        
        # Use shared utility to count matches
        matched_count = match_pattern_to_pdf(pdf_bytes, pattern)
        
        logger.debug(f"[Text Pattern] Pattern '{pattern_name}': {matched_count}/{len(field_patterns)} fields matched")
        
        if matched_count > 0:
            match_percentage = (matched_count / len(field_patterns) * 100) if field_patterns else 0
            logger.info(f"[Text Pattern] Pattern '{pattern_name}' matched: {match_percentage:.1f}% ({matched_count}/{len(field_patterns)} fields)")
            matches.append({
                'pattern': pattern,
                'pattern_id': pattern_data['pattern_id'],
                'matched_fields': matched_count,
                'total_fields': len(field_patterns),
                'match_percentage': match_percentage
            })
    
    # Sort by match percentage
    matches.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    if not matches:
        logger.warning(f"[Text Pattern] No patterns matched the PDF (checked {len(patterns)} patterns)")
    
    return matches


def extract_with_text_pattern(pdf_bytes: bytes, pattern_id: str) -> Dict[str, Any]:
    """
    Extract bill data from PDF using a specific text pattern.
    
    Args:
        pdf_bytes: PDF file as bytes
        pattern_id: Pattern ID (filename without .json)
        
    Returns:
        Dictionary with extracted data
    """
    # Load pattern
    pattern_file = os.path.join(TEXT_PATTERNS_DIR, f"{pattern_id}.json")
    if not os.path.exists(pattern_file):
        raise FileNotFoundError(f"Pattern {pattern_id} not found")
    
    with open(pattern_file, 'r', encoding='utf-8') as f:
        pattern = json.load(f)
    
    # Use shared extraction utility
    extracted_data = extract_with_pattern(pdf_bytes, pattern)
    
    return extracted_data


def extract_bill_from_pdf_auto(pdf_bytes: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str], Optional[str]]:
    """
    Automatically extract bill data from PDF by finding best matching pattern.
    
    Args:
        pdf_bytes: PDF file as bytes
        
    Returns:
        Tuple of (extracted_data, pattern_id, pattern_name, pattern_bill_type) or (None, None, None, None) if no match
    """
    # Find matching patterns
    matches = match_text_patterns(pdf_bytes)
    
    if not matches:
        logger.warning("[Text Pattern] No matching patterns found for PDF")
        return None, None, None, None
    
    # Use best match
    best_match = matches[0]
    pattern_id = best_match['pattern_id']
    pattern_name = best_match['pattern'].get('name', pattern_id)
    pattern_bill_type = best_match['pattern'].get('bill_type', 'utilities')  # Default to utilities
    
    logger.info(f"[Text Pattern] Best match: {pattern_name} ({best_match['match_percentage']:.1f}% match, bill_type={pattern_bill_type})")
    
    # Extract data using best pattern
    try:
        extracted_data = extract_with_text_pattern(pdf_bytes, pattern_id)
        return extracted_data, pattern_id, pattern_name, pattern_bill_type
    except Exception as e:
        logger.error(f"[Text Pattern] Error extracting with pattern {pattern_id}: {e}")
        return None, None, None, None

