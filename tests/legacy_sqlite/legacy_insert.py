
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
            last_verified
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "TEST001",
        "Sample Test Offence",
        "নমুনা পরীক্ষামূলক অপরাধ",
        '["test offence", "sample offence"]',
        "TEST ONLY",
        None,
        None,
        None,
        '[]',
        "test_only",
        "https://example.invalid/test",
        "TEST ONLY"
    ))

    print("Test record inserted successfully!")


    # Read the inserted record
    result = conn.execute("""
        SELECT * FROM offences
        WHERE offence_id = ?
    """, ("TEST001",)).fetchone()

    print("\nInserted Record:")
    print(result)
