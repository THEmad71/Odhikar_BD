
import sqlite3
import json

from contextlib import closing
from src.odhikar.database import DB_PATH


new_aliases = [
    "riding a motorcycle without wearing a helmet",
    "motorcycle without helmet",
    "riding without helmet",
    "not wearing helmet",
    "failure to wear helmet on a motorcycle"
]


with closing(sqlite3.connect(DB_PATH)) as conn:

    row = conn.execute("""
        SELECT aliases_banglish
        FROM offences
        WHERE offence_id = ?
    """, ("no_helmet",)).fetchone()

    if row is None:
        raise ValueError("Offence not found!")

    aliases = json.loads(row[0] or "[]")

    if not isinstance(aliases, list):
        raise ValueError("Invalid aliases format!")

    existing = {
        item.casefold().strip()
        for item in aliases
        if isinstance(item, str)
    }

    added = []

    for alias in new_aliases:

        if alias.casefold().strip() not in existing:

            aliases.append(alias)
            existing.add(alias.casefold().strip())
            added.append(alias)

    conn.execute("""
        UPDATE offences
        SET aliases_banglish = ?
        WHERE offence_id = ?
    """, (
        json.dumps(aliases, ensure_ascii=False),
        "no_helmet"
    ))

    conn.commit()

    print("New aliases added:")
    for alias in added:
        print("-", alias)

    print("\nTotal aliases:", len(aliases))
