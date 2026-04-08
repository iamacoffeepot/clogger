"""Render a full map of NPC locations as dots with labels.

Stitches plane-0 color map squares (downscaled to 1px/tile) and overlays
NPC location dots from the npc_locations table.
"""

import argparse
import sqlite3
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ragger.map import MapSquare


def render(db_path: Path, output_path: Path, font_path: Path) -> None:
    conn = sqlite3.connect(db_path)

    # Full world extent
    bounds = conn.execute(
        "SELECT MIN(region_x) * 64, (MAX(region_x) + 1) * 64, "
        "MIN(region_y) * 64, (MAX(region_y) + 1) * 64 "
        "FROM map_squares WHERE plane = 0 AND type = 'color'"
    ).fetchone()
    x_min, x_max, y_min, y_max = bounds

    print("Stitching map tiles...")
    canvas, extent = MapSquare.stitch(
        conn, x_min, x_max, y_min, y_max,
        region_padding=0, pixels_per_tile=1,
    )
    canvas_h, canvas_w = canvas.shape[:2]
    print(f"  Canvas: {canvas_w}x{canvas_h} px")

    npcs = conn.execute("SELECT game_id, name, x, y FROM npc_locations ORDER BY name").fetchall()
    print(f"  {len(npcs)} NPC locations to plot")
    conn.close()

    img = Image.fromarray(canvas)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(font_path), size=8)

    dot_radius = 2
    dot_color = (255, 50, 50)
    label_color = (255, 255, 255)
    shadow_color = (0, 0, 0)

    for _, name, gx, gy in npcs:
        px = gx - extent[0]
        py = canvas_h - (gy - extent[2]) - 1
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
    parser = argparse.ArgumentParser(description="Render NPC locations on the world map")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    parser.add_argument("--output", type=Path, default=Path("data/npc_map.png"))
    parser.add_argument("--font", type=Path, required=True)
    args = parser.parse_args()
    render(args.db, args.output, args.font)
