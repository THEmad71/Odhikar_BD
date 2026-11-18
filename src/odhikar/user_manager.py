
import sqlite3

from uuid import uuid4
from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing

from src.odhikar.database import DB_PATH


# ==========================================
# 1. USER DATABASE PATH
# ==========================================

USER_DB_PATH = Path(DB_PATH).with_name(
    "odhikar_users.sqlite"
)


# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

def get_connection():

    conn = sqlite3.connect(
        str(USER_DB_PATH),
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# ==========================================
# 3. INITIALIZE USER DATABASE
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


# Initialize database
initialize_user_db()


# ==========================================
# 4. CREATE NEW USER
# ==========================================

def create_user(display_name: str) -> dict:

    if not isinstance(display_name, str):
        raise ValueError("Display name must be text.")

    display_name = display_name.strip()

    if not display_name:
        raise ValueError("Display name is required.")

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

    with closing(get_connection()) as conn:

        record = conn.execute("""

            SELECT *
            FROM users
            WHERE user_id = ?

        """, (user_id.strip(),)).fetchone()

    if record is None:
        return None

    return dict(record)


# ==========================================
# 6. CREATE USER CONVERSATION
# ==========================================

def create_user_thread(user_id: str):

    user = get_user(user_id)

    if user is None:
        raise ValueError("User not found.")

    # Generate a unique conversation ID
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

    with closing(get_connection()) as conn:

        records = conn.execute("""

            SELECT *
            FROM user_threads
            WHERE user_id = ?
            ORDER BY created_at DESC

        """, (user_id.strip(),)).fetchall()

    return [
        dict(record)
        for record in records
    ]
