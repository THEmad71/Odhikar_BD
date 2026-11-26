
import sqlite3
from contextlib import closing

from src.odhikar.database import DB_PATH
from src.odhikar.tools import fine_lookup, load_json_list


# Test 1: Empty input
print("\n--- TEST 1: EMPTY INPUT ---")

result = fine_lookup("", "motorcycle")
print("Status:", result["status"])


# Test 2: Invalid input type
print("\n--- TEST 2: INVALID INPUT TYPE ---")

result = fine_lookup(None, "motorcycle")
print("Status:", result["status"])


# Test 3: Vehicle mismatch
print("\n--- TEST 3: VEHICLE MISMATCH ---")

result = fine_lookup("no_helmet", "car")
print("Status:", result["status"])


# Test 4: Malformed JSON
print("\n--- TEST 4: MALFORMED JSON ---")

result = load_json_list("{invalid-json")

print("Result:", result)


# Test 5: Ambiguous result
print("\n--- TEST 5: AMBIGUOUS MATCH ---")

test_id = "TEST_AMBIGUOUS"

try:

    # Insert temporary test record
    with closing(sqlite3.connect(DB_PATH)) as conn:

        conn.execute("""
            INSERT OR REPLACE INTO offences (
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
            test_id,
            "Temporary Test Offence",
            "পরীক্ষামূলক অপরাধ",
            '["helmet nai"]',
            "TEST ONLY",
            None,
            None,
            None,
            '["motorcycle"]',
            "test_only",
            "https://example.invalid",
            "TEST ONLY",
            None
        ))

        conn.commit()

    # Now two records share the same alias
    result = fine_lookup("helmet nai", "motorcycle")

    print("Status:", result["status"])


finally:

    # Always remove temporary record
    with closing(sqlite3.connect(DB_PATH)) as conn:

        conn.execute("""
            DELETE FROM offences
            WHERE offence_id = ?
        """, (test_id,))

        conn.commit()

    print("Temporary test record cleaned up!")


print("\nAll edge case tests completed!")
