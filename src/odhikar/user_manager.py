
import sqlite3

from uuid import uuid4
from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing

from src.odhikar.database import DB_PATH


# ==========================================
# 1. CENTRAL USER DATABASE PATH
# ==========================================

# All user data now uses the central database.

USER_DB_PATH = Path(DB_PATH)


# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

def get_connection():

    conn = sqlite3.connect(
        str(USER_DB_PATH),
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    # Enable foreign key enforcement.
    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    # Handle concurrent database access.
    conn.execute(
        "PRAGMA busy_timeout = 30000"
    )

    return conn


# ==========================================
# 3. INITIALIZE USER TABLES
# ==========================================

def initialize_user_db():

    USER_DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with closing(get_connection()) as conn:

        with conn:

            conn.executescript("""

                CREATE TABLE IF NOT EXISTS users (

                    user_id TEXT PRIMARY KEY,

                    display_name TEXT NOT NULL,

                    created_at TEXT NOT NULL

                );


                CREATE TABLE IF NOT EXISTS user_threads (

                    thread_id TEXT PRIMARY KEY,

                    user_id TEXT NOT NULL,

                    created_at TEXT NOT NULL,

                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE

                );


                CREATE INDEX IF NOT EXISTS
                idx_user_threads_user_id

                ON user_threads(user_id);

            """)


# Initialize central user tables.
initialize_user_db()


# ==========================================
# 4. CREATE NEW USER
# ==========================================

def create_user(display_name: str) -> dict:

    if not isinstance(display_name, str):
        raise ValueError(
            "Display name must be text."
        )

    display_name = display_name.strip()

    if not display_name:
        raise ValueError(
            "Display name is required."
        )

    user_id = f"user_{uuid4().hex}"

    created_at = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    with closing(get_connection()) as conn:

        with conn:

            conn.execute("""

                INSERT INTO users (
                    user_id,
                    display_name,
                    created_at
                )

                VALUES (?, ?, ?)

            """, (
                user_id,
                display_name,
                created_at
            ))

    return {
        "user_id": user_id,
        "display_name": display_name,
        "created_at": created_at
    }


# ==========================================
# 5. GET USER INFORMATION
# ==========================================

def get_user(user_id: str):

    if not isinstance(user_id, str):
        return None

    user_id = user_id.strip()

    if not user_id:
        return None

    with closing(get_connection()) as conn:

        record = conn.execute("""

            SELECT *
            FROM users
            WHERE user_id = ?

        """, (user_id,)).fetchone()

    if record is None:
        return None

    return dict(record)


# ==========================================
# 6. CREATE USER CONVERSATION
# ==========================================

def create_user_thread(user_id: str):

    if not isinstance(user_id, str):
        raise ValueError("Valid User ID required.")

    user_id = user_id.strip()

    user = get_user(user_id)

    if user is None:
        raise ValueError("User not found.")

    # Generate unique conversation ID.
    thread_id = f"odhikar_{uuid4().hex}"

    created_at = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    with closing(get_connection()) as conn:

        with conn:

            conn.execute("""

                INSERT INTO user_threads (
                    thread_id,
                    user_id,
                    created_at
                )

                VALUES (?, ?, ?)

            """, (
                thread_id,
                user_id,
                created_at
            ))

    return thread_id


# ==========================================
# 7. LIST USER CONVERSATIONS
# ==========================================

def list_user_threads(user_id: str) -> list:

    if not isinstance(user_id, str):
        return []

    user_id = user_id.strip()

    if not user_id:
        return []

    with closing(get_connection()) as conn:

        records = conn.execute("""

            SELECT *
            FROM user_threads
            WHERE user_id = ?
            ORDER BY created_at DESC

        """, (user_id,)).fetchall()

    return [
        dict(record)
        for record in records
    ]


# ==========================================
# 8. DELETE USER THREAD RECORD
# ==========================================

def delete_user_thread_record(
    user_id: str,
    thread_id: str
) -> bool:

    if not isinstance(user_id, str):
        return False

    if not isinstance(thread_id, str):
        return False

    user_id = user_id.strip()
    thread_id = thread_id.strip()

    if not user_id or not thread_id:
        return False

    with closing(get_connection()) as conn:

        with conn:

            cursor = conn.execute("""

                DELETE FROM user_threads

                WHERE user_id = ?

                AND thread_id = ?

            """, (
                user_id,
                thread_id
            ))

            return cursor.rowcount > 0
