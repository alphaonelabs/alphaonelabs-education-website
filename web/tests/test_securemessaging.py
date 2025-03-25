# tests/test_secure_messaging.py

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from web.models import PeerMessage
from web.secure_messaging import (
    decrypt_message_with_random_key,
    encrypt_message_with_random_key,
)

User = get_user_model()


class SecureMessagingEnvelopeTestCase(TestCase):
    def test_envelope_encryption_and_decryption(self):
        """
        Test that envelope encryption works:
         - encrypt_message_with_random_key returns a tuple of encrypted message and encrypted key.
         - decrypt_message_with_random_key properly recovers the original plaintext.
        """
        original_message = "This is a test message."
        encrypted_message, encrypted_key = encrypt_message_with_random_key(original_message)

        # Assert both values are strings and not equal to the original message.
        self.assertIsInstance(encrypted_message, str)
        self.assertIsInstance(encrypted_key, str)
        self.assertNotEqual(encrypted_message, original_message)
        self.assertNotEqual(encrypted_key, "")

        # Decrypt the message using the encrypted key.
        decrypted_message = decrypt_message_with_random_key(encrypted_message, encrypted_key)
        self.assertEqual(decrypted_message, original_message)


class SecureMessagingViewTestCase(TestCase):
    def setUp(self):
        # Create a test user and log in.
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
        self.client = Client()
        self.client.login(username="testuser", password="password")

    def test_send_encrypted_message_view(self):
        """
        Test that sending an encrypted message via the secure messaging view works correctly.
        The view should:
          - Accept the plaintext message and recipient.
          - Encrypt the message using envelope encryption.
          - Save the encrypted message and encrypted key.
          - Return a JSON response indicating success.
        """
        url = reverse("send_encrypted_message")
        original_message = "Hello envelope encryption!"
        # Post to the view. Assume the recipient is identified by username.
        response = self.client.post(url, {"message": original_message, "recipient": "testuser"})
        self.assertEqual(response.status_code, 200)

        # Retrieve the saved message.
        msg = PeerMessage.objects.first()
        self.assertIsNotNone(msg)
        # The stored content should not equal the plaintext.
        self.assertNotEqual(msg.content, original_message)
        # The encrypted_key field should be populated.
        self.assertIsNotNone(msg.encrypted_key)

        # Decrypt the message using our envelope decryption function.
        from web.secure_messaging import decrypt_message_with_random_key

        decrypted = decrypt_message_with_random_key(msg.content, msg.encrypted_key)
        self.assertEqual(decrypted, original_message)

    def test_inbox_view(self):
        """
        Test that the inbox view properly decrypts and displays messages.
        """
        original_message = "Inbox envelope test."
        # Encrypt the message using envelope encryption.
        encrypted_message, encrypted_key = encrypt_message_with_random_key(original_message)
        PeerMessage.objects.create(
            sender=self.user, receiver=self.user, content=encrypted_message, encrypted_key=encrypted_key
        )
        url = reverse("inbox")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that the decrypted original message is displayed in the response.
        self.assertContains(response, original_message)
