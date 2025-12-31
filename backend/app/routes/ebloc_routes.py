"""Ebloc integration routes."""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
import httpx
from app.models import (
    EblocConfigCreate, TokenData, UserRole, Supplier, PropertySupplier,
    UserSupplierCredential, BillType
)
from app.auth import require_landlord
from app.database import db
from app.utils.encryption import encrypt_password, decrypt_password

router = APIRouter(prefix="/ebloc", tags=["ebloc"])
logger = logging.getLogger(__name__)


@router.post("/discover")
async def discover_ebloc_properties(
    data: dict, current_user: TokenData = Depends(require_landlord)
):
    """Discover properties from e-bloc account"""
    username = data.get("username")
    password = data.get("password")
    logger.info(f"[E-Bloc] Discovery request from user {current_user.user_id}, username: {username}")
    
    if not username or not password:
        logger.warning("[E-Bloc] Missing username or password")
        raise HTTPException(status_code=400, detail="Username and password required")
    
    from app.ebloc_scraper import EblocScraper, EblocProperty
    
    # Enable debug mode to save HTML for inspection
    scraper = EblocScraper(debug=True)
    try:
        logger.info("[E-Bloc] Attempting login...")
        logged_in = await scraper.login(username, password)
        if not logged_in:
            logger.warning("[E-Bloc] Login failed - invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid e-bloc credentials")
        
        logger.info("[E-Bloc] Login successful, fetching properties...")
        properties = await scraper.get_available_properties()
        logger.info(f"[E-Bloc] Found {len(properties)} properties")
        
        result = {
            "status": "success",
            "properties": [
                {
                    "page_id": p.page_id,
                    "name": p.name,
                    "address": p.address or p.name,
                    "url": p.url  # Include the e-bloc URL
                }
                for p in properties
            ]
        }
        logger.info(f"[E-Bloc] Returning {len(result['properties'])} properties")
        return result
    
    except HTTPException:
        raise
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError) as e:
        logger.warning(f"[E-Bloc] Network error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Network connection error. Please check your internet connection and try again in a moment."
        )
    except Exception as e:
        logger.error(f"[E-Bloc] Discovery error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error discovering properties: {str(e)}")
    finally:
        await scraper.close()


@router.post("/configure")
async def configure_ebloc(
    data: EblocConfigCreate, current_user: TokenData = Depends(require_landlord)
):
    from app.ebloc_scraper import EblocScraper
    
    logger.info(f"[E-Bloc] Configure request from user {current_user.user_id}")
    
    # Verify credentials by attempting login
    scraper = EblocScraper()
    try:
        logged_in = await scraper.login(data.username, data.password)
        if not logged_in:
            raise HTTPException(status_code=401, detail="Invalid e-bloc credentials")
    except HTTPException:
        raise
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError) as e:
        logger.warning(f"[E-Bloc] Network error during credential verification: {e}")
        raise HTTPException(
            status_code=503,
            detail="Network connection error. Please check your internet connection and try again in a moment."
        )
    except Exception as e:
        logger.error(f"[E-Bloc] Login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error verifying credentials: {str(e)}")
    finally:
        await scraper.close()
    
    # Get user and update ebloc credentials
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Encrypt password (not hash, since we need to retrieve it for scraping)
    try:
        password_encrypted = encrypt_password(data.password)
        user.ebloc_username = data.username
        user.ebloc_password_hash = password_encrypted
        db.save_user(user)
        logger.info(f"[E-Bloc] Credentials saved for user {current_user.user_id}")
        
        # Verify the password was saved correctly by trying to decrypt it
        try:
            test_decrypt = decrypt_password(password_encrypted)
            if test_decrypt != data.password:
                logger.error(f"[E-Bloc] Password encryption/decryption verification failed!")
                raise HTTPException(status_code=500, detail="Password encryption verification failed")
        except ValueError as ve:
            # Re-raise ValueError as HTTPException with better message
            raise HTTPException(status_code=500, detail=str(ve))
        except Exception as e:
            logger.error(f"[E-Bloc] Password verification error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Password encryption error: {str(e)}")
        
        return {"status": "configured", "message": "E-bloc credentials saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[E-Bloc] Error saving credentials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error saving credentials: {str(e)}")


