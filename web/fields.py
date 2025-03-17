from django.db import models
from web.crypto import encrypt, decrypt

class EncryptedTextField(models.TextField):
    description = "Transparently encrypted text field"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt(value)
    
    def to_python(self, value):
        if value is None:
            return value
        # If the value is already decrypted, return it as-is
        if isinstance(value, str) and not value.startswith('gAAAAA'):
            return value
        return decrypt(value)
    
    def get_prep_value(self, value):
        if value is None:
            return value
        return encrypt(value)

class EncryptedCharField(models.CharField):
    description = "Transparently encrypted character field"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt(value)
    
    def to_python(self, value):
        if value is None:
            return value
        # If the value is already decrypted, return it as-is
        if isinstance(value, str) and not value.startswith('gAAAAA'):
            return value
        return decrypt(value)
    
    def get_prep_value(self, value):
        if value is None:
            return value
        return encrypt(value)

class EncryptedEmailField(EncryptedCharField):
    description = "Transparently encrypted email field"
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 254)
        super().__init__(*args, **kwargs) 