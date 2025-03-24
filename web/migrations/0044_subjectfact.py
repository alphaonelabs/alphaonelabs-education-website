# Generated by Django 5.1.6 on 2025-03-24 13:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0043_alter_studygroup_members_studygroupinvite"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubjectFact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fact_text", models.TextField()),
                ("generated_at", models.DateTimeField(auto_now_add=True)),
                (
                    "subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="facts", to="web.subject"
                    ),
                ),
            ],
            options={
                "ordering": ["-generated_at"],
                "unique_together": {("subject", "fact_text")},
            },
        ),
    ]
