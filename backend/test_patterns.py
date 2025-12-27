#!/usr/bin/env python3
"""Test PDF extraction patterns for E-Bloc and Digi.
Also includes PDF analyzer for future user-driven interface.
Run with: python backend/test_patterns.py
"""

import sys
import json
from pathlib import Path

# Add current directory to path  
sys.path.insert(0, str(Path(__file__).parent))

from app.pdf_parser import parse_pdf_with_patterns, extract_text_from_pdf
from app.models import ExtractionPattern
from app.pdf_analyzer import PDFAnalyzer
from app.pdf_analyzer import PDFAnalyzer


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


def test_pdf(pdf_path: str, pattern_path: str, supplier_name: str):
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
        print("EXTRACTED TEXT (full):")
        print("-" * 80)
        print(text)
        print("-" * 80)
        print()
        
        # Parse with pattern
        result, pattern_to_update = parse_pdf_with_patterns(pdf_bytes, [pattern])
        
        # Print results
        print("EXTRACTION RESULTS:")
        print("-" * 80)
        print(f"✓ Supplier: {result.matched_pattern_supplier}")
        print(f"✓ Pattern: {result.matched_pattern_name}")
        print(f"✓ IBAN: {result.iban}")
        print(f"✓ Amount: {result.amount}")
        print(f"✓ Due Date: {result.due_date}")
        print(f"✓ Bill Number: {result.bill_number}")
        print(f"✓ Contract ID: {result.contract_id}")
        print(f"✓ Business Name: {result.business_name}")
        print(f"✓ Address: {result.address}")
        print(f"✓ Bank Accounts: {len(result.bank_accounts)} found")
        for acc in result.bank_accounts:
            print(f"    - {acc.get('bank', 'Unknown')}: {acc.get('iban', '')}")
        
        # Also extract all IBANs from text for bank account setup
        print("\nALL IBANs FOUND IN PDF (for bank_accounts JSON):")
        import re
        iban_pattern = r'\bRO\d{2}[A-Z0-9]{4,28}\b'
        all_ibans = re.findall(iban_pattern, text, re.IGNORECASE)
        bank_keywords = {
            'CITI': 'Citibank',
            'INGB': 'ING Bank',
            'BRDE': 'BRD',
            'BTRL': 'Banca Transilvania',
            'RNCB': 'BCR',
            'BUCU': 'Alpha Bank',
            'BACX': 'UniCredit Bank',
            'RZBR': 'Raiffeisen Bank',
            'TREZ': 'Trezorerie',
            'PIRB': 'First Bank',
            'CECE': 'CEC Bank',
            'UGBI': 'Garanti Bank',
        }
        unique_ibans = []
        for iban in all_ibans:
            normalized = re.sub(r'\s+', '', iban.upper())
            if normalized not in unique_ibans:
                unique_ibans.append(normalized)
        for iban in unique_ibans:
            bank_name = "Unknown"
            for code, name in bank_keywords.items():
                if code in iban:
                    bank_name = name
                    break
            print(f'    {{"bank": "{bank_name}", "iban": "{iban}"}}')
        print("-" * 80)
        print()
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_pdf_standalone(pdf_path: str, supplier_name: str):
    """Analyze PDF using the PDF analyzer (useful for unknown PDFs)."""
    print(f"\n{'='*80}")
    print(f"PDF ANALYZER - {supplier_name}")
    print(f"File: {pdf_path}")
    print(f"{'='*80}\n")
    
    if not Path(pdf_path).exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        return None
    
    try:
        analyzer = PDFAnalyzer()
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        analysis = analyzer.analyze_pdf(pdf_bytes, supplier_name)
        
        # Print analysis report
        print(analyzer.format_analysis_report(analysis))
        
        return analysis
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Test E-Bloc
    ebloc_pdf = r"C:\Users\Pio Doi\Downloads\Nota de plată (50).pdf"
    ebloc_pattern = str(Path(__file__).parent / "extraction_patterns" / "ebloc.json")
    
    print("\n" + "="*80)
    print("PATTERN-BASED EXTRACTION TEST")
    print("="*80)
    ebloc_result = test_pdf(ebloc_pdf, ebloc_pattern, "E-Bloc")
    
    # Test Digi
    digi_pdf = r"C:\Users\Pio Doi\Downloads\DIGI_Factura #FDB25 88860925.pdf"
    digi_pattern = str(Path(__file__).parent / "extraction_patterns" / "digi.json")
    digi_result = test_pdf(digi_pdf, digi_pattern, "Digi")
    
    # Also run PDF analyzer for additional insights
    print("\n" + "="*80)
    print("PDF ANALYZER (for unknown PDFs)")
    print("="*80)
    ebloc_analysis = analyze_pdf_standalone(ebloc_pdf, "E-Bloc")
    digi_analysis = analyze_pdf_standalone(digi_pdf, "Digi")
    
    # Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - EXTRACTION RESULTS")
    print("="*80)
    print("\nE-Bloc Results:")
    if ebloc_result:
        print(f"  ✓ Amount: {ebloc_result.amount}")
        print(f"  ✓ Due Date: {ebloc_result.due_date}")
        print(f"  ✓ Bill Number: {ebloc_result.bill_number}")
        print(f"  ✓ Contract ID: {ebloc_result.contract_id}")
        print(f"  ✓ IBAN: {ebloc_result.iban}")
        print(f"  ✓ Business Name: {ebloc_result.business_name}")
        print(f"  ✓ Address: {ebloc_result.address}")
    else:
        print("  ✗ Failed to extract")
    
    print("\nDigi Results:")
    if digi_result:
        print(f"  ✓ Amount: {digi_result.amount}")
        print(f"  ✓ Due Date: {digi_result.due_date}")
        print(f"  ✓ Bill Number: {digi_result.bill_number}")
        print(f"  ✓ Contract ID: {digi_result.contract_id}")
        print(f"  ✓ IBAN: {digi_result.iban}")
        print(f"  ✓ Business Name: {digi_result.business_name}")
        print(f"  ✓ Address: {digi_result.address}")
    else:
        print("  ✗ Failed to extract")

