from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class GameVar:
    id: int
    name: str
    var_id: int
    var_type: str
    description: str | None

    @classmethod
    def all(cls, conn: sqlite3.Connection, var_type: str | None = None) -> list[GameVar]:
        if var_type:
            rows = conn.execute(
                "SELECT id, name, var_id, var_type, description FROM game_vars WHERE var_type = ? ORDER BY var_id",
                (var_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, var_id, var_type, description FROM game_vars ORDER BY var_type, var_id"
            ).fetchall()
        return [cls(*row) for row in rows]

    @classmethod
    def by_name(cls, conn: sqlite3.Connection, name: str) -> list[GameVar]:
        rows = conn.execute(
            "SELECT id, name, var_id, var_type, description FROM game_vars WHERE name = ?",
            (name,),
        ).fetchall()
        return [cls(*row) for row in rows]

    @classmethod
    def search(cls, conn: sqlite3.Connection, name: str) -> list[GameVar]:
        rows = conn.execute(
            "SELECT id, name, var_id, var_type, description FROM game_vars WHERE name LIKE ? ORDER BY var_type, var_id",
            (f"%{name}%",),
        ).fetchall()
        return [cls(*row) for row in rows]

    @classmethod
    def by_var_id(cls, conn: sqlite3.Connection, var_id: int, var_type: str) -> GameVar | None:
        row = conn.execute(
            "SELECT id, name, var_id, var_type, description FROM game_vars WHERE var_id = ? AND var_type = ?",
            (var_id, var_type),
        ).fetchone()
        return cls(*row) if row else None
