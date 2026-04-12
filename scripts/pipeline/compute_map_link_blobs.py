"""Resolve each `map_links` row's src/dst endpoints to blob IDs.

For every map_link with coordinates, looks up the blob at its src and dst
tiles in the stitched blob grid. If the exact tile is blocked (blob 0), scans
a small radius (max_radius tiles) for the nearest walkable blob. Unresolved
endpoints are left NULL.

Populates `map_links.src_blob_id` and `map_links.dst_blob_id` — the
pathfinder uses these to inject portal endpoints into the port-graph A* as
virtual nodes without rescanning the blob raster per query.

Requires: `compute_blobs.py` to have been run first.
"""

import argparse
from pathlib import Path

import numpy as np

from ragger.db import create_tables, get_connection
from ragger.map import GAME_TILES_PER_REGION, MapSquare

DEFAULT_MAX_RADIUS = 8


def resolve_blob(
    blob_grid: np.ndarray,
    x_min: int,
    y_max: int,
    gx: int,
    gy: int,
    max_radius: int = DEFAULT_MAX_RADIUS,
) -> int | None:
    """Return the blob id at (gx, gy), or the nearest walkable blob within
    `max_radius` tiles. Scans in expanding ring-shaped neighborhoods so the
    first non-zero blob hit is the closest.
    """
    H, W = blob_grid.shape

    px = gx - x_min
    py = y_max - 1 - gy
    if 0 <= px < W and 0 <= py < H:
        bid = int(blob_grid[py, px])
        if bid != 0:
            return bid

    for radius in range(1, max_radius + 1):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if abs(dy) != radius and abs(dx) != radius:
                    continue
                cx = (gx + dx) - x_min
                cy = y_max - 1 - (gy + dy)
                if 0 <= cx < W and 0 <= cy < H:
                    bid = int(blob_grid[cy, cx])
                    if bid != 0:
                        return bid
    return None


def ingest(db_path: Path, max_radius: int = DEFAULT_MAX_RADIUS) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    bbox = conn.execute(
        "SELECT MIN(region_x), MAX(region_x), MIN(region_y), MAX(region_y) "
        "FROM map_squares WHERE plane = 0 AND type = 'blob'"
    ).fetchone()
    if bbox[0] is None:
        raise ValueError("No blob map squares. Run compute_blobs.py first.")
    x_min = bbox[0] * GAME_TILES_PER_REGION
    x_max = (bbox[1] + 1) * GAME_TILES_PER_REGION
    y_min = bbox[2] * GAME_TILES_PER_REGION
    y_max = (bbox[3] + 1) * GAME_TILES_PER_REGION

    print("Loading blob grid...")
    blob_grid, _ = MapSquare.stitch_blobs(conn, x_min, x_max, y_min, y_max)

    conn.execute("UPDATE map_links SET src_blob_id = NULL, dst_blob_id = NULL")

    rows = conn.execute(
        "SELECT id, src_x, src_y, dst_x, dst_y FROM map_links "
        "WHERE src_x IS NOT NULL AND src_y IS NOT NULL "
        "AND dst_x IS NOT NULL AND dst_y IS NOT NULL"
    ).fetchall()
    print(f"Resolving blobs for {len(rows)} map_links...")

    updates: list[tuple[int | None, int | None, int]] = []
    src_hits = 0
    dst_hits = 0
    for lid, sx, sy, dx, dy in rows:
        sbid = resolve_blob(blob_grid, x_min, y_max, sx, sy, max_radius)
        dbid = resolve_blob(blob_grid, x_min, y_max, dx, dy, max_radius)
        if sbid is not None:
            src_hits += 1
        if dbid is not None:
            dst_hits += 1
        updates.append((sbid, dbid, lid))

    conn.executemany(
        "UPDATE map_links SET src_blob_id = ?, dst_blob_id = ? WHERE id = ?",
        updates,
    )
    conn.commit()
    print(f"Resolved {src_hits}/{len(rows)} src endpoints, {dst_hits}/{len(rows)} dst endpoints")

    conn.close()
    print("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resolve map_link endpoints to blob IDs")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    parser.add_argument("--max-radius", type=int, default=DEFAULT_MAX_RADIUS)
    args = parser.parse_args()
    ingest(args.db, max_radius=args.max_radius)
