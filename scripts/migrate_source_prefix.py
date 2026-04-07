"""One-time migration: prefix action source names with 'wiki-'.

Renames existing source_actions rows so that 'recipe' becomes 'wiki-recipe',
'fishing' becomes 'wiki-fishing', etc.  Safe to run multiple times — only
updates rows that don't already have the prefix.

Usage:
    uv run python scripts/migrate_source_prefix.py [--db data/ragger.db]
"""

import argparse
import sqlite3
from pathlib import Path

OLD_SOURCES = [
    "agility",
    "farming",
    "firemaking",
    "fishing",
    "hunter",
    "mining",
    "prayer",
    "recipe",
    "thieving",
    "woodcutting",
]


def migrate(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    total = 0
    for old in OLD_SOURCES:
        new = f"wiki-{old}"
        cursor = conn.execute(
            "UPDATE source_actions SET source = ? WHERE source = ?",
            (new, old),
        )
        if cursor.rowcount:
            print(f"  {old} -> {new}  ({cursor.rowcount} rows)")
            total += cursor.rowcount
    conn.commit()
    conn.close()
    if total:
        print(f"Migrated {total} rows")
    else:
        print("Nothing to migrate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prefix action sources with 'wiki-'")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    args = parser.parse_args()
    migrate(args.db)
