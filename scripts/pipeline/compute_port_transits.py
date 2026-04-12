"""Compute BFS-distance edges between ports that share a blob.

For every blob touched by at least two ports, we extract a local crop of the
blob mask and collision flags, then BFS from each port's representative tile
through the blob under the full directional movement predicate. Distances to
every other port in the same blob are recorded in the `port_transits` table.

Ports in different blobs cannot reach each other within a cell — only ports
sharing a blob are connected. These transit edges are the walking-cost part
of the port graph; ridge crossings (0-cost) and portals (existing
`map_links`) layer on top during pathfinding.

Requires: `compute_blobs.py` and `compute_ports.py` to have been run first.
"""

import argparse
from collections import defaultdict, deque
from pathlib import Path

import numpy as np

from ragger.collision import (
    BLOCK_E,
    BLOCK_FULL,
    BLOCK_N,
    BLOCK_S,
    BLOCK_W,
    build_flags_grid,
)
from ragger.db import create_tables, get_connection
from ragger.enums import MapSquareType
from ragger.map import GAME_TILES_PER_REGION, MapSquare


def _direction_mask(flags: np.ndarray, blob_mask: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Precompute a boolean array where True at (py, px) means you can step
    from (py, px) in direction (dy, dx) under can_move and stay inside the
    blob. Vectorized over the whole subgrid.
    """
    H, W = flags.shape

    out = np.zeros((H, W), dtype=bool)
    sy_lo, sy_hi = max(0, -dy), H - max(0, dy)
    sx_lo, sx_hi = max(0, -dx), W - max(0, dx)

    src = flags[sy_lo:sy_hi, sx_lo:sx_hi]
    dst = flags[sy_lo + dy:sy_hi + dy, sx_lo + dx:sx_hi + dx]
    src_in = blob_mask[sy_lo:sy_hi, sx_lo:sx_hi]
    dst_in = blob_mask[sy_lo + dy:sy_hi + dy, sx_lo + dx:sx_hi + dx]

    ok = src_in & dst_in

    if dx == 0 or dy == 0:
        if dy == -1:
            ok &= (src & BLOCK_N) == 0
        elif dy == 1:
            ok &= (src & BLOCK_S) == 0
        elif dx == 1:
            ok &= (src & BLOCK_E) == 0
        elif dx == -1:
            ok &= (src & BLOCK_W) == 0
    else:
        h_flag = BLOCK_E if dx == 1 else BLOCK_W
        v_flag = BLOCK_N if dy == -1 else BLOCK_S
        ok &= (src & h_flag) == 0
        ok &= (src & v_flag) == 0

        h_tile = flags[sy_lo:sy_hi, sx_lo + dx:sx_hi + dx]
        h_in = blob_mask[sy_lo:sy_hi, sx_lo + dx:sx_hi + dx]
        ok &= h_in
        ok &= (h_tile & v_flag) == 0

        v_tile = flags[sy_lo + dy:sy_hi + dy, sx_lo:sx_hi]
        v_in = blob_mask[sy_lo + dy:sy_hi + dy, sx_lo:sx_hi]
        ok &= v_in
        ok &= (v_tile & h_flag) == 0

    out[sy_lo:sy_hi, sx_lo:sx_hi] = ok
    return out


def blob_bfs_all_targets(
    blob_mask: np.ndarray,
    flags_local: np.ndarray,
    sources: list[tuple[int, int]],
    target_points: dict[tuple[int, int], list[int]],
) -> list[tuple[int, int, int]]:
    """For each source tile, BFS through the blob and return (src_port_id,
    dst_port_id, distance) edges to all target tiles reached.

    `sources` is a list of (py, px, port_id) per source.
    `target_points` maps (py, px) -> list of port_ids sitting on that tile
    (multiple ports can share a tile if segments collapse onto the same
    representative). Distance is measured in Chebyshev steps.
    """
    H, W = blob_mask.shape

    dirs: list[tuple[int, int, np.ndarray]] = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            dirs.append((dy, dx, _direction_mask(flags_local, blob_mask, dy, dx)))

    edges: list[tuple[int, int, int]] = []

    for src_py, src_px, src_port_id in sources:
        if not blob_mask[src_py, src_px]:
            continue

        dist = np.full((H, W), -1, dtype=np.int32)
        dist[src_py, src_px] = 0
        queue = deque([(src_py, src_px)])
        remaining = dict(target_points)
        remaining.pop((src_py, src_px), None)

        while queue and remaining:
            py, px = queue.popleft()
            d = dist[py, px]
            for dy, dx, mask in dirs:
                if not mask[py, px]:
                    continue
                ny, nx = py + dy, px + dx
                if dist[ny, nx] == -1:
                    dist[ny, nx] = d + 1
                    queue.append((ny, nx))
                    if (ny, nx) in remaining:
                        for dst_port_id in remaining.pop((ny, nx)):
                            if dst_port_id != src_port_id:
                                edges.append((src_port_id, dst_port_id, int(d + 1)))

    return edges


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

    print("Loading blob grid...")
    blob_grid, extent = MapSquare.stitch_blobs(conn, x_min, x_max, y_min, y_max)
    gx_min, _gx_max, _gy_min, gy_max = extent
    H, W = blob_grid.shape
    assert blob_grid.shape == flags_grid.shape, "blob and flags grids must align"

    print("Loading ports...")
    port_rows = conn.execute(
        "SELECT id, blob_id, rep_x, rep_y FROM ports ORDER BY blob_id"
    ).fetchall()
    print(f"  {len(port_rows)} ports across {len({r[1] for r in port_rows})} blobs")

    # Group ports by blob
    ports_by_blob: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for port_id, blob_id, rep_x, rep_y in port_rows:
        px = rep_x - gx_min
        py = gy_max - 1 - rep_y
        if 0 <= px < W and 0 <= py < H:
            ports_by_blob[blob_id].append((port_id, int(py), int(px)))

    conn.execute("DELETE FROM port_transits")

    print("BFS per blob...")
    total_edges = 0
    eligible_blobs = [b for b, ps in ports_by_blob.items() if len(ps) >= 2]
    for i, blob_id in enumerate(eligible_blobs):
        ports = ports_by_blob[blob_id]

        # Local crop covering all port reps and the full blob
        blob_mask_full = blob_grid == blob_id
        ys, xs = np.nonzero(blob_mask_full)
        if ys.size == 0:
            continue
        bb_y_min, bb_y_max = int(ys.min()), int(ys.max()) + 1
        bb_x_min, bb_x_max = int(xs.min()), int(xs.max()) + 1

        blob_mask = blob_mask_full[bb_y_min:bb_y_max, bb_x_min:bb_x_max]
        flags_local = flags_grid[bb_y_min:bb_y_max, bb_x_min:bb_x_max]

        sources: list[tuple[int, int, int]] = []
        targets: dict[tuple[int, int], list[int]] = defaultdict(list)
        for port_id, py, px in ports:
            lpy = py - bb_y_min
            lpx = px - bb_x_min
            sources.append((lpy, lpx, port_id))
            targets[(lpy, lpx)].append(port_id)

        edges = blob_bfs_all_targets(blob_mask, flags_local, sources, targets)
        total_edges += len(edges)

        if edges:
            conn.executemany(
                "INSERT OR REPLACE INTO port_transits (src_port_id, dst_port_id, distance) "
                "VALUES (?, ?, ?)",
                edges,
            )

        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(eligible_blobs)} blobs, {total_edges} edges so far")
            conn.commit()

    conn.commit()
    print(f"Inserted {total_edges} port-transit edges across {len(eligible_blobs)} blobs")

    conn.close()
    print("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute BFS distances between same-blob ports")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    args = parser.parse_args()
    ingest(args.db)
