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
    extract_with_pattern,
    match_pattern_to_pdf,
)
from app.paths import TEXT_PATTERNS_DIR, get_user_data_dir

logger = logging.getLogger(__name__)




def load_all_patterns(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load all patterns from admin text_patterns folder and optionally user folder.
    
    Args:
        user_id: If provided, also load patterns from user's text_patterns folder
        
    Returns:
        List of pattern dicts with 'pattern', 'pattern_id', and 'source' (admin/user)
    """
    patterns = []
    
    # Load admin patterns first (higher priority)
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
                            'pattern_id': filename_base,
                            'source': 'admin'
                        })
                except Exception as e:
                    logger.warning(f"[Text Pattern] Error loading admin pattern {filename}: {e}")
    
    # Load user patterns if user_id provided
    if user_id:
        user_patterns_dir = get_user_data_dir(user_id) / "text_patterns"
        if os.path.exists(user_patterns_dir):
            for filename in os.listdir(user_patterns_dir):
                if filename.endswith('.json'):
                    try:
                        pattern_file = os.path.join(user_patterns_dir, filename)
                        with open(pattern_file, 'r', encoding='utf-8') as f:
                            pattern = json.load(f)
                            filename_base = filename[:-5]  # Remove .json extension
                            # Use user_ prefix to distinguish from admin patterns
                            patterns.append({
                                'pattern': pattern,
                                'pattern_id': f"user_{filename_base}",
                                'source': 'user',
                                'user_id': user_id
                            })
                    except Exception as e:
                        logger.warning(f"[Text Pattern] Error loading user pattern {filename}: {e}")
    
    admin_count = len([p for p in patterns if p['source'] == 'admin'])
    user_count = len([p for p in patterns if p['source'] == 'user'])
    logger.info(f"[Text Pattern] Loaded {admin_count} admin patterns, {user_count} user patterns")
    
    return patterns


def match_text_patterns(pdf_bytes: bytes, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Match PDF against all text patterns and return matching patterns with scores.
    
    Args:
        pdf_bytes: PDF file as bytes
        user_id: If provided, also check patterns from user's folder
    
    Returns:
        List of dicts with 'pattern', 'pattern_id', 'matched_fields' count, and 'source'
    """
    patterns = load_all_patterns(user_id)
    logger.info(f"[Text Pattern] Checking {len(patterns)} patterns against PDF")
    
    matches = []
    for pattern_data in patterns:
        pattern = pattern_data['pattern']
        pattern_name = pattern.get('name', pattern_data['pattern_id'])
        field_patterns = pattern.get('field_patterns', [])
        source = pattern_data.get('source', 'admin')
        
        # Use shared utility to count matches
        matched_count = match_pattern_to_pdf(pdf_bytes, pattern)
        
        logger.debug(f"[Text Pattern] Pattern '{pattern_name}' ({source}): {matched_count}/{len(field_patterns)} fields matched")
        
        if matched_count > 0:
            match_percentage = (matched_count / len(field_patterns) * 100) if field_patterns else 0
            logger.info(f"[Text Pattern] Pattern '{pattern_name}' ({source}) matched: {match_percentage:.1f}% ({matched_count}/{len(field_patterns)} fields)")
            matches.append({
                'pattern': pattern,
                'pattern_id': pattern_data['pattern_id'],
                'matched_fields': matched_count,
                'total_fields': len(field_patterns),
                'match_percentage': match_percentage,
                'source': source
            })
    
    # Sort by match percentage (descending), then by source (admin first)
    # This ensures admin patterns take priority when match percentages are equal
    matches.sort(key=lambda x: (x['match_percentage'], 0 if x['source'] == 'admin' else 1), reverse=True)
    
    if not matches:
        logger.warning(f"[Text Pattern] No patterns matched the PDF (checked {len(patterns)} patterns)")
    
    return matches


def extract_with_text_pattern(pdf_bytes: bytes, pattern_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract bill data from PDF using a specific text pattern.
    
    Args:
        pdf_bytes: PDF file as bytes
        pattern_id: Pattern ID (filename without .json, or user_filename for user patterns)
        user_id: If provided and pattern_id starts with 'user_', load from user folder
        
    Returns:
        Dictionary with extracted data
    """
    # Check if this is a user pattern
    if pattern_id.startswith('user_') and user_id:
        actual_pattern_id = pattern_id[5:]  # Remove 'user_' prefix
        user_patterns_dir = get_user_data_dir(user_id) / "text_patterns"
        pattern_file = os.path.join(user_patterns_dir, f"{actual_pattern_id}.json")
    else:
        pattern_file = os.path.join(TEXT_PATTERNS_DIR, f"{pattern_id}.json")
    
    if not os.path.exists(pattern_file):
        raise FileNotFoundError(f"Pattern {pattern_id} not found at {pattern_file}")
    
    with open(pattern_file, 'r', encoding='utf-8') as f:
        pattern = json.load(f)
    
    # Use shared extraction utility
    extracted_data = extract_with_pattern(pdf_bytes, pattern)
    
    return extracted_data


def extract_bill_from_pdf_auto(pdf_bytes: bytes, user_id: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str], Optional[str]]:
    """
    Automatically extract bill data from PDF by finding best matching pattern.
    
    Args:
        pdf_bytes: PDF file as bytes
        user_id: If provided, also check patterns from user's folder
        
    Returns:
        Tuple of (extracted_data, pattern_id, pattern_name, pattern_bill_type) or (None, None, None, None) if no match
    """
    # Find matching patterns (includes both admin and user patterns)
    matches = match_text_patterns(pdf_bytes, user_id)
    
    if not matches:
        logger.warning("[Text Pattern] No matching patterns found for PDF")
        return None, None, None, None
    
    # Use best match (admin patterns have priority when match percentages are equal)
    best_match = matches[0]
    pattern_id = best_match['pattern_id']
    pattern_name = best_match['pattern'].get('name', pattern_id)
    pattern_bill_type = best_match['pattern'].get('bill_type', 'utilities')  # Default to utilities
    source = best_match.get('source', 'admin')
    
    logger.info(f"[Text Pattern] Best match: {pattern_name} ({best_match['match_percentage']:.1f}% match, bill_type={pattern_bill_type}, source={source})")
    
    # Extract data using best pattern
    try:
        extracted_data = extract_with_text_pattern(pdf_bytes, pattern_id, user_id)
        return extracted_data, pattern_id, pattern_name, pattern_bill_type
    except Exception as e:
        logger.error(f"[Text Pattern] Error extracting with pattern {pattern_id}: {e}")
        return None, None, None, None
