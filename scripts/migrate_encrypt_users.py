#!/usr/bin/env python3
"""
Production Migration Script for User Table Encryption

This script encrypts sensitive User model PII (email, first_name, last_name)
by copying the data to encrypted fields in the Profile model.

IMPORTANT: Before running this script in production:
1. Backup your database
2. Ensure MESSAGE_ENCRYPTION_KEY is set in environment variables
3. Test on a staging environment first
4. Run during low-traffic periods

Usage:
    python scripts/migrate_encrypt_users.py

The script will:
1. Check that migrations 0063 and 0064 are applied
2. Verify encryption key is configured
3. Encrypt all existing user PII data
4. Provide a summary of encrypted records

To rollback (if needed within 24 hours):
    python manage.py migrate web 0062
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.db import transaction  # noqa: E402

from web.models import Profile  # noqa: E402


def check_encryption_key():
    """Verify that MESSAGE_ENCRYPTION_KEY is properly configured."""
    if not hasattr(settings, "SECURE_MESSAGE_KEY") or not settings.SECURE_MESSAGE_KEY:
        print("❌ ERROR: MESSAGE_ENCRYPTION_KEY not configured in settings")
        print("   Set MESSAGE_ENCRYPTION_KEY in your .env file")
        sys.exit(1)
    print("✓ Encryption key is configured")


def check_migrations():
    """Verify required migrations are applied."""
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor

    connection = connections["default"]
    executor = MigrationExecutor(connection)
    applied = executor.loader.applied_migrations

    required_migrations = [
        ("web", "0063_add_encrypted_user_fields"),
        ("web", "0064_encrypt_existing_user_data"),
    ]

    for app, migration in required_migrations:
        if (app, migration) not in applied:
            print(f"❌ ERROR: Migration {app}.{migration} not applied")
            print("   Run: python manage.py migrate web")
            sys.exit(1)

    print("✓ Required migrations are applied")


def encrypt_user_data():
    """
    Main function to encrypt user PII data.
    """
    print("\n" + "=" * 60)
    print("User Table Encryption Migration")
    print("=" * 60 + "\n")

    # Pre-flight checks
    print("Running pre-flight checks...")
    check_encryption_key()
    check_migrations()
    print()

    # Get counts
    total_users = User.objects.count()
    total_profiles = Profile.objects.count()

    print("Database Statistics:")
    print(f"  Total Users: {total_users}")
    print(f"  Total Profiles: {total_profiles}")
    print()

    if total_users == 0:
        print("No users found. Nothing to encrypt.")
        return

    # Confirm before proceeding
    response = input("Proceed with encryption? [yes/no]: ")
    if response.lower() not in ["yes", "y"]:
        print("Operation cancelled.")
        sys.exit(0)

    print("\nEncrypting user data...")
    encrypted_count = 0
    error_count = 0
    already_encrypted = 0

    with transaction.atomic():
        profiles = Profile.objects.select_related("user").all()

        for profile in profiles:
            try:
                needs_update = False

                # Check if already encrypted (encrypted data starts with 'gAAAAA')
                if profile.encrypted_email and profile.encrypted_email.startswith("gAAAAA"):
                    already_encrypted += 1
                    continue

                # Encrypt email
                if profile.user.email and not profile.encrypted_email:
                    profile.encrypted_email = profile.user.email
                    needs_update = True

                # Encrypt first name
                if profile.user.first_name and not profile.encrypted_first_name:
                    profile.encrypted_first_name = profile.user.first_name
                    needs_update = True

                # Encrypt last name
                if profile.user.last_name and not profile.encrypted_last_name:
                    profile.encrypted_last_name = profile.user.last_name
                    needs_update = True

                if needs_update:
                    profile.save(update_fields=["encrypted_email", "encrypted_first_name", "encrypted_last_name"])
                    encrypted_count += 1

                    if encrypted_count % 100 == 0:
                        print(f"  Processed {encrypted_count} profiles...")

            except Exception as e:
                error_count += 1
                print(f"  ❌ Error encrypting profile {profile.id}: {str(e)}")

    print("\n" + "=" * 60)
    print("Encryption Complete")
    print("=" * 60)
    print(f"Successfully encrypted: {encrypted_count} profiles")
    print(f"Already encrypted: {already_encrypted} profiles")
    if error_count > 0:
        print(f"Errors encountered: {error_count} profiles")
    print()

    # Verify encryption worked
    print("Verification:")
    sample_profile = Profile.objects.filter(encrypted_email__isnull=False).first()
    if sample_profile:
        encrypted_email = sample_profile.encrypted_email
        if encrypted_email and encrypted_email.startswith("gAAAAA"):
            print("✓ Sample profile has encrypted data (token starts with 'gAAAAA')")
        else:
            print("⚠ Warning: Sample profile data may not be properly encrypted")
    print()

    print("Next Steps:")
    print("1. Verify encrypted data is accessible")
    print("2. Test authentication and user operations")
    print("3. Monitor application logs for any issues")
    print("4. Keep database backup for at least 7 days")
    print()


if __name__ == "__main__":
    try:
        encrypt_user_data()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
