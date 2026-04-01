"""Fetch all OSRS items from the wiki API and insert into the items table."""

import argparse
from pathlib import Path

import requests

from clogger.db import create_tables, get_connection

API_URL = "https://oldschool.runescape.wiki/api.php"
USER_AGENT = "clogger/0.1 - OSRS Leagues planner"
HEADERS = {"User-Agent": USER_AGENT}

EXCLUDED_PREFIXES = ("Items/",)
EXCLUDED_NAMESPACES = {2}  # User namespace


def fetch_items() -> list[str]:
    items: list[str] = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Items",
        "cmlimit": "500",
        "cmtype": "page",
        "format": "json",
    }

    while True:
        resp = requests.get(API_URL, params=params, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()

        for member in data["query"]["categorymembers"]:
            title = member["title"]
            ns = member["ns"]

            if ns in EXCLUDED_NAMESPACES:
                continue
            if title.startswith(EXCLUDED_PREFIXES):
                continue
            if title == "Items":
                continue

            items.append(title)

        if "continue" in data:
            params["cmcontinue"] = data["continue"]["cmcontinue"]
        else:
            break

    return sorted(items)


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    items = fetch_items()

    conn = get_connection(db_path)
    conn.executemany(
        "INSERT OR IGNORE INTO items (name) VALUES (?)",
        [(item,) for item in items],
    )
    conn.commit()
    print(f"Inserted {conn.total_changes} items into {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch OSRS items into the database")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/clogger.db"),
        help="Path to the SQLite database",
    )
    args = parser.parse_args()
    ingest(args.db)
