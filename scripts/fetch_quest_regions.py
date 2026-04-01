"""Fetch quest-to-region mappings from the Demonic Pacts League area pages.

Creates region requirements for quests based on which area page lists them.
A quest listed on multiple area pages gets a bitmask of all those regions (AND).

Requires: fetch_quests.py to have been run first.
"""

import argparse
import re
import time
from pathlib import Path

import requests

from clogger.db import create_tables, get_connection
from clogger.enums import Region

API_URL = "https://oldschool.runescape.wiki/api.php"
USER_AGENT = "clogger/0.1 - OSRS Leagues planner"
HEADERS = {"User-Agent": USER_AGENT}

AREA_PAGES: dict[str, Region] = {
    "Demonic_Pacts_League/Areas/Asgarnia": Region.ASGARNIA,
    "Demonic_Pacts_League/Areas/Kharidian_Desert": Region.DESERT,
    "Demonic_Pacts_League/Areas/Fremennik": Region.FREMENNIK,
    "Demonic_Pacts_League/Areas/Kandarin": Region.KANDARIN,
    "Demonic_Pacts_League/Areas/Karamja": Region.KARAMJA,
    "Demonic_Pacts_League/Areas/Kebos_and_Kourend": Region.KOUREND,
    "Demonic_Pacts_League/Areas/Morytania": Region.MORYTANIA,
    "Demonic_Pacts_League/Areas/Tirannwn": Region.TIRANNWN,
    "Demonic_Pacts_League/Areas/Varlamore": Region.VARLAMORE,
    "Demonic_Pacts_League/Areas/Wilderness": Region.WILDERNESS,
}

QUEST_LINK_PATTERN = re.compile(r"\[\[([^]|]+?)(?:\|[^]]+)?\]\]")


def fetch_wikitext(page: str) -> str:
    resp = requests.get(
        API_URL,
        params={"action": "parse", "page": page, "prop": "wikitext", "format": "json"},
        headers=HEADERS,
    )
    resp.raise_for_status()
    return resp.json()["parse"]["wikitext"]["*"]


def extract_quests_section(wikitext: str) -> str:
    """Extract the ===Quests=== section from the wikitext."""
    match = re.search(r"===\s*Quests\s*===\s*\n(.*?)(?:\n===|\Z)", wikitext, re.DOTALL)
    return match.group(1) if match else ""


def parse_quest_names(quests_section: str) -> list[str]:
    """Extract quest names from the bulleted list. Only top-level * entries are
    the quests for this region — nested ** entries are prerequisites."""
    names: list[str] = []
    for line in quests_section.split("\n"):
        stripped = line.strip()
        # Only top-level bullets (single *)
        if stripped.startswith("*") and not stripped.startswith("**"):
            match = QUEST_LINK_PATTERN.search(stripped)
            if match:
                name = match.group(1).strip()
                if name not in names:
                    names.append(name)
    return names


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    quest_ids = dict(conn.execute("SELECT name, id FROM quests").fetchall())

    # Build quest -> set of regions
    quest_regions: dict[str, int] = {}

    for page, region in AREA_PAGES.items():
        print(f"  Fetching {region.label}...")
        wikitext = fetch_wikitext(page)
        quests_section = extract_quests_section(wikitext)
        quest_names = parse_quest_names(quests_section)

        for name in quest_names:
            if name in quest_ids:
                quest_regions.setdefault(name, 0)
                quest_regions[name] |= region.mask

        print(f"    {len(quest_names)} quests listed, {sum(1 for n in quest_names if n in quest_ids)} matched")
        time.sleep(0.1)

    # Create region requirements and link to quests
    req_count = 0
    for quest_name, mask in quest_regions.items():
        quest_id = quest_ids[quest_name]
        conn.execute(
            "INSERT OR IGNORE INTO region_requirements (regions, any_region) VALUES (?, ?)",
            (mask, 0),
        )
        req_id = conn.execute(
            "SELECT id FROM region_requirements WHERE regions = ? AND any_region = 0",
            (mask,),
        ).fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO quest_region_requirements (quest_id, region_requirement_id) VALUES (?, ?)",
            (quest_id, req_id),
        )
        req_count += 1

    conn.commit()
    print(f"\nInserted {req_count} quest region requirements into {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch quest-to-region mappings")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/clogger.db"),
        help="Path to the SQLite database",
    )
    args = parser.parse_args()
    ingest(args.db)
