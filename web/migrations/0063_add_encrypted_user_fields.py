# Generated migration for adding encrypted fields to Profile model

from django.db import migrations
import web.fields


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0062_update_waitingroom_for_sessions"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="encrypted_email",
            field=web.fields.EncryptedEmailField(blank=True, help_text="Encrypted copy of user email", max_length=500),
        ),
        migrations.AddField(
            model_name="profile",
            name="encrypted_first_name",
            field=web.fields.EncryptedCharField(
                blank=True, help_text="Encrypted copy of user first name", max_length=300
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="encrypted_last_name",
            field=web.fields.EncryptedCharField(
                blank=True, help_text="Encrypted copy of user last name", max_length=300
            ),
        ),
    ]
