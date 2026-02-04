"""Supplier management routes."""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Query
from app.models import (
    Supplier, SupplierCreate, SupplierUpdate,
    PropertySupplier, PropertySupplierCreate, PropertySupplierUpdate,
    TokenData, UserRole
)
from app.auth import require_landlord, require_admin
from app.database import db
from app.utils.suppliers import initialize_suppliers, save_suppliers_to_json
from app.limits import check_can_add_supplier

router = APIRouter(tags=["suppliers"])
logger = logging.getLogger(__name__)


@router.get("/suppliers")
async def list_suppliers(
    assigned_only: bool = Query(False, description="Only return suppliers assigned to properties"),
    current_user: TokenData = Depends(require_landlord)
):
    """List all supported suppliers, optionally filtered to only those assigned to properties"""
    # Initialize suppliers on first request
    initialize_suppliers()
    
    if assigned_only:
        # Get all properties for this user
        user_properties = db.list_properties(landlord_id=current_user.user_id)
        if not user_properties:
            return []
        
        # Get all property suppliers for these properties
        assigned_supplier_ids = set()
        for prop in user_properties:
            property_suppliers = db.list_property_suppliers(prop.id)
            for ps in property_suppliers:
                assigned_supplier_ids.add(ps.supplier_id)
        
        # Get unique suppliers (excluding placeholder supplier id='0')
        all_suppliers = db.list_suppliers()
        return [s for s in all_suppliers if s.id in assigned_supplier_ids and s.id != "0"]
    else:
        # Exclude placeholder supplier (id='0') from the list
        suppliers = db.list_suppliers()
        return [s for s in suppliers if s.id != "0"]


@router.get("/admin/suppliers")
async def admin_list_suppliers(current_user: TokenData = Depends(require_admin)):
    """List all suppliers (admin only)"""
    # Initialize suppliers to ensure new ones from patterns are added, but don't overwrite manual changes
    initialize_suppliers()
    suppliers = db.list_suppliers()
    return suppliers


@router.post("/admin/suppliers", status_code=status.HTTP_201_CREATED)
async def admin_create_supplier(
    data: SupplierCreate, current_user: TokenData = Depends(require_admin)
):
    """Create a new supplier (admin only)"""
    # Check if supplier with same name already exists
    existing = db.get_supplier_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Supplier with this name already exists")
    
    supplier = Supplier(
        name=data.name,
        has_api=data.has_api,
        bill_type=data.bill_type,
        extraction_pattern_supplier=data.extraction_pattern_supplier,
    )
    db.save_supplier(supplier)
    
    # Sync to JSON file
    save_suppliers_to_json()
    
    return supplier


@router.put("/admin/suppliers/{supplier_id}")
async def admin_update_supplier(
    supplier_id: str, data: SupplierUpdate, current_user: TokenData = Depends(require_admin)
):
    """Update a supplier (admin only)"""
    supplier = db.get_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Check name uniqueness if name is being changed
    if data.name is not None and data.name != supplier.name:
        existing = db.get_supplier_by_name(data.name)
        if existing:
            raise HTTPException(status_code=400, detail="Supplier with this name already exists")
        supplier.name = data.name
    
    if data.has_api is not None:
        supplier.has_api = data.has_api
    if data.bill_type is not None:
        supplier.bill_type = data.bill_type
    if data.extraction_pattern_supplier is not None:
        supplier.extraction_pattern_supplier = data.extraction_pattern_supplier
    
    db.save_supplier(supplier)
    
    # Sync to JSON file
    save_suppliers_to_json()
    
    return supplier


@router.get("/admin/suppliers/{supplier_id}/properties")
async def admin_get_supplier_properties(
    supplier_id: str, current_user: TokenData = Depends(require_admin)
):
    """Get all properties using this supplier (admin only)"""
    supplier = db.get_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    property_suppliers = db.list_property_suppliers_by_supplier(supplier_id)
    result = []
    for ps in property_suppliers:
        prop = db.get_property(ps.property_id)
        if prop:
            result.append({
                "property_id": prop.id,
                "property_name": prop.name,
                "property_address": prop.address,
                "property_supplier_id": ps.id,
            })
    return result


