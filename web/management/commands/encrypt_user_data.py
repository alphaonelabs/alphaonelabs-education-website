"""
Management command to encrypt existing user data in production.

This command safely migrates existing user data to encrypted fields.
It handles the transition from plain text to encrypted data without data loss.

Usage:
    python manage.py encrypt_user_data [--dry-run] [--batch-size=1000]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
# encrypt_value no longer needed - EncryptedTextField handles encryption automatically
from web.models import UserEncryption
import logging

User = get_user_model()

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Encrypt existing user data using UserEncryption model. '
        'Use staged rollout: 1) --dry-run, 2) encrypt only, 3) --redact-original'
    )

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
        parser.add_argument(
            '--redact-original',
            action='store_true',
            help='After encrypting into UserEncryption, blank the original User fields',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        fields_to_encrypt = options['fields']
        redact_original = options['redact_original']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        if redact_original:
            self.stdout.write(
                self.style.WARNING(
                    'REDACTION ENABLED - Original User fields will be blanked '
                    'after encryption!'
                )
            )

        # Validate fields
        valid_fields = ['first_name', 'last_name', 'email']
        for field in fields_to_encrypt:
            if field not in valid_fields:
                raise CommandError(
                    f"Invalid field '{field}'. Valid fields: {valid_fields}"
                )

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

            self.stdout.write(
                f'Processing batch {batch_num} ({len(batch_users)} users)'
            )

            for user in batch_users:
                try:
                    if not dry_run:
                        self._encrypt_user_fields(
                            user, fields_to_encrypt, redact_original=redact_original
                        )
                    else:
                        self._show_user_encryption(user, fields_to_encrypt)

                    processed += 1

                    if processed % 100 == 0:
                        self.stdout.write(
                            f'Processed {processed}/{total_users} users'
                        )

                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing user {user.id}: {e}')
                    self.stdout.write(
                        self.style.ERROR(f'Error processing user {user.id}: {e}')
                    )

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Encryption Summary:')
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
                    self.style.WARNING(
                        f'Completed with {errors} errors. Check logs for details.'
                    )
                )

    def _encrypt_user_fields(self, user, fields_to_encrypt, *, redact_original=False):
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

                    # Only persist if non-empty and not already present (idempotent)
                    if current_value and not self._is_encrypted(current_value):
                        # Skip when decrypted value already exists
                        already_set = getattr(
                            user_encryption, field_name, ''
                        )  # property returns decrypted
                        if already_set:
                            continue
                        try:
                            # EncryptedTextField handles encryption automatically
                            encrypted_field_name = f'encrypted_{field_name}'
                            setattr(
                                user_encryption, encrypted_field_name, current_value
                            )
                        except Exception as e:
                            logger.error(
                                f'Failed to encrypt {field_name} for user '
                                f'{user.id}: {e}'
                            )
                            raise

            user_encryption.save()

            # Optionally blank originals on auth_user after successful encryption
            if redact_original:
                updated_fields = []
                for field_name in fields_to_encrypt:
                    if hasattr(user, field_name) and getattr(user, field_name):
                        setattr(user, field_name, '')
                        updated_fields.append(field_name)
                if updated_fields:
                    user.save(update_fields=updated_fields)

    def _show_user_encryption(self, user, fields_to_encrypt):
        """Show what would be encrypted for a user (dry run)."""
        for field_name in fields_to_encrypt:
            if hasattr(user, field_name):
                current_value = getattr(user, field_name)
                if current_value and not self._is_encrypted(current_value):
                    self.stdout.write(
                        f'  User {user.id}: {field_name} would be encrypted'
                    )

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
