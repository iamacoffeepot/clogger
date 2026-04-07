"""Import game variable constants from JSON files produced by DumpGameVars into the database."""

import argparse
import json
from pathlib import Path

from ragger.db import create_tables, get_connection

GAME_VARS_DIR = Path(__file__).parent.parent / "data/game-vars"


def ingest(db_path: Path, vars_dir: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    conn.execute("DELETE FROM game_vars")

    total = 0
    counts: list[str] = []

    for json_file in sorted(vars_dir.glob("*.json")):
        data = json.loads(json_file.read_text())
        var_type = data["var_type"]
        entries = data["entries"]

        conn.executemany(
            "INSERT INTO game_vars (name, var_id, var_type, description) VALUES (?, ?, ?, ?)",
            [(e["name"], e["id"], var_type, e.get("comment")) for e in entries],
        )

        total += len(entries)
        counts.append(f"{len(entries)} {var_type}")

    conn.commit()
    print(f"Imported {total} game vars ({', '.join(counts)})")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import game variable constants into the database")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/ragger.db"),
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "--vars-dir",
        type=Path,
        default=GAME_VARS_DIR,
        help="Directory containing JSON files from DumpGameVars",
    )
    args = parser.parse_args()
    ingest(args.db, args.vars_dir)
