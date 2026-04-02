"""Link facilities (banks, furnaces, anvils, altars) to their nearest locations.

Parses facility list pages from the wiki, extracts coordinates, and sets
the facilities bitmask on the nearest location.

Requires: fetch_locations.py to have been run first.
"""

import argparse
import math
import re
from pathlib import Path

from clogger.db import create_tables, get_connection
from clogger.enums import Facility
from clogger.wiki import fetch_page_wikitext

# Map template coordinate patterns
COORD_XY_PARAM = re.compile(r"\|x=(\d+)\|y=(\d+)")
COORD_XY_COLON = re.compile(r"x:(\d+),y:(\d+)")
COORD_POSITIONAL = re.compile(r"\|(\d{3,5}),(\d{3,5})")


def extract_coords_from_map(text: str) -> list[tuple[int, int]]:
    """Extract all x,y coordinate pairs from Map template text."""
    coords: list[tuple[int, int]] = []

    # Try x=N|y=N format
    match = COORD_XY_PARAM.search(text)
    if match:
        coords.append((int(match.group(1)), int(match.group(2))))
        return coords

    # Try x:N,y:N format (may have multiple per template)
    for match in COORD_XY_COLON.finditer(text):
        coords.append((int(match.group(1)), int(match.group(2))))
    if coords:
        return coords

    # Try positional format
    match = COORD_POSITIONAL.search(text)
    if match:
        coords.append((int(match.group(1)), int(match.group(2))))

    return coords


def parse_facility_coords(wikitext: str) -> list[tuple[int, int]]:
    """Extract all facility coordinates from a wiki page's tables."""
    all_coords: list[tuple[int, int]] = []

    for match in re.finditer(r"\{\{Map[^}]*\}\}", wikitext):
        map_text = match.group(0)
        coords = extract_coords_from_map(map_text)
        all_coords.extend(coords)

    return all_coords


FACILITY_PAGES = {
    Facility.BANK: "List_of_banks",
    Facility.FURNACE: "Furnace",
    Facility.ANVIL: "Anvil",
    Facility.ALTAR: "Altar",
}


def find_nearest_location(
    x: int, y: int, locations: list[tuple[int, int, int]]
) -> int | None:
    """Find the location ID closest to the given coordinates (Chebyshev distance)."""
    best_id = None
    best_dist = float("inf")
    for loc_id, loc_x, loc_y in locations:
        dist = max(abs(x - loc_x), abs(y - loc_y))
        if dist < best_dist:
            best_dist = dist
            best_id = loc_id
    return best_id


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    # Reset facilities
    conn.execute("UPDATE locations SET facilities = 0")

    # Load all locations with coordinates
    rows = conn.execute("SELECT id, x, y FROM locations WHERE x IS NOT NULL AND y IS NOT NULL").fetchall()
    locations = [(row[0], row[1], row[2]) for row in rows]
    print(f"Loaded {len(locations)} locations with coordinates")

    total = 0
    for facility, page in FACILITY_PAGES.items():
        print(f"\n=== {facility.label} ({page}) ===")
        wikitext = fetch_page_wikitext(page)
        coords = parse_facility_coords(wikitext)
        print(f"  Found {len(coords)} coordinate entries")

        matched = 0
        for x, y in coords:
            loc_id = find_nearest_location(x, y, locations)
            if loc_id is not None:
                conn.execute(
                    "UPDATE locations SET facilities = facilities | ? WHERE id = ?",
                    (facility.mask, loc_id),
                )
                matched += 1

        print(f"  Linked {matched} to locations")
        total += matched

    conn.commit()
    print(f"\nTotal: {total} facility-location links in {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Link facilities to locations")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/clogger.db"),
        help="Path to the SQLite database",
    )
    args = parser.parse_args()
    ingest(args.db)
