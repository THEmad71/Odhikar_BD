
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"
BACKUP = ROOT / "data" / "db_migration_backup"

TARGET = DATA / "odhikar.db"

SOURCES = {
    "odhikar_users.sqlite": [
        "users",
        "user_credentials",
        "user_sessions",
        "user_threads",
    ],
    "odhikar_usage.sqlite": [
        "guest_sessions",
        "guest_threads",
        "usage_events",
    ],
    "odhikar_checkpoints.sqlite": [
        "checkpoints",
        "writes",
    ],
}

TABLE_ORDER = [
    "users",
    "user_credentials",
    "user_sessions",
    "user_threads",
    "guest_sessions",
    "guest_threads",
    "usage_events",
    "checkpoints",
    "writes",
]


def readonly_connect(path):
    uri = path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=30)


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def check_integrity(conn):
    result = conn.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    if result != "ok":
        raise RuntimeError(f"Integrity failure: {result}")


def migrate():

    print("=" * 60)
    print("ODHIKAR BD SINGLE DATABASE MIGRATION")
    print("=" * 60)

    if not TARGET.exists():
        raise FileNotFoundError(TARGET)

    if not BACKUP.exists():
        raise RuntimeError("Verified backup directory missing.")

    # ----------------------------------
    # 1. VERIFY ALL BACKUPS
    # ----------------------------------

    backup_files = [
        "odhikar.db",
        *SOURCES.keys(),
    ]

    for filename in backup_files:

        backup_file = BACKUP / filename

        if not backup_file.exists():
            raise RuntimeError(
                f"Backup missing: {filename}"
            )

        with readonly_connect(backup_file) as backup_conn:
            check_integrity(backup_conn)

        print("BACKUP VERIFIED:", filename)

    # ----------------------------------
    # 2. LOAD SOURCE SCHEMAS AND DATA
    # ----------------------------------

    schemas = {}
    indexes = {}
    expected_counts = {}
    source_connections = {}

    try:

        for filename, expected_tables in SOURCES.items():

            source_path = DATA / filename

            if not source_path.exists():
                raise FileNotFoundError(source_path)

            src = readonly_connect(source_path)
            source_connections[filename] = src

            check_integrity(src)

            actual_tables = {
                row[0]
                for row in src.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                """)
            }

            if actual_tables != set(expected_tables):
                raise RuntimeError(
                    f"Unexpected tables in {filename}: "
                    f"{actual_tables}"
                )

            fk_errors = src.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if fk_errors:
                raise RuntimeError(
                    f"Source foreign-key errors in {filename}: "
                    f"{fk_errors}"
                )

            for table in expected_tables:

                row = src.execute("""
                    SELECT sql
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name = ?
                """, (table,)).fetchone()

                if not row or not row[0]:
                    raise RuntimeError(
                        f"Missing schema: {table}"
                    )

                cursor = src.execute(
                    f"SELECT * FROM {quote(table)}"
                )

                rows = cursor.fetchall()
                column_count = len(cursor.description)

                schemas[table] = {
                    "sql": row[0],
                    "rows": rows,
                    "columns": column_count,
                }

                expected_counts[table] = len(rows)

            indexes[filename] = src.execute("""
                SELECT sql
                FROM sqlite_master
                WHERE type = 'index'
                AND sql IS NOT NULL
            """).fetchall()

            print(
                f"LOADED: {filename} | "
                f"{len(expected_tables)} tables"
            )

        # Preserve AUTOINCREMENT sequence.
        usage_src = source_connections[
            "odhikar_usage.sqlite"
        ]

        sequence_row = usage_src.execute("""
            SELECT seq
            FROM sqlite_sequence
            WHERE name = 'usage_events'
        """).fetchone()

        usage_sequence = (
            sequence_row[0] if sequence_row else None
        )

        # ----------------------------------
        # 3. VERIFY TARGET DATABASE
        # ----------------------------------

        with readonly_connect(TARGET) as check:

            check_integrity(check)

            existing_tables = {
                row[0]
                for row in check.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                """)
            }

            if existing_tables != {"offences"}:
                raise RuntimeError(
                    "Target is not clean for migration. "
                    f"Existing tables: {existing_tables}"
                )

            offences_count = check.execute(
                "SELECT COUNT(*) FROM offences"
            ).fetchone()[0]

            with readonly_connect(
                BACKUP / "odhikar.db"
            ) as backup:

                backup_count = backup.execute(
                    "SELECT COUNT(*) FROM offences"
                ).fetchone()[0]

            if offences_count != backup_count:
                raise RuntimeError(
                    "Existing offences data differs from backup."
                )

        # ----------------------------------
        # 4. PREPARE TARGET TRANSACTION
        # ----------------------------------

        conn = sqlite3.connect(
            TARGET,
            timeout=30
        )

        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")

        try:

            conn.execute("BEGIN IMMEDIATE")

            # Create original table schemas.
            # Parent tables are created before children.

            for table in TABLE_ORDER:

                conn.execute(
                    schemas[table]["sql"]
                )

                print("TABLE CREATED:", table)

            # Copy all records.
            # Binary checkpoint data remains unchanged.

            for table in TABLE_ORDER:

                rows = schemas[table]["rows"]
                columns = schemas[table]["columns"]

                if rows:

                    placeholders = ", ".join(
                        ["?"] * columns
                    )

                    conn.executemany(
                        f"INSERT INTO {quote(table)} "
                        f"VALUES ({placeholders})",
                        rows
                    )

                copied = conn.execute(
                    f"SELECT COUNT(*) FROM {quote(table)}"
                ).fetchone()[0]

                if copied != expected_counts[table]:
                    raise RuntimeError(
                        f"Record mismatch: {table}"
                    )

                print(
                    f"DATA COPIED: {table} | {copied}"
                )

            # Restore indexes.
            for filename in SOURCES:

                for (index_sql,) in indexes[filename]:

                    conn.execute(index_sql)

            # Restore AUTOINCREMENT sequence.
            if usage_sequence is not None:

                conn.execute("""
                    UPDATE sqlite_sequence
                    SET seq = MAX(seq, ?)
                    WHERE name = 'usage_events'
                """, (usage_sequence,))

                if conn.execute(
                    "SELECT changes()"
                ).fetchone()[0] == 0:

                    conn.execute("""
                        INSERT INTO sqlite_sequence(name, seq)
                        VALUES ('usage_events', ?)
                    """, (usage_sequence,))

            # ----------------------------------
            # 5. FINAL VALIDATION BEFORE COMMIT
            # ----------------------------------

            expected_total = (
                offences_count
                + sum(expected_counts.values())
            )

            actual_tables = {
                row[0]
                for row in conn.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                """)
            }

            expected_tables = {
                "offences",
                *TABLE_ORDER,
            }

            if actual_tables != expected_tables:
                raise RuntimeError(
                    "Final table list mismatch."
                )

            actual_total = 0

            for table in sorted(expected_tables):

                count = conn.execute(
                    f"SELECT COUNT(*) FROM {quote(table)}"
                ).fetchone()[0]

                actual_total += count

                if table in expected_counts:
                    if count != expected_counts[table]:
                        raise RuntimeError(
                            f"Final count mismatch: {table}"
                        )

                print(
                    f"VERIFIED: {table} | {count}"
                )

            if actual_total != expected_total:
                raise RuntimeError(
                    "Total record count mismatch."
                )

            fk_errors = conn.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if fk_errors:
                raise RuntimeError(
                    f"Foreign key errors: {fk_errors}"
                )

            check_integrity(conn)

            # ----------------------------------
            # 6. COMMIT
            # ----------------------------------

            conn.commit()

            print("\nMIGRATION COMMITTED SUCCESSFULLY")

            print("TOTAL TABLES:", len(expected_tables))
            print("TOTAL RECORDS:", actual_total)

            print("FOREIGN KEY CHECK: PASS")
            print("INTEGRITY CHECK: PASS")

        except Exception:

            if conn.in_transaction:
                conn.rollback()

            print("\nMIGRATION FAILED — TRANSACTION ROLLED BACK")

            raise

        finally:
            conn.close()

    finally:

        for src in source_connections.values():
            src.close()

    print("\n" + "=" * 60)
    print("SINGLE DATABASE MIGRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
