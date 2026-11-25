
"""
ODHIKAR BD
PostgreSQL Session Manager

Primary database:
    Neon PostgreSQL

Driver:
    Psycopg 3

Connection management:
    Central PostgreSQL ConnectionPool

Security:
    Cryptographically secure session tokens
    SHA-256 token hashing
    Server-side session validation
    Session expiration
    Session revocation

Features:
    - Session initialization
    - Session creation
    - Session validation
    - Login with session
    - Logout current session
    - Logout all user sessions
"""

# ==========================================
# 1. IMPORTS
# ==========================================

import secrets
import hashlib

from datetime import (
    datetime,
    timezone,
    timedelta
)

from src.odhikar.database import (
    get_db_connection
)

from src.odhikar.auth_manager import (
    login_user,
    initialize_auth_db
)


# ==========================================
# 2. SESSION CONFIGURATION
# ==========================================

DEFAULT_SESSION_HOURS = 24

MAX_SESSION_HOURS = 720

SESSION_TOKEN_LENGTH = 32


# ==========================================
# 3. INITIALIZE SESSION DATABASE
# ==========================================

def initialize_session_db():
    """
    Verify the existing PostgreSQL session schema.

    Existing sessions are preserved.
    No existing records are overwritten.
    """

    initialize_auth_db()

    required_columns = {
        "token_hash",
        "user_id",
        "created_at",
        "expires_at",
        "revoked_at"
    }

    with get_db_connection() as conn:

        rows = conn.execute("""
            SELECT column_name

            FROM information_schema.columns

            WHERE table_schema = 'public'

            AND table_name = 'user_sessions'

        """).fetchall()

        existing_columns = {
            row["column_name"]
            for row in rows
        }

        missing_columns = (
            required_columns - existing_columns
        )

        if missing_columns:

            raise RuntimeError(
                "Missing PostgreSQL session columns: "
                + ", ".join(sorted(missing_columns))
            )

    print(
        "PostgreSQL session schema verified."
    )


# ==========================================
# 4. HASH SESSION TOKEN
# ==========================================

def hash_session_token(token: str) -> str:
    """
    Generate SHA-256 hash of session token.

    Original token is never stored in database.
    """

    if not isinstance(token, str) or not token:

        raise ValueError(
            "Valid session token is required."
        )

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


# ==========================================
# 5. CREATE SESSION
# ==========================================

def create_session(
    user_id: str,
    expires_hours: int = DEFAULT_SESSION_HOURS
) -> str:
    """
    Create a secure PostgreSQL session.

    Only the SHA-256 token hash is stored.
    Original token is returned once.
    """

    if not isinstance(user_id, str) or not user_id.strip():

        raise ValueError(
            "Valid User ID is required."
        )

    if (
        not isinstance(expires_hours, int)
        or isinstance(expires_hours, bool)
        or not 1 <= expires_hours <= MAX_SESSION_HOURS
    ):

        raise ValueError(
            "Session duration must be 1-720 hours."
        )

    # Generate cryptographically secure token.

    session_token = secrets.token_urlsafe(
        SESSION_TOKEN_LENGTH
    )

    # Store only its SHA-256 hash.

    token_hash = hash_session_token(
        session_token
    )

    now = datetime.now(
        timezone.utc
    )

    created_at = now.isoformat(
        timespec="seconds"
    )

    expires_at = (
        now + timedelta(hours=expires_hours)
    ).isoformat(
        timespec="seconds"
    )

    with get_db_connection() as conn:

        # Verify user exists.

        user = conn.execute("""

            SELECT user_id

            FROM users

            WHERE user_id = %s

        """, (
            user_id.strip(),
        )).fetchone()

        if user is None:

            raise ValueError(
                "User not found."
            )

        # Insert session.

        conn.execute("""

            INSERT INTO user_sessions (

                token_hash,

                user_id,

                created_at,

                expires_at,

                revoked_at

            )

            VALUES (%s, %s, %s, %s, NULL)

        """, (
            token_hash,
            user_id.strip(),
            created_at,
            expires_at
        ))

    return session_token


# ==========================================
# 6. VALIDATE SESSION
# ==========================================

