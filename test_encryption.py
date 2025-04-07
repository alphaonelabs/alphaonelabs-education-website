import os

import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
django.setup()

# Now we can import our module
from web.crypto_utils import decrypt_value, encrypt_value  # noqa: E402

# Test values
test_values = [
    "test@example.com",
    "User info with spaces",
    "192.168.1.1",
    "Longer text that might contain sensitive information about a user",
]

# Test encryption and decryption
print("Testing encryption and decryption:")
print("=================================")

for test_value in test_values:
    encrypted = encrypt_value(test_value)
    decrypted = decrypt_value(encrypted)

    print(f"\nOriginal: {test_value}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    print(f"Match: {test_value == decrypted}")

print("\nEncryption test complete!")
