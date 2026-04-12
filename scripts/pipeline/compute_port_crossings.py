"""Compute ridge-crossing edges between paired ports.

Ports emitted by `compute_ports.py` come in segment pairs — for each
contiguous run of samples sharing a `(blob_a, blob_b)` pair, one port row
lands on the A side and one on the B side, both carrying the same
`(ridge_location_a_id, ridge_location_b_id, sample_start, sample_end)`.

This pass self-joins to find those pairs, then **validates** that the two
representative tiles are actually connected by a short walk under `can_move`
(using the same directional collision model as everything else). When a
Voronoi ridge coincides with a river, wall, or cliff, the sample offsets on
each side reach two walkable tiles that look close but aren't walkably
connected — those pairs are silently dropped so A* never sees a ghost
crossing. Validated pairs land in `port_crossings` with the true BFS tile
distance as the cost.

Requires: `compute_blobs.py` and `compute_ports.py` to have been run first.
"""

import argparse
from collections import deque
from pathlib import Path

import numpy as np

from ragger.collision import BLOCK_FULL, build_flags_grid, can_move
from ragger.db import create_tables, get_connection
from ragger.enums import MapSquareType
from ragger.map import GAME_TILES_PER_REGION, MapSquare

MAX_CROSSING_DIST = 20  # tiles; BFS cap when validating a ridge crossing


def _bfs_distance(
    flags: np.ndarray,
    sx: int, sy: int, dx: int, dy: int,
    x_origin: int, y_top: int,
    max_dist: int = MAX_CROSSING_DIST,
) -> int | None:
    """Return the Chebyshev-step BFS distance from (sx, sy) to (dx, dy) under
    can_move, or None if unreachable within max_dist.
    """
    H, W = flags.shape
    spy, spx = y_top - 1 - sy, sx - x_origin
    dpy, dpx = y_top - 1 - dy, dx - x_origin
    if not (0 <= spy < H and 0 <= spx < W and 0 <= dpy < H and 0 <= dpx < W):
        return None
    if (flags[spy, spx] & BLOCK_FULL) or (flags[dpy, dpx] & BLOCK_FULL):
        return None

    dist = {(spy, spx): 0}
    queue: deque[tuple[int, int]] = deque([(spy, spx)])
    while queue:
        cy, cx = queue.popleft()
        d = dist[(cy, cx)]
        if (cy, cx) == (dpy, dpx):
            return d
        if d >= max_dist:
            continue
        for ddy in (-1, 0, 1):
            for ddx in (-1, 0, 1):
                if ddy == 0 and ddx == 0:
                    continue
                ny, nx = cy + ddy, cx + ddx
                if (ny, nx) in dist:
                    continue
                if can_move(flags, cy, cx, ddy, ddx, H, W):
                    dist[(ny, nx)] = d + 1
                    queue.append((ny, nx))
    return None


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    bbox = conn.execute(
        "SELECT MIN(region_x), MAX(region_x), MIN(region_y), MAX(region_y) "
        "FROM map_squares WHERE plane = 0 AND type = 'collision'"
    ).fetchone()
    if bbox[0] is None:
        raise ValueError("No collision map squares. Run import_map_squares.py first.")
    x_min = bbox[0] * GAME_TILES_PER_REGION
    x_max = (bbox[1] + 1) * GAME_TILES_PER_REGION
    y_min = bbox[2] * GAME_TILES_PER_REGION
    y_max = (bbox[3] + 1) * GAME_TILES_PER_REGION

    print("Loading collision + water layers...")
    collision, _ = MapSquare.stitch(conn, x_min, x_max, y_min, y_max, type=MapSquareType.COLLISION, region_padding=0)
    water, _ = MapSquare.stitch(conn, x_min, x_max, y_min, y_max, type=MapSquareType.WATER, region_padding=0)
    flags_grid = build_flags_grid(collision, water)
    del collision, water

    conn.execute("DELETE FROM port_crossings")

    pairs = conn.execute(
        """
        SELECT pa.id, pa.rep_x, pa.rep_y, pb.id, pb.rep_x, pb.rep_y
        FROM ports pa
        JOIN ports pb ON
            pa.ridge_location_a_id = pb.ridge_location_a_id
            AND pa.ridge_location_b_id = pb.ridge_location_b_id
            AND pa.sample_start = pb.sample_start
            AND pa.sample_end = pb.sample_end
            AND pa.side_location_id != pb.side_location_id
        """
    ).fetchall()
    print(f"Validating {len(pairs)} candidate crossings...")

    rows: list[tuple[int, int, int]] = []
    dropped = 0
    for a_id, ax, ay, b_id, bx, by in pairs:
        dist = _bfs_distance(flags_grid, ax, ay, bx, by, x_min, y_max)
        if dist is None:
            dropped += 1
            continue
        rows.append((a_id, b_id, dist))

    conn.executemany(
        "INSERT INTO port_crossings (src_port_id, dst_port_id, distance) VALUES (?, ?, ?)",
        rows,
    )
    print(f"Inserted {len(rows)} port-crossing edges (dropped {dropped} unreachable pairs)")

    conn.commit()
    conn.close()
    print("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute validated ridge-crossing edges between paired ports")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    args = parser.parse_args()
    ingest(args.db)
