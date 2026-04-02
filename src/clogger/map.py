from __future__ import annotations

import heapq
import sqlite3
from collections import defaultdict
from dataclasses import dataclass

from clogger.enums import MAP_LINK_ANYWHERE, MapLinkType
from clogger.location import DistanceMetric

GAME_TILES_PER_REGION = 64
PIXELS_PER_REGION = 256


@dataclass
class MapSquare:
    id: int
    plane: int
    region_x: int
    region_y: int
    image: bytes

    @property
    def game_x(self) -> int:
        return self.region_x * GAME_TILES_PER_REGION

    @property
    def game_y(self) -> int:
        return self.region_y * GAME_TILES_PER_REGION

    @classmethod
    def get(cls, conn: sqlite3.Connection, plane: int, region_x: int, region_y: int) -> MapSquare | None:
        row = conn.execute(
            "SELECT id, plane, region_x, region_y, image FROM map_squares WHERE plane = ? AND region_x = ? AND region_y = ?",
            (plane, region_x, region_y),
        ).fetchone()
        return cls(*row) if row else None

    @classmethod
    def all(cls, conn: sqlite3.Connection, plane: int = 0) -> list[MapSquare]:
        rows = conn.execute(
            "SELECT id, plane, region_x, region_y, image FROM map_squares WHERE plane = ? ORDER BY region_x, region_y",
            (plane,),
        ).fetchall()
        return [cls(*row) for row in rows]

    @classmethod
    def at_game_coord(cls, conn: sqlite3.Connection, x: int, y: int, plane: int = 0) -> MapSquare | None:
        rx = x // GAME_TILES_PER_REGION
        ry = y // GAME_TILES_PER_REGION
        return cls.get(conn, plane, rx, ry)

    @classmethod
    def count(cls, conn: sqlite3.Connection, plane: int = 0) -> int:
        return conn.execute("SELECT COUNT(*) FROM map_squares WHERE plane = ?", (plane,)).fetchone()[0]


@dataclass
class MapLink:
    id: int
    src_location: str
    dst_location: str
    src_x: int
    src_y: int
    dst_x: int
    dst_y: int
    link_type: MapLinkType
    description: str | None

    @classmethod
    def all(cls, conn: sqlite3.Connection, link_type: MapLinkType | None = None) -> list[MapLink]:
        query = "SELECT id, src_location, dst_location, src_x, src_y, dst_x, dst_y, type, description FROM map_links"
        params: list = []
        if link_type is not None:
            query += " WHERE type = ?"
            params.append(link_type.value)
        query += " ORDER BY src_location, dst_location"
        return [cls._from_row(r) for r in conn.execute(query, params).fetchall()]

    @classmethod
    def departing(cls, conn: sqlite3.Connection, location: str, link_type: MapLinkType | None = None) -> list[MapLink]:
        query = "SELECT id, src_location, dst_location, src_x, src_y, dst_x, dst_y, type, description FROM map_links WHERE src_location = ?"
        params: list = [location]
        if link_type is not None:
            query += " AND type = ?"
            params.append(link_type.value)
        query += " ORDER BY type, dst_location"
        return [cls._from_row(r) for r in conn.execute(query, params).fetchall()]

    @classmethod
    def arriving(cls, conn: sqlite3.Connection, location: str, link_type: MapLinkType | None = None) -> list[MapLink]:
        query = "SELECT id, src_location, dst_location, src_x, src_y, dst_x, dst_y, type, description FROM map_links WHERE dst_location = ?"
        params: list = [location]
        if link_type is not None:
            query += " AND type = ?"
            params.append(link_type.value)
        query += " ORDER BY type, src_location"
        return [cls._from_row(r) for r in conn.execute(query, params).fetchall()]

    @classmethod
    def between(cls, conn: sqlite3.Connection, location_a: str, location_b: str, link_type: MapLinkType | None = None) -> list[MapLink]:
        if link_type is not None:
            query = """SELECT id, src_location, dst_location, src_x, src_y, dst_x, dst_y, type, description FROM map_links
                        WHERE ((src_location = ? AND dst_location = ?)
                            OR (src_location = ? AND dst_location = ?))
                          AND type = ?
                        ORDER BY type"""
            params = [location_a, location_b, location_b, location_a, link_type.value]
        else:
            query = """SELECT id, src_location, dst_location, src_x, src_y, dst_x, dst_y, type, description FROM map_links
                        WHERE (src_location = ? AND dst_location = ?)
                           OR (src_location = ? AND dst_location = ?)
                        ORDER BY type"""
            params = [location_a, location_b, location_b, location_a]
        return [cls._from_row(r) for r in conn.execute(query, params).fetchall()]

    @classmethod
    def reachable_from(cls, conn: sqlite3.Connection, location: str) -> dict[str, list[MapLink]]:
        links = cls.departing(conn, location)
        result = {}
        for link in links:
            result.setdefault(link.dst_location, []).append(link)
        return result

    @classmethod
    def _from_row(cls, row: tuple):
        return cls(
            id=row[0],
            src_location=row[1],
            dst_location=row[2],
            src_x=row[3],
            src_y=row[4],
            dst_x=row[5],
            dst_y=row[6],
            link_type=MapLinkType(row[7]),
            description=row[8],
        )


