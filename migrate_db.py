
import sqlite3

from src.odhikar.database import DB_PATH


with sqlite3.connect(DB_PATH) as conn:

    # Get existing column names
    columns = conn.execute(
        "PRAGMA table_info(offences)"
    ).fetchall()

    column_names = [column[1] for column in columns]

    # Add new column if it does not exist
    if "additional_penalty" not in column_names:

        conn.execute("""
            ALTER TABLE offences
            ADD COLUMN additional_penalty TEXT
        """)

        print("New column added successfully!")

    else:
        print("Column already exists!")

    # Verify updated structure
    updated_columns = conn.execute(
        "PRAGMA table_info(offences)"
    ).fetchall()

    print("\nTotal Columns:", len(updated_columns))

    for column in updated_columns:
        print(column[1])
