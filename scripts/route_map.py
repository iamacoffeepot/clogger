"""Generate a stitched, annotated map of the Demonic Pacts route's key areas.

One-off script. Outputs data/demonic-pacts-route-map.png.
"""

from __future__ import annotations

import sqlite3
import sys

import matplotlib.pyplot as plt

from ragger.map import MapSquare


PANELS: list[dict] = [
    {
        "title": "Varlamore (surface)",
        "plane": 0,
        "bbox": (1190, 1740, 2880, 3380),
        "markers": [
            (1391, 2935, "Aldarin (Toci's gem store, spawn after Stage 1)"),
            (1725, 3128, "Civitas illa Fortis (Trader Stan's, furnace)"),
            (1223, 3111, "Tal Teklan (Quetzal hub for Cam Torum walk)"),
            (1417, 3360, "Auburnvale (Sebamo's staffs, optional)"),
            (1635, 3010, "Avium Savannah (Hill Giant task)"),
            (1290, 3135, "Tlati Rainforest (Dragon Nest entrance)"),
        ],
    },
    {
        "title": "Varlamore (underground)",
        "plane": 0,
        "bbox": (1230, 1540, 9480, 9590),
        "markers": [
            (1246, 9500, "Dragon Nest (Blue/Red dragons, Stage 3)"),
            (1311, 9520, "Ruins of Mokhaiotl (walking link)"),
            (1453, 9565, "Cam Torum (Runic Emporium - runes)"),
        ],
    },
    {
        "title": "Karamja (surface)",
        "plane": 0,
        "bbox": (2720, 2880, 2950, 3210),
        "markers": [
            (2760, 3184, "Brimhaven (Hajedy cart to Shilo)"),
            (2744, 3155, "Brimhaven Dungeon entrance (Steel dragons)"),
            (2849, 2972, "Shilo Village (Duradel - Anti-dragon shield)"),
            (2856, 3168, "Mor Ul Rek surface entrance"),
            (2845, 3174, "Karamja Volcano"),
        ],
    },
    {
        "title": "Mor Ul Rek (underground)",
        "plane": 0,
        "bbox": (2430, 2570, 5040, 5210),
        "markers": [
            (2543, 5144, "Mor Ul Rek bank"),
            (2446, 5179, "TzHaar City (Tz-Kih L22 - TzHaar task)"),
        ],
    },
]


def render_panel(ax, conn, panel: dict) -> None:
    x_min, x_max, y_min, y_max = panel["bbox"]
    canvas, extent = MapSquare.stitch(
        conn, x_min, x_max, y_min, y_max,
        plane=panel["plane"], region_padding=0,
    )
    ax.imshow(canvas, extent=extent, origin="upper")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_title(panel["title"], fontsize=11, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    for x, y, label in panel["markers"]:
        ax.plot(x, y, "o", color="red", markersize=6, markeredgecolor="white", markeredgewidth=1.5)
        ax.annotate(
            label, xy=(x, y), xytext=(8, 8), textcoords="offset points",
            fontsize=7, color="white",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="black", alpha=0.75, edgecolor="none"),
        )


def main() -> None:
    conn = sqlite3.connect("data/ragger.db")

    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    for ax, panel in zip(axes.flat, PANELS):
        render_panel(ax, conn, panel)

    fig.suptitle("Demonic Pacts Route - Key Areas", fontsize=14, fontweight="bold")
    fig.tight_layout()
    out = "data/demonic-pacts-route-map.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
