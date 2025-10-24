"""
Management command to encrypt existing user data in production.

This command safely migrates existing user data to encrypted fields.
It handles the transition from plain text to encrypted data without data loss.

Usage:
    python manage.py encrypt_user_data [--dry-run] [--batch-size=1000]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from web.encryption_fields import encrypt_value
from web.models import UserEncryption
import logging

User = get_user_model()

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Encrypt existing user data using UserEncryption model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be encrypted without making changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of users to process in each batch (default: 1000)',
        )
        parser.add_argument(
            '--fields',
            nargs='+',
            default=['first_name', 'last_name', 'email'],
            help='Fields to encrypt (default: first_name, last_name, email)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        fields_to_encrypt = options['fields']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Validate fields
        valid_fields = ['first_name', 'last_name', 'email']
        for field in fields_to_encrypt:
            if field not in valid_fields:
                raise CommandError(f"Invalid field '{field}'. Valid fields: {valid_fields}")
        
        # Get total count
        total_users = User.objects.count()
        if total_users == 0:
            self.stdout.write('No users found to encrypt.')
            return
        
        self.stdout.write(f'Found {total_users} users to process')
        
        # Process users in batches
        processed = 0
        errors = 0
        
        for offset in range(0, total_users, batch_size):
            batch_users = User.objects.all()[offset:offset + batch_size]
            batch_num = (offset // batch_size) + 1
            
            self.stdout.write(f'Processing batch {batch_num} ({len(batch_users)} users)')
            
            for user in batch_users:
                try:
                    if not dry_run:
                        self._encrypt_user_fields(user, fields_to_encrypt)
                    else:
                        self._show_user_encryption(user, fields_to_encrypt)
                    
                    processed += 1
                    
                    if processed % 100 == 0:
                        self.stdout.write(f'Processed {processed}/{total_users} users')
                        
                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing user {user.id}: {e}')
                    self.stdout.write(
                        self.style.ERROR(f'Error processing user {user.id}: {e}')
                    )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Encryption Summary:')
        self.stdout.write(f'Total users: {total_users}')
        self.stdout.write(f'Processed: {processed}')
        self.stdout.write(f'Errors: {errors}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN COMPLETE - No changes were made')
            )
        else:
            if errors == 0:
                self.stdout.write(
                    self.style.SUCCESS('All users encrypted successfully!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Completed with {errors} errors. Check logs for details.')
                )

    def _encrypt_user_fields(self, user, fields_to_encrypt):
        """Encrypt specified fields for a user using UserEncryption model."""
        with transaction.atomic():
            # Get or create UserEncryption instance
            user_encryption, created = UserEncryption.objects.get_or_create(
                user=user,
                defaults={
                    'encrypted_first_name': '',
                    'encrypted_last_name': '',
                    'encrypted_email': ''
                }
            )
            
            for field_name in fields_to_encrypt:
                if hasattr(user, field_name):
                    current_value = getattr(user, field_name)
                    
                    # Only encrypt if the value is not empty and not already encrypted
                    if current_value and not self._is_encrypted(current_value):
                        try:
                            encrypted_value = encrypt_value(current_value)
                            # Store in UserEncryption model
                            if field_name == 'first_name':
                                user_encryption.encrypted_first_name = encrypted_value
                            elif field_name == 'last_name':
                                user_encryption.encrypted_last_name = encrypted_value
                            elif field_name == 'email':
                                user_encryption.encrypted_email = encrypted_value
                        except Exception as e:
                            logger.error(f'Failed to encrypt {field_name} for user {user.id}: {e}')
                            raise
            
            user_encryption.save()

    def _show_user_encryption(self, user, fields_to_encrypt):
        """Show what would be encrypted for a user (dry run)."""
        for field_name in fields_to_encrypt:
            if hasattr(user, field_name):
                current_value = getattr(user, field_name)
                if current_value and not self._is_encrypted(current_value):
                    self.stdout.write(f'  User {user.id}: {field_name} would be encrypted')

    def _is_encrypted(self, value):
        """
        Check if a value is already encrypted.
        
        This is a simple heuristic - encrypted values are typically longer
        and contain base64 characters. This helps avoid double-encryption.
        """
        if not value:
            return False
        
        # Simple heuristic: encrypted values are typically much longer
        # and contain base64 characters
        if len(value) > 100 and all(c.isalnum() or c in '+/=' for c in value):
            return True
        
        return False