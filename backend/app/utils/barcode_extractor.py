"""
Barcode extraction from PDF files using pyzbar and pymupdf.

This module extracts barcodes from PDF files by:
1. Converting PDF pages to images using pymupdf
2. Detecting barcodes in images using pyzbar
"""
import io
import logging
from typing import List, Optional, Dict, Any

import fitz  # pymupdf

logger = logging.getLogger(__name__)

# Try to import pyzbar - it requires zbar library to be installed
try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    logger.warning("pyzbar not available - barcode extraction will be disabled")

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow not available - barcode extraction will be disabled")


def extract_barcodes_from_pdf(pdf_bytes: bytes, max_pages: int = 3) -> List[Dict[str, Any]]:
    """
    Extract barcodes from a PDF file.
    
    Args:
        pdf_bytes: PDF file as bytes
        max_pages: Maximum number of pages to scan (default: 3)
        
    Returns:
        List of dicts with barcode info:
        - data: The barcode data (string)
        - type: The barcode type (e.g., 'CODE128', 'EAN13', 'QR')
        - page: Page number where found (1-indexed)
        - rect: Bounding rectangle (x, y, width, height)
    """
    if not PYZBAR_AVAILABLE or not PILLOW_AVAILABLE:
        logger.warning("Barcode extraction not available - missing dependencies")
        return []
    
    barcodes = []
    
    try:
        # Open PDF with pymupdf
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Process each page (up to max_pages)
        pages_to_scan = min(len(doc), max_pages)
        
        for page_num in range(pages_to_scan):
            page = doc[page_num]
            
            # Convert page to image with higher resolution for better barcode detection
            # Using a zoom factor of 2.0 (144 DPI instead of default 72 DPI)
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Detect barcodes using pyzbar
            # Try to detect all barcode types
            detected = pyzbar.decode(img)
            
            for barcode in detected:
                barcode_data = barcode.data.decode('utf-8', errors='ignore')
                barcode_type = barcode.type
                rect = barcode.rect
                
                # Skip empty barcodes
                if not barcode_data.strip():
                    continue
                
                barcodes.append({
                    'data': barcode_data,
                    'type': barcode_type,
                    'page': page_num + 1,
                    'rect': {
                        'x': rect.left,
                        'y': rect.top,
                        'width': rect.width,
                        'height': rect.height
                    }
                })
                
                logger.info(f"Found barcode on page {page_num + 1}: {barcode_type} - {barcode_data[:50]}...")
        
        doc.close()
        
    except Exception as e:
        logger.error(f"Error extracting barcodes from PDF: {e}")
    
    # Remove duplicates (same barcode might be detected multiple times)
    seen = set()
    unique_barcodes = []
    for bc in barcodes:
        key = (bc['data'], bc['type'])
        if key not in seen:
            seen.add(key)
            unique_barcodes.append(bc)
    
    logger.info(f"Extracted {len(unique_barcodes)} unique barcodes from PDF")
    return unique_barcodes


def get_primary_barcode(pdf_bytes: bytes) -> Optional[str]:
    """
    Get the primary barcode from a PDF file.
    
    This function extracts barcodes and returns the most likely "payment" barcode,
    prioritizing longer numeric/alphanumeric codes that are typically used for
    utility bill payments.
    
    Args:
        pdf_bytes: PDF file as bytes
        
    Returns:
        The barcode data string, or None if no suitable barcode found
    """
    barcodes = extract_barcodes_from_pdf(pdf_bytes)
    
    if not barcodes:
        return None
    
    # Score barcodes to find the best one for payment
    def score_barcode(bc: Dict[str, Any]) -> int:
        data = bc['data']
        bc_type = bc['type']
        score = 0
        
        # Prefer longer barcodes (utility payment codes are usually 15-30 chars)
        if 15 <= len(data) <= 40:
            score += 50
        elif 10 <= len(data) <= 50:
            score += 30
        elif len(data) > 50:
            score += 10
        
        # Prefer numeric or alphanumeric codes
        if data.isdigit():
            score += 30
        elif data.isalnum():
            score += 20
        
        # Prefer certain barcode types commonly used for payments
        payment_types = ['CODE128', 'CODE39', 'EAN13', 'EAN8', 'ITF', 'CODABAR']
        if bc_type in payment_types:
            score += 20
        
        # QR codes might contain URLs or other data, lower priority
        if bc_type == 'QRCODE':
            score -= 10
        
        # Prefer barcodes found on first page
        if bc['page'] == 1:
            score += 10
        
        return score
    
    # Sort by score (highest first)
    sorted_barcodes = sorted(barcodes, key=score_barcode, reverse=True)
    
    if sorted_barcodes:
        best = sorted_barcodes[0]
        logger.info(f"Selected primary barcode: {best['type']} - {best['data'][:50]}...")
        return best['data']
    
    return None


def is_barcode_extraction_available() -> bool:
    """Check if barcode extraction is available (dependencies installed)."""
    return PYZBAR_AVAILABLE and PILLOW_AVAILABLE
