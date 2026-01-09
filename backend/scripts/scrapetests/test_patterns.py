#!/usr/bin/env python3
"""Test PDF extraction patterns for all JSON files in extraction_patterns (except suppliers.json).
Run with: python backend/test_patterns.py
"""

import sys
import json
from pathlib import Path

# Add current directory to path  
sys.path.insert(0, str(Path(__file__).parent))

from app.pdf_parser import parse_pdf_with_patterns, extract_text_from_pdf
from app.models import ExtractionPattern


def load_pattern_from_json(json_path: str) -> ExtractionPattern:
    """Load an extraction pattern from a JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Generate a temporary ID for testing
    return ExtractionPattern(
        id="test-pattern",
        supplier=data["supplier"],
        name=data["name"],
        bill_type=data["bill_type"],
        vendor_hint=data.get("vendor_hint"),
        iban_pattern=data.get("iban_pattern"),
        amount_pattern=data.get("amount_pattern"),
        address_pattern=data.get("address_pattern"),
        bill_number_pattern=data.get("bill_number_pattern"),
        business_name_pattern=data.get("business_name_pattern"),
        contract_id_pattern=data.get("contract_id_pattern"),
        due_date_pattern=data.get("due_date_pattern"),
        bank_accounts=data.get("bank_accounts", []),
        priority=data.get("priority", 100),
        enabled=data.get("enabled", True),
    )


def test_pdf(pdf_path: str, pattern_path: str, supplier_name: str, json_name: str):
    """Test PDF extraction with a pattern."""
    print(f"\n{'='*80}")
    print(f"Testing {supplier_name}")
    print(f"PDF: {pdf_path}")
    print(f"Pattern: {pattern_path}")
    print(f"{'='*80}\n")
    
    if not Path(pdf_path).exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        return None
    
    if not Path(pattern_path).exists():
        print(f"ERROR: Pattern file not found: {pattern_path}")
        return None
    
    try:
        # Load pattern
        pattern = load_pattern_from_json(pattern_path)
        
        # Read PDF
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # Extract text first to show it
        text = extract_text_from_pdf(pdf_bytes)
        
        # Save extracted text for debugging
        txt_output_path = Path(__file__).parent / f"{json_name}_pdf2txt.txt"
        with open(txt_output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Saved extracted text to: {txt_output_path}")
        
        print()
        # Parse with pattern
        result, pattern_to_update = parse_pdf_with_patterns(pdf_bytes, [pattern])
        
        # Print results (use ASCII-safe characters for Windows console)
        print("EXTRACTION RESULTS:")
        print("-" * 80)
        print(f"[OK] Supplier: {result.matched_pattern_supplier}")
        print(f"[OK] Pattern: {result.matched_pattern_name}")
        print(f"[OK] IBAN: {result.iban}")
        print(f"[OK] Amount: {result.amount}")
        print(f"[OK] Due Date: {result.due_date}")
        print(f"[OK] Bill Number: {result.bill_number}")
        print(f"[OK] Contract ID: {result.contract_id}")
        if result.client_code:
            print(f"[OK] Client Code: {result.client_code}")
        print(f"[OK] Business Name: {result.business_name}")
        print(f"[OK] Address: {result.address}")
        print(f"[OK] Bank Accounts: {len(result.bank_accounts)} found")
        for acc in result.bank_accounts:
            print(f"    - {acc.get('bank', 'Unknown')}: {acc.get('iban', '')}")
        
        print()
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    patterns_dir = Path(__file__).parent / "extraction_patterns"
    downloads_dir = Path.home() / "Downloads"
    
    # Find all JSON files except suppliers.json
    json_files = [f for f in patterns_dir.glob("*.json") if f.name != "suppliers.json"]
    
    print("\n" + "="*80)
    print("PATTERN-BASED EXTRACTION TEST")
    print("="*80)
    
    results = {}
    
    # Test each JSON pattern
    for json_file in sorted(json_files):
        json_name = json_file.stem  # e.g., "engie" from "engie.json"
        supplier_name = json_name.capitalize()
        
        # Look for PDF with same name in Downloads
        pdf_candidates = [
            downloads_dir / f"{json_name}.pdf",
            downloads_dir / f"{json_name.upper()}.pdf",
            downloads_dir / f"{supplier_name}.pdf",
        ]
        
        # Also try to find any PDF that contains the JSON name
        pdf_found = None
        for candidate in pdf_candidates:
            if candidate.exists():
                pdf_found = candidate
                break
        
        if not pdf_found:
            # Try to find any PDF with the name in it
            for pdf_file in downloads_dir.glob(f"*{json_name}*.pdf"):
                pdf_found = pdf_file
                break
        
        if not pdf_found:
            print(f"\nSkipping {supplier_name}: PDF not found (looked for {json_name}.pdf in Downloads)")
            continue
        
        pattern_path = str(json_file)
        pdf_path = str(pdf_found)
        
        result = test_pdf(pdf_path, pattern_path, supplier_name, json_name)
        results[json_name] = result
    
    # Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - EXTRACTION RESULTS")
    print("="*80)
    
    for json_name, result in sorted(results.items()):
        supplier_name = json_name.capitalize()
        print(f"\n{supplier_name} Results:")
        if result:
            print(f"  [OK] Amount: {result.amount}")
            print(f"  [OK] Due Date: {result.due_date}")
            print(f"  [OK] Bill Number: {result.bill_number}")
            print(f"  [OK] Contract ID: {result.contract_id}")
            if result.client_code:
                print(f"  [OK] Client Code: {result.client_code}")
            print(f"  [OK] IBAN: {result.iban}")
            print(f"  [OK] Business Name: {result.business_name}")
            print(f"  [OK] Address: {result.address}")
        else:
            print("  [FAIL] Failed to extract")

