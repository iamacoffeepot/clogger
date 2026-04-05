"""Import game variable constants from VarpConstants.java and VarcConstants.java into the database."""

import argparse
import re
from pathlib import Path

from ragger.db import create_tables, get_connection

PLUGIN_DIR = Path(__file__).parent.parent / "plugin/src/main/java/dev/ragger/plugin/scripting"
VARP_FILE = PLUGIN_DIR / "VarpConstants.java"
VARC_FILE = PLUGIN_DIR / "VarcConstants.java"

PUT_RE = re.compile(r'map\.put\("(\w+)",\s*(\d+)\)')


def parse_varp_constants(path: Path) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """Parse VarpConstants.java, returning (varplayer_entries, varbit_entries)."""
    text = path.read_text()
    varplayers: list[tuple[str, int]] = []
    varbits: list[tuple[str, int]] = []

    # Split by init method boundaries to determine type
    in_varbit = False
    for line in text.splitlines():
        if "initVarbit" in line and "private static void" in line:
            in_varbit = True
        elif "initVarPlayer" in line and "private static void" in line:
            in_varbit = False

        m = PUT_RE.search(line)
        if m:
            name, var_id = m.group(1), int(m.group(2))
            if in_varbit:
                varbits.append((name, var_id))
            else:
                varplayers.append((name, var_id))

    return varplayers, varbits


def parse_varc_constants(path: Path) -> list[tuple[str, int]]:
    """Parse VarcConstants.java, returning varc_int entries."""
    text = path.read_text()
    entries: list[tuple[str, int]] = []
    for m in PUT_RE.finditer(text):
        entries.append((m.group(1), int(m.group(2))))
    return entries


def ingest(db_path: Path) -> None:
    create_tables(db_path)
    conn = get_connection(db_path)

    conn.execute("DELETE FROM game_vars")

    varplayers, varbits = parse_varp_constants(VARP_FILE)
    varc_ints = parse_varc_constants(VARC_FILE)

    conn.executemany(
        "INSERT INTO game_vars (name, var_id, var_type) VALUES (?, ?, 'varp')",
        [(name, var_id) for name, var_id in varplayers],
    )
    conn.executemany(
        "INSERT INTO game_vars (name, var_id, var_type) VALUES (?, ?, 'varbit')",
        [(name, var_id) for name, var_id in varbits],
    )
    conn.executemany(
        "INSERT INTO game_vars (name, var_id, var_type) VALUES (?, ?, 'varc_int')",
        [(name, var_id) for name, var_id in varc_ints],
    )

    conn.commit()
    total = len(varplayers) + len(varbits) + len(varc_ints)
    print(f"Imported {total} game vars ({len(varplayers)} varps, {len(varbits)} varbits, {len(varc_ints)} varc_ints)")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import game variable constants into the database")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/ragger.db"),
        help="Path to the SQLite database",
    )
    args = parser.parse_args()
    ingest(args.db)
