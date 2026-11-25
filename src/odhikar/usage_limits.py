
"""
ODHIKAR BD
PostgreSQL Guest Identity and Atomic Usage Limits

Primary database:
    Neon PostgreSQL

Driver:
    Psycopg 3

Connection management:
    Central PostgreSQL ConnectionPool

Guest:
    5 accepted messages in a rolling 24-hour window.

Member:
    30 accepted messages per Bangladesh calendar day.

Security:
    SHA-256 guest token hashing.
    No plaintext guest tokens in database.
    Atomic quota enforcement.
    PostgreSQL transaction-level advisory locks.

Existing application data is preserved.
No SQLite fallback is permitted.
"""

# ==========================================
# 1. IMPORTS
# ==========================================

import hashlib
import secrets
import time

from dataclasses import dataclass

from src.odhikar.database import (
    get_db_connection
)


# ==========================================
# 2. QUOTA CONFIGURATION
# ==========================================

GUEST_LIMIT = 5

MEMBER_LIMIT = 30

DAY_SECONDS = 86_400

DHAKA_OFFSET = 6 * 3_600

GUEST_COOKIE = "odhikar_guest"


# ==========================================
# 3. QUOTA RESULT
# ==========================================

@dataclass(frozen=True)
class QuotaResult:

    allowed: bool

    limit: int

    used: int

    remaining: int

    reset_at: int


# ==========================================
# 4. DATABASE ROW COMPATIBILITY
# ==========================================

def _row_value(row, key, index):
    """
    Support both Psycopg tuple rows
    and dictionary-style rows.
    """

    if row is None:
        raise ValueError("Database returned no row.")

    try:
        return row[key]

    except (TypeError, KeyError, IndexError):

        return row[index]


# ==========================================
# 5. USAGE STORE
# ==========================================

