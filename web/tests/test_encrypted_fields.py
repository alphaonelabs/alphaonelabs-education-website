"""
Tests for encrypted user fields in Profile model.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from web.models import Profile


class EncryptedFieldsTestCase(TestCase):
    """Test encryption and decryption of user PII fields."""

    def setUp(self):
        """Create test user and profile."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123", first_name="Test", last_name="User"
        )
        # Profile is created automatically via signal
        self.profile = Profile.objects.get(user=self.user)

    def test_encrypted_email_field(self):
        """Test that email is encrypted and decrypted correctly."""
        test_email = "encrypted@example.com"

        # Set the encrypted field
        self.profile.encrypted_email = test_email
        self.profile.save()

        # Reload from database
        profile = Profile.objects.get(id=self.profile.id)

        # Should decrypt to original value
        self.assertEqual(profile.encrypted_email, test_email)

    def test_encrypted_first_name_field(self):
        """Test that first_name is encrypted and decrypted correctly."""
        test_name = "John"

        # Set the encrypted field
        self.profile.encrypted_first_name = test_name
        self.profile.save()

        # Reload from database
        profile = Profile.objects.get(id=self.profile.id)

        # Should decrypt to original value
        self.assertEqual(profile.encrypted_first_name, test_name)

    def test_encrypted_last_name_field(self):
        """Test that last_name is encrypted and decrypted correctly."""
        test_name = "Doe"

        # Set the encrypted field
        self.profile.encrypted_last_name = test_name
        self.profile.save()

        # Reload from database
        profile = Profile.objects.get(id=self.profile.id)

        # Should decrypt to original value
        self.assertEqual(profile.encrypted_last_name, test_name)

    def test_encrypted_field_empty_values(self):
        """Test that empty values are handled correctly."""
        # Set empty values
        self.profile.encrypted_email = ""
        self.profile.encrypted_first_name = ""
        self.profile.encrypted_last_name = ""
        self.profile.save()

        # Reload from database
        profile = Profile.objects.get(id=self.profile.id)

        # Should remain empty
        self.assertEqual(profile.encrypted_email, "")
        self.assertEqual(profile.encrypted_first_name, "")
        self.assertEqual(profile.encrypted_last_name, "")

    def test_sync_encrypted_fields_from_user(self):
        """Test that sync_encrypted_fields_from_user() works correctly."""
        # Update user fields
        self.user.email = "newemail@example.com"
        self.user.first_name = "NewFirst"
        self.user.last_name = "NewLast"
        self.user.save()

        # Sync to encrypted fields
        self.profile.sync_encrypted_fields_from_user()
        self.profile.save()

        # Reload and verify
        profile = Profile.objects.get(id=self.profile.id)
        self.assertEqual(profile.encrypted_email, "newemail@example.com")
        self.assertEqual(profile.encrypted_first_name, "NewFirst")
        self.assertEqual(profile.encrypted_last_name, "NewLast")

    def test_sync_user_fields_from_encrypted(self):
        """Test that sync_user_fields_from_encrypted() works correctly."""
        # Set encrypted fields
        self.profile.encrypted_email = "encrypted@example.com"
        self.profile.encrypted_first_name = "EncFirst"
        self.profile.encrypted_last_name = "EncLast"
        self.profile.save()

        # Sync to user fields
        self.profile.sync_user_fields_from_encrypted()
        self.user.save()

        # Reload and verify
        user = User.objects.get(id=self.user.id)
        self.assertEqual(user.email, "encrypted@example.com")
        self.assertEqual(user.first_name, "EncFirst")
        self.assertEqual(user.last_name, "EncLast")

    def test_data_is_actually_encrypted_in_database(self):
        """Verify that data is encrypted in the database."""
        from django.db import connection

        test_email = "secret@example.com"
        self.profile.encrypted_email = test_email
        self.profile.save()

        # Query raw database value
        with connection.cursor() as cursor:
            cursor.execute("SELECT encrypted_email FROM web_profile WHERE id = %s", [self.profile.id])
            row = cursor.fetchone()
            raw_value = row[0]

        # Raw value should NOT be the plaintext
        self.assertNotEqual(raw_value, test_email)
        # Fernet tokens start with 'gAAAAA'
        self.assertTrue(raw_value.startswith("gAAAAA"), f"Expected Fernet token, got: {raw_value[:20]}")

    def test_special_characters_in_encrypted_fields(self):
        """Test that special characters are handled correctly."""
        test_email = "test+special@example.com"
        test_first = "O'Brien"
        test_last = "De La Cruz"

        self.profile.encrypted_email = test_email
        self.profile.encrypted_first_name = test_first
        self.profile.encrypted_last_name = test_last
        self.profile.save()

        # Reload from database
        profile = Profile.objects.get(id=self.profile.id)

        self.assertEqual(profile.encrypted_email, test_email)
        self.assertEqual(profile.encrypted_first_name, test_first)
        self.assertEqual(profile.encrypted_last_name, test_last)

    def test_unicode_in_encrypted_fields(self):
        """Test that Unicode characters are handled correctly."""
        test_first = "José"
        test_last = "François"

        self.profile.encrypted_first_name = test_first
        self.profile.encrypted_last_name = test_last
        self.profile.save()

        # Reload from database
        profile = Profile.objects.get(id=self.profile.id)

        self.assertEqual(profile.encrypted_first_name, test_first)
        self.assertEqual(profile.encrypted_last_name, test_last)
