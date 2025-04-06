import sqlite3

db_path = "db.sqlite3"  # Replace with your database path if different
app_name = "web"  # Replace with your app name
migration_name = "0055_question_required_question_scale_max_and_more"  # Replace with your migration name

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    sql_command = f"DELETE FROM django_migrations WHERE app = '{app_name}' AND name = '{migration_name}';"
    cursor.execute(sql_command)
    conn.commit()
    print(f"Migration entry '{migration_name}' for app '{app_name}' deleted successfully.")
except sqlite3.OperationalError as e:
    print(f"Error: {e}")
except sqlite3.Error as e:
    print(f"An error occurred: {e}")
finally:
    if conn:
        conn.close()