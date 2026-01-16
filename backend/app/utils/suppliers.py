"""Supplier initialization and utility functions."""
import json
import logging
from app.database import db
from app.models import Supplier, BillType
from app.paths import SUPPLIERS_FILE

logger = logging.getLogger(__name__)


def save_suppliers_to_json():
    """Save all suppliers from database to suppliers.json file."""
    suppliers_file = SUPPLIERS_FILE
    
    try:
        # Get all suppliers from database
        all_suppliers = db.list_suppliers()
        
        # Convert to JSON format, excluding the placeholder supplier (id='0')
        suppliers_data = []
        for supplier in all_suppliers:
            # Skip the pattern-based placeholder supplier
            if supplier.id == "0":
                continue
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
    """Load suppliers from suppliers.json file."""
    suppliers_file = SUPPLIERS_FILE
    
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


def ensure_pattern_placeholder_supplier():
    """Ensure the special placeholder supplier for pattern-based property suppliers exists."""
    # Check if the placeholder supplier with id='0' exists
    existing = db.get_supplier("0")
    if not existing:
        # Create the placeholder supplier
        placeholder = Supplier(
            id="0",
            name="[Pattern-based Supplier]",
            has_api=False,
            bill_type=BillType.UTILITIES,
            extraction_pattern_supplier=None,
        )
        db.save_supplier(placeholder)
        logger.info("Created placeholder supplier for pattern-based property suppliers (id='0')")


def initialize_suppliers():
    """Initialize suppliers from suppliers.json file.
    
    JSON is the source of truth:
    - New suppliers in JSON are created in DB
    - Suppliers removed from JSON are deleted from DB (if not linked to properties)
    - All fields are synced from JSON to DB
    """
    # First, ensure the pattern placeholder supplier exists
    ensure_pattern_placeholder_supplier()
    
    # Load suppliers from JSON file (source of truth)
    suppliers_data = load_suppliers_from_json()
    
    # Track supplier names in JSON for cleanup
    json_supplier_names = {s["name"].lower() for s in suppliers_data}
    
    # Create or update suppliers in database
    for supplier_data in suppliers_data:
        # Convert bill_type string to enum if needed
        if isinstance(supplier_data.get("bill_type"), str):
            supplier_data["bill_type"] = BillType(supplier_data["bill_type"])
        
        existing = db.get_supplier_by_name(supplier_data["name"])
        if existing:
            # Update all fields from JSON (JSON is source of truth)
            updated = False
            if existing.bill_type != supplier_data["bill_type"]:
                existing.bill_type = supplier_data["bill_type"]
                updated = True
            if existing.has_api != supplier_data.get("has_api", False):
                existing.has_api = supplier_data.get("has_api", False)
                updated = True
            if existing.extraction_pattern_supplier != supplier_data.get("extraction_pattern_supplier"):
                existing.extraction_pattern_supplier = supplier_data.get("extraction_pattern_supplier")
                updated = True
            if updated:
                db.save_supplier(existing)
                logger.debug(f"Updated supplier: {existing.name}")
        else:
            # Create new supplier
            supplier = Supplier(**supplier_data)
            db.save_supplier(supplier)
            logger.info(f"Created supplier: {supplier.name} (API: {supplier.has_api}, Type: {supplier.bill_type.value})")
    
    # Remove suppliers from DB that are no longer in JSON
    # (except the placeholder supplier and suppliers linked to properties)
    db_suppliers = db.list_suppliers()
    for db_supplier in db_suppliers:
        # Skip placeholder supplier
        if db_supplier.id == "0":
            continue
        
        # Check if supplier is in JSON
        if db_supplier.name.lower() not in json_supplier_names:
            # Check if supplier is linked to any property
            linked_properties = db.list_property_suppliers_by_supplier(db_supplier.id)
            if linked_properties and len(linked_properties) > 0:
                logger.warning(f"Supplier '{db_supplier.name}' not in JSON but linked to {len(linked_properties)} properties - keeping in DB")
            else:
                # Safe to delete - not linked to any properties
                db.delete_supplier(db_supplier.id)
                logger.info(f"Removed supplier '{db_supplier.name}' from DB (not in JSON and not linked to properties)")
