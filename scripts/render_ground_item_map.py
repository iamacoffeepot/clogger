"""Render a full map of ground item spawn locations as dots with labels.

Stitches plane-0 color map squares (downscaled to 1px/tile) and overlays
ground item spawn dots from the ground_items table.
"""

import argparse
import io
import sqlite3
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TILES_PER_REGION = 64
COLOR_PX_PER_REGION = 256
TARGET_PX = TILES_PER_REGION


def stitch_map(conn: sqlite3.Connection) -> tuple[np.ndarray, int, int, int, int]:
    """Stitch all plane-0 color map squares into a single canvas at 1px/tile."""
    bounds = conn.execute(
        "SELECT MIN(region_x), MAX(region_x), MIN(region_y), MAX(region_y) "
        "FROM map_squares WHERE plane = 0 AND type = 'color'"
    ).fetchone()
    rx_min, rx_max, ry_min, ry_max = bounds

    w = (rx_max - rx_min + 1) * TARGET_PX
    h = (ry_max - ry_min + 1) * TARGET_PX
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    rows = conn.execute(
        "SELECT region_x, region_y, image FROM map_squares WHERE plane = 0 AND type = 'color'"
    ).fetchall()

    for rx, ry, img_data in rows:
        try:
            tile = Image.open(io.BytesIO(img_data)).convert("RGB")
            tile = tile.resize((TARGET_PX, TARGET_PX), Image.LANCZOS)
            arr = np.array(tile)
            px = (rx - rx_min) * TARGET_PX
            py = (ry_max - ry) * TARGET_PX
            canvas[py:py + TARGET_PX, px:px + TARGET_PX] = arr
        except Exception:
            pass

    x_min = rx_min * TILES_PER_REGION
    x_max = (rx_max + 1) * TILES_PER_REGION
    y_min = ry_min * TILES_PER_REGION
    y_max = (ry_max + 1) * TILES_PER_REGION

    return canvas, x_min, x_max, y_min, y_max


def game_to_pixel(
    gx: int, gy: int,
    x_min: int, y_min: int, y_max: int,
    canvas_h: int,
) -> tuple[int, int]:
    """Convert game coordinates to pixel coordinates on the canvas."""
    px = gx - x_min
    py = canvas_h - (gy - y_min) - 1
    return px, py


def render(db_path: Path, output_path: Path, font_path: Path) -> None:
    conn = sqlite3.connect(db_path)

    print("Stitching map tiles...")
    canvas, x_min, x_max, y_min, y_max = stitch_map(conn)
    canvas_h, canvas_w = canvas.shape[:2]
    print(f"  Canvas: {canvas_w}x{canvas_h} px, extent: ({x_min},{y_min})-({x_max},{y_max})")

    spawns = conn.execute(
        "SELECT item_name, x, y FROM ground_items WHERE plane = 0 ORDER BY item_name"
    ).fetchall()
    print(f"  {len(spawns)} ground item spawns to plot")
    conn.close()

    img = Image.fromarray(canvas)
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(str(font_path), size=8)

    dot_radius = 2
    dot_color = (50, 200, 50)
    label_color = (255, 255, 255)
    shadow_color = (0, 0, 0)

    for name, gx, gy in spawns:
        px, py = game_to_pixel(gx, gy, x_min, y_min, y_max, canvas_h)
        if 0 <= px < canvas_w and 0 <= py < canvas_h:
            draw.ellipse(
                (px - dot_radius, py - dot_radius, px + dot_radius, py + dot_radius),
                fill=dot_color,
            )
            lx, ly = px + dot_radius + 2, py - 4
            draw.text((lx + 1, ly + 1), name, fill=shadow_color, font=font)
            draw.text((lx, ly), name, fill=label_color, font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path))
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render ground item spawns on the world map")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    parser.add_argument("--output", type=Path, default=Path("data/ground_item_map.png"))
    parser.add_argument("--font", type=Path, required=True)
    args = parser.parse_args()
    render(args.db, args.output, args.font)