# Zero-cost link types (instant transitions)
_ZERO_COST_TYPES = {
    MapLinkType.ENTRANCE,
    MapLinkType.EXIT,
    MapLinkType.FAIRY_RING,
    MapLinkType.CHARTER_SHIP,
    MapLinkType.QUETZAL,
    MapLinkType.TELEPORT,
}


def _build_adjacency(conn: sqlite3.Connection) -> dict[str, list[MapLink]]:
    """Build adjacency dict from all non-ANYWHERE map links."""
    adj: dict[str, list[MapLink]] = defaultdict(list)
    rows = conn.execute(
        "SELECT id, src_location, dst_location, src_x, src_y, dst_x, dst_y, type, description "
        "FROM map_links WHERE src_location != ?",
        (MAP_LINK_ANYWHERE,),
    ).fetchall()
    for row in rows:
        link = MapLink._from_row(row)
        adj[link.src_location].append(link)
    return adj


def _edge_cost(link: MapLink) -> float:
    """Compute traversal cost for a map link."""
    if link.link_type in _ZERO_COST_TYPES:
        return 0
    # Walkable: Chebyshev distance between endpoints
    dx = abs(link.src_x - link.dst_x)
    dy = abs(link.src_y - link.dst_y)
    return DistanceMetric.CHEBYSHEV.compute(dx, dy)


def _heuristic(loc_coords: dict[str, tuple[int, int]], current: str, goal: str) -> float:
    """A* heuristic: Chebyshev distance between coordinates."""
    c = loc_coords.get(current)
    g = loc_coords.get(goal)
    if c is None or g is None:
        return 0
    # If either is underground (y > 5000), heuristic is unreliable
    if c[1] > 5000 or g[1] > 5000:
        return 0
    dx = abs(c[0] - g[0])
    dy = abs(c[1] - g[1])
    return DistanceMetric.CHEBYSHEV.compute(dx, dy)


def _astar(
    adj: dict[str, list[MapLink]],
    loc_coords: dict[str, tuple[int, int]],
    start: str,
    goal: str,
) -> list[MapLink] | None:
    """Run A* from start to goal. Returns list of MapLinks or None if unreachable."""
    if start == goal:
        return []

    # Priority queue: (f_score, counter, node, path)
    counter = 0
    open_set: list[tuple[float, int, str, list[MapLink]]] = []
    heapq.heappush(open_set, (0, counter, start, []))
    g_scores: dict[str, float] = {start: 0}

    while open_set:
        f, _, current, path = heapq.heappop(open_set)

        if current == goal:
            return path

        current_g = g_scores.get(current, float("inf"))

        for link in adj.get(current, []):
            cost = _edge_cost(link)
            new_g = current_g + cost

            if new_g < g_scores.get(link.dst_location, float("inf")):
                g_scores[link.dst_location] = new_g
                h = _heuristic(loc_coords, link.dst_location, goal)
                counter += 1
                heapq.heappush(open_set, (new_g + h, counter, link.dst_location, path + [link]))

    return None


def find_path(
    conn: sqlite3.Connection,
    src: str,
    dst: str,
) -> list[MapLink] | None:
    """Find the shortest path between two locations.

    Considers all ANYWHERE teleports as potential starting points and
    picks the overall shortest path. Returns a list of MapLinks to
    traverse in order, or None if no path exists.
    """
    adj = _build_adjacency(conn)

    # Build location coordinate lookup
    loc_coords: dict[str, tuple[int, int]] = {}
    for row in conn.execute("SELECT name, x, y FROM locations WHERE x IS NOT NULL").fetchall():
        loc_coords[row[0]] = (row[1], row[2])

    # Collect ANYWHERE teleport links
    anywhere_links = conn.execute(
        "SELECT id, src_location, dst_location, src_x, src_y, dst_x, dst_y, type, description "
        "FROM map_links WHERE src_location = ?",
        (MAP_LINK_ANYWHERE,),
    ).fetchall()
    anywhere = [MapLink._from_row(r) for r in anywhere_links]

    # Candidate starts: actual source + each ANYWHERE teleport destination
    candidates: list[tuple[list[MapLink], str]] = [([], src)]
    for link in anywhere:
        candidates.append(([link], link.dst_location))

    best_path: list[MapLink] | None = None
    best_cost = float("inf")

    for prefix, start in candidates:
        prefix_cost = sum(_edge_cost(l) for l in prefix)
        if prefix_cost >= best_cost:
            continue

        result = _astar(adj, loc_coords, start, dst)
        if result is not None:
            total_cost = prefix_cost + sum(_edge_cost(l) for l in result)
            if total_cost < best_cost:
                best_cost = total_cost
                best_path = prefix + result

    return best_path


