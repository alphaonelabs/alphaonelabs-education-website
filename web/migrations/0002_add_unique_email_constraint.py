# Updated migration file
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL - Add unique constraint after handling duplicates
            """
            -- Create a temporary table to store duplicates
            CREATE TEMPORARY TABLE tmp_duplicates AS
            SELECT email FROM auth_user GROUP BY email HAVING COUNT(*) > 1;

            -- Create another temporary table to store the update information
            CREATE TEMPORARY TABLE tmp_updates AS
            SELECT 
                a.id,
                a.email,
                (SELECT COUNT(*) FROM auth_user b WHERE b.email = a.email AND b.id <= a.id) AS row_num
            FROM auth_user a
            JOIN tmp_duplicates d ON a.email = d.email;

            -- Update all but the first occurrence of each duplicate email
            UPDATE auth_user u
            JOIN tmp_updates t ON u.id = t.id
            SET u.email = CONCAT(u.email, '_', t.row_num - 1)
            WHERE t.row_num > 1;

            -- Drop temporary tables
            DROP TEMPORARY TABLE tmp_duplicates;
            DROP TEMPORARY TABLE tmp_updates;

            -- Check if index exists first, then create it
            SET @index_exists = (
                SELECT COUNT(1) 
                FROM information_schema.statistics 
                WHERE table_schema = DATABASE() 
                AND table_name = 'auth_user' 
                AND index_name = 'auth_user_email_unique'
            );
            
            SET @sql = IF(@index_exists = 0, 
                'CREATE UNIQUE INDEX auth_user_email_unique ON auth_user(email)', 
                'SELECT "Index already exists"'
            );
            
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            """,
            # Reverse SQL - Remove unique constraint
            "DROP INDEX IF EXISTS auth_user_email_unique ON auth_user;",
        )
    ]
