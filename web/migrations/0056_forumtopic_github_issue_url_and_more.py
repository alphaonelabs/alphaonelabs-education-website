# Generated by Django 5.1.6 on 2025-04-09 04:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0055_peermessage_encrypted_key_peermessage_read_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="forumtopic",
            name="github_issue_url",
            field=models.URLField(blank=True, help_text="Link to related GitHub issue"),
        ),
        migrations.AddField(
            model_name="forumtopic",
            name="github_milestone_url",
            field=models.URLField(blank=True, help_text="Link to related GitHub milestone"),
        ),
    ]
