from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from ragger.enums import ContentCategory, FunctionalTag


@dataclass
class ContentTag:
    """A parsed content tag like quest:troll_stronghold."""

    category: ContentCategory
    name: str

    def __str__(self) -> str:
        return f"{self.category.value}:{self.name}"

    @classmethod
    def parse(cls, raw: str) -> ContentTag | None:
        if ":" not in raw:
            return None
        cat_str, name = raw.split(":", 1)
        try:
            return cls(category=ContentCategory.from_label(cat_str), name=name)
        except ValueError:
            return None

    @classmethod
    def parse_list(cls, raw_list: list[str]) -> list[ContentTag]:
        tags = []
        for raw in raw_list:
            tag = cls.parse(raw)
            if tag:
                tags.append(tag)
        return tags


@dataclass
class GameVar:
    id: int
    name: str
    var_id: int
    var_type: str
    description: str | None
    content_tags: list[ContentTag] = field(default_factory=list)
    functional_tags: list[FunctionalTag] = field(default_factory=list)

    @classmethod
    def _from_row(cls, row: tuple) -> GameVar:
        id_, name, var_id, var_type, description, content_raw, functional_raw = row
        raw_content = json.loads(content_raw) if content_raw else []
        raw_functional = json.loads(functional_raw) if functional_raw else []
        return cls(
            id=id_,
            name=name,
            var_id=var_id,
            var_type=var_type,
            description=description,
            content_tags=ContentTag.parse_list(raw_content),
            functional_tags=_parse_functional(raw_functional),
        )

    _COLS = "id, name, var_id, var_type, description, content_tags, functional_tags"

    @classmethod
    def all(cls, conn: sqlite3.Connection, var_type: str | None = None) -> list[GameVar]:
        if var_type:
            rows = conn.execute(
                f"SELECT {cls._COLS} FROM game_vars WHERE var_type = ? ORDER BY var_id",
                (var_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {cls._COLS} FROM game_vars ORDER BY var_type, var_id"
            ).fetchall()
        return [cls._from_row(row) for row in rows]

    @classmethod
    def by_name(cls, conn: sqlite3.Connection, name: str) -> list[GameVar]:
        rows = conn.execute(
            f"SELECT {cls._COLS} FROM game_vars WHERE name = ?",
            (name,),
        ).fetchall()
        return [cls._from_row(row) for row in rows]

    @classmethod
    def search(cls, conn: sqlite3.Connection, name: str) -> list[GameVar]:
        rows = conn.execute(
            f"SELECT {cls._COLS} FROM game_vars WHERE name LIKE ? ORDER BY var_type, var_id",
            (f"%{name}%",),
        ).fetchall()
        return [cls._from_row(row) for row in rows]

    @classmethod
    def by_var_id(cls, conn: sqlite3.Connection, var_id: int, var_type: str) -> GameVar | None:
        row = conn.execute(
            f"SELECT {cls._COLS} FROM game_vars WHERE var_id = ? AND var_type = ?",
            (var_id, var_type),
        ).fetchone()
        return cls._from_row(row) if row else None

    @classmethod
    def by_content_tag(
        cls, conn: sqlite3.Connection, tag: str, var_type: str | None = None,
    ) -> list[GameVar]:
        """Find vars matching a content tag like 'quest:troll_stronghold' or category prefix like 'quest'."""
        if ":" in tag:
            pattern = f'%"{tag}"%'
        else:
            pattern = f'%"{tag}:%'
        query = f"SELECT {cls._COLS} FROM game_vars WHERE content_tags LIKE ?"
        params: list = [pattern]
        if var_type:
            query += " AND var_type = ?"
            params.append(var_type)
        query += " ORDER BY var_type, var_id"
        rows = conn.execute(query, params).fetchall()
        return [cls._from_row(row) for row in rows]

    @classmethod
    def by_functional_tag(
        cls, conn: sqlite3.Connection, tag: FunctionalTag | str, var_type: str | None = None,
    ) -> list[GameVar]:
        """Find vars matching a functional tag like FunctionalTag.TIMER or 'timer'."""
        value = tag.value if isinstance(tag, FunctionalTag) else tag
        pattern = f'%"{value}"%'
        query = f"SELECT {cls._COLS} FROM game_vars WHERE functional_tags LIKE ?"
        params: list = [pattern]
        if var_type:
            query += " AND var_type = ?"
            params.append(var_type)
        query += " ORDER BY var_type, var_id"
        rows = conn.execute(query, params).fetchall()
        return [cls._from_row(row) for row in rows]


def _parse_functional(raw: list[str]) -> list[FunctionalTag]:
    tags = []
    for s in raw:
        try:
            tags.append(FunctionalTag.from_label(s))
        except ValueError:
            pass
    return tags
