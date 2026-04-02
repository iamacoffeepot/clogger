"""Import map square images from a zip file into the database.

Usage:
    uv run python scripts/import_map_squares.py [--db data/clogger.db] [--zip data/map-squares.zip]
"""

import argparse
import re
import zipfile
from pathlib import Path

from clogger.db import create_tables, get_connection


def ingest(db_path: Path, zip_path: Path) -> None:
    if not zip_path.exists():
        print(f"Error: {zip_path} not found.")
        return

    create_tables(db_path)
    conn = get_connection(db_path)

    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            m = re.match(r"(\d+)_(\d+)_(\d+)\.png", name)
            if not m:
                continue
            plane = int(m.group(1))
            region_x = int(m.group(2))
            region_y = int(m.group(3))
            image = zf.read(name)

            conn.execute(
                "INSERT OR REPLACE INTO map_squares (plane, region_x, region_y, image) VALUES (?, ?, ?, ?)",
                (plane, region_x, region_y, image),
            )
            count += 1

    conn.commit()
    print(f"Imported {count} map squares into {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import map squares from zip into database")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/clogger.db"),
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "--zip",
        type=Path,
        default=Path("data/map-squares.zip"),
        help="Path to the map squares zip file",
    )
    args = parser.parse_args()
    ingest(args.db, args.zip)
