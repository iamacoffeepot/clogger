"""Link shops to locations by matching shop location text to location names.

Requires: fetch_shops.py and fetch_locations.py to have been run first.
"""

import argparse
from pathlib import Path

from clogger.db import create_tables, get_connection


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    # Build location name -> id lookup
    location_ids = dict(conn.execute("SELECT name, id FROM locations").fetchall())

    shops = conn.execute("SELECT id, name, location FROM shops").fetchall()

    matched = 0
    unmatched = 0

    for shop_id, shop_name, shop_location in shops:
        if not shop_location:
            unmatched += 1
            continue

        # Try exact match first
        loc_id = location_ids.get(shop_location)

        # Try matching against comma-separated parts (e.g. "Mistrock, South of Aldarin")
        if loc_id is None and "," in shop_location:
            first_part = shop_location.split(",")[0].strip()
            loc_id = location_ids.get(first_part)

        if loc_id is not None:
            conn.execute(
                "INSERT OR IGNORE INTO shop_locations (shop_id, location_id) VALUES (?, ?)",
                (shop_id, loc_id),
            )
            matched += 1
        else:
            print(f"  Warning: no location match for shop '{shop_name}' (location: '{shop_location}')")
            unmatched += 1

    conn.commit()
    print(f"Linked {matched} shops to locations ({unmatched} unmatched) in {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Link shops to locations")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/clogger.db"),
        help="Path to the SQLite database",
    )
    args = parser.parse_args()
    ingest(args.db)
