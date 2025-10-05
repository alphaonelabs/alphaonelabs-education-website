"""
Custom User model with encrypted PII fields.

This custom user model extends Django's AbstractUser and encrypts
sensitive personal information (first_name, last_name, email) at rest.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from web.encryption import CustomEncryptedCharField, CustomEncryptedEmailField


class User(AbstractUser):
    """
    Custom User model with encrypted PII fields.
    
    This model extends Django's AbstractUser and replaces the standard
    first_name, last_name, and email fields with encrypted versions.
    """

    # Override the default fields with encrypted versions
    first_name = CustomEncryptedCharField(
        max_length=255,
        blank=True,
        verbose_name="first name",
        help_text="Encrypted first name",
    )
    last_name = CustomEncryptedCharField(
        max_length=255,
        blank=True,
        verbose_name="last name",
        help_text="Encrypted last name",
    )
    email = CustomEncryptedEmailField(
        blank=True,
        verbose_name="email address",
        help_text="Encrypted email address",
    )

    class Meta:
        db_table = "auth_user"  # Keep the same table name to avoid migration issues
        verbose_name = "user"
        verbose_name_plural = "users"
        swappable = "AUTH_USER_MODEL"

    def __str__(self):
        return self.username
