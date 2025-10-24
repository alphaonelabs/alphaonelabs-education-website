"""
Encryption field utilities for sensitive user data.

This module provides encrypted field implementations that maintain
compatibility with Django's ORM while encrypting sensitive data at rest.
"""

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


class EncryptedTextField(models.TextField):
    """
    A TextField that automatically encrypts data before saving and decrypts when retrieving.
    
    Uses Fernet encryption with the master key from settings.
    Maintains compatibility with Django's ORM and admin interface.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = Fernet(settings.SECURE_MESSAGE_KEY)
    
    def from_db_value(self, value, expression, connection):
        """Decrypt the value when retrieving from database."""
        if value is None:
            return value
        try:
            return self._fernet.decrypt(value.encode('utf-8')).decode('utf-8')
        except Exception:
            # If decryption fails, return the raw value (for migration compatibility)
            return value
    
    def to_python(self, value):
        """Convert the value to Python object."""
        if value is None:
            return value
        if isinstance(value, str):
            return value
        return str(value)
    
    def get_prep_value(self, value):
        """Encrypt the value before saving to database."""
        if value is None:
            return value
        try:
            return self._fernet.encrypt(str(value).encode('utf-8')).decode('utf-8')
        except Exception as e:
            raise ValidationError(f"Encryption failed: {e}")
    
    def value_to_string(self, obj):
        """Convert the field value to string for serialization."""
        value = self.value_from_object(obj)
        return self.get_prep_value(value)


class EncryptedCharField(models.CharField):
    """
    A CharField that automatically encrypts data before saving and decrypts when retrieving.
    
    Uses Fernet encryption with the master key from settings.
    Maintains compatibility with Django's ORM and admin interface.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = Fernet(settings.SECURE_MESSAGE_KEY)
    
    def from_db_value(self, value, expression, connection):
        """Decrypt the value when retrieving from database."""
        if value is None:
            return value
        try:
            return self._fernet.decrypt(value.encode('utf-8')).decode('utf-8')
        except Exception:
            # If decryption fails, return the raw value (for migration compatibility)
            return value
    
    def to_python(self, value):
        """Convert the value to Python object."""
        if value is None:
            return value
        if isinstance(value, str):
            return value
        return str(value)
    
    def get_prep_value(self, value):
        """Encrypt the value before saving to database."""
        if value is None:
            return value
        try:
            return self._fernet.encrypt(str(value).encode('utf-8')).decode('utf-8')
        except Exception as e:
            raise ValidationError(f"Encryption failed: {e}")
    
    def value_to_string(self, obj):
        """Convert the field value to string for serialization."""
        value = self.value_from_object(obj)
        return self.get_prep_value(value)


def encrypt_value(value):
    """
    Utility function to encrypt a value using the master key.
    
    Args:
        value (str): The value to encrypt
        
    Returns:
        str: The encrypted value as a string
        
    Raises:
        ValidationError: If encryption fails
    """
    if value is None:
        return value
    try:
        return Fernet(settings.SECURE_MESSAGE_KEY).encrypt(str(value).encode('utf-8')).decode('utf-8')
    except Exception as e:
        raise ValidationError(f"Encryption failed: {e}")


def decrypt_value(value):
    """
    Utility function to decrypt a value using the master key.
    
    Args:
        value (str): The encrypted value as a string
        
    Returns:
        str: The decrypted value as a string
        
    Raises:
        ValidationError: If decryption fails
    """
    if value is None:
        return value
    try:
        return Fernet(settings.SECURE_MESSAGE_KEY).decrypt(value.encode('utf-8')).decode('utf-8')
    except Exception as e:
        raise ValidationError(f"Decryption failed: {e}")