def validate_session(session_token: str):
    """
    Validate an existing session.

    Returns user information if valid.
    Returns None if invalid, expired or revoked.
    """

    if (
        not isinstance(session_token, str)
        or not session_token
        or len(session_token) > 256
    ):

        return None

    token_hash = hash_session_token(
        session_token
    )

    now = datetime.now(
        timezone.utc
    )

    now_string = now.isoformat(
        timespec="seconds"
    )

    with get_db_connection() as conn:

        record = conn.execute("""

            SELECT

                u.user_id,

                u.display_name,

                u.created_at,

                c.email,

                s.expires_at

            FROM user_sessions s

            INNER JOIN users u

            ON s.user_id = u.user_id

            INNER JOIN user_credentials c

            ON u.user_id = c.user_id

            WHERE s.token_hash = %s

            AND s.revoked_at IS NULL

        """, (
            token_hash,
        )).fetchone()

        if record is None:

            return None

        # Parse expiration time.

        try:

            expires_at = datetime.fromisoformat(
                record["expires_at"]
            )

            # Handle legacy timestamps without timezone.

            if expires_at.tzinfo is None:

                expires_at = expires_at.replace(
                    tzinfo=timezone.utc
                )

        except (ValueError, TypeError):

            # Fail closed if stored expiration is invalid.

            conn.execute("""

                UPDATE user_sessions

                SET revoked_at = %s

                WHERE token_hash = %s

                AND revoked_at IS NULL

            """, (
                now_string,
                token_hash
            ))

            return None

        # Revoke expired sessions.

        if expires_at <= now:

            conn.execute("""

                UPDATE user_sessions

                SET revoked_at = %s

                WHERE token_hash = %s

                AND revoked_at IS NULL

            """, (
                now_string,
                token_hash
            ))

            return None

        return {

            "user_id": record["user_id"],

            "display_name": record["display_name"],

            "email": record["email"],

            "created_at": record["created_at"],

            "session_expires_at": record["expires_at"]
        }


# ==========================================
# 7. LOGIN WITH SESSION
# ==========================================

def login_with_session(
    email: str,
    password: str
):
    """
    Authenticate user and create session.
    """

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
# 8. LOGOUT CURRENT SESSION
# ==========================================

def logout_session(session_token: str) -> bool:
    """
    Revoke the current session.
    """

    if (
        not isinstance(session_token, str)
        or not session_token
        or len(session_token) > 256
    ):

        return False

    token_hash = hash_session_token(
        session_token
    )

    now = datetime.now(
        timezone.utc
    ).isoformat(
        timespec="seconds"
    )

    with get_db_connection() as conn:

        cursor = conn.execute("""

            UPDATE user_sessions

            SET revoked_at = %s

            WHERE token_hash = %s

            AND revoked_at IS NULL

        """, (
            now,
            token_hash
        ))

        return cursor.rowcount > 0


# ==========================================
# 9. LOGOUT ALL USER SESSIONS
# ==========================================

def logout_all_sessions(user_id: str) -> int:
    """
    Revoke every active session belonging
    to a particular user.
    """

    if not isinstance(user_id, str) or not user_id.strip():

        return 0

    now = datetime.now(
        timezone.utc
    ).isoformat(
        timespec="seconds"
    )

    with get_db_connection() as conn:

        cursor = conn.execute("""

            UPDATE user_sessions

            SET revoked_at = %s

            WHERE user_id = %s

            AND revoked_at IS NULL

        """, (
            now,
            user_id.strip()
        ))

        return cursor.rowcount


# ==========================================
# 10. SESSION MANAGER INFORMATION
# ==========================================

def get_session_manager_info() -> dict:

    return {

        "module": "Odhikar BD Session Manager",

        "database": "Neon PostgreSQL",

        "driver": "Psycopg 3",

        "connection_pool": True,

        "token_hash": "SHA-256",

        "default_session_hours": DEFAULT_SESSION_HOURS,

        "maximum_session_hours": MAX_SESSION_HOURS,

        "secure_token_generation": True,

        "session_validation": True,

        "session_revocation": True,

        "legacy_sqlite": False
    }


# ==========================================
# 11. INITIALIZE SESSION SYSTEM
# ==========================================

initialize_session_db()


# ==========================================
# 12. DIRECT EXECUTION
# ==========================================

if __name__ == "__main__":

    print("=" * 55)

    print(
        "ODHIKAR BD POSTGRESQL SESSION MANAGER"
    )

    print("=" * 55)

    try:

        print(
            "\nSESSION MANAGER INFORMATION:"
        )

        print(
            get_session_manager_info()
        )

        with get_db_connection() as conn:

            result = conn.execute("""

                SELECT

                    COUNT(*) AS total_sessions,

                    COUNT(*) FILTER (
                        WHERE revoked_at IS NULL
                    ) AS active_sessions

                FROM user_sessions

            """).fetchone()

        print(
            "\nTOTAL SESSIONS:",
            result["total_sessions"]
        )

        print(
            "ACTIVE SESSIONS:",
            result["active_sessions"]
        )

        print(
            "\nSESSION SCHEMA: VERIFIED"
        )

        print(
            "SESSION MANAGER TEST COMPLETED."
        )

    finally:

        from src.odhikar.database import close_db_pool

        close_db_pool()
