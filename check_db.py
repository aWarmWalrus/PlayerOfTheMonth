import sqlite3
import os

db_file = "data/bball_data.db"

print(f"Checking database: {db_file}")
if not os.path.exists(db_file):
    print(f"Database file {db_file} does not exist.")
    exit(1)

conn = None
try:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    print("\nTables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    if tables:
        for table in tables:
            print(f"- {table[0]}")
    else:
        print("No tables found.")

    table_names = [table[0] for table in tables]

    if "games" in table_names:
        cursor.execute("SELECT COUNT(*) FROM games;")
        print(f"\nCOUNT(*) FROM games: {cursor.fetchone()[0]}")
        cursor.execute("SELECT * FROM games LIMIT 3;")
        print("Sample from games:")
        for row in cursor.fetchall():
            print(row)
    else:
        print("\nTable 'games' not found.")

    if "player_stats" in table_names:
        cursor.execute("SELECT COUNT(*) FROM player_stats;")
        print(f"\nCOUNT(*) FROM player_stats: {cursor.fetchone()[0]}")
        cursor.execute("SELECT * FROM player_stats LIMIT 3;")
        print("Sample from player_stats:")
        for row in cursor.fetchall():
            print(row)
    else:
        print("\nTable 'player_stats' not found.")

    award_tables = ["player_of_the_month", "player_of_the_week", "rookie_of_the_month", "coach_of_the_month"]
    for award_table in award_tables:
        if award_table in table_names:
            cursor.execute(f"SELECT COUNT(*) FROM {award_table};")
            print(f"\nCOUNT(*) FROM {award_table}: {cursor.fetchone()[0]}")
        else:
            print(f"\nTable '{award_table}' not found.")

except sqlite3.Error as e:
    print(f"SQLite error: {e}")
finally:
    if conn:
        conn.close()

print("\nDatabase check complete.")
