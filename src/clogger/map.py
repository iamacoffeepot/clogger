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
