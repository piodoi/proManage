"""Supplier initialization and utility functions."""
from app.database import db
from app.models import Supplier, BillType


def initialize_suppliers():
    """Initialize suppliers from extraction patterns and hardcoded list"""
    # Hardcoded suppliers with API support
    api_suppliers = [
        {"name": "Apanova", "has_api": True, "bill_type": BillType.UTILITIES},
        {"name": "Nova power & gas", "has_api": True, "bill_type": BillType.UTILITIES},
        {"name": "EonRomania", "has_api": True, "bill_type": BillType.UTILITIES},
        {"name": "MyElectrica", "has_api": True, "bill_type": BillType.UTILITIES},
    ]
    
    # Load suppliers from extraction patterns
    patterns = db.list_extraction_patterns()
    pattern_suppliers = {}
    for pattern in patterns:
        if pattern.supplier:
            supplier_name = pattern.supplier
            if supplier_name not in pattern_suppliers:
                pattern_suppliers[supplier_name] = {
                    "name": supplier_name,
                    "has_api": False,  # Default to False unless in hardcoded list
                    "bill_type": pattern.bill_type,
                    "extraction_pattern_supplier": supplier_name,
                }
    
    # Check if hardcoded suppliers also exist in patterns
    for api_supplier in api_suppliers:
        api_name_lower = api_supplier["name"].lower()
        for pattern_supplier_name, pattern_supplier_data in pattern_suppliers.items():
            if pattern_supplier_name.lower() == api_name_lower:
                # Update pattern supplier to have API support
                pattern_supplier_data["has_api"] = True
                break
        else:
            # API supplier not in patterns, add it
            pattern_suppliers[api_supplier["name"]] = api_supplier
    
    # Create or update suppliers in database
    for supplier_data in pattern_suppliers.values():
        existing = db.get_supplier_by_name(supplier_data["name"])
        if existing:
            # Don't overwrite existing supplier's has_api - preserve manual changes
            # Only create new suppliers with the default has_api value
            pass
        else:
            # Create new supplier
            supplier = Supplier(**supplier_data)
            db.save_supplier(supplier)

