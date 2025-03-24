# Generated by Django 5.1.6 on 2025-03-24 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0043_alter_studygroup_members_studygroupinvite"),
    ]

    operations = [
        migrations.AddField(
            model_name="subject",
            name="facts",
            field=models.JSONField(blank=True, default=list, help_text="List of facts about this subject"),
        ),
    ]
