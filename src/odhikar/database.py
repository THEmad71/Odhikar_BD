
import os
import sqlite3

from pathlib import Path
from dotenv import load_dotenv


# ==========================================
# 1. LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


# ==========================================
# 2. PROJECT ROOT
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ==========================================
# 3. CENTRAL DATABASE PATH
# ==========================================

DEFAULT_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "odhikar.db"
)

configured_path = os.getenv("ODHIKAR_DB_PATH")

DB_PATH = Path(
    configured_path
).expanduser() if configured_path else DEFAULT_DB_PATH

if not DB_PATH.is_absolute():
    DB_PATH = PROJECT_ROOT / DB_PATH

DB_PATH = DB_PATH.resolve()


# ==========================================
# 4. DATABASE INITIALIZATION
# ==========================================

def init_db():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with sqlite3.connect(
        DB_PATH,
        timeout=30
    ) as conn:

        conn.execute(
            "PRAGMA busy_timeout = 30000"
        )

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

        conn.commit()

    print("Database initialized:", DB_PATH)


# ==========================================
# 5. DIRECT EXECUTION
# ==========================================

if __name__ == "__main__":
    init_db()
