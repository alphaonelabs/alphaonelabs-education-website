# Generated by Django 5.1.6 on 2025-03-25 05:03

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0049_merge_migration_paths"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="userbadge",
            options={"ordering": ["-awarded_at"]},
        ),
    ]
