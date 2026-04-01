import sqlite3
from pathlib import Path

from clogger.enums import Skill

_skill_values = ", ".join(f"'{s.value}'" for s in Skill)

SCHEMAS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS quests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quest_requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        quest_id INTEGER NOT NULL,
        partial INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (task_id) REFERENCES tasks(id),
        FOREIGN KEY (quest_id) REFERENCES quests(id)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS skill_requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        skill TEXT NOT NULL CHECK(skill IN ({_skill_values})),
        level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 99),
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    )
    """,
]


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(db_path: Path) -> None:
    conn = get_connection(db_path)
    for schema in SCHEMAS:
        conn.execute(schema)
    conn.commit()
    conn.close()
