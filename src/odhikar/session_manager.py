
import sqlite3
import secrets
import hashlib

from datetime import datetime, timezone, timedelta
from contextlib import closing

from src.odhikar.user_manager import get_connection
from src.odhikar.auth_manager import (
    login_user,
    initialize_auth_db
)


# ==========================================
# 1. SESSION CONFIGURATION
# ==========================================

DEFAULT_SESSION_HOURS = 24


# ==========================================
# 2. INITIALIZE SESSION DATABASE
# ==========================================

def initialize_session_db():

    initialize_auth_db()

    with closing(get_connection()) as conn:

        with conn:

            conn.execute("""

                CREATE TABLE IF NOT EXISTS user_sessions (

                    token_hash TEXT PRIMARY KEY,

                    user_id TEXT NOT NULL,

                    created_at TEXT NOT NULL,

                    expires_at TEXT NOT NULL,

                    revoked_at TEXT,

                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE

                )

            """)

            conn.execute("""

                CREATE INDEX IF NOT EXISTS
                idx_user_sessions_user_id

                ON user_sessions(user_id)

            """)


# ==========================================
# 3. HASH SESSION TOKEN
# ==========================================

def hash_session_token(token: str) -> str:

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


# ==========================================
# 4. CREATE SESSION
# ==========================================

def create_session(
    user_id: str,
    expires_hours: int = DEFAULT_SESSION_HOURS
) -> str:

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Valid User ID is required.")

    if (
        not isinstance(expires_hours, int)
        or isinstance(expires_hours, bool)
        or not 1 <= expires_hours <= 720
    ):
        raise ValueError("Session duration must be 1-720 hours.")

    # Generate a secure random token
    session_token = secrets.token_urlsafe(32)

    # Store only its hash
    token_hash = hash_session_token(session_token)

    now = datetime.now(timezone.utc)

    created_at = now.isoformat(timespec="seconds")

    expires_at = (
        now + timedelta(hours=expires_hours)
    ).isoformat(timespec="seconds")

    with closing(get_connection()) as conn:

        with conn:

            conn.execute("""

                INSERT INTO user_sessions (
                    token_hash,
                    user_id,
                    created_at,
                    expires_at,
                    revoked_at
                )

                VALUES (?, ?, ?, ?, NULL)

            """, (
                token_hash,
                user_id.strip(),
                created_at,
                expires_at
            ))

    # Return original token only once
    return session_token


# ==========================================
# 5. VALIDATE SESSION
# ==========================================

def validate_session(session_token: str):

    if (
        not isinstance(session_token, str)
        or not session_token
        or len(session_token) > 256
    ):
        return None

    token_hash = hash_session_token(session_token)

    with closing(get_connection()) as conn:

        record = conn.execute("""

            SELECT
                u.user_id,
                u.display_name,
                u.created_at,
                c.email,
                s.expires_at

            FROM user_sessions s

            JOIN users u
            ON s.user_id = u.user_id

            JOIN user_credentials c
            ON u.user_id = c.user_id

            WHERE s.token_hash = ?
            AND s.revoked_at IS NULL

        """, (token_hash,)).fetchone()

        if record is None:
            return None

        expires_at = datetime.fromisoformat(
            record["expires_at"]
        )

        now = datetime.now(timezone.utc)

        if expires_at <= now:

            conn.execute("""

                UPDATE user_sessions

                SET revoked_at = ?

                WHERE token_hash = ?
                AND revoked_at IS NULL

            """, (
                now.isoformat(timespec="seconds"),
                token_hash
            ))

            conn.commit()

            return None

        return {
            "user_id": record["user_id"],
            "display_name": record["display_name"],
            "email": record["email"],
            "created_at": record["created_at"],
            "session_expires_at": record["expires_at"]
        }


# ==========================================
# 6. LOGIN WITH SESSION
# ==========================================

def login_with_session(
    email: str,
    password: str
):

    user = login_user(
        email,
        password
    )

    if user is None:
        return None

    session_token = create_session(
        user["user_id"]
    )

    return {
        "user": user,
        "session_token": session_token
    }


# ==========================================
# 7. LOGOUT CURRENT SESSION
# ==========================================

def logout_session(session_token: str) -> bool:

    if (
        not isinstance(session_token, str)
        or not session_token
        or len(session_token) > 256
    ):
        return False

    token_hash = hash_session_token(session_token)

    now = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    with closing(get_connection()) as conn:

        with conn:

            cursor = conn.execute("""

                UPDATE user_sessions

                SET revoked_at = ?

                WHERE token_hash = ?
                AND revoked_at IS NULL

            """, (
                now,
                token_hash
            ))

            return cursor.rowcount > 0


# ==========================================
# 8. LOGOUT ALL USER SESSIONS
# ==========================================

def logout_all_sessions(user_id: str) -> int:

    if not isinstance(user_id, str) or not user_id.strip():
        return 0

    now = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    with closing(get_connection()) as conn:

        with conn:

            cursor = conn.execute("""

                UPDATE user_sessions

                SET revoked_at = ?

                WHERE user_id = ?
                AND revoked_at IS NULL

            """, (
                now,
                user_id.strip()
            ))

            return cursor.rowcount


# ==========================================
# 9. INITIALIZE SESSION SYSTEM
# ==========================================

initialize_session_db()
