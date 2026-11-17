
import sqlite3

from src.odhikar.database import DB_PATH


# Connect to database
with sqlite3.connect(DB_PATH) as conn:

    # Get table information
    columns = conn.execute(
        "PRAGMA table_info(offences)"
    ).fetchall()

    print("Database:", DB_PATH)
    print("\nOffences Table Columns:")

    for column in columns:
        print(column[1])

    print("\nTotal columns:", len(columns))

    if len(columns) == 12:
        print("Database verification successful!")
    else:
        print("Database structure needs checking.")
