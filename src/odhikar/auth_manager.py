
"""
ODHIKAR BD
PostgreSQL Authentication Manager

Primary database:
    Neon PostgreSQL

Driver:
    Psycopg 3

Security:
    PBKDF2-HMAC-SHA256
    600,000 iterations
    Random 16-byte salt
    Constant-time password comparison

Features:
    - Email validation
    - Password hashing
    - Password verification
    - User registration
    - User login

Existing password hashes are preserved.
"""

# ==========================================
# 1. IMPORTS
# ==========================================

import re
import secrets
import hmac

from hashlib import pbkdf2_hmac
from uuid import uuid4

from datetime import datetime, timezone

from psycopg.errors import UniqueViolation

from src.odhikar.database import (
    get_db_connection
)

from src.odhikar.user_manager import (
    initialize_user_db
)


# ==========================================
# 2. AUTHENTICATION CONFIGURATION
# ==========================================

HASH_ALGORITHM = "sha256"

PBKDF2_ITERATIONS = 600_000

SALT_LENGTH = 16

PASSWORD_MIN_LENGTH = 12

PASSWORD_HASH_PREFIX = "pbkdf2_sha256"


# ==========================================
# 3. INITIALIZE AUTH DATABASE
# ==========================================

def initialize_auth_db():
    """
    Verify the existing PostgreSQL authentication
    schema.

    This function does not recreate tables or
    overwrite existing credentials.
    """

    initialize_user_db()

    required_columns = {
        "user_id",
        "email",
        "password_hash",
        "created_at"
    }

    with get_db_connection() as conn:

        rows = conn.execute("""
            SELECT column_name

            FROM information_schema.columns

            WHERE table_schema = 'public'

            AND table_name = 'user_credentials'

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
                "Invalid user_credentials schema. "
                "Missing columns: "
                + ", ".join(sorted(missing_columns))
            )

    print(
        "PostgreSQL authentication schema verified."
    )


# ==========================================
# 4. VALIDATE EMAIL
# ==========================================

def validate_email(email: str) -> str:
    """
    Normalize and validate email addresses.
    """

    if not isinstance(email, str):

        raise ValueError(
            "Email must be text."
        )

    email = email.strip().lower()

    if len(email) > 254:

        raise ValueError(
            "Email address is too long."
        )

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.fullmatch(pattern, email):

        raise ValueError(
            "Invalid email address."
        )

    return email


# ==========================================
# 5. HASH PASSWORD
# ==========================================

def hash_password(password: str) -> str:
    """
    Generate a PBKDF2-SHA256 password hash.

    The original hash format is retained
    for compatibility with existing accounts.
    """

    if not isinstance(password, str):

        raise ValueError(
            "Password must be text."
        )

    if len(password) < PASSWORD_MIN_LENGTH:

        raise ValueError(
            "Password must contain at least 12 characters."
        )

    salt = secrets.token_bytes(
        SALT_LENGTH
    )

    password_hash = pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS
    )

    return (
        f"{PASSWORD_HASH_PREFIX}$"
        f"{PBKDF2_ITERATIONS}$"
        f"{salt.hex()}$"
        f"{password_hash.hex()}"
    )


# ==========================================
# 6. VERIFY PASSWORD
# ==========================================

def verify_password(
    password: str,
    stored_hash: str
) -> bool:
    """
    Verify a password against an existing
    PBKDF2-SHA256 hash.

    Supports the existing stored hash format.
    Does not modify or regenerate stored hashes.
    """

    if not isinstance(password, str):

        return False

    if not isinstance(stored_hash, str):

        return False

    try:

        algorithm, iterations, salt_hex, hash_hex = (
            stored_hash.split("$")
        )

        if algorithm != PASSWORD_HASH_PREFIX:

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

    except (
        ValueError,
        TypeError,
        AttributeError,
        OverflowError
    ):

        return False


# ==========================================
# 7. REGISTER NEW USER
# ==========================================

def register_user(
    display_name: str,
    email: str,
    password: str
) -> dict:
    """
    Register a new user.

    User and credential records are inserted
    within one PostgreSQL transaction.

    If either insertion fails, both are rolled back.
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

    email = validate_email(email)

    # Hash password before database storage.

    password_hash = hash_password(password)

    user_id = f"user_{uuid4().hex}"

    created_at = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    try:

        with get_db_connection() as conn:

            # ==================================
            # CREATE USER
            # ==================================

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

            # ==================================
            # SAVE LOGIN CREDENTIALS
            # ==================================

            conn.execute("""

                INSERT INTO user_credentials (

                    user_id,

                    email,

                    password_hash,

                    created_at

                )

                VALUES (%s, %s, %s, %s)

            """, (
                user_id,
                email,
                password_hash,
                created_at
            ))

    except UniqueViolation as exc:

        constraint_name = getattr(
            getattr(exc, "diag", None),
            "constraint_name",
            None
        )

        if (
            constraint_name == "user_credentials_email_key"
            or (
                constraint_name is None
                and "email" in str(exc).lower()
            )
        ):

            raise ValueError(
                "This email is already registered."
            ) from exc

        raise

    return {

        "user_id": user_id,

        "display_name": display_name,

        "email": email,

        "created_at": created_at
    }


# ==========================================
# 8. LOGIN USER
# ==========================================

def login_user(
    email: str,
    password: str
):
    """
    Authenticate an existing user.

    Existing password hashes are verified
    without modifying the database.
    """

    try:

        email = validate_email(email)

    except ValueError:

        return None

    if not isinstance(password, str):

        return None

    with get_db_connection() as conn:

        record = conn.execute("""

            SELECT

                u.user_id,

                u.display_name,

                u.created_at,

                c.email,

                c.password_hash

            FROM users u

            INNER JOIN user_credentials c

            ON u.user_id = c.user_id

            WHERE c.email = %s

        """, (
            email,
        )).fetchone()

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
# 9. AUTHENTICATION MODULE INFORMATION
# ==========================================

def get_auth_manager_info() -> dict:

    return {

        "module": "Odhikar BD Authentication Manager",

        "database": "Neon PostgreSQL",

        "driver": "Psycopg 3",

        "connection_pool": True,

        "password_algorithm": "PBKDF2-HMAC-SHA256",

        "iterations": PBKDF2_ITERATIONS,

        "salt_length": SALT_LENGTH,

        "existing_hash_compatibility": True,

        "legacy_sqlite": False
    }


# ==========================================
# 10. INITIALIZE AUTHENTICATION
# ==========================================

initialize_auth_db()


# ==========================================
# 11. DIRECT EXECUTION
# ==========================================

if __name__ == "__main__":

    print("=" * 55)

    print(
        "ODHIKAR BD POSTGRESQL AUTHENTICATION"
    )

    print("=" * 55)

    try:

        print(
            "\nAUTHENTICATION INFORMATION:"
        )

        print(
            get_auth_manager_info()
        )

        with get_db_connection() as conn:

            user_count = conn.execute("""

                SELECT COUNT(*) AS total

                FROM users

            """).fetchone()

            credential_count = conn.execute("""

                SELECT COUNT(*) AS total

                FROM user_credentials

            """).fetchone()

        print(
            "\nEXISTING USERS:",
            user_count["total"]
        )

        print(
            "EXISTING CREDENTIALS:",
            credential_count["total"]
        )

        print(
            "\nAUTHENTICATION SCHEMA: VERIFIED"
        )

        print(
            "AUTHENTICATION TEST COMPLETED."
        )

    finally:

        from src.odhikar.database import close_db_pool

        close_db_pool()
