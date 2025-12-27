#!/usr/bin/env python3
"""
PDF Analyzer - A reusable tool for analyzing PDF bills and extracting data.
Can be used for pattern development and future user-driven interface for unknown PDFs.
"""

import re
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

from app.pdf_parser import extract_text_from_pdf
import logging

logger = logging.getLogger(__name__)


@dataclass
class PDFAnalysisResult:
    """Results from PDF analysis."""
    supplier: Optional[str] = None
    full_text: Optional[str] = None
    ibans: List[str] = None
    amounts: List[str] = None
    dates: List[str] = None
    bill_number_candidates: List[str] = None
    contract_id_candidates: List[str] = None
    business_name_candidates: List[str] = None
    address_candidates: List[str] = None
    due_date_context: Optional[str] = None
    structured_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.ibans is None:
            self.ibans = []
        if self.amounts is None:
            self.amounts = []
        if self.dates is None:
            self.dates = []
        if self.bill_number_candidates is None:
            self.bill_number_candidates = []
        if self.contract_id_candidates is None:
            self.contract_id_candidates = []
        if self.business_name_candidates is None:
            self.business_name_candidates = []
        if self.address_candidates is None:
            self.address_candidates = []
        if self.structured_data is None:
            self.structured_data = {}


class PDFAnalyzer:
    """Analyzer for PDF bills that extracts various information patterns."""
    
    def __init__(self):
        # Romanian month names
        self.romanian_months = [
            'ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie',
            'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie'
        ]
    
    def analyze_pdf(self, pdf_bytes: bytes, supplier_hint: Optional[str] = None) -> PDFAnalysisResult:
        """
        Analyze a PDF and extract various information patterns.
        
        Args:
            pdf_bytes: PDF file content as bytes
            supplier_hint: Optional hint about the supplier name
            
        Returns:
            PDFAnalysisResult with extracted information
        """
        result = PDFAnalysisResult(supplier=supplier_hint)
        
        try:
            # Extract text
            text = extract_text_from_pdf(pdf_bytes)
            result.full_text = text
            
            # Extract IBANs
            result.ibans = self._extract_ibans(text)
            
            # Extract amounts
            result.amounts = self._extract_amounts(text)
            
            # Extract dates
            result.dates = self._extract_dates(text)
            
            # Extract bill number candidates
            result.bill_number_candidates = self._extract_bill_numbers(text)
            
            # Extract contract ID candidates
            result.contract_id_candidates = self._extract_contract_ids(text)
            
            # Extract business name candidates
            result.business_name_candidates = self._extract_business_names(text)
            
            # Extract address candidates
            result.address_candidates = self._extract_addresses(text)
            
            # Extract due date context
            result.due_date_context = self._extract_due_date_context(text)
            
            # Create structured data summary
            result.structured_data = {
                'ibans': result.ibans,
                'amounts': result.amounts,
                'dates': result.dates,
                'bill_numbers': result.bill_number_candidates,
                'contract_ids': result.contract_id_candidates,
                'business_names': list(set(result.business_name_candidates)),
                'addresses': result.address_candidates,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing PDF: {e}")
            raise
        
        return result
    
    def _extract_ibans(self, text: str) -> List[str]:
        """Extract Romanian IBANs from text."""
        # Romanian IBAN pattern: RO + 2 digits + 4 letters + account number
        pattern = r'\bRO\d{2}\s*[A-Z]{4}\s*(?:\d{4}\s*){4,6}\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        # Normalize (remove spaces, uppercase)
        ibans = [re.sub(r'\s+', '', m.upper()) for m in matches]
        return list(set(ibans))
    
    def _extract_amounts(self, text: str) -> List[str]:
        """Extract monetary amounts from text."""
        amounts = []
        patterns = [
            r'(?:TOTAL|Total|total)[\s]+(?:DE|de)[\s]+(?:PLATĂ|plată|PLATA|plata)[\s:]*([0-9.,]+)',
            r'(?:total|suma|amount|de plata|plata)[\s:]*(\d+[.,]\d{2})\s*(?:lei|ron|eur|LEI|RON|EUR)?',
            r'(\d+[.,]\d{2})\s*(?:lei|ron|eur|LEI|RON|EUR)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            amounts.extend(matches)
        # Remove duplicates while preserving order
        seen = set()
        unique_amounts = []
        for amt in amounts:
            if amt not in seen:
                seen.add(amt)
                unique_amounts.append(amt)
        return unique_amounts[:10]  # Limit to first 10
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates in various formats."""
        dates = []
        patterns = [
            r'\d{2}[/.-]\d{2}[/.-]\d{4}',  # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
            r'\d{4}[/.-]\d{2}[/.-]\d{2}',  # YYYY-MM-DD
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        return list(set(dates))[:20]  # Limit to first 20 unique dates
    
    def _extract_bill_numbers(self, text: str) -> List[str]:
        """Extract bill number candidates."""
        candidates = []
        patterns = [
            r'NOTA[\s]+DE[\s]+PLATĂ[\s]+PENTRU[\s]+LUNA[\s]+([A-Za-z]+[\s]+[0-9]{4})',
            r'Nota[\s]+de[\s]+plată[\s]+nr\.?[\s]*([0-9]+)',
            r'Factură[\s]+seria[\s]+și[\s]+nr\.:[\s]*([A-Z0-9\-\/\s]+)',
            r'Factura[\s]*#?[\s]*([A-Z0-9]+)',
            r'(?:nr\.?|număr|numar|factura|invoice|nota|NOTA|FACTURA)\s*[:\s#]*([A-Z0-9\-/\s]+)',
            r'#([A-Z0-9]+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            candidates.extend([m.strip() if isinstance(m, str) else m[0].strip() for m in matches])
        # Filter out very short results
        candidates = [c for c in candidates if len(c) >= 3]
        return list(set(candidates))[:10]
    
    def _extract_contract_ids(self, text: str) -> List[str]:
        """Extract contract/client ID candidates."""
        candidates = []
        patterns = [
            r'NOTA[\s]+DE[\s]+PLATĂ[\s]+PENTRU[\s]+LUNA[\s]+([A-Za-z]+[\s]+[0-9]{4})',
            r'Cod[\s]+client[\s:]*([0-9]+)',
            r'Cod[\s]+Cont[\s]+Contract[\s:]*([0-9]+)',
            r'(?:cont|contract|cod)\s*(?:client|contract)?[:\s]*([0-9]+)',
            r'contract[:\s]*([0-9]+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            candidates.extend([m.strip() if isinstance(m, str) else m[0].strip() for m in matches])
        return list(set(candidates))[:10]
    
    def _extract_business_names(self, text: str) -> List[str]:
        """Extract business name candidates."""
        candidates = []
        # Look for company names with legal suffixes
        pattern = r'([A-Z][A-Za-z\s&\.]+(?:SA|S\.A\.|SRL|LTD|S\.R\.L\.))'
        matches = re.findall(pattern, text)
        candidates.extend(matches)
        # Also look for common Romanian utility companies
        company_keywords = ['Digi Romania', 'RCS', 'RDS', 'Vodafone', 'E-BLOC', 'E-Bloc', 'Hidroelectrica']
        for keyword in company_keywords:
            if keyword in text:
                # Try to extract full company name
                pattern = rf'{re.escape(keyword)}[A-Za-z\s&\.]*(?:SA|S\.A\.|SRL|LTD)?'
                matches = re.findall(pattern, text, re.IGNORECASE)
                candidates.extend(matches)
        return list(set(candidates))[:10]
    
    def _extract_addresses(self, text: str) -> List[str]:
        """Extract address candidates."""
        candidates = []
        patterns = [
            r'Adresa[\s:]*([^\n]{10,150})',
            r'address[\s:]*([^\n]{10,150})',
            r'(?:str\.|strada|bd\.|bulevard)[\s]+([^\n]{10,100})',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            candidates.extend([m.strip() for m in matches if len(m.strip()) > 10])
        return candidates[:10]
    
    def _extract_due_date_context(self, text: str) -> Optional[str]:
        """Extract context around due date keywords."""
        due_date_keywords = ['scaden', 'due', 'data scadentei', 'data scadență', 'data scadenţei', 'scadenta']
        for keyword in due_date_keywords:
            if keyword.lower() in text.lower():
                idx = text.lower().find(keyword.lower())
                context = text[max(0, idx-30):min(len(text), idx+100)]
                return context
        return None
    
    def generate_pattern_suggestions(self, analysis: PDFAnalysisResult) -> Dict[str, Any]:
        """
        Generate pattern suggestions based on analysis results.
        Useful for creating extraction patterns for unknown PDFs.
        """
        suggestions = {
            'iban_pattern': None,
            'amount_pattern': None,
            'bill_number_pattern': None,
            'contract_id_pattern': None,
            'business_name_pattern': None,
            'address_pattern': None,
            'due_date_pattern': None,
        }
        
        if analysis.ibans:
            # Suggest IBAN pattern
            iban_example = analysis.ibans[0]
            suggestions['iban_pattern'] = f"RO\\d{{2}}\\s*[A-Z]{{4}}\\s*(?:\\d{{4}}\\s*){{4,6}}"
        
        if analysis.amounts:
            suggestions['amount_pattern'] = "TOTAL[\\s]+DE[\\s]+PLATĂ[\\s:]*([0-9.,]+)"
        
        if analysis.bill_number_candidates:
            suggestions['bill_number_pattern'] = "Suggested: Look for patterns near these candidates"
        
        if analysis.contract_id_candidates:
            suggestions['contract_id_pattern'] = "Suggested: Look for patterns near these candidates"
        
        if analysis.business_name_candidates:
            business_name = analysis.business_name_candidates[0]
            # Escape special regex characters
            escaped = re.escape(business_name)
            suggestions['business_name_pattern'] = escaped
        
        return suggestions
    
    def format_analysis_report(self, analysis: PDFAnalysisResult) -> str:
        """Format analysis results as a readable report."""
        lines = [
            "=" * 80,
            "PDF ANALYSIS REPORT",
            "=" * 80,
            f"Supplier Hint: {analysis.supplier or 'None'}",
            "",
            "IBANs Found:",
            f"  {', '.join(analysis.ibans) if analysis.ibans else 'None'}",
            "",
            "Amounts Found:",
            f"  {', '.join(analysis.amounts) if analysis.amounts else 'None'}",
            "",
            "Dates Found (first 10):",
            f"  {', '.join(analysis.dates[:10]) if analysis.dates else 'None'}",
            "",
            "Bill Number Candidates:",
            f"  {', '.join(analysis.bill_number_candidates) if analysis.bill_number_candidates else 'None'}",
            "",
            "Contract ID Candidates:",
            f"  {', '.join(analysis.contract_id_candidates) if analysis.contract_id_candidates else 'None'}",
            "",
            "Business Name Candidates:",
            f"  {', '.join(analysis.business_name_candidates) if analysis.business_name_candidates else 'None'}",
            "",
            "Address Candidates:",
            "\n".join([f"  - {addr}" for addr in analysis.address_candidates[:5]]) if analysis.address_candidates else "  None",
            "",
        ]
        
        if analysis.due_date_context:
            lines.extend([
                "Due Date Context:",
                f"  {repr(analysis.due_date_context)}",
                "",
            ])
        
        lines.append("=" * 80)
        
        return "\n".join(lines)

