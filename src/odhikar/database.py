
"""
ODHIKAR BD
Central Database Management

Primary database:
    Neon PostgreSQL

Driver:
    Psycopg 3

Connection management:
    Psycopg ConnectionPool

Legacy SQLite:
    Fully removed from active database module.
"""

import warnings

from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from src.odhikar.config import settings


# ==========================================
# 1. POSTGRESQL CONNECTION POOL
# ==========================================

_db_pool: ConnectionPool | None = None


# ==========================================
# 2. DATABASE URL
# ==========================================

def get_database_url() -> str:
    """
    Return the PostgreSQL runtime connection URL.

    Prefer DATABASE_URL (Neon pooled connection).

    DATABASE_URL_DIRECT is a fallback only.
    """

    if settings.database_url:
        return settings.database_url

    if settings.database_url_direct:
        warnings.warn(
            "DATABASE_URL is not configured. "
            "Using DATABASE_URL_DIRECT. "
            "Configure the Neon pooled URL "
            "for production runtime.",
            RuntimeWarning
        )

        return settings.database_url_direct

    raise RuntimeError(
        "PostgreSQL connection URL is missing. "
        "Configure DATABASE_URL in the environment."
    )


# ==========================================
# 3. OPEN CONNECTION POOL
# ==========================================

def open_db_pool() -> ConnectionPool:
    """
    Initialize the PostgreSQL connection pool.

    Safe to call repeatedly within one process.
    """

    global _db_pool

    if _db_pool is not None:
        return _db_pool

    database_url = get_database_url()

    pool = ConnectionPool(
        conninfo=database_url,

        min_size=settings.database_pool_min_size,
        max_size=settings.database_pool_max_size,

        timeout=settings.database_pool_timeout,

        kwargs={
            "autocommit": False,
            "prepare_threshold": None,
            "row_factory": dict_row
        },

        open=False
    )

    try:
        pool.open(wait=True)

        with pool.connection() as conn:
            conn.execute("SELECT 1")

        _db_pool = pool

        print(
            "Neon PostgreSQL connection pool initialized."
        )

        return _db_pool

    except Exception:
        pool.close()
        raise


# ==========================================
# 4. CLOSE CONNECTION POOL
# ==========================================

def close_db_pool():
    """
    Gracefully close all pooled connections.
    """

    global _db_pool

    if _db_pool is not None:
        _db_pool.close()
        _db_pool = None

        print(
            "Neon PostgreSQL connection pool closed."
        )


# ==========================================
# 5. GET DATABASE CONNECTION
# ==========================================

@contextmanager
def get_db_connection():
    """
    Obtain a PostgreSQL connection.

    Successful transactions are committed
    automatically when the context exits.

    Failed transactions are rolled back.
    """

    pool = open_db_pool()

    with pool.connection() as conn:
        yield conn


# ==========================================
# 6. DATABASE HEALTH CHECK
# ==========================================

def check_database_connection() -> dict:
    """
    Verify PostgreSQL connectivity.
    """

    with get_db_connection() as conn:

        row = conn.execute("""
            SELECT
                current_database() AS database_name,
                current_user AS database_user,
                version() AS server_version
        """).fetchone()

        return {
            "status": "connected",
            "database": row["database_name"],
            "user": row["database_user"],
            "server_version": (
                row["server_version"].split(",")[0]
            )
        }


# ==========================================
# 7. REQUIRED POSTGRESQL TABLES
# ==========================================

REQUIRED_POSTGRES_TABLES = [

    "users",

    "user_credentials",

    "user_sessions",

    "user_threads",

    "guest_sessions",

    "guest_threads",

    "offences",

    "usage_events",

    "checkpoints",

    "checkpoint_blobs",

    "checkpoint_writes",

    "checkpoint_migrations"
]


# ==========================================
# 8. VERIFY POSTGRESQL SCHEMA
# ==========================================

def verify_postgres_schema() -> bool:
    """
    Verify required application and LangGraph
    tables exist in Neon PostgreSQL.

    Does not create, modify or delete tables.
    """

    with get_db_connection() as conn:

        rows = conn.execute("""
            SELECT
                table_name

            FROM information_schema.tables

            WHERE table_schema = 'public'

            AND table_type = 'BASE TABLE'

        """).fetchall()

        existing_tables = {
            row["table_name"]
            for row in rows
        }

        missing_tables = (
            set(REQUIRED_POSTGRES_TABLES)
            - existing_tables
        )

        if missing_tables:

            raise RuntimeError(
                "Missing PostgreSQL tables: "
                + ", ".join(
                    sorted(missing_tables)
                )
            )

        print(
            "POSTGRESQL SCHEMA: VERIFIED"
        )

        for table in REQUIRED_POSTGRES_TABLES:

            print(
                f"  [OK] {table}"
            )

        return True


# ==========================================
# 9. DATABASE INFORMATION
# ==========================================

def get_database_info() -> dict:
    """
    Return PostgreSQL database information.
    """

    with get_db_connection() as conn:

        rows = conn.execute("""
            SELECT table_name

            FROM information_schema.tables

            WHERE table_schema = 'public'

            AND table_type = 'BASE TABLE'

        """).fetchall()

        existing_tables = {
            row["table_name"]
            for row in rows
        }

        schema_verified = (
            set(REQUIRED_POSTGRES_TABLES)
            <= existing_tables
        )

    return {

        "primary_database": "Neon PostgreSQL",

        "driver": "Psycopg 3",

        "connection_pool": True,

        "pool_min_size": (
            settings.database_pool_min_size
        ),

        "pool_max_size": (
            settings.database_pool_max_size
        ),

        "legacy_sqlite_enabled": False,

        "postgres_schema_verified": schema_verified

    }


# ==========================================
# 10. DIRECT EXECUTION
# ==========================================

if __name__ == "__main__":

    try:

        print("=" * 55)

        print(
            "ODHIKAR BD DATABASE CONNECTION TEST"
        )

        print("=" * 55)

        print(
            "\nDATABASE CONNECTION:"
        )

        print(
            check_database_connection()
        )

        print(
            "\nSCHEMA VERIFICATION:"
        )

        verify_postgres_schema()

        print(
            "\nDATABASE INFO:"
        )

        print(
            get_database_info()
        )

        print(
            "\nDATABASE TEST COMPLETED"
        )

    finally:

        close_db_pool()
