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
from app.utils.suppliers import initialize_suppliers
from app.utils.encryption import encrypt_password

router = APIRouter(tags=["suppliers"])
logger = logging.getLogger(__name__)


@router.get("/suppliers")
async def list_suppliers(current_user: TokenData = Depends(require_landlord)):
    """List all supported suppliers"""
    # Initialize suppliers on first request
    initialize_suppliers()
    suppliers = db.list_suppliers()
    return suppliers


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
    db.delete_supplier(supplier_id)
    return {"status": "deleted"}


@router.get("/properties/{property_id}/suppliers")
async def list_property_suppliers(
    property_id: str, current_user: TokenData = Depends(require_landlord)
):
    """List suppliers configured for a property"""
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    property_suppliers = db.list_property_suppliers(property_id)
    # Enrich with supplier details
    result = []
    for ps in property_suppliers:
        supplier = db.get_supplier(ps.supplier_id)
        if supplier:
            result.append({
                "id": ps.id,
                "supplier": supplier,
                "property_id": ps.property_id,
                "supplier_id": ps.supplier_id,
                "has_credentials": bool(ps.username and ps.password_hash),
                "created_at": ps.created_at,
                "updated_at": ps.updated_at,
            })
    return result


@router.post("/properties/{property_id}/suppliers", status_code=status.HTTP_201_CREATED)
async def create_property_supplier(
    property_id: str, data: PropertySupplierCreate, current_user: TokenData = Depends(require_landlord)
):
    """Add a supplier to a property (with optional credentials)"""
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    supplier = db.get_supplier(data.supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Check if already exists
    existing = db.get_property_supplier_by_supplier(property_id, data.supplier_id)
    if existing:
        raise HTTPException(status_code=400, detail="Supplier already configured for this property")
    
    # Check if same supplier exists for other properties of the same user - copy credentials
    username = None
    password_hash = None
    if not data.username or not data.password:
        # Try to find credentials from another property of the same user
        user_properties = db.list_properties(landlord_id=prop.landlord_id)
        for user_prop in user_properties:
            if user_prop.id != property_id:
                existing_ps = db.get_property_supplier_by_supplier(user_prop.id, data.supplier_id)
                if existing_ps and existing_ps.username and existing_ps.password_hash:
                    # Copy credentials from existing property supplier
                    username = existing_ps.username
                    password_hash = existing_ps.password_hash
                    logger.info(f"[Property Supplier] Copied credentials from property {user_prop.id} for supplier {supplier.name}")
                    break
    
    # Use provided credentials if available, otherwise use copied ones
    if data.username:
        username = encrypt_password(data.username)
    if data.password:
        password_hash = encrypt_password(data.password)
    
    property_supplier = PropertySupplier(
        property_id=property_id,
        supplier_id=data.supplier_id,
        username=username,
        password_hash=password_hash,
    )
    db.save_property_supplier(property_supplier)
    
    return {
        "id": property_supplier.id,
        "supplier": supplier,
        "property_id": property_supplier.property_id,
        "supplier_id": property_supplier.supplier_id,
        "has_credentials": bool(property_supplier.username and property_supplier.password_hash),
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
    """Update supplier credentials for a property"""
    prop = db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    property_supplier = db.get_property_supplier(property_supplier_id)
    if not property_supplier:
        raise HTTPException(status_code=404, detail="Property supplier not found")
    if property_supplier.property_id != property_id:
        raise HTTPException(status_code=400, detail="Property supplier does not belong to this property")
    
    # Update credentials if provided
    if data.username is not None:
        property_supplier.username = encrypt_password(data.username) if data.username else None
    if data.password is not None:
        property_supplier.password_hash = encrypt_password(data.password) if data.password else None
    
    property_supplier.updated_at = datetime.utcnow()
    db.save_property_supplier(property_supplier)
    
    supplier = db.get_supplier(property_supplier.supplier_id)
    return {
        "id": property_supplier.id,
        "supplier": supplier,
        "property_id": property_supplier.property_id,
        "supplier_id": property_supplier.supplier_id,
        "has_credentials": bool(property_supplier.username and property_supplier.password_hash),
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
    if current_user.role != UserRole.ADMIN and prop.landlord_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    property_supplier = db.get_property_supplier(property_supplier_id)
    if not property_supplier:
        raise HTTPException(status_code=404, detail="Property supplier not found")
    if property_supplier.property_id != property_id:
        raise HTTPException(status_code=400, detail="Property supplier does not belong to this property")
    
    db.delete_property_supplier(property_supplier_id)
    return {"status": "deleted"}

