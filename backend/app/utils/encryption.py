"""Encryption utilities for password storage."""
import os
import base64
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Ensure dotenv is loaded before reading environment variables
from dotenv import load_dotenv
load_dotenv()

# Encryption key for passwords (in production, use a secure key from env)
# Fernet keys must be 32 bytes when base64-decoded (44 characters when base64-encoded)
EBLOC_ENCRYPTION_KEY = os.getenv("EBLOC_ENCRYPTION_KEY")
if EBLOC_ENCRYPTION_KEY:
    try:
        # Validate the key format
        decoded_key = base64.urlsafe_b64decode(EBLOC_ENCRYPTION_KEY)
        if len(decoded_key) != 32:
            raise ValueError(f"Invalid key length: {len(decoded_key)} bytes (expected 32)")
        fernet = Fernet(EBLOC_ENCRYPTION_KEY.encode())
        logger.info("[E-Bloc] Using encryption key from environment")
    except Exception as e:
        logger.warning(f"[E-Bloc] Invalid encryption key in environment: {e}. Generating new key.")
        # If key is invalid, generate a new one
        EBLOC_ENCRYPTION_KEY = Fernet.generate_key().decode()
        fernet = Fernet(EBLOC_ENCRYPTION_KEY.encode())
        logger.warning(f"[E-Bloc] Generated new encryption key. Save this to .env: EBLOC_ENCRYPTION_KEY={EBLOC_ENCRYPTION_KEY}")
else:
    # No key in environment, generate a new one
    EBLOC_ENCRYPTION_KEY = Fernet.generate_key().decode()
    fernet = Fernet(EBLOC_ENCRYPTION_KEY.encode())
    logger.warning(f"[E-Bloc] No encryption key in environment. Generated new key. Save this to .env: EBLOC_ENCRYPTION_KEY={EBLOC_ENCRYPTION_KEY}")


def encrypt_password(password: str) -> str:
    """Encrypt password for suppliers (needs to be retrievable)"""
    return fernet.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """Decrypt password for suppliers"""
    try:
        return fernet.decrypt(encrypted.encode()).decode()
    except Exception as e:
        logger.error(f"[E-Bloc] Error decrypting password: {e}", exc_info=True)
        # If decryption fails, it might be because the encryption key changed
        # This can happen if the server restarted and EBLOC_ENCRYPTION_KEY wasn't set in env
        raise ValueError(f"Failed to decrypt password. The encryption key may have changed. Please reconfigure your E-bloc credentials. Error: {str(e)}")

