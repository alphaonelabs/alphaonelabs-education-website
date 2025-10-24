# Quick Start Guide - User Encryption

## For Developers

### Understanding Encrypted Fields

User PII is now encrypted in the `Profile` model:

```python
from web.models import Profile

profile = Profile.objects.get(user=user)

# These fields are automatically encrypted/decrypted
email = profile.encrypted_email          # Returns decrypted email
first_name = profile.encrypted_first_name  # Returns decrypted first name
last_name = profile.encrypted_last_name    # Returns decrypted last name

# Set encrypted fields (automatic encryption on save)
profile.encrypted_email = "new@example.com"
profile.save()  # Automatically encrypted before saving
```

### Syncing User and Profile

The signal handler automatically syncs fields, but you can manually sync:

```python
# Copy User → Profile (encrypt)
profile.sync_encrypted_fields_from_user()
profile.save()

# Copy Profile → User (decrypt)
profile.sync_user_fields_from_encrypted()
user.save()
```

### Working with User Data

**Recommended**: Use the encrypted fields for sensitive data:

```python
# Good ✓
user_email = user.profile.encrypted_email

# Also works (User.email still exists but not encrypted)
user_email = user.email
```

### Testing

Run the encryption tests:

```bash
python manage.py test web.tests.test_encrypted_fields
```

### Common Patterns

#### Getting User Email
```python
# Get decrypted email from profile
email = user.profile.encrypted_email
```

#### Updating User Info
```python
# Update user fields
user.email = "newemail@example.com"
user.first_name = "John"
user.last_name = "Doe"
user.save()

# Encrypted fields auto-sync via signal
# Or manually:
user.profile.sync_encrypted_fields_from_user()
user.profile.save()
```

#### Creating New Users
```python
# User creation works as before
user = User.objects.create_user(
    username="newuser",
    email="user@example.com",
    first_name="John",
    last_name="Doe"
)

# Profile is created automatically (signal)
# Encrypted fields are synced automatically
```

## For Deployment

### Quick Deploy Checklist

1. **Backup Database**
   ```bash
   mysqldump -u user -p db > backup_$(date +%Y%m%d).sql
   ```

2. **Verify Encryption Key**
   ```bash
   grep MESSAGE_ENCRYPTION_KEY .env
   ```

3. **Deploy Code**
   ```bash
   git pull origin main
   sudo systemctl restart your-app
   ```

4. **Run Migrations**
   ```bash
   python manage.py migrate web
   ```

5. **Verify**
   ```bash
   python scripts/migrate_encrypt_users.py
   ```

### Rollback

If something goes wrong:

```bash
python manage.py migrate web 0062
sudo systemctl restart your-app
```

## FAQ

### Q: Is authentication affected?
**A:** No. Authentication uses `username` and `password` which are not encrypted.

### Q: Can I search encrypted fields?
**A:** Not directly. Search by `username` or other non-encrypted fields.

### Q: What happens to existing data?
**A:** Migration `0064` automatically encrypts all existing user data.

### Q: What if decryption fails?
**A:** Fields return empty string. Check encryption key is correct.

### Q: Can I encrypt other fields?
**A:** Yes! Use `EncryptedCharField`, `EncryptedEmailField`, or `EncryptedTextField` from `web.fields`.

## Need Help?

- Read `ENCRYPTION_MIGRATION.md` for detailed guide
- Read `IMPLEMENTATION_SUMMARY.md` for architecture
- Check application logs for errors
- Run tests: `python manage.py test web.tests.test_encrypted_fields`
