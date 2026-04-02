"""Derive facility bitmasks on locations from the facilities table.

For each facility, finds the nearest location by Chebyshev distance
and sets the corresponding bit on that location's facilities column.

Requires: fetch_facilities.py and fetch_locations.py to have been run first.
"""

import argparse
from pathlib import Path

from clogger.db import create_tables, get_connection
from clogger.enums import Facility


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    # Reset facilities bitmask
    conn.execute("UPDATE locations SET facilities = 0")

    # Load all locations with coordinates
    loc_rows = conn.execute(
        "SELECT id, x, y FROM locations WHERE x IS NOT NULL AND y IS NOT NULL"
    ).fetchall()
    print(f"Loaded {len(loc_rows)} locations with coordinates")

    # Load all facilities
    facility_rows = conn.execute("SELECT id, type, x, y FROM facilities").fetchall()
    print(f"Loaded {len(facility_rows)} facilities")

    linked = 0
    for _, ftype, fx, fy in facility_rows:
        # Find nearest location by Chebyshev distance
        best_id = None
        best_dist = float("inf")
        for loc_id, loc_x, loc_y in loc_rows:
            dist = max(abs(fx - loc_x), abs(fy - loc_y))
            if dist < best_dist:
                best_dist = dist
                best_id = loc_id

        if best_id is not None:
            mask = Facility(ftype).mask
            conn.execute(
                "UPDATE locations SET facilities = facilities | ? WHERE id = ?",
                (mask, best_id),
            )
            linked += 1

    conn.commit()

    # Report summary per facility type
    for facility in Facility:
        count = conn.execute(
            "SELECT COUNT(*) FROM locations WHERE facilities & ? != 0",
            (facility.mask,),
        ).fetchone()[0]
        print(f"  {facility.label}: {count} locations")

    print(f"\nLinked {linked} facilities to locations in {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Derive facility bitmasks on locations")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/clogger.db"),
        help="Path to the SQLite database",
    )
    args = parser.parse_args()
    ingest(args.db)