@router.delete("/admin/suppliers/{supplier_id}")
async def admin_delete_supplier(
    supplier_id: str,
    remove_property_references: bool = Query(False, description="Also remove all property-supplier references"),
    current_user: TokenData = Depends(require_admin)
):
    """Delete a supplier (admin only)"""
    supplier = db.get_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Check if supplier is used by any properties
    property_suppliers = db.list_property_suppliers_by_supplier(supplier_id)
    
    if property_suppliers and not remove_property_references:
        # Return information about connected properties without deleting
        properties_info = []
        for ps in property_suppliers:
            prop = db.get_property(ps.property_id)
            if prop:
                properties_info.append({
                    "property_id": prop.id,
                    "property_name": prop.name,
                    "property_address": prop.address,
                    "property_supplier_id": ps.id,
                })
        # Return 400 with a message - frontend should call getProperties separately to show them
        raise HTTPException(
            status_code=400,
            detail=f"Supplier is used by {len(property_suppliers)} property/properties. Use getProperties endpoint to see details, or set remove_property_references=true to delete them as well."
        )
    
    # Remove property-supplier references if requested
    if remove_property_references:
        for ps in property_suppliers:
            db.delete_property_supplier(ps.id)
    
    # Delete the supplier
    deleted = db.delete_supplier(supplier_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete supplier")
    
    # Sync to JSON file
    save_suppliers_to_json()
    
    return {"status": "deleted"}


@router.get("/properties/{property_id}/suppliers")
async def list_property_suppliers(
    property_id: str, current_user: TokenData = Depends(require_landlord)
):
    """List suppliers configured for a property"""
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    property_suppliers = db.list_property_suppliers(property_id)
    # Enrich with supplier details
    result = []
    for ps in property_suppliers:
        # Handle pattern-based suppliers (supplier_id = "0")
        if ps.supplier_id == "0":
            # Create a virtual supplier object from the pattern data
            from app.models import BillType
            virtual_supplier = {
                "id": "0",
                "name": ps.extraction_pattern_supplier or "Unknown Pattern",
                "has_api": False,
                "bill_type": BillType.UTILITIES.value,
                "extraction_pattern_supplier": ps.extraction_pattern_supplier,
                "created_at": ps.created_at,
            }
            result.append({
                "id": ps.id,
                "supplier": virtual_supplier,
                "property_id": ps.property_id,
                "supplier_id": ps.supplier_id,
                "extraction_pattern_supplier": ps.extraction_pattern_supplier,
                "contract_id": ps.contract_id,
                "direct_debit": ps.direct_debit,
                "created_at": ps.created_at,
                "updated_at": ps.updated_at,
            })
        else:
            supplier = db.get_supplier(ps.supplier_id)
            if supplier:
                result.append({
                    "id": ps.id,
                    "supplier": supplier,
                    "property_id": ps.property_id,
                    "supplier_id": ps.supplier_id,
                    "extraction_pattern_supplier": ps.extraction_pattern_supplier,
                    "contract_id": ps.contract_id,
                    "direct_debit": ps.direct_debit,
                    "created_at": ps.created_at,
                    "updated_at": ps.updated_at,
                })
    return result


@router.post("/properties/{property_id}/suppliers", status_code=status.HTTP_201_CREATED)
async def create_property_supplier(
    property_id: str, data: PropertySupplierCreate, current_user: TokenData = Depends(require_landlord)
):
    """Add a supplier to a property"""
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Handle pattern-based suppliers (supplier_id = "0")
    is_pattern_supplier = data.supplier_id == "0"
    
    # Check subscription limit for suppliers
    user = db.get_user(current_user.user_id)
    if user and current_user.role != UserRole.ADMIN:
        # Pattern-based suppliers are a premium feature
        if is_pattern_supplier and user.subscription_tier == 0:
            raise HTTPException(status_code=403, detail="upgrade_required")
        
        # Both free and paid tiers check suppliers per property (max 5 for free, 10 for paid)
        current_property_suppliers = len(db.list_property_suppliers(property_id))
        can_add, _ = check_can_add_supplier(user.subscription_tier, current_property_suppliers)
        
        if not can_add:
            raise HTTPException(status_code=403, detail="upgrade_required")
    
    if is_pattern_supplier:
        # For pattern-based suppliers, validate extraction_pattern_supplier is provided
        if not data.extraction_pattern_supplier:
            raise HTTPException(status_code=400, detail="extraction_pattern_supplier is required when supplier_id is 0")
        supplier = None
        from app.models import BillType
        virtual_supplier = {
            "id": "0",
            "name": data.extraction_pattern_supplier,
            "has_api": False,
            "bill_type": BillType.UTILITIES.value,
            "extraction_pattern_supplier": data.extraction_pattern_supplier,
        }
    else:
        supplier = db.get_supplier(data.supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        virtual_supplier = None
    
    # Check if exact duplicate exists (same supplier + same contract_id, including both None)
    # For pattern suppliers, also check extraction_pattern_supplier
    contract_id_value = data.contract_id if data.contract_id else None
    existing = db.get_property_supplier_by_supplier_and_contract(property_id, data.supplier_id, contract_id_value)
    
    # For pattern suppliers, also need to match extraction_pattern_supplier
    if existing and is_pattern_supplier:
        if existing.extraction_pattern_supplier != data.extraction_pattern_supplier:
            existing = None  # Not a match, different pattern
    
    if existing:
        # Check if direct_debit is the same
        requested_direct_debit = data.direct_debit if data.direct_debit is not None else False
        if existing.direct_debit == requested_direct_debit:
            # Same configuration, nothing to do
            if is_pattern_supplier:
                return_supplier = virtual_supplier
            else:
                return_supplier = db.get_supplier(existing.supplier_id)
            return {
                "id": existing.id,
                "supplier": return_supplier,
                "property_id": existing.property_id,
                "supplier_id": existing.supplier_id,
                "extraction_pattern_supplier": existing.extraction_pattern_supplier,
                "contract_id": existing.contract_id,
                "direct_debit": existing.direct_debit,
                "created_at": existing.created_at,
                "updated_at": existing.updated_at,
                "message": "Supplier with this contract ID already configured with the same settings. No changes made."
            }
        else:
            # Different direct_debit value, update it
            existing.direct_debit = requested_direct_debit
            existing.updated_at = datetime.utcnow()
            db.save_property_supplier(existing)
            
            if is_pattern_supplier:
                return_supplier = virtual_supplier
            else:
                return_supplier = db.get_supplier(existing.supplier_id)
            
            return {
                "id": existing.id,
                "supplier": return_supplier,
                "property_id": existing.property_id,
                "supplier_id": existing.supplier_id,
                "extraction_pattern_supplier": existing.extraction_pattern_supplier,
                "contract_id": existing.contract_id,
                "direct_debit": existing.direct_debit,
                "created_at": existing.created_at,
                "updated_at": existing.updated_at,
            }
    
    property_supplier = PropertySupplier(
        property_id=property_id,
        supplier_id=data.supplier_id,
        extraction_pattern_supplier=data.extraction_pattern_supplier if is_pattern_supplier else None,
        contract_id=data.contract_id if data.contract_id else None,
        direct_debit=data.direct_debit if data.direct_debit is not None else False,
    )
    db.save_property_supplier(property_supplier)
    
    return {
        "id": property_supplier.id,
        "supplier": virtual_supplier if is_pattern_supplier else supplier,
        "property_id": property_supplier.property_id,
        "supplier_id": property_supplier.supplier_id,
        "extraction_pattern_supplier": property_supplier.extraction_pattern_supplier,
        "contract_id": property_supplier.contract_id,
        "direct_debit": property_supplier.direct_debit,
        "created_at": property_supplier.created_at,
        "updated_at": property_supplier.updated_at,
    }


@router.put("/properties/{property_id}/suppliers/{property_supplier_id}")
async def update_property_supplier(
    property_id: str,
    property_supplier_id: str,
    data: PropertySupplierUpdate,
    current_user: TokenData = Depends(require_landlord),
):
    """Update property supplier settings"""
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    property_supplier = db.get_property_supplier(property_supplier_id)
    if not property_supplier:
        raise HTTPException(status_code=404, detail="Property supplier not found")
    if property_supplier.property_id != property_id:
        raise HTTPException(status_code=400, detail="Property supplier does not belong to this property")
    
    # Update extraction_pattern_supplier if provided
    if data.extraction_pattern_supplier is not None:
        property_supplier.extraction_pattern_supplier = data.extraction_pattern_supplier if data.extraction_pattern_supplier else None
    
    # Update contract_id if provided
    if data.contract_id is not None:
        property_supplier.contract_id = data.contract_id if data.contract_id else None
    
    # Update direct_debit if provided
    if data.direct_debit is not None:
        property_supplier.direct_debit = data.direct_debit
    
    property_supplier.updated_at = datetime.utcnow()
    db.save_property_supplier(property_supplier)
    
    # Handle pattern-based suppliers (supplier_id = "0")
    if property_supplier.supplier_id == "0":
        from app.models import BillType
        return_supplier = {
            "id": "0",
            "name": property_supplier.extraction_pattern_supplier or "Unknown Pattern",
            "has_api": False,
            "bill_type": BillType.UTILITIES.value,
            "extraction_pattern_supplier": property_supplier.extraction_pattern_supplier,
        }
    else:
        return_supplier = db.get_supplier(property_supplier.supplier_id)
    
    return {
        "id": property_supplier.id,
        "supplier": return_supplier,
        "property_id": property_supplier.property_id,
        "supplier_id": property_supplier.supplier_id,
        "extraction_pattern_supplier": property_supplier.extraction_pattern_supplier,
        "contract_id": property_supplier.contract_id,
        "direct_debit": property_supplier.direct_debit,
        "created_at": property_supplier.created_at,
        "updated_at": property_supplier.updated_at,
    }


@router.delete("/properties/{property_id}/suppliers/{property_supplier_id}")
async def delete_property_supplier(
    property_id: str, property_supplier_id: str, current_user: TokenData = Depends(require_landlord)
):
    """Remove a supplier from a property"""
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    # User isolation: all users (including admins) can only access their own properties
    if prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    property_supplier = db.get_property_supplier(property_supplier_id)
    if not property_supplier:
        raise HTTPException(status_code=404, detail="Property supplier not found")
    if property_supplier.property_id != property_id:
        raise HTTPException(status_code=400, detail="Property supplier does not belong to this property")
    
    db.delete_property_supplier(property_supplier_id)
    return {"status": "deleted"}

