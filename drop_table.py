import sqlite3

db_path = "db.sqlite3"  # Replace with the path to your database if different

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE web_response;")
    conn.commit()
    print("Table 'web_response' dropped successfully.")
except sqlite3.OperationalError as e:
    print(f"Error: {e}")
except sqlite3.Error as e:
    print(f"An error occurred: {e}")
finally:
    if conn:
        conn.close()