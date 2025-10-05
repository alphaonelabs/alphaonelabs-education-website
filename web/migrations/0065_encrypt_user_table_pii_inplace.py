"""
Migration to encrypt User PII data in-place in the auth_user table.

This migration encrypts existing User data (first_name, last_name, email) 
in the database without changing the table structure or requiring a custom User model.
"""

from django.db import migrations
from cryptography.fernet import Fernet


def encrypt_user_pii(apps, schema_editor):
    """
    Encrypt existing User PII data in the auth_user table.
    """
    from django.conf import settings
    
    User = apps.get_model('auth', 'User')
    
    # Get encryption key
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode('utf-8')
    fernet = Fernet(key)
    
    users = User.objects.all()
    count = 0
    
    for user in users:
        updated = False
        
        # Encrypt first_name if not already encrypted
        if user.first_name:
            try:
                # Try to decrypt - if it succeeds, it's already encrypted
                fernet.decrypt(user.first_name.encode('utf-8'))
            except Exception:
                # Not encrypted yet, encrypt it
                encrypted = fernet.encrypt(user.first_name.encode('utf-8'))
                user.first_name = encrypted.decode('utf-8')
                updated = True
        
        # Encrypt last_name if not already encrypted
        if user.last_name:
            try:
                fernet.decrypt(user.last_name.encode('utf-8'))
            except Exception:
                encrypted = fernet.encrypt(user.last_name.encode('utf-8'))
                user.last_name = encrypted.decode('utf-8')
                updated = True
        
        # Encrypt email if not already encrypted
        if user.email:
            try:
                fernet.decrypt(user.email.encode('utf-8'))
            except Exception:
                encrypted = fernet.encrypt(user.email.encode('utf-8'))
                user.email = encrypted.decode('utf-8')
                updated = True
        
        if updated:
            user.save()
            count += 1
    
    print(f"Encrypted PII for {count} users")


def decrypt_user_pii(apps, schema_editor):
    """
    Reverse migration: decrypt User PII data.
    """
    from django.conf import settings
    
    User = apps.get_model('auth', 'User')
    
    # Get encryption key
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode('utf-8')
    fernet = Fernet(key)
    
    users = User.objects.all()
    count = 0
    
    for user in users:
        updated = False
        
        # Decrypt first_name if encrypted
        if user.first_name:
            try:
                decrypted = fernet.decrypt(user.first_name.encode('utf-8'))
                user.first_name = decrypted.decode('utf-8')
                updated = True
            except Exception:
                # Already plaintext
                pass
        
        # Decrypt last_name if encrypted
        if user.last_name:
            try:
                decrypted = fernet.decrypt(user.last_name.encode('utf-8'))
                user.last_name = decrypted.decode('utf-8')
                updated = True
            except Exception:
                pass
        
        # Decrypt email if encrypted
        if user.email:
            try:
                decrypted = fernet.decrypt(user.email.encode('utf-8'))
                user.email = decrypted.decode('utf-8')
                updated = True
            except Exception:
                pass
        
        if updated:
            user.save()
            count += 1
    
    print(f"Decrypted PII for {count} users")


class Migration(migrations.Migration):
    
    dependencies = [
        ('web', '0064_add_encrypted_user_pii'),
    ]
    
    operations = [
        migrations.RunPython(encrypt_user_pii, decrypt_user_pii),
    ]
