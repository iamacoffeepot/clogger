"""Compute walkable connections between locations using Voronoi edges and map tile collision data.

Uses Euclidean Voronoi to determine which locations are neighbors, then samples
the map tiles along each edge to determine if the path is blocked (water, walls, void).

Stores walkable pairs as map links with type "walkable".

Requires: fetch_locations.py to have been run and data/map-squares.zip to exist.
"""

import argparse
import os
import re
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import Voronoi

from clogger.db import create_tables, get_connection
from clogger.enums import MapLinkType


DEFAULT_THRESHOLD = 0.975
DEFAULT_SAMPLES = 60


def load_canvas(zip_path: Path) -> tuple[np.ndarray, int, int, int, int]:
    """Load ground plane tiles from zip and stitch into a canvas.

    Returns (canvas, x_min_game, x_max_game, y_min_game, y_max_game).
    """
    px_per_region = 256
    game_per_region = 64

    tiles: dict[tuple[int, int], bytes] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            m = re.match(r"0_(\d+)_(\d+)\.png", name)
            if m:
                tiles[(int(m.group(1)), int(m.group(2)))] = zf.read(name)

    rxs = [t[0] for t in tiles]
    rys = [t[1] for t in tiles]
    min_rx, max_rx = min(rxs), max(rxs)
    min_ry, max_ry = min(rys), max(rys)

    width = (max_rx - min_rx + 1) * px_per_region
    height = (max_ry - min_ry + 1) * px_per_region
    canvas = np.zeros((height, width, 3), dtype=np.uint8)

    for (rx, ry), data in tiles.items():
        try:
            tile = np.array(Image.open(__import__("io").BytesIO(data)).convert("RGB"))
            px = (rx - min_rx) * px_per_region
            py = (max_ry - ry) * px_per_region
            canvas[py:py + px_per_region, px:px + px_per_region] = tile
        except Exception:
            pass

    x_min = min_rx * game_per_region
    x_max = (max_rx + 1) * game_per_region
    y_min = min_ry * game_per_region
    y_max = (max_ry + 1) * game_per_region

    return canvas, x_min, x_max, y_min, y_max


def make_blocked_checker(canvas: np.ndarray, x_min: int, x_max: int, y_min: int, y_max: int):
    """Return a function that checks if a game coordinate is blocked."""
    height, width = canvas.shape[:2]

    def is_blocked(gx: float, gy: float) -> bool:
        px = int((gx - x_min) * 4)
        py = int((y_max - gy) * 4)
        if px < 0 or py < 0 or px >= width or py >= height:
            return True
        r, g, b = int(canvas[py, px, 0]), int(canvas[py, px, 1]), int(canvas[py, px, 2])
        # Red = collision flag from map renderer
        if r > 200 and g < 50 and b < 50:
            return True
        # Black void
        if r < 10 and g < 10 and b < 10:
            return True
        # Ocean blue
        if b > 120 and b > r + 20 and b > g:
            return True
        return False

    return is_blocked


def edge_blocked_ratio(v0, v1, is_blocked, num_samples: int) -> float:
    """Sample along an edge and return the ratio of blocked points."""
    blocked = 0
    for i in range(num_samples):
        t = i / (num_samples - 1)
        gx = v0[0] + t * (v1[0] - v0[0])
        gy = v0[1] + t * (v1[1] - v0[1])
        if is_blocked(gx, gy):
            blocked += 1
    return blocked / num_samples


def ingest(db_path: Path, threshold: float, samples: int) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    zip_path = Path("data/map-squares.zip")
    if not zip_path.exists():
        print(f"Error: {zip_path} not found.")
        return

    print("Loading map tiles...")
    canvas, x_min, x_max, y_min, y_max = load_canvas(zip_path)
    is_blocked = make_blocked_checker(canvas, x_min, x_max, y_min, y_max)
    print(f"Canvas: {canvas.shape[1]}x{canvas.shape[0]} px, game coords {x_min}-{x_max} x {y_min}-{y_max}")

    # Process overworld and underworld separately
    for world_name, y_op, y_threshold in [("overworld", "<", 5000), ("underworld", ">=", 5000)]:
        rows = conn.execute(
            f"SELECT name, x, y FROM locations WHERE x IS NOT NULL AND y IS NOT NULL AND y {y_op} ?",
            (y_threshold,),
        ).fetchall()

        if len(rows) < 4:
            print(f"{world_name}: only {len(rows)} locations, skipping")
            continue

        points = np.array([(r[1], r[2]) for r in rows])
        names = [r[0] for r in rows]

        print(f"{world_name}: Computing Voronoi with {len(rows)} locations...")
        vor = Voronoi(points)

        walkable = 0
        blocked = 0

        # ridge_points tells us which two input points each edge separates
        for ridge_idx, simplex in enumerate(vor.ridge_vertices):
            if -1 in simplex:
                continue

            v0 = vor.vertices[simplex[0]]
            v1 = vor.vertices[simplex[1]]

            # Get the two locations this edge separates
            pt_indices = vor.ridge_points[ridge_idx]
            loc_a = names[pt_indices[0]]
            loc_b = names[pt_indices[1]]

            ratio = edge_blocked_ratio(v0, v1, is_blocked, samples)

            if ratio < threshold:
                # Walkable — store bidirectional map link
                conn.execute(
                    """INSERT INTO map_links
                       (from_location, to_location, from_x, from_y, to_x, to_y, type, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (loc_a, loc_b,
                     int(points[pt_indices[0]][0]), int(points[pt_indices[0]][1]),
                     int(points[pt_indices[1]][0]), int(points[pt_indices[1]][1]),
                     MapLinkType.WALKABLE.value if hasattr(MapLinkType, 'WALKABLE') else "walkable",
                     f"Voronoi walkable: {loc_a} <-> {loc_b}"),
                )
                conn.execute(
                    """INSERT INTO map_links
                       (from_location, to_location, from_x, from_y, to_x, to_y, type, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (loc_b, loc_a,
                     int(points[pt_indices[1]][0]), int(points[pt_indices[1]][1]),
                     int(points[pt_indices[0]][0]), int(points[pt_indices[0]][1]),
                     MapLinkType.WALKABLE.value if hasattr(MapLinkType, 'WALKABLE') else "walkable",
                     f"Voronoi walkable: {loc_b} <-> {loc_a}"),
                )
                walkable += 1
            else:
                blocked += 1

        print(f"{world_name}: {walkable} walkable pairs, {blocked} blocked")

    conn.commit()
    print("Done")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute walkability from map tiles")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/clogger.db"),
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Blocked ratio threshold (default {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=DEFAULT_SAMPLES,
        help=f"Number of samples per edge (default {DEFAULT_SAMPLES})",
    )
    args = parser.parse_args()
    ingest(args.db, args.threshold, args.samples)
