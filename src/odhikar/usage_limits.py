
"""Odhikar BD: guest identity and atomic message quotas.

Guest: 5 accepted messages in a rolling 24-hour window.
Member: 30 accepted messages per Bangladesh calendar day.

This module stores no plaintext guest tokens,
passwords or conversation contents.
"""

import hashlib
import secrets
import sqlite3
import time

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DB = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "odhikar_usage.sqlite"
)

GUEST_LIMIT = 5
MEMBER_LIMIT = 30

DAY_SECONDS = 86_400
DHAKA_OFFSET = 6 * 3_600

GUEST_COOKIE = "odhikar_guest"


@dataclass(frozen=True)
class QuotaResult:
    allowed: bool
    limit: int
    used: int
    remaining: int
    reset_at: int


class UsageStore:

    def __init__(self, db_path=DEFAULT_DB):
        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=15,
            isolation_level=None
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA busy_timeout=15000"
        )

        return connection

    def _initialize(self):
        connection = self._connect()

        try:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS guest_sessions (
                    token_hash TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    principal_kind TEXT NOT NULL
                    CHECK (
                        principal_kind IN ('guest', 'member')
                    ),

                    principal_id TEXT NOT NULL,
                    occurred_at INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_usage_window
                ON usage_events (
                    principal_kind,
                    principal_id,
                    occurred_at
                );
            """)
        finally:
            connection.close()

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()

    # ====================================
    # CREATE GUEST SESSION
    # ====================================

    def create_guest(self, *, now=None):
        instant = (
            int(time.time())
            if now is None
            else now
        )

        token = secrets.token_urlsafe(32)

        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO guest_sessions (
                    token_hash,
                    created_at,
                    expires_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    self._digest(token),
                    instant,
                    instant + DAY_SECONDS
                )
            )

        return token

    # ====================================
    # VERIFY GUEST TOKEN
    # ====================================

    def guest_principal(
        self,
        token,
        *,
        now=None
    ):
        if not token or len(token) > 256:
            return None

        instant = (
            int(time.time())
            if now is None
            else now
        )

        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT token_hash
                FROM guest_sessions
                WHERE token_hash = ?
                  AND expires_at > ?
                """,
                (
                    self._digest(token),
                    instant
                )
            ).fetchone()

        if row is None:
            return None

        return str(row["token_hash"])

    # ====================================
    # ATOMIC QUOTA ENFORCEMENT
    # ====================================

    def check_and_consume(
        self,
        kind,
        principal_id,
        *,
        now=None
    ):
        if kind not in ("guest", "member"):
            raise ValueError("Invalid account type")

        if not principal_id or not principal_id.strip():
            raise ValueError("Principal ID required")

        instant = (
            int(time.time())
            if now is None
            else now
        )

        if kind == "guest":
            limit = GUEST_LIMIT
            start = instant - DAY_SECONDS
        else:
            limit = MEMBER_LIMIT

            # Bangladesh calendar-day boundary
            start = (
                (
                    (instant + DHAKA_OFFSET)
                    // DAY_SECONDS
                ) * DAY_SECONDS
                - DHAKA_OFFSET
            )

        conn = self._connect()

        try:
            # Prevent concurrent requests from
            # bypassing the quota.
            conn.execute("BEGIN IMMEDIATE")

            if kind == "guest":
                valid = conn.execute(
                    """
                    SELECT 1
                    FROM guest_sessions
                    WHERE token_hash = ?
                      AND expires_at > ?
                    """,
                    (principal_id, instant)
                ).fetchone()

                if valid is None:
                    raise ValueError(
                        "Guest session expired or invalid"
                    )

            rows = conn.execute(
                """
                SELECT occurred_at
                FROM usage_events
                WHERE principal_kind = ?
                  AND principal_id = ?
                  AND occurred_at > ?
                ORDER BY occurred_at ASC, id ASC
                """,
                (
                    kind,
                    principal_id,
                    start - 1
                )
            ).fetchall()

            used = len(rows)
            allowed = used < limit

            if allowed:
                conn.execute(
                    """
                    INSERT INTO usage_events (
                        principal_kind,
                        principal_id,
                        occurred_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        kind,
                        principal_id,
                        instant
                    )
                )

                used += 1

            if kind == "guest":
                reset_at = (
                    int(rows[0]["occurred_at"])
                    + DAY_SECONDS
                    if rows
                    else instant + DAY_SECONDS
                )
            else:
                reset_at = start + DAY_SECONDS

            conn.execute("COMMIT")

            return QuotaResult(
                allowed=allowed,
                limit=limit,
                used=used,
                remaining=max(0, limit - used),
                reset_at=reset_at
            )

        except Exception:
            conn.execute("ROLLBACK")
            raise

        finally:
            conn.close()

    # ====================================
    # CHECK STATUS WITHOUT CHARGING
    # ====================================

    def status(
        self,
        kind,
        principal_id,
        *,
        now=None
    ):
        if kind not in ("guest", "member"):
            raise ValueError("Invalid account type")

        if not principal_id:
            raise ValueError("Principal ID required")

        instant = (
            int(time.time())
            if now is None
            else now
        )

        if kind == "guest":
            limit = GUEST_LIMIT
            start = instant - DAY_SECONDS
        else:
            limit = MEMBER_LIMIT
            start = (
                (
                    (instant + DHAKA_OFFSET)
                    // DAY_SECONDS
                ) * DAY_SECONDS
                - DHAKA_OFFSET
            )

        with closing(self._connect()) as conn:
            if kind == "guest":
                valid = conn.execute(
                    """
                    SELECT 1 FROM guest_sessions
                    WHERE token_hash = ?
                      AND expires_at > ?
                    """,
                    (principal_id, instant)
                ).fetchone()

                if valid is None:
                    raise ValueError(
                        "Guest session expired or invalid"
                    )

            rows = conn.execute(
                """
                SELECT occurred_at
                FROM usage_events
                WHERE principal_kind = ?
                  AND principal_id = ?
                  AND occurred_at > ?
                ORDER BY occurred_at ASC, id ASC
                """,
                (
                    kind,
                    principal_id,
                    start - 1
                )
            ).fetchall()

        used = len(rows)

        if kind == "guest":
            reset_at = (
                int(rows[0]["occurred_at"])
                + DAY_SECONDS
                if rows
                else instant + DAY_SECONDS
            )
        else:
            reset_at = start + DAY_SECONDS

        return QuotaResult(
            allowed=used < limit,
            limit=limit,
            used=used,
            remaining=max(0, limit - used),
            reset_at=reset_at
        )