class UsageStore:

    def __init__(self, db_path=None):
        """
        Initialize PostgreSQL usage storage.

        SQLite database paths are no longer supported.
        """

        if db_path is not None:

            raise ValueError(
                "SQLite db_path is no longer supported. "
                "UsageStore now uses Neon PostgreSQL."
            )

        self._initialize()

    # ======================================
    # 6. VERIFY POSTGRESQL SCHEMA
    # ======================================

    def _initialize(self):
        """
        Verify existing PostgreSQL tables.

        Does not create, overwrite or delete
        any existing application records.
        """

        required_columns = {

            "guest_sessions": {

                "token_hash",

                "created_at",

                "expires_at"
            },

            "usage_events": {

                "id",

                "principal_kind",

                "principal_id",

                "occurred_at"
            }
        }

        with get_db_connection() as conn:

            rows = conn.execute("""

                SELECT

                    table_name,

                    column_name

                FROM information_schema.columns

                WHERE table_schema = 'public'

                AND table_name IN (
                    %s,
                    %s
                )

            """, (
                "guest_sessions",
                "usage_events"
            )).fetchall()

            actual_columns = {

                table: set()

                for table in required_columns
            }

            for row in rows:

                table = _row_value(
                    row,
                    "table_name",
                    0
                )

                column = _row_value(
                    row,
                    "column_name",
                    1
                )

                if table in actual_columns:

                    actual_columns[table].add(
                        column
                    )

            for table, expected in required_columns.items():

                missing = (
                    expected - actual_columns[table]
                )

                if missing:

                    raise RuntimeError(
                        f"PostgreSQL schema incomplete: "
                        f"{table} is missing "
                        f"{', '.join(sorted(missing))}"
                    )

        print(
            "PostgreSQL guest and usage tables verified."
        )

    # ======================================
    # 7. HASH GUEST TOKEN
    # ======================================

    @staticmethod
    def _digest(value: str) -> str:
        """
        Generate SHA-256 token hash.
        """

        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()

    # ======================================
    # 8. CURRENT TIMESTAMP
    # ======================================

    @staticmethod
    def _timestamp(now=None) -> int:
        """
        Return Unix timestamp in seconds.
        """

        if now is None:

            return int(time.time())

        if isinstance(now, bool):

            raise ValueError(
                "Invalid timestamp."
            )

        try:

            return int(now)

        except (ValueError, TypeError, OverflowError) as exc:

            raise ValueError(
                "Invalid timestamp."
            ) from exc

    # ======================================
    # 9. CALCULATE QUOTA WINDOW
    # ======================================

    @staticmethod
    def _window_start(kind: str, instant: int) -> int:
        """
        Guest:
            Rolling 24-hour window.

        Member:
            Bangladesh calendar-day window.
        """

        if kind == "guest":

            return instant - DAY_SECONDS

        if kind == "member":

            return (

                (
                    (instant + DHAKA_OFFSET)
                    // DAY_SECONDS
                ) * DAY_SECONDS

                - DHAKA_OFFSET

            )

        raise ValueError(
            "Invalid account type."
        )

    # ======================================
    # 10. VERIFY GUEST SESSION
    # ======================================

    @staticmethod
    def _valid_guest(
        conn,
        guest_hash: str,
        instant: int
    ) -> bool:
        """
        Verify guest token hash and expiration.
        """

        row = conn.execute("""

            SELECT 1

            FROM guest_sessions

            WHERE token_hash = %s

            AND expires_at > %s

            LIMIT 1

        """, (
            guest_hash,
            instant
        )).fetchone()

        return row is not None

    # ======================================
    # 11. GET USAGE STATISTICS
    # ======================================

    @staticmethod
    def _usage_statistics(
        conn,
        kind: str,
        principal_id: str,
        window_start: int
    ):
        """
        Get message count and oldest event
        inside the applicable quota window.
        """

        row = conn.execute("""

            SELECT

                COUNT(*) AS used,

                MIN(occurred_at) AS oldest

            FROM usage_events

            WHERE principal_kind = %s

            AND principal_id = %s

            AND occurred_at > %s

        """, (
            kind,
            principal_id,
            window_start - 1
        )).fetchone()

        used = int(
            _row_value(
                row,
                "used",
                0
            )
        )

        oldest = _row_value(
            row,
            "oldest",
            1
        )

        return used, oldest

    # ======================================
    # 12. CREATE GUEST SESSION
    # ======================================

    def create_guest(self, *, now=None):
        """
        Create a new anonymous guest session.

        Only the SHA-256 hash is stored.
        """

        instant = self._timestamp(now)

        token = secrets.token_urlsafe(32)

        token_hash = self._digest(token)

        with get_db_connection() as conn:

            conn.execute("""

                INSERT INTO guest_sessions (

                    token_hash,

                    created_at,

                    expires_at

                )

                VALUES (%s, %s, %s)

            """, (
                token_hash,
                instant,
                instant + DAY_SECONDS
            ))

        # Original token is returned only once.
        return token

    # ======================================
    # 13. VERIFY GUEST TOKEN
    # ======================================

    def guest_principal(
        self,
        token,
        *,
        now=None
    ):
        """
        Verify a guest cookie.

        Returns:
            SHA-256 guest identity hash
            or None if invalid/expired.
        """

        if (
            not isinstance(token, str)
            or not token
            or len(token) > 256
        ):

            return None

        instant = self._timestamp(now)

        guest_hash = self._digest(token)

        with get_db_connection() as conn:

            valid = self._valid_guest(
                conn,
                guest_hash,
                instant
            )

        if not valid:

            return None

        return guest_hash

    # ======================================
    # 14. ATOMIC QUOTA ENFORCEMENT
    # ======================================

    def check_and_consume(
        self,
        kind,
        principal_id,
        *,
        now=None
    ):
        """
        Atomically check and consume one message.

        PostgreSQL transaction-level advisory locks
        prevent concurrent requests from bypassing
        quota restrictions for the same principal.

        A denied request does not consume quota.
        """

        if kind not in ("guest", "member"):

            raise ValueError(
                "Invalid account type."
            )

        if (
            not isinstance(principal_id, str)
            or not principal_id.strip()
        ):

            raise ValueError(
                "Principal ID required."
            )

        principal_id = principal_id.strip()

        instant = self._timestamp(now)

        limit = (
            GUEST_LIMIT
            if kind == "guest"
            else MEMBER_LIMIT
        )

        start = self._window_start(
            kind,
            instant
        )

        lock_key = (
            f"odhikar:quota:{kind}:{principal_id}"
        )

        with get_db_connection() as conn:

            # ----------------------------------
            # A. LOCK PRINCIPAL QUOTA
            # ----------------------------------

            conn.execute("""

                SELECT pg_advisory_xact_lock(
                    hashtextextended(%s, 0)
                )

            """, (
                lock_key,
            ))

            # ----------------------------------
            # B. VERIFY GUEST SESSION
            # ----------------------------------

            if kind == "guest":

                valid = self._valid_guest(
                    conn,
                    principal_id,
                    instant
                )

                if not valid:

                    raise ValueError(
                        "Guest session expired or invalid."
                    )

            # ----------------------------------
            # C. GET EXISTING USAGE
            # ----------------------------------

            used, oldest = self._usage_statistics(
                conn,
                kind,
                principal_id,
                start
            )

            # ----------------------------------
            # D. CHECK QUOTA
            # ----------------------------------

            allowed = used < limit

            # ----------------------------------
            # E. CONSUME ONLY IF ALLOWED
            # ----------------------------------

            if allowed:

                conn.execute("""

                    INSERT INTO usage_events (

                        principal_kind,

                        principal_id,

                        occurred_at

                    )

                    VALUES (%s, %s, %s)

                """, (
                    kind,
                    principal_id,
                    instant
                ))

                used += 1

            # ----------------------------------
            # F. CALCULATE RESET TIME
            # ----------------------------------

            if kind == "guest":

                reset_at = (

                    int(oldest) + DAY_SECONDS

                    if oldest is not None

                    else instant + DAY_SECONDS

                )

            else:

                reset_at = start + DAY_SECONDS

            # ----------------------------------
            # G. RETURN QUOTA RESULT
            # ----------------------------------

            return QuotaResult(

                allowed=allowed,

                limit=limit,

                used=used,

                remaining=max(
                    0,
                    limit - used
                ),

                reset_at=reset_at

            )

    # ======================================
    # 15. CHECK STATUS WITHOUT CHARGING
    # ======================================

    def status(
        self,
        kind,
        principal_id,
        *,
        now=None
    ):
        """
        Check current quota without consuming
        a message.
        """

        if kind not in ("guest", "member"):

            raise ValueError(
                "Invalid account type."
            )

        if (
            not isinstance(principal_id, str)
            or not principal_id.strip()
        ):

            raise ValueError(
                "Principal ID required."
            )

        principal_id = principal_id.strip()

        instant = self._timestamp(now)

        limit = (
            GUEST_LIMIT
            if kind == "guest"
            else MEMBER_LIMIT
        )

        start = self._window_start(
            kind,
            instant
        )

        with get_db_connection() as conn:

            # Verify guest identity.

            if kind == "guest":

                valid = self._valid_guest(
                    conn,
                    principal_id,
                    instant
                )

                if not valid:

                    raise ValueError(
                        "Guest session expired or invalid."
                    )

            # Read usage without consuming.

            used, oldest = self._usage_statistics(
                conn,
                kind,
                principal_id,
                start
            )

        # Calculate reset time.

        if kind == "guest":

            reset_at = (

                int(oldest) + DAY_SECONDS

                if oldest is not None

                else instant + DAY_SECONDS

            )

        else:

            reset_at = start + DAY_SECONDS

        return QuotaResult(

            allowed=used < limit,

            limit=limit,

            used=used,

            remaining=max(
                0,
                limit - used
            ),

            reset_at=reset_at

        )


