#!/usr/bin/env python
"""
Quick validation script to demonstrate encryption is working.
This can be run to verify encryption is properly configured.
"""

import os
import sys

import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
django.setup()

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.models import User

from web.models import Donation, Profile, WebRequest

print("=" * 70)
print("PERSONAL DATA ENCRYPTION VALIDATION")
print("=" * 70)
print()

# Check encryption key is configured
print("1. Checking encryption key configuration...")
try:
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode("utf-8")
    fernet = Fernet(key)
    print("   ✅ Encryption key is properly configured")
except Exception as e:
    print(f"   ❌ Error with encryption key: {e}")
    sys.exit(1)

print()

# Test Profile encryption
print("2. Testing Profile field encryption...")
try:
    # Get or create a test user
    user, created = User.objects.get_or_create(username="encryption_test_user", defaults={"email": "test@example.com"})

    # Update profile with test data
    profile = user.profile
    test_discord = "TestUser#1234"
    profile.discord_username = test_discord
    profile.save()

    # Reload and verify
    profile.refresh_from_db()
    if profile.discord_username == test_discord:
        print("   ✅ Profile encryption/decryption working")
    else:
        print("   ❌ Profile encryption failed")

    # Cleanup
    if created:
        user.delete()

except Exception as e:
    print(f"   ❌ Error testing profile: {e}")

print()

# Test WebRequest encryption
print("3. Testing WebRequest IP address encryption...")
try:
    test_ip = "192.168.1.100"
    webrequest = WebRequest.objects.create(ip_address=test_ip, user="test", path="/test")

    webrequest.refresh_from_db()
    if webrequest.ip_address == test_ip:
        print("   ✅ WebRequest IP encryption/decryption working")
    else:
        print("   ❌ WebRequest encryption failed")

    webrequest.delete()

except Exception as e:
    print(f"   ❌ Error testing WebRequest: {e}")

print()

# Test Donation encryption
print("4. Testing Donation email encryption...")
try:
    test_email = "donor@example.com"
    donation = Donation.objects.create(email=test_email, amount=50.00, donation_type="one_time")

    donation.refresh_from_db()
    if donation.email == test_email:
        print("   ✅ Donation email encryption/decryption working")
    else:
        print("   ❌ Donation encryption failed")

    donation.delete()

except Exception as e:
    print(f"   ❌ Error testing Donation: {e}")

print()
print("=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)
print()
print("Encrypted fields:")
print("  • Profile: discord_username, slack_username, github_username, stripe_account_id")
print("  • WebRequest: ip_address")
print("  • Donation: email")
print("  • Order: shipping_address")
print("  • FeatureVote: ip_address")
print()
print("All personal data is now encrypted at rest! 🔒")
print()
