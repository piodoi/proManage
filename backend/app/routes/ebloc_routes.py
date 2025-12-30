"""Ebloc integration routes."""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.models import EblocConfigCreate, TokenData, UserRole
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

