# Generated by Django 5.1.6 on 2025-03-31 07:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0049_session_latitude_session_longitude_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='discord_username',
            field=models.CharField(blank=True, help_text='Your Discord username (e.g., User#1234)', max_length=50),
        ),
        migrations.AddField(
            model_name='profile',
            name='github_username',
            field=models.CharField(blank=True, help_text='Your GitHub username (without @)', max_length=50),
        ),
        migrations.AddField(
            model_name='profile',
            name='slack_username',
            field=models.CharField(blank=True, help_text='Your Slack username', max_length=50),
        ),
    ]
