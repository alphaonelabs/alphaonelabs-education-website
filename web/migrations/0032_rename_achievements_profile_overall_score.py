# Generated by Django 5.1.6 on 2025-03-19 22:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0031_profile_achievements_profile_username_is_public"),
    ]

    operations = [
        migrations.RenameField(
            model_name="profile",
            old_name="achievements",
            new_name="overall_score",
        ),
    ]
