"""
User PII encryption utilities.

This module provides utilities to encrypt/decrypt User model PII fields
(first_name, last_name, email) in the auth_user table without requiring
a custom User model.
"""

from cryptography.fernet import Fernet
from django.conf import settings


def get_fernet():
    """Get Fernet cipher instance."""
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


def encrypt_user_field(value):
    """
    Encrypt a User field value.

    Args:
        value: The plaintext value to encrypt

    Returns:
        Encrypted value as string, or empty string if value is empty
    """
    if not value:
        return ""

    try:
        fernet = get_fernet()
        # Check if already encrypted
        try:
            fernet.decrypt(value.encode("utf-8"))
            return value  # Already encrypted
        except Exception:
            # Not encrypted, encrypt it
            encrypted = fernet.encrypt(value.encode("utf-8"))
            return encrypted.decode("utf-8")
    except Exception:
        # If encryption fails, return as-is
        return value


def decrypt_user_field(value):
    """
    Decrypt a User field value.

    Args:
        value: The encrypted value to decrypt

    Returns:
        Decrypted value as string, or the original value if not encrypted
    """
    if not value:
        return ""

    try:
        fernet = get_fernet()
        decrypted = fernet.decrypt(value.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        # If decryption fails, return as-is (backward compatibility)
        return value


def get_user_email(user):
    """
    Get decrypted email from User.

    Args:
        user: Django User instance

    Returns:
        Decrypted email address
    """
    return decrypt_user_field(user.email)


def get_user_first_name(user):
    """
    Get decrypted first name from User.

    Args:
        user: Django User instance

    Returns:
        Decrypted first name
    """
    return decrypt_user_field(user.first_name)


def get_user_last_name(user):
    """
    Get decrypted last name from User.

    Args:
        user: Django User instance

    Returns:
        Decrypted last name
    """
    return decrypt_user_field(user.last_name)


def set_user_email(user, email):
    """
    Set encrypted email on User.

    Args:
        user: Django User instance
        email: Email address to encrypt and set
    """
    user.email = encrypt_user_field(email)


def set_user_first_name(user, first_name):
    """
    Set encrypted first name on User.

    Args:
        user: Django User instance
        first_name: First name to encrypt and set
    """
    user.first_name = encrypt_user_field(first_name)


def set_user_last_name(user, last_name):
    """
    Set encrypted last name on User.

    Args:
        user: Django User instance
        last_name: Last name to encrypt and set
    """
    user.last_name = encrypt_user_field(last_name)
