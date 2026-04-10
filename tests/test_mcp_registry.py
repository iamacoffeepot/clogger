from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from enum import Enum

import pytest

from ragger.enums import EquipmentSlot, Region, Skill
from ragger.mcp_registry import _coerce_enum, _serialize, mcp_tool, register_all


class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Priority(int, Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


@dataclass
class _Good:
    x: int

    def asdict(self) -> dict:
        return {"x": self.x}


@dataclass
class _Bad:
    x: int


def test_serialize_none() -> None:
    assert _serialize(None) is None


def test_serialize_primitives() -> None:
    assert _serialize(42) == 42
    assert _serialize(3.14) == 3.14
    assert _serialize("hello") == "hello"
    assert _serialize(True) is True


def test_serialize_list() -> None:
    assert _serialize([1, 2, 3]) == [1, 2, 3]


def test_serialize_dataclass_with_asdict() -> None:
    assert _serialize(_Good(x=5)) == {"x": 5}


def test_serialize_dataclass_without_asdict() -> None:
    with pytest.raises(TypeError, match="must implement asdict"):
        _serialize(_Bad(x=5))


def test_serialize_list_of_dataclasses() -> None:
    assert _serialize([_Good(x=1), _Good(x=2)]) == [{"x": 1}, {"x": 2}]


def test_serialize_enum() -> None:
    assert _serialize(Color.RED) == "red"
    assert _serialize(Priority.HIGH) == 2
    assert _serialize(Skill.MINING) == 16


def test_serialize_empty_list() -> None:
    assert _serialize([]) == []


def test_coerce_enum_by_name() -> None:
    assert _coerce_enum("RED", Color) == Color.RED
    assert _coerce_enum("HIGH", Priority) == Priority.HIGH


def test_coerce_enum_case_insensitive() -> None:
    assert _coerce_enum("red", Color) == Color.RED
    assert _coerce_enum("mining", Skill) == Skill.MINING
    assert _coerce_enum("Mining", Skill) == Skill.MINING


def test_coerce_enum_by_value() -> None:
    assert _coerce_enum("red", Color) == Color.RED


def test_coerce_enum_already_correct_type() -> None:
    assert _coerce_enum(Skill.MINING, Skill) == Skill.MINING


def test_coerce_enum_invalid() -> None:
    with pytest.raises(ValueError, match="is not a valid"):
        _coerce_enum("PURPLE", Color)


def test_coerce_enum_error_lists_members() -> None:
    with pytest.raises(ValueError, match="RED.*GREEN.*BLUE"):
        _coerce_enum("PURPLE", Color)


def test_coerce_real_enums() -> None:
    assert _coerce_enum("HEAD", EquipmentSlot) == EquipmentSlot.HEAD
    assert _coerce_enum("DESERT", Region) == Region.DESERT
    assert _coerce_enum("FIREMAKING", Skill) == Skill.FIREMAKING
    assert _coerce_enum("firemaking", Skill) == Skill.FIREMAKING


@dataclass
class _Thing:
    id: int
    name: str

    def asdict(self) -> dict:
        return {"id": self.id, "name": self.name}

    @classmethod
    @mcp_tool(name="TestThingByName", description="Find a thing")
    def by_name(cls, conn: sqlite3.Connection, name: str) -> _Thing | None:
        row = conn.execute("SELECT id, name FROM things WHERE name = ?", (name,)).fetchone()
        return cls(*row) if row else None


def test_register_all_classmethod(tmp_path) -> None:
    from mcp.server.fastmcp import FastMCP

    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE things (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO things VALUES (1, 'Widget')")
    conn.commit()
    conn.close()

    mcp = FastMCP("test")
    register_all(mcp, db_path)

    tool = mcp._tool_manager._tools.get("TestThingByName")
    assert tool is not None
    assert tool.parameters["properties"]["name"]["type"] == "string"
    assert "conn" not in tool.parameters.get("properties", {})
    assert "cls" not in tool.parameters.get("properties", {})

    result = json.loads(tool.fn(name="Widget"))
    assert result == {"id": 1, "name": "Widget"}
    assert tool.fn(name="Nonexistent") == "null"


def test_register_all_enum_coercion(tmp_path) -> None:
    from mcp.server.fastmcp import FastMCP

    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE colors (id INTEGER PRIMARY KEY, color TEXT)")
    conn.execute("INSERT INTO colors VALUES (1, 'red')")
    conn.commit()
    conn.close()

    @mcp_tool(name="TestFindColor", description="Find by color")
    def find_color(conn: sqlite3.Connection, color: Color) -> str | None:
        row = conn.execute("SELECT color FROM colors WHERE color = ?", (color.value,)).fetchone()
        return row[0] if row else None

    mcp = FastMCP("test")
    register_all(mcp, db_path)

    tool = mcp._tool_manager._tools.get("TestFindColor")
    assert tool is not None
    assert tool.parameters["properties"]["color"]["type"] == "string"

    result = json.loads(tool.fn(color="RED"))
    assert result == "red"

    result = json.loads(tool.fn(color="red"))
    assert result == "red"
