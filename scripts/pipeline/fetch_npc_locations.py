"""Fetch NPC locations from the OSRS wiki.

Associates NPC game IDs with wiki-stated coordinates by parsing
versioned id and map fields from Infobox NPC templates.

Runs after fetch_npcs.py. Uses wiki cache when available.
"""

import argparse
from pathlib import Path

from ragger.db import create_tables, get_connection
from ragger.wiki import (
    extract_coords,
    extract_template,
    fetch_category_members,
    fetch_pages_wikitext_batch,
    parse_int,
    parse_template_param,
    record_attributions_batch,
)


def parse_npc_locations(wikitext: str) -> list[dict]:
    """Extract (game_id, x, y) entries from an Infobox NPC.

    Handles versioned parameters: for each version, collects all game IDs
    (comma-separated id or id1..idN) and all coordinates from the map field,
    then produces one row per (game_id, coord) pair.
    """
    block = extract_template(wikitext, "Infobox NPC")
    if not block:
        return []

    # Detect versions
    versions: list[str] = []
    i = 1
    while True:
        if parse_template_param(block, f"version{i}") is not None:
            versions.append(str(i))
            i += 1
        else:
            break

    if not versions:
        versions = [""]

    entries = []
    for v in versions:
        # Collect game IDs for this version
        game_ids: list[int] = []
        id_field = parse_template_param(block, f"id{v}" if v else "id")
        if id_field:
            for part in id_field.split(","):
                val = parse_int(part.strip())
                if val is not None:
                    game_ids.append(val)

        # Extract coords from map field
        coords: list[tuple[int, int]] = []
        map_field = f"map{v}" if v else "map"
        idx = block.find(f"|{map_field}")
        if idx >= 0:
            chunk = block[idx:idx + 300]
            coords = extract_coords(chunk)

        # Cross-product: each game_id × each coord pair
        for gid in game_ids:
            if coords:
                for x, y in coords:
                    entries.append({"game_id": gid, "x": x, "y": y})
            else:
                # Game ID known but no coordinates on the wiki page
                entries.append({"game_id": gid, "x": None, "y": None})

    return entries


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    conn.execute("DELETE FROM npc_locations")

    pages = fetch_category_members("Non-player characters")
    # Exclude monsters (handled separately)
    monster_names = set(
        r[0] for r in conn.execute("SELECT DISTINCT name FROM monsters").fetchall()
    )

    print(f"Found {len(pages)} NPC pages, excluding {len(monster_names)} monsters...")

    loc_count = 0
    attributed_pages: list[str] = []

    for i in range(0, len(pages), 50):
        batch = pages[i:i + 50]
        wikitext_batch = fetch_pages_wikitext_batch(batch)

        for page_name, wikitext in wikitext_batch.items():
            if page_name in monster_names:
                continue
            if not wikitext:
                continue

            entries = parse_npc_locations(wikitext)
            if not entries:
                continue

            attributed_pages.append(page_name)
            for entry in entries:
                if entry["x"] is None:
                    continue
                conn.execute(
                    """INSERT OR IGNORE INTO npc_locations
                       (game_id, name, x, y)
                       VALUES (?, ?, ?, ?)""",
                    (entry["game_id"], page_name, entry["x"], entry["y"]),
                )
                loc_count += 1

        if (i + 50) % 500 == 0:
            print(f"  Processed {i + 50}/{len(pages)}...")

    print("Recording attributions...")
    record_attributions_batch(conn, "npc_locations", attributed_pages)

    conn.commit()
    print(f"Inserted {loc_count} NPC location entries into {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch OSRS NPC locations")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    args = parser.parse_args()
    ingest(args.db)
