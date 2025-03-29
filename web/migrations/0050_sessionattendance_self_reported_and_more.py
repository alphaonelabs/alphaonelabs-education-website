# Generated by Django 5.1.6 on 2025-03-29 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0049_session_latitude_session_longitude_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessionattendance",
            name="self_reported",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="sessionattendance",
            name="verified_by_teacher",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="sessionattendance",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Verification"),
                    ("present", "Present"),
                    ("absent", "Absent"),
                    ("excused", "Excused"),
                    ("late", "Late"),
                ],
                default="absent",
                max_length=10,
            ),
        ),
    ]
