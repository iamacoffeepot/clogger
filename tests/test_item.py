import sqlite3

from ragger.item import Item


def _seed_items(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO items (name, members, tradeable, weight, game_id, examine) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("Coins", 0, 1, 0.0, 995, "Lovely money!"),
            ("Rope", 0, 1, 0.8, 954, "A coil of rope."),
            ("Spade", 0, 1, 2.0, 952, "A fairly small spade."),
        ],
    )
    conn.commit()


def test_all(conn: sqlite3.Connection) -> None:
    _seed_items(conn)
    items = Item.all(conn)
    assert len(items) == 3
    assert all(isinstance(i, Item) for i in items)
    assert items[0].name == "Coins"


def test_by_name(conn: sqlite3.Connection) -> None:
    _seed_items(conn)
    item = Item.by_name(conn, "Rope")
    assert item is not None
    assert item.name == "Rope"
    assert item.members is False
    assert item.tradeable is True
    assert item.weight == 0.8
    assert item.game_id == 954
    assert item.examine == "A coil of rope."


def test_by_name_not_found(conn: sqlite3.Connection) -> None:
    _seed_items(conn)
    assert Item.by_name(conn, "Nonexistent") is None


def test_search(conn: sqlite3.Connection) -> None:
    _seed_items(conn)
    results = Item.search(conn, "ope")
    assert len(results) == 1
    assert results[0].name == "Rope"


def test_nullable_fields(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO items (name) VALUES (?)", ("Mystery box",))
    conn.commit()
    item = Item.by_name(conn, "Mystery box")
    assert item is not None
    assert item.members is None
    assert item.tradeable is None
    assert item.weight is None
    assert item.game_id is None
    assert item.examine is None