# ==========================================
# 16. USAGE STORE INFORMATION
# ==========================================

def get_usage_store_info() -> dict:

    return {

        "module": "Odhikar BD Usage Store",

        "database": "Neon PostgreSQL",

        "driver": "Psycopg 3",

        "connection_pool": True,

        "guest_limit": GUEST_LIMIT,

        "guest_window": "Rolling 24 hours",

        "member_limit": MEMBER_LIMIT,

        "member_window": "Bangladesh calendar day",

        "guest_token_hash": "SHA-256",

        "atomic_quota_enforcement": True,

        "concurrency_control": (
            "PostgreSQL transaction-level advisory lock"
        ),

        "legacy_sqlite": False

    }


# ==========================================
# 17. DIRECT EXECUTION
# ==========================================

if __name__ == "__main__":

    from src.odhikar.database import (
        close_db_pool,
        get_db_connection
    )

    print("=" * 55)

    print(
        "ODHIKAR BD POSTGRESQL USAGE LIMITS"
    )

    print("=" * 55)

    try:

        store = UsageStore()

        print(
            "\nUSAGE STORE INFORMATION:"
        )

        print(
            get_usage_store_info()
        )

        with get_db_connection() as conn:

            guest_count = conn.execute("""

                SELECT COUNT(*)

                FROM guest_sessions

            """).fetchone()

            usage_count = conn.execute("""

                SELECT COUNT(*)

                FROM usage_events

            """).fetchone()

        print(
            "\nEXISTING GUEST SESSIONS:",
            _row_value(guest_count, "count", 0)
        )

        print(
            "EXISTING USAGE EVENTS:",
            _row_value(usage_count, "count", 0)
        )

        print(
            "\nPOSTGRESQL USAGE SCHEMA: VERIFIED"
        )

        print(
            "NO TEST QUOTA CONSUMED."
        )

        print(
            "USAGE LIMITS TEST COMPLETED."
        )

    finally:

        close_db_pool()
