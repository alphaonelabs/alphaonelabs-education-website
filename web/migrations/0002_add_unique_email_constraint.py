# Updated migration file for cross-database compatibility
from django.db import connection, migrations
from django.db.models import Count


def deduplicate_emails(apps, schema_editor):
    """
    Handle duplicate emails by appending _id to duplicate entries
    """
    # Get the User model from the migrations
    User = apps.get_model("auth", "User")

    # Find emails that are duplicated
    duplicate_emails = (
        User.objects.values("email").annotate(count=Count("id")).filter(count__gt=1).values_list("email", flat=True)
    )

    for email in duplicate_emails:
        # Find all users with this email except the first one
        users_with_email = User.objects.filter(email=email).order_by("id")
        first_user = users_with_email.first()

        # Update all other users with this email
        for user in users_with_email.exclude(id=first_user.id):
            user.email = f"{user.email}_{user.id}"
            user.save()


def add_unique_constraint(apps, schema_editor):
    """
    Add a unique constraint to the email field
    """
    # Check database type to handle SQLite differently
    db_engine = connection.vendor

    with connection.cursor() as cursor:
        if db_engine == "sqlite":
            # For SQLite, use the SQLite-specific syntax (without rowid references)
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique ON auth_user(email);")
        else:
            # For other databases like MySQL or PostgreSQL
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique ON auth_user(email);")


def remove_unique_constraint(apps, schema_editor):
    """
    Remove the unique constraint from the email field
    """
    # Drop the unique index directly using the database connection
    with connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS auth_user_email_unique;")


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(deduplicate_emails, migrations.RunPython.noop),
        migrations.RunPython(add_unique_constraint, remove_unique_constraint),
    ]
