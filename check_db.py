import sqlite3

connection = sqlite3.connect("cineverse.db")
cursor = connection.cursor()

for table in ["watchlist", "completed"]:
    print(f"\nTable: {table}")
    cursor.execute(f"PRAGMA table_info({table})")
    for column in cursor.fetchall():
        print(column)

connection.close()