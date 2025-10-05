# Production Deployment Guide for Encryption

## Pre-Deployment Checklist

Before deploying the encryption changes to production:

### 1. Verify Encryption Key is Set

Ensure `MESSAGE_ENCRYPTION_KEY` is set in your production environment:

```bash
# Check if the environment variable exists
echo $MESSAGE_ENCRYPTION_KEY

# It should be a base64-encoded 32-byte key
# Example format: b'xSNq8PvZzLnBBM5GJj4xtKrPt1Q4yY7NRs7u-Kab2c8='
```

If not set, generate one securely:

```bash
# Using Python
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"
```

**CRITICAL**: Save this key securely. Store it in:
- Environment variables on your production server
- AWS Secrets Manager / Azure Key Vault / Google Secret Manager
- Kubernetes secrets
- Never commit to git or share publicly

### 2. Backup Database

Before running migrations, create a full database backup:

```bash
# For SQLite
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)

# For PostgreSQL
pg_dump -U username -d database_name -F c -f backup_$(date +%Y%m%d_%H%M%S).dump

# For MySQL
mysqldump -u username -p database_name > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 3. Test in Staging First

1. Deploy to staging environment
2. Run migrations
3. Run encryption command with --dry-run
4. Run encryption command for real
5. Verify data can be read/written correctly
6. Run all tests

## Deployment Steps

### Step 1: Deploy Code

```bash
# Pull latest code
git pull origin main

# Install new dependencies
poetry install

# Or with pip
pip install -r requirements.txt
```

### Step 2: Run Database Migration

```bash
# This updates the schema to use encrypted field types
poetry run python manage.py migrate

# The migration is: 0063_add_encryption_to_personal_data
```

**What this does:**
- Changes field types to encrypted fields
- Does NOT encrypt existing data yet
- Safe to run - data remains accessible

### Step 3: Encrypt Existing Data (Optional but Recommended)

For a production system with existing data, you may want to encrypt in batches:

```bash
# First, do a dry run to see what will be encrypted
poetry run python manage.py encrypt_personal_data --dry-run

# Review the output, then run for real
poetry run python manage.py encrypt_personal_data
```

**Alternative**: Let data encrypt automatically on next save
- Each record will be encrypted when it's next updated
- No bulk operation needed
- Gradual migration over time

### Step 4: Verify Encryption

After migration, verify encryption is working:

```bash
# Run tests
poetry run python manage.py test web.tests.test_encryption

# Check a few records manually
poetry run python manage.py shell
```

In the Django shell:
```python
from web.models import Profile
profile = Profile.objects.first()
print(profile.discord_username)  # Should decrypt and display
```

### Step 5: Monitor Logs

Watch application logs for any encryption-related errors:

```bash
# Common issues to watch for:
# - cryptography.fernet.InvalidToken (wrong encryption key)
# - Database errors on save (field size issues)
# - Performance degradation (unlikely but possible)
```

## Rollback Plan

If something goes wrong, you can rollback:

### Option 1: Revert Code and Migration

```bash
# Rollback the migration
poetry run python manage.py migrate web 0062

# Revert code
git revert <commit-hash>

# Redeploy
```

**WARNING**: If data was encrypted, you'll need the encryption key to decrypt it again.

### Option 2: Restore from Backup

```bash
# For SQLite
cp db.sqlite3.backup_TIMESTAMP db.sqlite3

# For PostgreSQL  
pg_restore -U username -d database_name backup_TIMESTAMP.dump

# For MySQL
mysql -u username -p database_name < backup_TIMESTAMP.sql
```

## Performance Considerations

### Expected Impact

- **CPU**: Minimal increase (1-2%) for encryption/decryption
- **Memory**: Negligible 
- **Database**: Encrypted fields are ~30-40% larger
- **Query Performance**: Reads/writes unchanged for encrypted fields

### Monitoring

Monitor these metrics:
- Response times for views accessing encrypted data
- Database CPU usage
- Memory usage
- Disk space (encrypted data is larger)

### Optimization Tips

If you see performance issues:

1. **Index Related Fields**: Can't index encrypted fields, but can index related fields
   ```python
   # Instead of querying encrypted email
   # Use a non-encrypted user_id or username
   ```

2. **Cache Frequently Accessed Data**:
   ```python
   from django.core.cache import cache
   
   profile_data = cache.get(f'profile_{user.id}')
   if not profile_data:
       profile_data = user.profile
       cache.set(f'profile_{user.id}', profile_data, 300)
   ```

3. **Batch Operations**: Process in chunks if encrypting large datasets

## Security Best Practices

### Key Rotation

Plan for periodic key rotation:

1. Generate new encryption key
2. Update `FIELD_ENCRYPTION_KEY` to list of keys: `[new_key, old_key]`
3. Re-encrypt all data with new key
4. Remove old key from list

### Access Control

- Limit who can access `MESSAGE_ENCRYPTION_KEY`
- Use environment variables, not hardcoded keys
- Rotate keys if compromised
- Audit access to encrypted data

### Compliance

Document your encryption for compliance:
- What data is encrypted
- How keys are managed
- Encryption algorithm used (Fernet/AES-128-CBC)
- Key rotation policy

## Troubleshooting

### "InvalidToken" Error

**Cause**: Encryption key mismatch

**Fix**:
1. Verify `MESSAGE_ENCRYPTION_KEY` environment variable
2. Check if key was changed accidentally
3. If data was encrypted with different key, restore from backup

### Field Size Errors

**Cause**: Encrypted data exceeds field length

**Fix**: Migration already increases field sizes, but if issues persist:
```python
# In models.py, increase max_length
discord_username = CustomEncryptedCharField(max_length=500, ...)
```

### Data Not Decrypting

**Cause**: Data was never encrypted or wrong key

**Debug**:
```python
# In Django shell
from web.models import Profile
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT discord_username FROM web_profile LIMIT 1")
    raw_value = cursor.fetchone()[0]
    print(f"Raw DB value: {raw_value}")
    # Should look like encrypted data (gAAA...)
```

## Support

If you encounter issues:

1. Check logs for specific error messages
2. Review ENCRYPTION.md documentation
3. Verify encryption key is correct
4. Test in development environment first
5. Create issue on GitHub with details

## Post-Deployment

After successful deployment:

1. ✅ Verify all tests pass
2. ✅ Check encryption is working on new data
3. ✅ Monitor error rates for 24-48 hours
4. ✅ Document the encryption key location
5. ✅ Update runbooks with new procedures
6. ✅ Train team on encryption key management
7. ✅ Schedule first key rotation (recommend 6-12 months)
