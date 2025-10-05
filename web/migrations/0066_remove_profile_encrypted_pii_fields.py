"""
Remove encrypted PII fields from Profile model since we're now encrypting
directly in the User table.
"""

from django.db import migrations


class Migration(migrations.Migration):
    
    dependencies = [
        ('web', '0065_encrypt_user_table_pii_inplace'),
    ]
    
    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='encrypted_first_name',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='encrypted_last_name',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='encrypted_email',
        ),
    ]
