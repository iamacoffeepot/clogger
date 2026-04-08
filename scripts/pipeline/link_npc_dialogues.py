"""Link NPCs to dialogue pages by matching NPC names to transcript titles.

Only creates authoritative links where the NPC name exactly matches
a transcript page title. For non-authoritative mentions (e.g. an NPC
referenced in a quest transcript), query dialogue_tags directly.
"""

import argparse
from pathlib import Path

from ragger.db import create_tables, get_connection


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    conn.execute("DELETE FROM npc_dialogues")

    linked = conn.execute(
        """INSERT OR IGNORE INTO npc_dialogues (npc_id, page_id)
           SELECT n.id, dp.id
           FROM npcs n
           JOIN dialogue_pages dp ON dp.title = n.name
           WHERE dp.page_type = 'npc'""",
    ).rowcount

    conn.commit()

    npcs_linked = conn.execute("SELECT COUNT(DISTINCT npc_id) FROM npc_dialogues").fetchone()[0]
    print(f"Linked {linked} NPC-dialogue pairs ({npcs_linked} distinct NPCs)", flush=True)

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Link NPCs to dialogue pages")
    parser.add_argument("--db", type=Path, default=Path("data/ragger.db"))
    args = parser.parse_args()
    ingest(args.db)
