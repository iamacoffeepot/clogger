"""Apply league configuration from a YAML file to the database.

Sets autocompleted flags on quests based on the config.
Resets all quests to not autocompleted first, then sets the ones listed.
"""

import argparse
from pathlib import Path

import yaml

from clogger.db import get_connection


def apply(db_path: Path, config_path: Path, chain: bool = True) -> None:
    with open(config_path) as f:
        config = yaml.safe_load(f)

    conn = get_connection(db_path)

    # Reset all quests to not autocompleted
    conn.execute("UPDATE quests SET autocompleted = 0")

    autocompleted = config.get("autocompleted_quests", [])
    missing: list[str] = []
    quest_ids: set[int] = set()

    for quest_name in autocompleted:
        row = conn.execute("SELECT id FROM quests WHERE name = ?", (quest_name,)).fetchone()
        if row:
            quest_ids.add(row[0])
        else:
            missing.append(quest_name)

    # Traverse requirement chains to find all implicitly completed quests
    if not chain:
        to_visit = []
    else:
        to_visit = list(quest_ids)
    while to_visit:
        qid = to_visit.pop()
        rows = conn.execute(
            """
            SELECT q.id FROM quests q
            JOIN quest_requirements qr ON qr.required_quest_id = q.id
            JOIN quest_quest_requirements qqr ON qqr.quest_requirement_id = qr.id
            WHERE qqr.quest_id = ?
            """,
            (qid,),
        ).fetchall()
        for row in rows:
            if row[0] not in quest_ids:
                quest_ids.add(row[0])
                to_visit.append(row[0])

    # Apply
    if quest_ids:
        placeholders = ",".join("?" * len(quest_ids))
        conn.execute(
            f"UPDATE quests SET autocompleted = 1 WHERE id IN ({placeholders})",
            list(quest_ids),
        )

    conn.commit()
    conn.close()

    print(f"Set {len(quest_ids)} quests as autocompleted ({len(autocompleted)} listed, {len(quest_ids) - len(autocompleted)} from chains)")
    if missing:
        print(f"Warning — not found in database: {', '.join(missing)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply league config to the database")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/clogger.db"),
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "config",
        type=Path,
        help="Path to the league YAML config file",
    )
    parser.add_argument(
        "--no-chain",
        action="store_true",
        help="Only mark listed quests, don't resolve prerequisite chains",
    )
    args = parser.parse_args()
    apply(args.db, args.config, chain=not args.no_chain)
