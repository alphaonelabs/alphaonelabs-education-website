from base64 import urlsafe_b64decode, urlsafe_b64encode
from cryptography.fernet import Fernet
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

def get_encryption_key():
    """
    Get the encryption key from settings or environment variable.
    If not available, generate a new one (but this should be avoided in production).
    """
    if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY:
        key = settings.ENCRYPTION_KEY
        # If the key is provided as a string, ensure it's properly formatted
        if isinstance(key, str):
            # Add padding if needed
            key = key.encode()
            padding = b'=' * (4 - (len(key) % 4))
            return urlsafe_b64decode(key + padding)
        return key
    
    # Fallback - generate a key
    # NOTE: This should only happen in development. In production, a key should be
    # properly configured to avoid data loss when the server restarts.
    logger.warning("Generating temporary encryption key. This should NOT happen in production!")
    return Fernet.generate_key()

# Get or create the encryption key
ENCRYPTION_KEY = get_encryption_key()
FERNET = Fernet(ENCRYPTION_KEY)

def encrypt(text):
    """
    Encrypt the given text.
    """
    if text is None:
        return None
    
    if isinstance(text, str):
        text = text.encode('utf-8')
    
    encrypted_data = FERNET.encrypt(text)
    return urlsafe_b64encode(encrypted_data).decode('ascii')

def decrypt(encrypted_text):
    """
    Decrypt the given encrypted text.
    """
    if encrypted_text is None:
        return None
    
    if isinstance(encrypted_text, str):
        encrypted_text = encrypted_text.encode('ascii')
    
    try:
        decrypted_data = FERNET.decrypt(urlsafe_b64decode(encrypted_text))
        return decrypted_data.decode('utf-8')
    except Exception as e:
        logger.error(f"Error decrypting data: {e}")
        # Return original value if decryption fails
        return None 