def _stitch_canvas(conn: sqlite3.Connection, x_min: int, x_max: int, y_min: int, y_max: int):
    """Stitch map tiles for a game coordinate region. Returns (canvas, extent)."""
    import io

    import numpy as np
    from PIL import Image

    rx_min = max(0, x_min // GAME_TILES_PER_REGION - 1)
    rx_max = x_max // GAME_TILES_PER_REGION + 1
    ry_min = max(0, y_min // GAME_TILES_PER_REGION - 1)
    ry_max = y_max // GAME_TILES_PER_REGION + 1

    canvas_w = (rx_max - rx_min + 1) * PIXELS_PER_REGION
    canvas_h = (ry_max - ry_min + 1) * PIXELS_PER_REGION
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

    rows = conn.execute(
        "SELECT region_x, region_y, image FROM map_squares WHERE plane = 0 "
        "AND region_x >= ? AND region_x <= ? AND region_y >= ? AND region_y <= ?",
        (rx_min, rx_max, ry_min, ry_max),
    ).fetchall()
    for rx, ry, img_data in rows:
        try:
            tile = np.array(Image.open(io.BytesIO(img_data)).convert("RGB"))
            px = (rx - rx_min) * PIXELS_PER_REGION
            py = (ry_max - ry) * PIXELS_PER_REGION
            canvas[py:py + PIXELS_PER_REGION, px:px + PIXELS_PER_REGION] = tile
        except Exception:
            pass

    extent = [
        rx_min * GAME_TILES_PER_REGION,
        (rx_max + 1) * GAME_TILES_PER_REGION,
        ry_min * GAME_TILES_PER_REGION,
        (ry_max + 1) * GAME_TILES_PER_REGION,
    ]
    return canvas, extent


def render_path(
    conn: sqlite3.Connection,
    path: list[MapLink],
    output_path: str,
    padding: int = 200,
    dpi: int = 200,
) -> None:
    """Render a path on the map with colored arrows for each edge type.

    Solid arrows for walking, dashed for teleports/transport.
    Surface and underground are rendered as stacked subplots.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not path:
        return

    UNDERGROUND_THRESHOLD = 5000

    edge_styles = {
        MapLinkType.WALKABLE: {"color": "lime", "linestyle": "-", "label": "Walk"},
        MapLinkType.ENTRANCE: {"color": "cyan", "linestyle": "-", "label": "Entrance"},
        MapLinkType.EXIT: {"color": "cyan", "linestyle": "-", "label": "Exit"},
        MapLinkType.FAIRY_RING: {"color": "magenta", "linestyle": "--", "label": "Fairy ring"},
        MapLinkType.CHARTER_SHIP: {"color": "orange", "linestyle": "--", "label": "Charter ship"},
        MapLinkType.QUETZAL: {"color": "yellow", "linestyle": "--", "label": "Quetzal"},
        MapLinkType.TELEPORT: {"color": "white", "linestyle": ":", "label": "Teleport"},
    }
    default_style = {"color": "white", "linestyle": "--", "label": "Other"}

    # Chain links for visual continuity: each link starts where the previous ended.
    # Insert implicit walk segments when there's a gap between links.
    chained: list[MapLink] = []
    for i, link in enumerate(path):
        if i > 0:
            prev = chained[-1]
            # If there's a gap, insert an implicit walk to bridge it
            if prev.dst_x != link.src_x or prev.dst_y != link.src_y:
                chained.append(MapLink(
                    id=-1,
                    src_location=prev.dst_location,
                    dst_location=link.src_location,
                    src_x=prev.dst_x,
                    src_y=prev.dst_y,
                    dst_x=link.src_x,
                    dst_y=link.src_y,
                    link_type=MapLinkType.WALKABLE,
                    description=f"Walk to {link.src_location}",
                ))
        chained.append(link)
    path = chained

    # Collect coordinates per zone
    coords: list[tuple[int, int]] = []
    for link in path:
        if link.src_location != MAP_LINK_ANYWHERE:
            coords.append((link.src_x, link.src_y))
        coords.append((link.dst_x, link.dst_y))

    surface_coords = [(x, y) for x, y in coords if y < UNDERGROUND_THRESHOLD]
    underground_coords = [(x, y) for x, y in coords if y >= UNDERGROUND_THRESHOLD]
    has_underground = len(underground_coords) > 0

    # Determine subplot layout
    n_panels = 2 if has_underground else 1
    fig, axes = plt.subplots(n_panels, 1, figsize=(16, 8 * n_panels),
                              gridspec_kw={"height_ratios": [2, 1] if has_underground else [1]})
    if n_panels == 1:
        axes = [axes]

    # --- Surface panel ---
    ax_surface = axes[0]
    if surface_coords:
        sx = [c[0] for c in surface_coords]
        sy = [c[1] for c in surface_coords]
        s_xmin, s_xmax = min(sx) - padding, max(sx) + padding
        s_ymin, s_ymax = min(sy) - padding, max(sy) + padding

        canvas, extent = _stitch_canvas(conn, s_xmin, s_xmax, s_ymin, s_ymax)
        ax_surface.imshow(canvas, extent=extent, aspect="equal")
        ax_surface.set_xlim(s_xmin, s_xmax)
        ax_surface.set_ylim(s_ymin, s_ymax)
    ax_surface.set_title("Surface", fontsize=12)
    ax_surface.axis("off")

    # --- Underground panel ---
    ax_under = axes[1] if has_underground else None
    if has_underground:
        ux = [c[0] for c in underground_coords]
        uy = [c[1] for c in underground_coords]
        u_xmin, u_xmax = min(ux) - padding, max(ux) + padding
        u_ymin, u_ymax = min(uy) - padding, max(uy) + padding

        canvas, extent = _stitch_canvas(conn, u_xmin, u_xmax, u_ymin, u_ymax)
        ax_under.imshow(canvas, extent=extent, aspect="equal")
        ax_under.set_xlim(u_xmin, u_xmax)
        ax_under.set_ylim(u_ymin, u_ymax)
        ax_under.set_title("Underground", fontsize=12)
        ax_under.axis("off")

    def get_ax(y: int):
        if y >= UNDERGROUND_THRESHOLD and ax_under is not None:
            return ax_under
        return ax_surface

    # Draw edges
    seen_labels: set[str] = set()
    for link in path:
        style = edge_styles.get(link.link_type, default_style)

        if link.src_location == MAP_LINK_ANYWHERE:
            ax = get_ax(link.dst_y)
            ax.plot(link.dst_x, link.dst_y, "*", color=style["color"], markersize=15, zorder=15,
                    label=style["label"] if style["label"] not in seen_labels else None)
            seen_labels.add(style["label"])
            continue

        src_ax = get_ax(link.src_y)
        dst_ax = get_ax(link.dst_y)

        if src_ax is dst_ax:
            # Same panel — draw normal arrow
            ax = src_ax
            ax.annotate("",
                         xy=(link.dst_x, link.dst_y),
                         xytext=(link.src_x, link.src_y),
                         arrowprops=dict(arrowstyle="->", color=style["color"],
                                         linestyle=style["linestyle"], lw=2),
                         zorder=10)
        else:
            # Cross-panel — mark source with label pointing to destination
            src_ax.plot(link.src_x, link.src_y, "v", color=style["color"], markersize=12,
                        markeredgecolor="black", markeredgewidth=1, zorder=15)
            src_ax.text(link.src_x, link.src_y - 15, f"→ {link.dst_location}",
                        fontsize=8, color=style["color"], ha="center", va="top",
                        fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="black", alpha=0.8))

        label = style["label"] if style["label"] not in seen_labels else None
        if label:
            ax_surface.plot([], [], color=style["color"], linestyle=style["linestyle"], lw=2, label=label)
            seen_labels.add(style["label"])

    # Mark locations
    locations_on_path = []
    for link in path:
        if link.src_location != MAP_LINK_ANYWHERE:
            locations_on_path.append((link.src_location, link.src_x, link.src_y))
        locations_on_path.append((link.dst_location, link.dst_x, link.dst_y))

    seen_locs: set[str] = set()
    unique_locs = []
    for name, x, y in locations_on_path:
        if name not in seen_locs:
            seen_locs.add(name)
            unique_locs.append((name, x, y))

    for name, x, y in unique_locs:
        ax = get_ax(y)
        ax.plot(x, y, "o", color="white", markersize=8, markeredgecolor="black",
                markeredgewidth=1, zorder=20)
        ax.text(x, y + 12, name, fontsize=8, color="white", ha="center", va="bottom",
                zorder=21, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="black", alpha=0.7))

    ax_surface.legend(loc="upper left", fontsize=10, framealpha=0.8)
    fig.suptitle(f"{unique_locs[0][0]} → {unique_locs[-1][0]}", fontsize=14)
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close()
