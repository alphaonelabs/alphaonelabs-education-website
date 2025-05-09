# Generated by Django 5.1.6 on 2025-04-10 03:30

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0056_forumvote"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="educationalvideo",
            name="uploader",
            field=models.ForeignKey(
                blank=True,
                help_text="User who uploaded the video. If null, the submission is considered anonymous.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="educational_videos",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
