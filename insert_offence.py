
import sqlite3
import json

from src.odhikar.database import DB_PATH, init_db


# ==========================================
# 1. VERIFIED DATABASE RECORD
# ==========================================

OFFENCE = {
    "offence_id": "no_helmet",

    "name_en": "Failure to wear helmet on a motorcycle",

    "name_bn": "মোটরসাইকেলের চালক বা সহযাত্রীর হেলমেট ব্যবহার না করা",

    "aliases_banglish": [
        "helmet nai",
        "helmet chara",
        "helmet chilo na",
        "riding a motorcycle without wearing a helmet",
        "motorcycle without helmet",
        "riding without helmet",
        "not wearing helmet",
        "failure to wear helmet on a motorcycle",
        "হেলমেট না পরা",
        "হেলমেট না পরে",
        "হেলমেট ছাড়া",
        "হেলমেট ছাড়া",
        "হেলমেট ছাড়া মোটরসাইকেল চালানো",
        "হেলমেট ছাড়া মোটরসাইকেল চালানো",
        "হেলমেট না পরে বাইক চালানো",
        "মোটরসাইকেলে হেলমেট না পরা",
        "হেলমেট ব্যবহার না করা",
        "মোটরসাইকেলের হেলমেট না থাকা",
        "চালক হেলমেট পরে নাই",
        "যাত্রী হেলমেট পরে নাই",
        "পেছনের যাত্রীর হেলমেট নেই",
        "হেলমেটবিহীন মোটরসাইকেল চালানো"
    ],

    "section": "49(1)(চ) read with 92(1)",

    "max_fine_bdt": 10000,

    "max_imprisonment": "Up to 3 months",

    "bailable": None,

    "vehicle_types": ["motorcycle"],

    "law_status": "in_force",

    "source_url": "https://bdlaws.minlaw.gov.bd/act-print-1262.html",

    "last_verified": "2026-11-16",

    "additional_penalty": "For the driver: 1 demerit point deduction."
}


# ==========================================
# 2. VALIDATE DATA
# ==========================================

aliases = OFFENCE["aliases_banglish"]

if len(aliases) != len(set(aliases)):
    raise ValueError("Duplicate aliases detected.")

if len(aliases) != 22:
    raise ValueError("Unexpected alias count.")

if OFFENCE["name_bn"].isascii():
    raise ValueError("Bengali Unicode text is missing.")


# ==========================================
# 3. INITIALIZE DATABASE
# ==========================================

init_db()

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

alias_json = json.dumps(
    aliases,
    ensure_ascii=False
)

vehicle_json = json.dumps(
    OFFENCE["vehicle_types"],
    ensure_ascii=False
)


# ==========================================
# 4. SAFE INSERTION
# ==========================================

with sqlite3.connect(DB_PATH, timeout=30) as conn:

    conn.row_factory = sqlite3.Row

    existing = conn.execute(
        """
        SELECT *
        FROM offences
        WHERE offence_id = ?
        """,
        (OFFENCE["offence_id"],)
    ).fetchone()

    if existing is None:

        conn.execute(
            """
            INSERT INTO offences (
                offence_id,
                name_en,
                name_bn,
                aliases_banglish,
                section,
                max_fine_bdt,
                max_imprisonment,
                bailable,
                vehicle_types,
                law_status,
                source_url,
                last_verified,
                additional_penalty
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                OFFENCE["offence_id"],
                OFFENCE["name_en"],
                OFFENCE["name_bn"],
                alias_json,
                OFFENCE["section"],
                OFFENCE["max_fine_bdt"],
                OFFENCE["max_imprisonment"],
                OFFENCE["bailable"],
                vehicle_json,
                OFFENCE["law_status"],
                OFFENCE["source_url"],
                OFFENCE["last_verified"],
                OFFENCE["additional_penalty"]
            )
        )

        print("SUCCESS: Offence inserted.")

    else:

        # Never silently overwrite existing legal records.
        if (
            existing["name_en"] != OFFENCE["name_en"]
            or existing["name_bn"] != OFFENCE["name_bn"]
            or json.loads(existing["aliases_banglish"]) != aliases
            or existing["section"] != OFFENCE["section"]
            or existing["max_fine_bdt"] != OFFENCE["max_fine_bdt"]
            or existing["max_imprisonment"] != OFFENCE["max_imprisonment"]
            or json.loads(existing["vehicle_types"]) != OFFENCE["vehicle_types"]
        ):
            raise RuntimeError(
                "Existing offence differs from seed data. "
                "Manual review required. No changes made."
            )

        print("ALREADY PRESENT: Existing record preserved.")

    conn.commit()


# ==========================================
# 5. VERIFY
# ==========================================

with sqlite3.connect(DB_PATH) as conn:

    row = conn.execute(
        """
        SELECT
            offence_id,
            name_bn,
            section,
            max_fine_bdt,
            max_imprisonment,
            aliases_banglish
        FROM offences
        WHERE offence_id = ?
        """,
        ("no_helmet",)
    ).fetchone()

    print("\nDATABASE:", DB_PATH)
    print("OFFENCE:", row[0])
    print("BANGLA:", row[1])
    print("SECTION:", row[2])
    print("MAX FINE:", row[3])
    print("MAX IMPRISONMENT:", row[4])
    print("ALIASES:", len(json.loads(row[5])))

    print(
        "INTEGRITY:",
        conn.execute("PRAGMA integrity_check").fetchone()[0]
    )
