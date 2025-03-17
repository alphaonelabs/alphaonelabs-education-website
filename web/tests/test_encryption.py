from django.test import TestCase
from django.contrib.auth.models import User
from web.crypto import encrypt, decrypt
from web.models import Profile, WebRequest, Order
from web.fields import EncryptedTextField, EncryptedCharField, EncryptedEmailField

class EncryptionTests(TestCase):
    def setUp(self):
        self.test_user = User.objects.create_user(
            username="testuser", 
            email="test@example.com", 
            password="testpassword"
        )
        
    def test_encryption_decryption(self):
        """Test that our encryption and decryption functions work properly"""
        original_text = "This is sensitive information"
        encrypted = encrypt(original_text)
        decrypted = decrypt(encrypted)
        
        # The encrypted text should be different from the original
        self.assertNotEqual(original_text, encrypted)
        # Decryption should restore the original text
        self.assertEqual(original_text, decrypted)
        
        # Test with None values
        self.assertIsNone(encrypt(None))
        self.assertIsNone(decrypt(None))
        
        # Test with empty string
        self.assertEqual(decrypt(encrypt("")), "")
    
    def test_encrypted_model_fields(self):
        """Test that our encrypted fields work properly in models"""
        sensitive_bio = "This is sensitive bio information"
        sensitive_expertise = "Python, Django, Security"
        
        # Create profile with sensitive info
        profile = Profile.objects.get(user=self.test_user)
        profile.bio = sensitive_bio
        profile.expertise = sensitive_expertise
        profile.save()
        
        # Get a fresh instance from the database
        db_profile = Profile.objects.get(id=profile.id)
        
        # The retrieved values should match the original
        self.assertEqual(db_profile.bio, sensitive_bio)
        self.assertEqual(db_profile.expertise, sensitive_expertise)
        
        # Test WebRequest model
        web_request = WebRequest.objects.create(
            ip_address="192.168.1.1",
            user="testuser",
            agent="Mozilla/5.0",
            referer="https://example.com"
        )
        
        # Get fresh instance
        db_request = WebRequest.objects.get(id=web_request.id)
        
        # Values should be decrypted
        self.assertEqual(db_request.ip_address, "192.168.1.1")
        self.assertEqual(db_request.user, "testuser")
        self.assertEqual(db_request.agent, "Mozilla/5.0")
        self.assertEqual(db_request.referer, "https://example.com")
        
        # Test Order model
        order = Order.objects.create(
            tracking_number="TRACK123456"
        )
        
        # Get fresh instance
        db_order = Order.objects.get(id=order.id)
        
        # Value should be decrypted
        self.assertEqual(db_order.tracking_number, "TRACK123456")
    
    def test_encrypted_field_types(self):
        """Test the different types of encrypted fields"""
        # Test EncryptedTextField
        text_field = EncryptedTextField()
        test_text = "This is a long text field"
        encrypted = text_field.get_prep_value(test_text)
        decrypted = text_field.to_python(encrypted)
        self.assertEqual(decrypted, test_text)
        
        # Test EncryptedCharField
        char_field = EncryptedCharField(max_length=100)
        test_char = "Short text"
        encrypted = char_field.get_prep_value(test_char)
        decrypted = char_field.to_python(encrypted)
        self.assertEqual(decrypted, test_char)
        
        # Test EncryptedEmailField
        email_field = EncryptedEmailField()
        test_email = "test@example.com"
        encrypted = email_field.get_prep_value(test_email)
        decrypted = email_field.to_python(encrypted)
        self.assertEqual(decrypted, test_email) 