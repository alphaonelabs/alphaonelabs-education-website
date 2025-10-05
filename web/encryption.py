"""
Encryption utilities for personal data fields.

This module provides encrypted field types for sensitive personal data.
The encryption uses the FIELD_ENCRYPTION_KEY from settings (same as MESSAGE_ENCRYPTION_KEY).
"""

import json

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedEmailField, EncryptedTextField

# Re-export the encrypted fields for easy import
CustomEncryptedCharField = EncryptedCharField
CustomEncryptedEmailField = EncryptedEmailField
CustomEncryptedTextField = EncryptedTextField


class CustomEncryptedJSONField(models.TextField):
    """
    Encrypted JSONField that encrypts the entire JSON structure.
    Uses the FIELD_ENCRYPTION_KEY from settings for encryption.
    Stores encrypted data as text in the database.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fernet = None

    def get_fernet(self):
        """Lazy initialization of Fernet cipher."""
        if self.fernet is None:
            key = settings.FIELD_ENCRYPTION_KEY
            if isinstance(key, str):
                key = key.encode("utf-8")
            self.fernet = Fernet(key)
        return self.fernet

    def get_prep_value(self, value):
        """Encrypt the JSON data before saving to database."""
        if value is None:
            return None

        # Convert to JSON string first
        if isinstance(value, str):
            json_str = value
        else:
            json_str = json.dumps(value)

        # Encrypt the JSON string
        fernet = self.get_fernet()
        encrypted_data = fernet.encrypt(json_str.encode("utf-8"))
        return encrypted_data.decode("utf-8")

    def from_db_value(self, value, expression, connection):
        """Decrypt the JSON data when loading from database."""
        if value is None:
            return None

        try:
            # Try to decrypt - if it fails, assume it's plaintext (for migration)
            fernet = self.get_fernet()
            decrypted_data = fernet.decrypt(value.encode("utf-8"))
            json_str = decrypted_data.decode("utf-8")
            return json.loads(json_str)
        except Exception:
            # If decryption fails, treat as plaintext (backward compatibility)
            try:
                return json.loads(value)
            except Exception:
                return value

    def to_python(self, value):
        """Convert the value to Python object."""
        if value is None:
            return None

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                # Try to decrypt first
                fernet = self.get_fernet()
                decrypted_data = fernet.decrypt(value.encode("utf-8"))
                json_str = decrypted_data.decode("utf-8")
                return json.loads(json_str)
            except Exception:
                # If decryption fails, treat as plaintext
                try:
                    return json.loads(value)
                except Exception:
                    return value

        return value
