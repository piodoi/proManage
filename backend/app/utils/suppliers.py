"""Supplier initialization and utility functions."""
import json
import logging
from pathlib import Path
from app.database import db
from app.models import Supplier, BillType

logger = logging.getLogger(__name__)


def save_suppliers_to_json():
    """Save all suppliers from database to suppliers.json file."""
    suppliers_file = Path(__file__).parent.parent.parent / "extraction_patterns" / "suppliers.json"
    
    try:
        # Get all suppliers from database
        all_suppliers = db.list_suppliers()
        
        # Convert to JSON format
        suppliers_data = []
        for supplier in all_suppliers:
            supplier_dict = {
                "name": supplier.name,
                "bill_type": supplier.bill_type.value,
                "has_api": supplier.has_api,
                "extraction_pattern_supplier": supplier.extraction_pattern_supplier,
            }
            suppliers_data.append(supplier_dict)
        
        # Sort alphabetically by name
        suppliers_data.sort(key=lambda x: x["name"].lower())
        
        # Write to JSON file
        with open(suppliers_file, 'w', encoding='utf-8') as f:
            json.dump(suppliers_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(suppliers_data)} suppliers to {suppliers_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving suppliers to JSON: {e}")
        return False


def load_suppliers_from_json():
    """Load suppliers from suppliers.json file in extraction_patterns directory."""
    suppliers_file = Path(__file__).parent.parent.parent / "extraction_patterns" / "suppliers.json"
    
    if not suppliers_file.exists():
        logger.warning(f"Suppliers file not found at {suppliers_file}")
        return []
    
    try:
        with open(suppliers_file, 'r', encoding='utf-8') as f:
            suppliers_data = json.load(f)
        
        # Validate and convert to supplier objects
        suppliers = []
        for data in suppliers_data:
            try:
                supplier = {
                    "name": data["name"],
                    "bill_type": BillType(data["bill_type"]),
                    "has_api": data.get("has_api", False),
                    "extraction_pattern_supplier": data.get("extraction_pattern_supplier"),
                }
                suppliers.append(supplier)
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid supplier data in suppliers.json: {data}, error: {e}")
                continue
        
        return suppliers
    except Exception as e:
        logger.error(f"Error loading suppliers from JSON: {e}")
        return []


def initialize_suppliers():
    """Initialize suppliers from suppliers.json file."""
    # Load suppliers from JSON file
    suppliers_data = load_suppliers_from_json()
    
    # Also get suppliers from extraction patterns to ensure they're created if not in JSON
    patterns = db.list_extraction_patterns()
    pattern_suppliers = {}
    for pattern in patterns:
        if pattern.supplier:
            supplier_name = pattern.supplier
            # Check if supplier already exists in JSON data
            exists_in_json = any(
                s.get("name", "").lower() == supplier_name.lower() 
                or (s.get("extraction_pattern_supplier") and s.get("extraction_pattern_supplier").lower() == supplier_name.lower())
                for s in suppliers_data
            )
            
            if not exists_in_json and supplier_name not in pattern_suppliers:
                pattern_suppliers[supplier_name] = {
                    "name": supplier_name,
                    "has_api": False,
                    "bill_type": pattern.bill_type,
                    "extraction_pattern_supplier": supplier_name,
                }
    
    # Merge pattern suppliers into main list
    all_suppliers = suppliers_data + list(pattern_suppliers.values())
    
    # Create or update suppliers in database
    for supplier_data in all_suppliers:
        # Convert bill_type string to enum if needed
        if isinstance(supplier_data.get("bill_type"), str):
            supplier_data["bill_type"] = BillType(supplier_data["bill_type"])
        
        existing = db.get_supplier_by_name(supplier_data["name"])
        if existing:
            # Don't overwrite existing supplier's has_api - preserve manual changes
            # Only update extraction_pattern_supplier if it's provided and different
            if supplier_data.get("extraction_pattern_supplier") is not None:
                if existing.extraction_pattern_supplier != supplier_data["extraction_pattern_supplier"]:
                    existing.extraction_pattern_supplier = supplier_data["extraction_pattern_supplier"]
                    db.save_supplier(existing)
        else:
            # Create new supplier
            supplier = Supplier(**supplier_data)
            db.save_supplier(supplier)
            logger.debug(f"Created supplier: {supplier.name} (API: {supplier.has_api}, Type: {supplier.bill_type.value})")
