# Generated by Django 5.1.6 on 2025-03-26 17:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0045_add_membership_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="is_featured",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
