
"""
ODHIKAR BD
PostgreSQL User Management

Primary database:
    Neon PostgreSQL

Driver:
    Psycopg 3

Connection management:
    Central PostgreSQL ConnectionPool

Features:
    - User creation
    - User information retrieval
    - Conversation creation
    - Conversation listing
    - Conversation record deletion

Legacy SQLite user management is no longer used
by this module.
"""

# ==========================================
# 1. IMPORTS
# ==========================================

from uuid import uuid4

from datetime import datetime, timezone

from contextlib import contextmanager

from src.odhikar.database import (
    get_db_connection
)


# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

@contextmanager
def get_connection():
    """
    Provide a PostgreSQL connection through
    the central connection pool.

    Transactions are committed on success
    and rolled back on failure.
    """

    with get_db_connection() as conn:

        yield conn


# ==========================================
# 3. INITIALIZE USER TABLES
# ==========================================

def initialize_user_db():
    """
    Verify that the migrated PostgreSQL
    user tables exist.

    Existing records are preserved.
    No tables or records are deleted.
    """

    required_tables = {
        "users",
        "user_threads"
    }

    with get_db_connection() as conn:

        rows = conn.execute("""
            SELECT table_name

            FROM information_schema.tables

            WHERE table_schema = 'public'

            AND table_type = 'BASE TABLE'

            AND table_name IN (
                'users',
                'user_threads'
            )

        """).fetchall()

        existing_tables = {
            row["table_name"]
            for row in rows
        }

        missing_tables = (
            required_tables - existing_tables
        )

        if missing_tables:

            raise RuntimeError(
                "Missing PostgreSQL user tables: "
                + ", ".join(sorted(missing_tables))
            )

    print(
        "PostgreSQL user tables verified."
    )


# Initialize PostgreSQL user system.

initialize_user_db()


# ==========================================
# 4. CREATE NEW USER
# ==========================================

def create_user(display_name: str) -> dict:
    """
    Create a new user in PostgreSQL.
    """

    if not isinstance(display_name, str):

        raise ValueError(
            "Display name must be text."
        )

    display_name = display_name.strip()

    if not display_name:

        raise ValueError(
            "Display name is required."
        )

    if len(display_name) > 150:

        raise ValueError(
            "Display name cannot exceed 150 characters."
        )

    user_id = f"user_{uuid4().hex}"

    created_at = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    with get_db_connection() as conn:

        conn.execute("""

            INSERT INTO users (
                user_id,
                display_name,
                created_at
            )

            VALUES (%s, %s, %s)

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
    """
    Retrieve user information.
    """

    if not isinstance(user_id, str):

        return None

    user_id = user_id.strip()

    if not user_id:

        return None

    with get_db_connection() as conn:

        record = conn.execute("""

            SELECT
                user_id,
                display_name,
                created_at

            FROM users

            WHERE user_id = %s

        """, (
            user_id,
        )).fetchone()

    if record is None:

        return None

    return dict(record)


# ==========================================
# 6. CREATE USER CONVERSATION
# ==========================================

def create_user_thread(user_id: str):
    """
    Create a new conversation for a user.
    """

    if not isinstance(user_id, str):

        raise ValueError(
            "Valid User ID required."
        )

    user_id = user_id.strip()

    if not user_id:

        raise ValueError(
            "Valid User ID required."
        )

    thread_id = (
        f"odhikar_{uuid4().hex}"
    )

    created_at = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    with get_db_connection() as conn:

        user = conn.execute("""

            SELECT user_id

            FROM users

            WHERE user_id = %s

        """, (
            user_id,
        )).fetchone()

        if user is None:

            raise ValueError(
                "User not found."
            )

        conn.execute("""

            INSERT INTO user_threads (
                thread_id,
                user_id,
                created_at
            )

            VALUES (%s, %s, %s)

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
    """
    Retrieve all conversations belonging
    to a particular user.
    """

    if not isinstance(user_id, str):

        return []

    user_id = user_id.strip()

    if not user_id:

        return []

    with get_db_connection() as conn:

        records = conn.execute("""

            SELECT
                thread_id,
                user_id,
                created_at

            FROM user_threads

            WHERE user_id = %s

            ORDER BY created_at DESC

        """, (
            user_id,
        )).fetchall()

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
    """
    Delete a conversation ownership record.

    This does not delete LangGraph checkpoints.
    """

    if not isinstance(user_id, str):

        return False

    if not isinstance(thread_id, str):

        return False

    user_id = user_id.strip()

    thread_id = thread_id.strip()

    if not user_id or not thread_id:

        return False

    with get_db_connection() as conn:

        cursor = conn.execute("""

            DELETE FROM user_threads

            WHERE user_id = %s

            AND thread_id = %s

        """, (
            user_id,
            thread_id
        ))

        return cursor.rowcount > 0


# ==========================================
# 9. MODULE INFORMATION
# ==========================================

def get_user_manager_info() -> dict:

    return {

        "module": "Odhikar BD User Manager",

        "database": "Neon PostgreSQL",

        "driver": "Psycopg 3",

        "connection_pool": True,

        "user_creation": True,

        "user_retrieval": True,

        "conversation_management": True,

        "legacy_sqlite": False
    }


# ==========================================
# 10. DIRECT EXECUTION
# ==========================================

if __name__ == "__main__":

    print("=" * 55)

    print(
        "ODHIKAR BD POSTGRESQL USER MANAGER"
    )

    print("=" * 55)

    try:

        initialize_user_db()

        print(
            "\nUSER MANAGER INFORMATION:"
        )

        print(
            get_user_manager_info()
        )

        print(
            "\nEXISTING USER COUNT:"
        )

        with get_db_connection() as conn:

            result = conn.execute("""

                SELECT COUNT(*) AS total

                FROM users

            """).fetchone()

            print(
                result["total"]
            )

        print(
            "\nUSER MANAGER TEST COMPLETED."
        )

    finally:

        from src.odhikar.database import close_db_pool

        close_db_pool()
