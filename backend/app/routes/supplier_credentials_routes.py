"""User-supplier credential management routes."""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from app.models import (
    UserSupplierCredential, UserSupplierCredentialCreate, UserSupplierCredentialUpdate,
    TokenData, Supplier
)
from app.auth import require_landlord
from app.database import db
from app.utils.encryption import encrypt_password, decrypt_password

router = APIRouter(tags=["supplier-credentials"])
logger = logging.getLogger(__name__)


@router.get("/supplier-credentials")
async def list_user_supplier_credentials(current_user: TokenData = Depends(require_landlord)):
    """List all supplier credentials for the current user"""
    credentials = db.list_user_supplier_credentials(current_user.user_id)
    
    # Enrich with supplier details
    result = []
    for cred in credentials:
        supplier = db.get_supplier(cred.supplier_id)
        if supplier:
            result.append({
                "id": cred.id,
                "supplier": supplier,
                "user_id": cred.user_id,
                "supplier_id": cred.supplier_id,
                "has_credentials": bool(cred.username and cred.password_hash),
                "created_at": cred.created_at,
                "updated_at": cred.updated_at,
            })
    return result


@router.post("/supplier-credentials", status_code=201)
async def create_user_supplier_credential(
    data: UserSupplierCredentialCreate, current_user: TokenData = Depends(require_landlord)
):
    """Create or update supplier credentials for the current user"""
    supplier = db.get_supplier(data.supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Check if credential already exists
    existing = db.get_user_supplier_credential_by_user_supplier(current_user.user_id, data.supplier_id)
    
    if existing:
        # Update existing credential
        if data.username is not None:
            existing.username = encrypt_password(data.username) if data.username else None
        if data.password is not None:
            existing.password_hash = encrypt_password(data.password) if data.password else None
        existing.updated_at = datetime.utcnow()
        credential = db.save_user_supplier_credential(existing)
    else:
        # Create new credential
        credential = UserSupplierCredential(
            user_id=current_user.user_id,
            supplier_id=data.supplier_id,
            username=encrypt_password(data.username) if data.username else None,
            password_hash=encrypt_password(data.password) if data.password else None,
        )
        credential = db.save_user_supplier_credential(credential)
    
    return {
        "id": credential.id,
        "supplier": supplier,
        "user_id": credential.user_id,
        "supplier_id": credential.supplier_id,
        "has_credentials": bool(credential.username and credential.password_hash),
        "created_at": credential.created_at,
        "updated_at": credential.updated_at,
    }


@router.put("/supplier-credentials/{credential_id}")
async def update_user_supplier_credential(
    credential_id: str,
    data: UserSupplierCredentialUpdate,
    current_user: TokenData = Depends(require_landlord),
):
    """Update supplier credentials for the current user"""
    credential = db.get_user_supplier_credential(credential_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    if credential.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update credentials if provided
    if data.username is not None:
        credential.username = encrypt_password(data.username) if data.username else None
    if data.password is not None:
        credential.password_hash = encrypt_password(data.password) if data.password else None
    
    credential.updated_at = datetime.utcnow()
    credential = db.save_user_supplier_credential(credential)
    
    supplier = db.get_supplier(credential.supplier_id)
    return {
        "id": credential.id,
        "supplier": supplier,
        "user_id": credential.user_id,
        "supplier_id": credential.supplier_id,
        "has_credentials": bool(credential.username and credential.password_hash),
        "created_at": credential.created_at,
        "updated_at": credential.updated_at,
    }


@router.delete("/supplier-credentials/{credential_id}")
async def delete_user_supplier_credential(
    credential_id: str, current_user: TokenData = Depends(require_landlord)
):
    """Delete supplier credentials for the current user"""
    credential = db.get_user_supplier_credential(credential_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    if credential.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete_user_supplier_credential(credential_id)
    return {"status": "deleted"}