@router.get("/config")
async def get_ebloc_config(current_user: TokenData = Depends(require_landlord)):
    """Get e-bloc configuration for current user (including decrypted password for form)"""
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.ebloc_username:
        return {"username": None, "password": None, "configured": False}
    
    # Decrypt password for form (since it's encrypted, not hashed, we can retrieve it)
    password = None
    if user.ebloc_password_hash:
        try:
            password = decrypt_password(user.ebloc_password_hash)
        except Exception as e:
            logger.warning(f"[E-Bloc] Could not decrypt password for user {current_user.user_id}: {e}")
            # Password might be encrypted with a different key (e.g., server restarted with new key)
            # Return None for password - user will need to re-enter it
            password = None
    
    return {
        "username": user.ebloc_username,
        "password": password,
        "configured": True,
    }


@router.post("/setup-supplier-for-properties")
async def setup_ebloc_supplier_for_properties(
    property_ids: list[str], current_user: TokenData = Depends(require_landlord)
):
    """Automatically set up E-bloc supplier and credentials for imported properties"""
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.ebloc_username or not user.ebloc_password_hash:
        raise HTTPException(status_code=400, detail="E-bloc credentials not configured")
    
    # Find or create E-bloc supplier
    ebloc_supplier = db.get_supplier_by_name("E-bloc")
    if not ebloc_supplier:
        ebloc_supplier = Supplier(
            name="E-bloc",
            bill_type=BillType.EBLOC,
            has_api=True,
        )
        db.save_supplier(ebloc_supplier)
        logger.info(f"[E-Bloc] Created E-bloc supplier: {ebloc_supplier.id}")
    
    # Create or update user supplier credentials
    existing_credential = db.get_user_supplier_credential_by_user_supplier(
        current_user.user_id, ebloc_supplier.id
    )
    
    try:
        password = decrypt_password(user.ebloc_password_hash)
    except Exception as e:
        logger.error(f"[E-Bloc] Error decrypting password: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error decrypting E-bloc password")
    
    if existing_credential:
        # Update existing credential
        existing_credential.username = encrypt_password(user.ebloc_username)
        existing_credential.password_hash = encrypt_password(password)
        existing_credential.updated_at = datetime.utcnow()
        credential = db.save_user_supplier_credential(existing_credential)
        logger.info(f"[E-Bloc] Updated existing credential for user {current_user.user_id}")
    else:
        # Create new credential
        credential = UserSupplierCredential(
            user_id=current_user.user_id,
            supplier_id=ebloc_supplier.id,
            username=encrypt_password(user.ebloc_username),
            password_hash=encrypt_password(password),
        )
        credential = db.save_user_supplier_credential(credential)
        logger.info(f"[E-Bloc] Created new credential for user {current_user.user_id}")
    
    # Add E-bloc supplier to all specified properties
    added_count = 0
    for property_id in property_ids:
        prop = db.get_property(property_id)
        if not prop:
            logger.warning(f"[E-Bloc] Property {property_id} not found, skipping")
            continue
        
        if prop.landlord_id != current_user.user_id:
            logger.warning(f"[E-Bloc] Property {property_id} does not belong to user {current_user.user_id}, skipping")
            continue
        
        # Check if already added
        existing_property_suppliers = db.list_property_suppliers(property_id)
        if any(ps.supplier_id == ebloc_supplier.id for ps in existing_property_suppliers):
            logger.info(f"[E-Bloc] E-bloc supplier already added to property {property_id}, skipping")
            continue
        
        # Add supplier to property
        property_supplier = PropertySupplier(
            property_id=property_id,
            supplier_id=ebloc_supplier.id,
            credential_id=credential.id,
        )
        db.save_property_supplier(property_supplier)
        added_count += 1
        logger.info(f"[E-Bloc] Added E-bloc supplier to property {property_id}")
    
    return {
        "status": "success",
        "supplier_id": ebloc_supplier.id,
        "credential_id": credential.id,
        "properties_updated": added_count,
    }

