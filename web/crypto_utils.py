"""
Utility functions for encrypting and decrypting PII (Personally Identifiable Information)
using the cryptography library's Fernet symmetric encryption.
"""

import base64

# Handle cryptography import for both runtime and linting
try:
    from cryptography.fernet import Fernet
except ImportError:
    # For type checking only - the real import will succeed at runtime
    class Fernet:  # type: ignore
        """Stub class for cryptography.fernet.Fernet"""

        def __init__(self, key):
            pass

        def encrypt(self, data):
            return b""

        def decrypt(self, token):
            return b""


from django.conf import settings
from django.db import models


# Generate a fixed key from the SECRET_KEY to ensure consistent encryption/decryption
def get_encryption_key():
    """Generate a Fernet key from the Django SECRET_KEY."""
    # Use a fixed subset of the SECRET_KEY to ensure consistent key generation
    key_material = settings.SECRET_KEY[:32].encode()
    # Pad or truncate to exactly 32 bytes as required by Fernet
    key_material = key_material.ljust(32, b"0")[:32]
    return base64.urlsafe_b64encode(key_material)


# Global fernet instance
_fernet = None


def get_fernet():
    """Get or create a Fernet instance for encryption/decryption."""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_encryption_key())
    return _fernet


# Encryption/decryption functions
def encrypt_value(value):
    """Encrypt a value using Fernet symmetric encryption."""
    if value is None or value == "":
        return value

    value_bytes = str(value).encode("utf-8")
    return get_fernet().encrypt(value_bytes).decode("utf-8")


def decrypt_value(value):
    """Decrypt a value that was encrypted using Fernet."""
    if value is None or value == "":
        return value

    try:
        value_bytes = value.encode("utf-8")
        return get_fernet().decrypt(value_bytes).decode("utf-8")
    except Exception:
        return value  # Return original value if decryption fails


# Field classes for models
class EncryptedCharField(models.CharField):
    """CharField that encrypts its contents before saving to the database."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            value = encrypt_value(value)
        return value

    def from_db_value(self, value, expression, connection):
        if value is not None:
            value = decrypt_value(value)
        return value

    def to_python(self, value):
        if isinstance(value, str) and value.startswith("gAAAAA"):  # Likely encrypted
            value = decrypt_value(value)
        return super().to_python(value)


class EncryptedTextField(models.TextField):
    """TextField that encrypts its contents before saving to the database."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            value = encrypt_value(value)
        return value

    def from_db_value(self, value, expression, connection):
        if value is not None:
            value = decrypt_value(value)
        return value

    def to_python(self, value):
        if isinstance(value, str) and value.startswith("gAAAAA"):  # Likely encrypted
            value = decrypt_value(value)
        return super().to_python(value)


class EncryptedEmailField(models.EmailField):
    """EmailField that encrypts its contents before saving to the database."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            value = encrypt_value(value)
        return value

    def from_db_value(self, value, expression, connection):
        if value is not None:
            value = decrypt_value(value)
        return value

    def to_python(self, value):
        if isinstance(value, str) and value.startswith("gAAAAA"):  # Likely encrypted
            value = decrypt_value(value)
        return super().to_python(value)


def anonymize_email(email):
    """
    Convert an email to anonymized form while preserving the domain.
    Example: user@example.com -> u***r@example.com
    """
    if not email or "@" not in email:
        return email

    username, domain = email.split("@", 1)
    if len(username) <= 2:
        anonymized_username = username[0] + "*" * (len(username) - 1)
    else:
        anonymized_username = username[0] + "*" * (len(username) - 2) + username[-1]

    return f"{anonymized_username}@{domain}"
