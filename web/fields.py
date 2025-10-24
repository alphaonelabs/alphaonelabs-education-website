"""
Encrypted field implementations for Django models.

Uses Fernet symmetric encryption to protect sensitive data at rest.
"""

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class EncryptedTextField(models.TextField):
    """
    A TextField that automatically encrypts data before saving
    and decrypts data when loading from the database.

    Uses the SECURE_MESSAGE_KEY from settings for encryption.
    """

    description = "Encrypted text field"

    def __init__(self, *args, **kwargs):
        # Encrypted data is typically larger than plaintext
        # Set a reasonable max_length if not specified
        if "max_length" not in kwargs:
            kwargs["max_length"] = 500
        super().__init__(*args, **kwargs)
        self._fernet = None

    @property
    def fernet(self):
        """Lazy initialize Fernet cipher."""
        if self._fernet is None:
            key = settings.SECURE_MESSAGE_KEY
            if isinstance(key, str):
                key = key.encode("utf-8")
            self._fernet = Fernet(key)
        return self._fernet

    def get_prep_value(self, value):
        """Encrypt the value before saving to database."""
        if value is None or value == "":
            return value
        # If already encrypted (starts with gAAAAA which is Fernet token prefix), don't re-encrypt
        if isinstance(value, str) and value.startswith("gAAAAA"):
            return value
        # Encrypt the value
        try:
            encrypted = self.fernet.encrypt(value.encode("utf-8"))
            return encrypted.decode("utf-8")
        except Exception:
            # If encryption fails, return empty string rather than raising
            return ""

    def from_db_value(self, value, expression, connection):
        """Decrypt the value when loading from database."""
        if value is None or value == "":
            return value
        # Decrypt the value
        try:
            decrypted = self.fernet.decrypt(value.encode("utf-8"))
            return decrypted.decode("utf-8")
        except Exception:
            # If decryption fails, return empty string
            return ""

    def to_python(self, value):
        """Convert the value to Python string."""
        if value is None or value == "":
            return value
        # If it's already a string (decrypted), return as is
        if isinstance(value, str):
            # Try to decrypt if it looks encrypted
            if value.startswith("gAAAAA"):
                try:
                    decrypted = self.fernet.decrypt(value.encode("utf-8"))
                    return decrypted.decode("utf-8")
                except Exception:
                    return ""
            return value
        return str(value)


class EncryptedCharField(models.CharField):
    """
    A CharField that automatically encrypts data before saving
    and decrypts data when loading from the database.

    Uses the SECURE_MESSAGE_KEY from settings for encryption.
    """

    description = "Encrypted char field"

    def __init__(self, *args, **kwargs):
        # Encrypted data is typically larger than plaintext
        # Increase max_length to accommodate encrypted data
        if "max_length" in kwargs:
            # Fernet tokens are approximately 50% larger + base overhead
            kwargs["max_length"] = max(kwargs["max_length"] * 2, 255)
        else:
            kwargs["max_length"] = 255
        super().__init__(*args, **kwargs)
        self._fernet = None

    @property
    def fernet(self):
        """Lazy initialize Fernet cipher."""
        if self._fernet is None:
            key = settings.SECURE_MESSAGE_KEY
            if isinstance(key, str):
                key = key.encode("utf-8")
            self._fernet = Fernet(key)
        return self._fernet

    def get_prep_value(self, value):
        """Encrypt the value before saving to database."""
        if value is None or value == "":
            return value
        # If already encrypted (starts with gAAAAA which is Fernet token prefix), don't re-encrypt
        if isinstance(value, str) and value.startswith("gAAAAA"):
            return value
        # Encrypt the value
        try:
            encrypted = self.fernet.encrypt(value.encode("utf-8"))
            return encrypted.decode("utf-8")
        except Exception:
            # If encryption fails, return empty string rather than raising
            return ""

    def from_db_value(self, value, expression, connection):
        """Decrypt the value when loading from database."""
        if value is None or value == "":
            return value
        # Decrypt the value
        try:
            decrypted = self.fernet.decrypt(value.encode("utf-8"))
            return decrypted.decode("utf-8")
        except Exception:
            # If decryption fails, return empty string
            return ""

    def to_python(self, value):
        """Convert the value to Python string."""
        if value is None or value == "":
            return value
        # If it's already a string (decrypted), return as is
        if isinstance(value, str):
            # Try to decrypt if it looks encrypted
            if value.startswith("gAAAAA"):
                try:
                    decrypted = self.fernet.decrypt(value.encode("utf-8"))
                    return decrypted.decode("utf-8")
                except Exception:
                    return ""
            return value
        return str(value)


class EncryptedEmailField(models.EmailField):
    """
    An EmailField that automatically encrypts data before saving
    and decrypts data when loading from the database.

    Uses the SECURE_MESSAGE_KEY from settings for encryption.
    """

    description = "Encrypted email field"

    def __init__(self, *args, **kwargs):
        # Encrypted data is typically larger than plaintext
        # Email max_length is usually 254, make it larger for encryption
        kwargs["max_length"] = 500
        super().__init__(*args, **kwargs)
        self._fernet = None

    @property
    def fernet(self):
        """Lazy initialize Fernet cipher."""
        if self._fernet is None:
            key = settings.SECURE_MESSAGE_KEY
            if isinstance(key, str):
                key = key.encode("utf-8")
            self._fernet = Fernet(key)
        return self._fernet

    def get_prep_value(self, value):
        """Encrypt the value before saving to database."""
        if value is None or value == "":
            return value
        # If already encrypted (starts with gAAAAA which is Fernet token prefix), don't re-encrypt
        if isinstance(value, str) and value.startswith("gAAAAA"):
            return value
        # Encrypt the value
        try:
            encrypted = self.fernet.encrypt(value.encode("utf-8"))
            return encrypted.decode("utf-8")
        except Exception:
            # If encryption fails, return empty string rather than raising
            return ""

    def from_db_value(self, value, expression, connection):
        """Decrypt the value when loading from database."""
        if value is None or value == "":
            return value
        # Decrypt the value
        try:
            decrypted = self.fernet.decrypt(value.encode("utf-8"))
            return decrypted.decode("utf-8")
        except Exception:
            # If decryption fails, return empty string
            return ""

    def to_python(self, value):
        """Convert the value to Python string."""
        if value is None or value == "":
            return value
        # If it's already a string (decrypted), return as is
        if isinstance(value, str):
            # Try to decrypt if it looks encrypted
            if value.startswith("gAAAAA"):
                try:
                    decrypted = self.fernet.decrypt(value.encode("utf-8"))
                    return decrypted.decode("utf-8")
                except Exception:
                    return ""
            return value
        return str(value)
