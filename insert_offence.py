
import sqlite3

from src.odhikar.database import DB_PATH


with sqlite3.connect(DB_PATH) as conn:

    conn.execute("""
        INSERT OR IGNORE INTO offences (
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
    """, (
        "no_helmet",
        "Failure to wear helmet on a motorcycle",
        "মোটরসাইকেলের চালক বা সহযাত্রীর হেলমেট ব্যবহার না করা",
        '["helmet nai", "helmet chara", "helmet chilo na"]',
        "49(1)(চ) read with 92(1)",
        10000,
        "Up to 3 months",
        None,
        '["motorcycle"]',
        "in_force",
        "https://bdlaws.minlaw.gov.bd/act-print-1262.html",
        "2026-11-16",
        "For the driver: 1 demerit point deduction."
    ))

    print("Offence insertion completed!")

    record = conn.execute("""
        SELECT * FROM offences
        WHERE offence_id = ?
    """, ("no_helmet",)).fetchone()

    print("\nInserted Record:")
    print(record)
