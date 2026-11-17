
import sqlite3
from pathlib import Path


# Find project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Database file location
DB_PATH = PROJECT_ROOT / "data" / "processed" / "odhikar.db"


def init_db():

    # Create database directory
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    with sqlite3.connect(DB_PATH) as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS offences (
                offence_id TEXT PRIMARY KEY,
                name_en TEXT NOT NULL,
                name_bn TEXT NOT NULL,
                aliases_banglish TEXT NOT NULL DEFAULT '[]',
                section TEXT NOT NULL,
                max_fine_bdt INTEGER,
                max_imprisonment TEXT,
                bailable INTEGER,
                vehicle_types TEXT NOT NULL DEFAULT '[]',
                law_status TEXT NOT NULL,
                source_url TEXT NOT NULL,
                last_verified TEXT NOT NULL,
                additional_penalty TEXT
            )
        """)

    print("Database created successfully!")


if __name__ == "__main__":
    init_db()
