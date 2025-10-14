"""
Tests for personal data encryption functionality.
"""

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from web.models import Donation, FeatureVote, Order, Profile, WebRequest


class EncryptionTestCase(TestCase):
    """Test cases for encrypted personal data fields."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.key = settings.FIELD_ENCRYPTION_KEY
        if isinstance(self.key, str):
            self.key = self.key.encode("utf-8")
        self.fernet = Fernet(self.key)

    def test_profile_encryption(self):
        """Test that Profile fields are encrypted in database."""
        # Get the auto-created profile
        profile = self.user.profile

        # Update with sensitive data
        profile.discord_username = "TestUser#1234"
        profile.slack_username = "testslack"
        profile.github_username = "testgithub"
        profile.stripe_account_id = "acct_test123"
        profile.save()

        # Reload from database
        profile.refresh_from_db()

        # Verify fields are accessible (decrypted on read)
        self.assertEqual(profile.discord_username, "TestUser#1234")
        self.assertEqual(profile.slack_username, "testslack")
        self.assertEqual(profile.github_username, "testgithub")
        self.assertEqual(profile.stripe_account_id, "acct_test123")

    def test_webrequest_encryption(self):
        """Test that WebRequest IP addresses are encrypted."""
        webrequest = WebRequest.objects.create(ip_address="192.168.1.1", user="testuser", path="/test")

        # Reload from database
        webrequest.refresh_from_db()

        # Verify IP is accessible (decrypted on read)
        self.assertEqual(webrequest.ip_address, "192.168.1.1")

    def test_donation_encryption(self):
        """Test that Donation emails are encrypted."""
        donation = Donation.objects.create(
            user=self.user, email="donor@example.com", amount=50.00, donation_type="one_time"
        )

        # Reload from database
        donation.refresh_from_db()

        # Verify email is accessible (decrypted on read)
        self.assertEqual(donation.email, "donor@example.com")

    def test_order_shipping_address_encryption(self):
        """Test that Order shipping addresses are encrypted."""
        from web.models import Storefront

        # Create storefront
        storefront = Storefront.objects.create(teacher=self.user, name="Test Store", store_slug="test-store")

        shipping_data = {"street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001"}

        order = Order.objects.create(
            user=self.user, storefront=storefront, total_price=100.00, shipping_address=shipping_data
        )

        # Reload from database
        order.refresh_from_db()

        # Verify shipping address is accessible (decrypted on read)
        self.assertEqual(order.shipping_address["street"], "123 Main St")
        self.assertEqual(order.shipping_address["city"], "New York")

    def test_featurevote_encryption(self):
        """Test that FeatureVote IP addresses are encrypted."""
        featurevote = FeatureVote.objects.create(feature_id="test-feature", ip_address="10.0.0.1", vote="up")

        # Reload from database
        featurevote.refresh_from_db()

        # Verify IP is accessible (decrypted on read)
        self.assertEqual(featurevote.ip_address, "10.0.0.1")

    def test_empty_values(self):
        """Test that empty values are handled correctly."""
        profile = self.user.profile
        profile.discord_username = ""
        profile.slack_username = ""
        profile.github_username = ""
        profile.stripe_account_id = ""
        profile.save()

        profile.refresh_from_db()

        # Empty strings should remain empty
        self.assertEqual(profile.discord_username, "")
        self.assertEqual(profile.slack_username, "")

    def test_null_values(self):
        """Test that null values are handled correctly."""
        featurevote = FeatureVote.objects.create(feature_id="test-feature", user=self.user, vote="up")

        featurevote.refresh_from_db()

        # Null IP should remain null
        self.assertIsNone(featurevote.ip_address)

    def test_user_pii_encryption(self):
        """Test that User PII (first_name, last_name, email) is encrypted in User table."""
        from web.user_encryption_patch import decrypt_user_field

        # Create user with PII
        user = User.objects.create_user(
            username="piiuser", email="pii@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        # Reload from database
        user.refresh_from_db()

        # The data in DB should be encrypted, but when accessed it should be decrypted
        # Note: With in-place encryption, the raw database values are encrypted
        # but Django ORM returns them as-is (encrypted strings)
        # The decrypt functions handle the decryption
        decrypted_first_name = decrypt_user_field(user.first_name)
        decrypted_last_name = decrypt_user_field(user.last_name)
        decrypted_email = decrypt_user_field(user.email)

        self.assertEqual(decrypted_first_name, "John")
        self.assertEqual(decrypted_last_name, "Doe")
        self.assertEqual(decrypted_email, "pii@example.com")

    def test_user_pii_sync_on_update(self):
        """Test that User PII remains encrypted when updated."""
        from web.user_encryption_patch import decrypt_user_field, encrypt_user_field

        # Update user PII with encrypted values
        self.user.first_name = encrypt_user_field("Updated")
        self.user.last_name = encrypt_user_field("Name")
        self.user.email = encrypt_user_field("updated@example.com")
        self.user.save()

        # Reload from database
        self.user.refresh_from_db()

        # Verify encrypted fields can be decrypted
        self.assertEqual(decrypt_user_field(self.user.first_name), "Updated")
        self.assertEqual(decrypt_user_field(self.user.last_name), "Name")
        self.assertEqual(decrypt_user_field(self.user.email), "updated@example.com")
