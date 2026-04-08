"""Fetch ground item spawn data from the OSRS wiki.

Finds all pages using the {{ItemSpawnLine}} template, parses item name,
location, members status, coordinates, plane, and league region. Stores
one row per spawn coordinate in the ground_items table.

Item and location linking are done in separate passes.
"""

import argparse
import re
from pathlib import Path

from ragger.db import create_tables, get_connection
from ragger.wiki import (
    extract_all_templates,
    extract_coords,
    fetch_pages_wikitext_batch,
    fetch_template_users,
    parse_template_param,
    record_attributions_batch,
    resolve_region,
    strip_refs,
    strip_wiki_links,
)

_FLOOR_NUMBER = re.compile(r"\{\{FloorNumber\|uk=(\d+)\}\}")
_TEMPLATE_ARTIFACT = re.compile(r"\{\{[^}]*\}\}?")
_HTML_ENTITY = re.compile(r"&\w+;")
_REF_TAG = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.DOTALL)


def _clean_location(raw: str) -> tuple[str, int]:
    """Clean location text and extract plane from {{FloorNumber}} if present."""
    plane = 0
    floor_match = _FLOOR_NUMBER.search(raw)
    if floor_match:
        plane = int(floor_match.group(1))

    text = strip_wiki_links(raw)
    text = _FLOOR_NUMBER.sub("", text)
    text = _REF_TAG.sub("", text)
    text = _TEMPLATE_ARTIFACT.sub("", text)
    text = _HTML_ENTITY.sub("-", text)
    text = re.sub(r"\s+", " ", text).strip(" -,()")
    return text, plane


def parse_spawn_lines(wikitext: str) -> list[dict]:
    """Extract all ItemSpawnLine entries from a page's wikitext."""
    entries = []
    for block in extract_all_templates(wikitext, "ItemSpawnLine"):
        name = parse_template_param(block, "name")
        if not name:
            continue
        name = strip_wiki_links(name).strip()

        location_raw = parse_template_param(block, "location")
        if location_raw:
            location, plane = _clean_location(location_raw)
        else:
            location, plane = "Unknown", 0

        members_raw = parse_template_param(block, "members")
        members = 1 if not members_raw or members_raw.strip().lower() != "no" else 0

        league_region = parse_template_param(block, "leagueRegion")
        region = resolve_region(league_region)

        coords = extract_coords(block)

        for x, y in coords:
            entries.append({
                "name": name,
                "location": location,
                "plane": plane,
                "members": members,
                "x": x,
                "y": y,
                "region": region,
            })

    return entries


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    pages = fetch_template_users("ItemSpawnLine")
    print(f"Found {len(pages)} pages using ItemSpawnLine")

    spawn_count = 0

    for i in range(0, len(pages), 50):
        batch = pages[i:i + 50]
        wikitext_batch = fetch_pages_wikitext_batch(batch)

        for page_name, wikitext in wikitext_batch.items():
            if not wikitext:
                continue

            entries = parse_spawn_lines(wikitext)
            for entry in entries:
                conn.execute(
                    """INSERT OR IGNORE INTO ground_items
                       (item_name, location, members, x, y, plane, region)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        entry["name"],
                        entry["location"],
                        entry["members"],
                        entry["x"],
                        entry["y"],
                        entry["plane"],
                        entry["region"],
                    ),
                )
                spawn_count += 1

        if (i + 50) % 500 == 0:
            print(f"  Processed {i + 50}/{len(pages)}...")

    print("Recording attributions...")
    record_attributions_batch(conn, "ground_items", pages)

    conn.commit()
    print(f"Inserted {spawn_count} ground item spawns into {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ground item spawn data from wiki")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    args = parser.parse_args()
    ingest(args.db)
