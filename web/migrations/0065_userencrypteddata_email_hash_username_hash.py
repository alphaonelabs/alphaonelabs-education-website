from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0064_userencrypteddata"),
    ]

    operations = [
        migrations.AddField(
            model_name="userencrypteddata",
            name="email_hash",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="userencrypteddata",
            name="username_hash",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
    ]
