import math
import sqlite3

from clogger.enums import Region
from clogger.location import Adjacency, DistanceMetric, Location


def _seed_locations(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO locations (name, region, type, members, x, y) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("Lumbridge", Region.MISTHALIN.value, "settlement", 0, 3188, 3220),
            ("Varrock", Region.MISTHALIN.value, "settlement", 0, 3210, 3448),
            ("Aldarin", Region.VARLAMORE.value, "Island", 1, 1391, 2935),
        ],
    )
    conn.executemany(
        "INSERT INTO location_adjacencies (location_id, direction, neighbor) VALUES (?, ?, ?)",
        [
            (1, "north", "Varrock"),
            (1, "east", "Al Kharid"),
            (2, "south", "Lumbridge"),
        ],
    )
    conn.commit()


def test_all(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    locations = Location.all(conn)
    assert len(locations) == 3
    assert all(isinstance(loc, Location) for loc in locations)


def test_all_filter_region(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    locations = Location.all(conn, region=Region.MISTHALIN)
    assert len(locations) == 2
    assert all(loc.region == Region.MISTHALIN for loc in locations)


def test_by_name(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    loc = Location.by_name(conn, "Lumbridge")
    assert loc is not None
    assert loc.region == Region.MISTHALIN
    assert loc.type == "settlement"
    assert loc.members is False


def test_by_name_not_found(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    assert Location.by_name(conn, "Nonexistent") is None


def test_adjacencies(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    loc = Location.by_name(conn, "Lumbridge")
    adjs = loc.adjacencies(conn)
    assert len(adjs) == 2
    assert all(isinstance(a, Adjacency) for a in adjs)
    directions = {a.direction: a.neighbor for a in adjs}
    assert directions["north"] == "Varrock"
    assert directions["east"] == "Al Kharid"


def test_neighbors(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    loc = Location.by_name(conn, "Lumbridge")
    neighbors = loc.neighbors(conn)
    assert neighbors["north"] is not None
    assert neighbors["north"].name == "Varrock"
    # Al Kharid is not in the DB
    assert neighbors["east"] is None


def test_nearby_chebyshev(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    loc = Location.by_name(conn, "Lumbridge")
    # Varrock is dx=22, dy=228 -> chebyshev = 228
    results = loc.nearby(conn, 300, metric=DistanceMetric.CHEBYSHEV)
    names = [r[0].name for r in results]
    assert "Varrock" in names
    # Aldarin is dx=1797, dy=285 -> chebyshev = 1797, too far
    assert "Aldarin" not in names


def test_nearby_manhattan(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    loc = Location.by_name(conn, "Lumbridge")
    # Varrock: dx=22, dy=228 -> manhattan = 250
    results = loc.nearby(conn, 250, metric=DistanceMetric.MANHATTAN)
    assert len(results) == 1
    assert results[0][0].name == "Varrock"
    assert results[0][1] == 250


def test_nearby_euclidean(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    loc = Location.by_name(conn, "Lumbridge")
    # Varrock: sqrt(22^2 + 228^2) = sqrt(484 + 51984) = sqrt(52468) ~ 229.06
    results = loc.nearby(conn, 230, metric=DistanceMetric.EUCLIDEAN)
    assert len(results) == 1
    assert results[0][0].name == "Varrock"
    expected = math.sqrt(22**2 + 228**2)
    assert abs(results[0][1] - expected) < 0.01


def test_nearby_default_is_chebyshev(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    loc = Location.by_name(conn, "Lumbridge")
    results_default = loc.nearby(conn, 300)
    results_chebyshev = loc.nearby(conn, 300, metric=DistanceMetric.CHEBYSHEV)
    assert len(results_default) == len(results_chebyshev)
    assert [r[0].name for r in results_default] == [r[0].name for r in results_chebyshev]


def test_nearby_no_coordinates(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    # Insert a location without coordinates
    conn.execute(
        "INSERT INTO locations (name, region, type, members) VALUES (?, ?, ?, ?)",
        ("Mystery", Region.MISTHALIN.value, "dungeon", 1),
    )
    conn.commit()
    loc = Location.by_name(conn, "Mystery")
    assert loc.nearby(conn, 1000) == []


def test_nearby_excludes_self(conn: sqlite3.Connection) -> None:
    _seed_locations(conn)
    loc = Location.by_name(conn, "Lumbridge")
    results = loc.nearby(conn, 100000)
    names = [r[0].name for r in results]
    assert "Lumbridge" not in names
