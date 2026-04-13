"""Fetch Quetzal Transport System data and create map links between all stops.

Every Quetzal stop connects to every other stop. Whether a given stop is
selectable from the menu is gated by a `QUETZAL_<NAME>` varbit that flips
on once the player builds (or earns) that stop. We attach the destination
stop's varbit as a var requirement on each outbound link, so consumers
can check live state without us guessing what "default" means.
"""

import argparse
import re
from pathlib import Path

from ragger.db import create_tables, get_connection
from ragger.enums import MapLinkType
from ragger.wiki import (
    fetch_page_wikitext_with_attribution,
    link_group_requirement,
)

# Wiki stop name -> game_vars.name. The game_vars naming drops spaces and
# uses uppercase; Auburnvale is "AUBURNVALLEY" (typo baked into the varbit).
_STOP_VAR_NAMES: dict[str, str] = {
    "Aldarin": "QUETZAL_ALDARIN",
    "Auburnvale": "QUETZAL_AUBURNVALLEY",
    "Civitas illa Fortis": "QUETZAL_FORTIS",
    "Hunter Guild": "QUETZAL_HUNTERGUILD",
    "Quetzacalli Gorge": "QUETZAL_QUETZACALLIGORGE",
    "Sunset Coast": "QUETZAL_SUNSETCOAST",
    "Tal Teklan": "QUETZAL_TALTEKLAN",
    "The Teomat": "QUETZAL_TEOMAT",
    "Cam Torum": "QUETZAL_CAMTORUM",
    "Colossal Wyrm Remains": "QUETZAL_COLOSSALWYRM",
    "Fortis Colosseum": "QUETZAL_COLOSSEUM",
    "Kastori": "QUETZAL_KASTORI",
    "Outer Fortis": "QUETZAL_OUTERFORTIS",
    "Salvager Overlook": "QUETZAL_SALVAGEROVERLOOK",
}


def parse_quetzal_stops(wikitext: str) -> list[dict]:
    """Parse quetzal transport stops from the Locations table.

    Returns a dict per stop with its display name (as used by the DB) and
    coordinates. The wiki's "Default status" column is ignored — it reflects
    main-game state, not league availability, and the authoritative answer
    lives in the per-stop varbit.
    """
    stops: list[dict] = []
    seen: set[str] = set()
    rows = wikitext.split("|-")
    for row in rows:
        # Each stop row has `[[Name]]...{{Map|...|x:NNN,y:NNN|...}}`.
        name_match = re.search(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]", row)
        coord_match = re.search(r"x:(\d+),\s*y:(\d+)", row)
        if not name_match or not coord_match:
            continue
        name = name_match.group(1).strip()
        if name in seen or name not in _STOP_VAR_NAMES:
            continue
        seen.add(name)
        stops.append({
            "name": name,
            "x": int(coord_match.group(1)),
            "y": int(coord_match.group(2)),
        })
    return stops


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    print("Fetching Quetzal Transport System data...")
    wikitext = fetch_page_wikitext_with_attribution(conn, "Quetzal Transport System", "map_links")
    stops = parse_quetzal_stops(wikitext)
    print(f"Found {len(stops)} quetzal stops")

    # Resolve each stop's unlock varbit into a game_vars.id once, up-front.
    stop_var_ids: dict[str, int] = {}
    for stop in stops:
        var_name = _STOP_VAR_NAMES[stop["name"]]
        row = conn.execute("SELECT id FROM game_vars WHERE name = ?", (var_name,)).fetchone()
        if row is None:
            raise ValueError(
                f"Missing game_vars row for {var_name} — run import_game_vars.py first",
            )
        stop_var_ids[stop["name"]] = row[0]

    # Wipe previous ingestion's rows (links + junction) so re-running is
    # idempotent. Orphaned requirement_groups are left behind intentionally;
    # a full rebuild from create_tables drops them.
    conn.execute(
        "DELETE FROM map_link_requirement_groups "
        "WHERE map_link_id IN (SELECT id FROM map_links WHERE type = ?)",
        (MapLinkType.QUETZAL.value,),
    )
    conn.execute("DELETE FROM map_links WHERE type = ?", (MapLinkType.QUETZAL.value,))

    link_count = 0
    for from_stop in stops:
        for to_stop in stops:
            if from_stop["name"] == to_stop["name"]:
                continue
            conn.execute(
                """INSERT INTO map_links
                   (src_location, dst_location, src_x, src_y, dst_x, dst_y, type, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    from_stop["name"],
                    to_stop["name"],
                    from_stop["x"],
                    from_stop["y"],
                    to_stop["x"],
                    to_stop["y"],
                    MapLinkType.QUETZAL.value,
                    f"Quetzal: {from_stop['name']} -> {to_stop['name']}",
                ),
            )
            map_link_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            link_group_requirement(
                conn,
                "group_varbit_requirements",
                {"var_id": stop_var_ids[to_stop["name"]], "value": 1, "operator": "=="},
                "map_link_requirement_groups",
                "map_link_id",
                map_link_id,
            )
            link_count += 1

    conn.commit()
    print(f"Inserted {link_count} quetzal transport links into {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Quetzal Transport System map links")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/ragger.db"),
        help="Path to the SQLite database",
    )
    args = parser.parse_args()
    ingest(args.db)
