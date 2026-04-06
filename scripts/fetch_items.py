"""Fetch all OSRS items from the wiki API and insert into the items table.

Pulls item names from Category:Items, then batch-fetches wikitext to parse
members, tradeable, weight, game_id, and examine from {{Infobox Item}}.
"""

import argparse
from pathlib import Path

from ragger.db import create_tables, get_connection
from ragger.wiki import (
    extract_template,
    fetch_category_members,
    fetch_pages_wikitext_batch,
    parse_template_param,
    record_attributions_batch,
    strip_wiki_links,
)


def parse_int(val: str | None) -> int | None:
    if not val:
        return None
    val = val.strip().replace(",", "").replace("+", "")
    try:
        return int(val)
    except ValueError:
        return None


def parse_float(val: str | None) -> float | None:
    if not val:
        return None
    val = val.strip().replace(",", "").replace("kg", "").strip()
    try:
        return float(val)
    except ValueError:
        return None


def parse_bool(val: str | None) -> int | None:
    if not val:
        return None
    cleaned = val.strip().lower()
    if cleaned in ("yes", "true", "1"):
        return 1
    if cleaned in ("no", "false", "0"):
        return 0
    return None


def parse_item(name: str, wikitext: str) -> dict:
    """Parse item metadata from a page's wikitext."""
    item: dict = {"name": name}

    block = extract_template(wikitext, "Infobox Item")
    if not block:
        return item

    item["members"] = parse_bool(parse_template_param(block, "members"))
    item["tradeable"] = parse_bool(parse_template_param(block, "tradeable"))
    item["weight"] = parse_float(parse_template_param(block, "weight"))
    item["game_id"] = parse_int(parse_template_param(block, "id"))

    examine = parse_template_param(block, "examine")
    if examine:
        examine = strip_wiki_links(examine)
    item["examine"] = examine

    return item


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    pages = fetch_category_members(
        "Items",
        exclude_prefixes=("Items/",),
        exclude_titles={"Items"},
        exclude_namespaces={2},
    )
    print(f"Found {len(pages)} items in Category:Items")

    conn = get_connection(db_path)

    # Insert names first so other scripts can reference items by id
    conn.executemany(
        "INSERT OR IGNORE INTO items (name) VALUES (?)",
        [(page,) for page in pages],
    )
    conn.commit()
    print(f"Inserted {conn.total_changes} new item names")

    # Batch-fetch wikitext and parse metadata
    all_wikitext: dict[str, str] = {}
    for i in range(0, len(pages), 50):
        batch = pages[i:i + 50]
        print(f"  Fetching pages {i + 1}-{i + len(batch)}...")
        all_wikitext.update(fetch_pages_wikitext_batch(batch))

    print(f"Fetched {len(all_wikitext)} pages, parsing...")

    updated = 0
    for page_name, wikitext in all_wikitext.items():
        item = parse_item(page_name, wikitext)

        # Only update if we parsed at least one field
        if any(item.get(k) is not None for k in ("members", "tradeable", "weight", "game_id", "examine")):
            conn.execute(
                """UPDATE items SET members = ?, tradeable = ?, weight = ?, game_id = ?, examine = ?
                   WHERE name = ?""",
                (item.get("members"), item.get("tradeable"), item.get("weight"),
                 item.get("game_id"), item.get("examine"), page_name),
            )
            updated += 1

    conn.commit()
    print(f"Updated metadata for {updated} items")

    # Record attributions
    record_attributions_batch(conn, "items", list(all_wikitext.keys()))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch OSRS items into the database")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/ragger.db"),
        help="Path to the SQLite database",
    )
    args = parser.parse_args()
    ingest(args.db)
