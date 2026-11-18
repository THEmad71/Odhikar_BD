
import sqlite3
import re
import secrets
import hmac

from hashlib import pbkdf2_hmac
from uuid import uuid4
from datetime import datetime, timezone
from contextlib import closing

from src.odhikar.user_manager import (
    get_connection,
    initialize_user_db
)


# ==========================================
# 1. AUTHENTICATION CONFIGURATION
# ==========================================

HASH_ALGORITHM = "sha256"

PBKDF2_ITERATIONS = 600_000

SALT_LENGTH = 16

PASSWORD_MIN_LENGTH = 12


# ==========================================
# 2. INITIALIZE AUTH DATABASE
# ==========================================

def initialize_auth_db():

    initialize_user_db()

    with closing(get_connection()) as conn:

        with conn:

            conn.execute("""

                CREATE TABLE IF NOT EXISTS user_credentials (

                    user_id TEXT PRIMARY KEY,

                    email TEXT NOT NULL UNIQUE,

                    password_hash TEXT NOT NULL,

                    created_at TEXT NOT NULL,

                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE

                )

            """)


# ==========================================
# 3. VALIDATE EMAIL
# ==========================================

def validate_email(email: str) -> str:

    if not isinstance(email, str):
        raise ValueError("Email must be text.")

    email = email.strip().lower()

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.fullmatch(pattern, email):
        raise ValueError("Invalid email address.")

    return email


# ==========================================
# 4. HASH PASSWORD
# ==========================================

def hash_password(password: str) -> str:

    if not isinstance(password, str):
        raise ValueError("Password must be text.")

    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            "Password must contain at least 12 characters."
        )

    salt = secrets.token_bytes(SALT_LENGTH)

    password_hash = pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS
    )

    return (
        f"pbkdf2_sha256$"
        f"{PBKDF2_ITERATIONS}$"
        f"{salt.hex()}$"
        f"{password_hash.hex()}"
    )


# ==========================================
# 5. VERIFY PASSWORD
# ==========================================

def verify_password(
    password: str,
    stored_hash: str
) -> bool:

    if not isinstance(password, str):
        return False

    try:

        algorithm, iterations, salt_hex, hash_hex = (
            stored_hash.split("$")
        )

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations)

        if not 100_000 <= iterations <= 1_000_000:
            return False

        salt = bytes.fromhex(salt_hex)

        expected_hash = bytes.fromhex(hash_hex)

        if len(salt) != SALT_LENGTH:
            return False

        if len(expected_hash) != 32:
            return False

        calculated_hash = pbkdf2_hmac(
            HASH_ALGORITHM,
            password.encode("utf-8"),
            salt,
            iterations
        )

        return hmac.compare_digest(
            calculated_hash,
            expected_hash
        )

    except (ValueError, TypeError, AttributeError):
        return False


# ==========================================
# 6. REGISTER NEW USER
# ==========================================

def register_user(
    display_name: str,
    email: str,
    password: str
) -> dict:

    if not isinstance(display_name, str):
        raise ValueError("Display name must be text.")

    display_name = display_name.strip()

    if not display_name:
        raise ValueError("Display name is required.")

    email = validate_email(email)

    # Hash password before database storage
    password_hash = hash_password(password)

    user_id = f"user_{uuid4().hex}"

    created_at = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    try:

        with closing(get_connection()) as conn:

            with conn:

                # Create user
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

                # Save login credentials
                conn.execute("""

                    INSERT INTO user_credentials (
                        user_id,
                        email,
                        password_hash,
                        created_at
                    )

                    VALUES (?, ?, ?, ?)

                """, (
                    user_id,
                    email,
                    password_hash,
                    created_at
                ))

    except sqlite3.IntegrityError as exc:

        raise ValueError(
            "This email is already registered."
        ) from exc

    return {
        "user_id": user_id,
        "display_name": display_name,
        "email": email,
        "created_at": created_at
    }


# ==========================================
# 7. LOGIN USER
# ==========================================

def login_user(
    email: str,
    password: str
):

    try:
        email = validate_email(email)

    except ValueError:
        return None

    if not isinstance(password, str):
        return None

    with closing(get_connection()) as conn:

        record = conn.execute("""

            SELECT
                u.user_id,
                u.display_name,
                u.created_at,
                c.email,
                c.password_hash

            FROM users u

            JOIN user_credentials c
            ON u.user_id = c.user_id

            WHERE c.email = ?

        """, (email,)).fetchone()

    if record is None:
        return None

    if not verify_password(
        password,
        record["password_hash"]
    ):
        return None

    return {
        "user_id": record["user_id"],
        "display_name": record["display_name"],
        "email": record["email"],
        "created_at": record["created_at"]
    }


# ==========================================
# 8. INITIALIZE AUTHENTICATION
# ==========================================

initialize_auth_db()
