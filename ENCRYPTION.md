# Personal Data Encryption Implementation

## Overview

This implementation adds field-level encryption to all personal data in the AlphaOne Labs Education Platform. The encryption uses the existing `MESSAGE_ENCRYPTION_KEY` from settings, ensuring seamless integration with the current infrastructure.

## What Data Is Encrypted?

The following personal data fields are now encrypted at rest in the database:

### User Model PII (via Profile)
- `first_name` - First name (synced from User.first_name)
- `last_name` - Last name (synced from User.last_name)
- `email` - Email address (synced from User.email)

**Note:** User PII is automatically synced from the User model to encrypted fields in the Profile model whenever a User is saved. This provides encrypted storage while maintaining Django auth compatibility.

### Profile Model
- `discord_username` - Discord usernames
- `slack_username` - Slack usernames
- `github_username` - GitHub usernames
- `stripe_account_id` - Stripe account identifiers

### WebRequest Model
- `ip_address` - IP addresses from web requests

### Donation Model
- `email` - Donor email addresses

### Order Model
- `shipping_address` - Complete shipping address information (JSON field)

### FeatureVote Model
- `ip_address` - IP addresses from feature votes

## How It Works

### Encryption Library

We use the `django-encrypted-model-fields` library which:
- Transparently encrypts data when saving to database
- Automatically decrypts data when reading from database
- Uses the Fernet symmetric encryption (cryptography library)
- Is compatible with the existing `MESSAGE_ENCRYPTION_KEY`

### Configuration

The encryption key is configured in `web/settings.py`:

```python
MESSAGE_ENCRYPTION_KEY = env.str("MESSAGE_ENCRYPTION_KEY", default=Fernet.generate_key()).strip()
SECURE_MESSAGE_KEY = MESSAGE_ENCRYPTION_KEY
FIELD_ENCRYPTION_KEY = SECURE_MESSAGE_KEY
```

**Important for Production**: Ensure the `MESSAGE_ENCRYPTION_KEY` environment variable is set in production and kept secure. Without this key, encrypted data cannot be decrypted.

### Custom Encryption Fields

Located in `web/encryption.py`:

- `CustomEncryptedCharField` - For encrypting text fields (usernames, IDs, IP addresses)
- `CustomEncryptedEmailField` - For encrypting email addresses
- `CustomEncryptedJSONField` - For encrypting JSON data (shipping addresses)

## Migration Strategy

### Automatic Migration

The implementation is designed for seamless migration:

1. **Schema Migration**: Run `python manage.py migrate` to update field types
   - The migration file is: `web/migrations/0063_add_encryption_to_personal_data.py` (includes all encryption including User PII)

2. **Data Migration**: Existing plaintext data is automatically encrypted on first save
   - No manual data migration needed for most cases
   - Encrypted fields library handles encryption transparently

### Manual Migration Command

For bulk encryption of existing data, use:

```bash
# Dry run to see what would be encrypted
python manage.py encrypt_personal_data --dry-run

# Actually encrypt the data
python manage.py encrypt_personal_data
```

This command:
- Is idempotent (safe to run multiple times)
- Detects already-encrypted data and skips it
- Provides progress feedback
- Can be run on production data

## Testing

Tests are located in `web/tests/test_encryption.py` and cover:

- Encryption/decryption of all encrypted fields
- Empty value handling
- Null value handling
- Data integrity after save/reload

Run tests with:
```bash
python manage.py test web.tests.test_encryption
```

## Security Considerations

### Key Management

1. **Never commit the encryption key** to version control
2. Store `MESSAGE_ENCRYPTION_KEY` in environment variables
3. Use a secure key management service in production (AWS KMS, Azure Key Vault, etc.)
4. Rotate keys periodically (requires re-encryption of data)

### Key Rotation

If you need to rotate encryption keys:

1. Set `FIELD_ENCRYPTION_KEY` to a list: `[new_key, old_key]`
2. The library will try decrypting with each key
3. Re-save all encrypted data to encrypt with new key
4. Remove old key from list

Example:
```python
FIELD_ENCRYPTION_KEY = [
    b'new-key-here',
    b'old-key-here'
]
```

### Database Security

Even with field-level encryption:
- Use encrypted database backups
- Restrict database access
- Use SSL/TLS for database connections
- Enable database encryption at rest when available

## Performance Impact

Field-level encryption has minimal performance impact:

- Encryption/decryption happens in memory
- Modern CPUs handle Fernet encryption efficiently
- No significant slowdown for typical operations
- Database storage slightly increases (encrypted data is larger)

## Compliance

This implementation helps meet compliance requirements for:

- **GDPR** - Personal data protection
- **CCPA** - California Consumer Privacy Act
- **HIPAA** - If handling health data
- **PCI DSS** - Payment card data security

## Backward Compatibility

The implementation is designed to be backward-compatible:

- Existing unencrypted data is automatically encrypted on first write
- No breaking changes to model APIs
- All existing code continues to work unchanged
- Read/write operations remain the same from application perspective

## Troubleshooting

### Cannot decrypt data

**Symptom**: `cryptography.fernet.InvalidToken` errors

**Solution**:
- Verify `MESSAGE_ENCRYPTION_KEY` is correctly set
- Check if key has changed (shouldn't happen in production)
- If key is lost, encrypted data cannot be recovered

### Migration issues

**Symptom**: Migration fails

**Solution**:
- Ensure `django-encrypted-model-fields` is installed
- Check database has necessary permissions
- Run migrations in stages if needed

### Performance concerns

**Symptom**: Slow queries

**Solution**:
- Encrypted fields cannot be indexed efficiently
- Use separate indexed fields for lookups
- Consider caching frequently accessed encrypted data

## Future Enhancements

Potential improvements:

1. Add encryption for User email addresses (requires allauth compatibility)
2. Implement encrypted search capabilities
3. Add audit logging for access to encrypted data
4. Implement field-level access controls
5. Add encryption for file uploads (avatars, attachments)

## References

- [django-encrypted-model-fields Documentation](https://pypi.org/project/django-encrypted-model-fields/)
- [Cryptography Library](https://cryptography.io/)
- [Fernet Specification](https://github.com/fernet/spec/)
