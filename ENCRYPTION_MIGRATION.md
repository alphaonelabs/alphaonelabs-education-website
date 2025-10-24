# User Table Encryption Migration Guide

This document explains the user table encryption implementation and production migration process.

## Overview

This implementation encrypts sensitive PII (Personally Identifiable Information) from the User table:
- Email addresses
- First names
- Last names

The encrypted data is stored in the Profile model using Fernet symmetric encryption (same encryption used for secure messaging in the platform).

## Architecture

### Components

1. **Encrypted Field Classes** (`web/fields.py`)
   - `EncryptedEmailField`: Encrypts email addresses
   - `EncryptedCharField`: Encrypts character fields (first_name, last_name)
   - `EncryptedTextField`: Encrypts longer text fields

2. **Profile Model Extensions** (`web/models.py`)
   - `encrypted_email`: Encrypted copy of user.email
   - `encrypted_first_name`: Encrypted copy of user.first_name
   - `encrypted_last_name`: Encrypted copy of user.last_name

3. **Signal Handler** (`web/signals.py`)
   - Automatically syncs encrypted fields when Profile is saved
   - Keeps User and encrypted Profile fields in sync

4. **Migrations**
   - `0063_add_encrypted_user_fields.py`: Adds encrypted fields to Profile
   - `0064_encrypt_existing_user_data.py`: Migrates existing data

### How It Works

1. Sensitive fields are stored encrypted in the Profile model
2. The Profile model has a OneToOne relationship with User
3. Custom field classes automatically encrypt/decrypt on save/load
4. A signal keeps User and Profile fields synchronized
5. Authentication continues to use the unencrypted username/password

## Production Migration Steps

### Prerequisites

1. **Backup Database**
   ```bash
   # Example for MySQL
   mysqldump -u username -p database_name > backup_$(date +%Y%m%d).sql
   ```

2. **Verify Encryption Key**
   Ensure `MESSAGE_ENCRYPTION_KEY` is set in your `.env` file:
   ```bash
   grep MESSAGE_ENCRYPTION_KEY .env
   ```
   If not set, generate a new key:
   ```bash
   python web/master_key.py
   ```

3. **Test on Staging**
   Always test the migration on a staging environment first.

### Migration Process

#### Step 1: Deploy Code

Deploy the code changes to production:
```bash
git pull origin main
# Restart your application server
```

#### Step 2: Run Migrations

Apply the database migrations:
```bash
python manage.py migrate web
```

This will:
- Add the three new encrypted fields to the Profile table
- Run the data migration to encrypt existing user data

#### Step 3: Verify Encryption

Check that data was encrypted:
```bash
python scripts/migrate_encrypt_users.py
```

This script will:
- Verify encryption key is configured
- Check migrations are applied
- Show statistics about encrypted records
- Optionally re-encrypt any missed records

#### Step 4: Test Application

1. Test user login/authentication
2. Test user profile viewing/editing
3. Test signup flow
4. Check that email notifications work
5. Verify admin panel access

### Alternative: Manual Migration Script

If you prefer to run the encryption separately from the migration:

```bash
# Run migrations without data migration
python manage.py migrate web 0063

# Run the manual encryption script
python scripts/migrate_encrypt_users.py

# Then apply the data migration
python manage.py migrate web 0064
```

## Rollback Procedure

If you encounter issues, you can rollback:

### Within 24 Hours (Data Still in User Table)

```bash
# Rollback migrations
python manage.py migrate web 0062

# Restart application
sudo systemctl restart your-app-service
```

### After 24 Hours

If you need to decrypt data back to User table:

```python
# In Django shell
from web.models import Profile

for profile in Profile.objects.all():
    if profile.encrypted_email:
        profile.user.email = profile.encrypted_email
    if profile.encrypted_first_name:
        profile.user.first_name = profile.encrypted_first_name
    if profile.encrypted_last_name:
        profile.user.last_name = profile.encrypted_last_name
    profile.user.save()
```

Then rollback migrations as above.

## Monitoring

After migration, monitor for:

1. **Authentication Issues**
   - Users unable to login
   - Password reset failures

2. **Email Delivery**
   - Notifications not sent
   - Email addresses not resolved

3. **Profile Display**
   - Names not displaying correctly
   - Profile edit failures

## Security Considerations

1. **Encryption Key Protection**
   - Store `MESSAGE_ENCRYPTION_KEY` securely (environment variable)
   - Never commit encryption key to version control
   - Rotate key periodically (requires re-encryption)

2. **Database Access**
   - Encrypted data is only readable with the encryption key
   - Direct database queries will show encrypted values

3. **Backup Security**
   - Database backups contain encrypted data
   - Backups are useless without the encryption key
   - Store backups and keys separately

## Performance Impact

- Minimal performance impact (< 1ms per operation)
- Encryption happens on save, decryption on load
- No impact on User authentication (username/password unchanged)

## Troubleshooting

### Decryption Errors

If you see `[Error decrypting message]`:
1. Check that MESSAGE_ENCRYPTION_KEY matches the key used for encryption
2. Verify the key is properly formatted (base64 encoded)
3. Check for data corruption in database

### Migration Failures

If migration fails:
1. Check database permissions
2. Verify all dependencies are installed
3. Review migration logs for specific errors
4. Rollback and retry with verbose logging:
   ```bash
   python manage.py migrate web --verbosity 2
   ```

### Signal Not Firing

If encrypted fields aren't syncing:
1. Check that `web.signals` is imported in `web/apps.py`
2. Verify Profile signals are registered
3. Check for transaction isolation issues

## Support

For issues or questions:
1. Check application logs: `tail -f /var/log/your-app/error.log`
2. Review Django logs for exceptions
3. Contact development team

## Changelog

### Version 1.0 (Current)
- Initial implementation of user table encryption
- Added encrypted fields to Profile model
- Created production migration scripts
- Added automatic sync signals
