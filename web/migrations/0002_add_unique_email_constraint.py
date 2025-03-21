# Updated migration file for SQLite compatibility
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL - Add unique constraint after handling duplicates (SQLite compatible)
            """
            -- Find and update duplicate emails
            UPDATE auth_user
            SET email = email || '_' || rowid
            WHERE email IN (
                SELECT email
                FROM auth_user
                GROUP BY email
                HAVING COUNT(*) > 1
            )
            AND rowid NOT IN (
                SELECT MIN(rowid)
                FROM auth_user
                GROUP BY email
                HAVING COUNT(*) > 1
            );

            -- Add unique index on email
            CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique ON auth_user(email);
            """,
            # Reverse SQL - Remove unique constraint
            "DROP INDEX IF EXISTS auth_user_email_unique;",
        )
    ]
