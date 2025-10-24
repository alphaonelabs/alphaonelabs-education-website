# Data migration to encrypt existing user PII data

from django.db import migrations


def encrypt_user_data(apps, schema_editor):
    """
    Copy and encrypt user PII from User model to Profile encrypted fields.
    """
    Profile = apps.get_model("web", "Profile")
    User = apps.get_model("auth", "User")

    # Get all profiles
    profiles = Profile.objects.select_related("user").all()

    for profile in profiles:
        # The encrypted fields will automatically encrypt the data on save
        # thanks to our custom field implementation
        if profile.user.email:
            profile.encrypted_email = profile.user.email
        if profile.user.first_name:
            profile.encrypted_first_name = profile.user.first_name
        if profile.user.last_name:
            profile.encrypted_last_name = profile.user.last_name

        profile.save(update_fields=["encrypted_email", "encrypted_first_name", "encrypted_last_name"])


def reverse_encryption(apps, schema_editor):
    """
    Reverse migration - clear encrypted fields.
    """
    Profile = apps.get_model("web", "Profile")

    Profile.objects.all().update(encrypted_email="", encrypted_first_name="", encrypted_last_name="")


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0063_add_encrypted_user_fields"),
    ]

    operations = [
        migrations.RunPython(encrypt_user_data, reverse_encryption),
    ]
