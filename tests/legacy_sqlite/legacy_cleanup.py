
import sqlite3

from src.odhikar.database import DB_PATH


with sqlite3.connect(DB_PATH) as conn:

    # Delete the test record
    cursor = conn.execute("""
        DELETE FROM offences
        WHERE offence_id = ?
    """, ("TEST001",))

    print("Rows deleted:", cursor.rowcount)


    # Check whether the record still exists
    result = conn.execute("""
        SELECT * FROM offences
        WHERE offence_id = ?
    """, ("TEST001",)).fetchone()

    if result is None:
        print("Test record successfully deleted!")
    else:
        print("Record still exists:", result)


import sqlite3

from src.odhikar.database import DB_PATH


with sqlite3.connect(DB_PATH) as conn:

    # Count all records
    total = conn.execute("""
        SELECT COUNT(*) FROM offences
    """).fetchone()[0]

    # Check test record
    test_record = conn.execute("""
        SELECT * FROM offences
        WHERE offence_id = ?
    """, ("TEST001",)).fetchone()

    print("Total Records:", total)

    if test_record is None:
        print("TEST001 successfully removed!")
    else:
        print("Warning: Test record still exists!")

    print("\nDatabase cleanup check completed!")
