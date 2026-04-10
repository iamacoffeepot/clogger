"""MCP tool auto-registration from annotated Python API methods."""

from __future__ import annotations

import dataclasses
import enum
import importlib
import inspect
import json
import sqlite3
from typing import Any, get_type_hints


_tools: list[dict[str, Any]] = []


def mcp_tool(*, name: str, description: str):
    """Mark a method for MCP tool registration.

    Apply before @classmethod so the raw function is captured::

        @classmethod
        @mcp_tool(name="ItemByName", description="Find an item by exact name")
        def by_name(cls, conn: sqlite3.Connection, name: str) -> Item | None:
            ...

    At startup the MCP server calls :func:`register_all` which inspects each
    registered function, strips ``cls`` and ``conn``, and exposes the remaining
    parameters as an MCP tool.
    """

    def decorator(fn):
        _tools.append({"name": name, "description": description, "fn": fn})
        return fn

    return decorator


def _serialize(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        if not hasattr(obj, "asdict"):
            raise TypeError(
                f"{type(obj).__name__} must implement asdict() to be returned from an MCP tool"
            )
        return obj.asdict()
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (int, float, str, bool)):
        return obj
    return str(obj)


def _is_enum_type(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, enum.Enum)


def _coerce_enum(value: Any, enum_type: type[enum.Enum]) -> enum.Enum:
    """Coerce a string value to an enum member by name, then by value."""
    if isinstance(value, enum_type):
        return value

    by_name = value.upper().replace(" ", "_") if isinstance(value, str) else str(value)
    try:
        return enum_type[by_name]
    except KeyError:
        pass

    try:
        return enum_type(value)
    except ValueError:
        pass

    members = ", ".join(enum_type.__members__)
    raise ValueError(f"{value!r} is not a valid {enum_type.__name__} (expected one of: {members})")


def _schema_annotation(annotation: Any) -> Any:
    """Map a Python type hint to something FastMCP can express as JSON schema."""
    if _is_enum_type(annotation):
        return str
    return annotation


def _resolve_owner(fn) -> type | None:
    """Resolve the owning class of a method from its __qualname__."""
    qualname = fn.__qualname__
    if "." not in qualname:
        return None
    class_name = qualname.rsplit(".", 1)[0]
    module = importlib.import_module(fn.__module__)
    return getattr(module, class_name, None)


def register_all(mcp, db_path: str) -> None:
    """Register all @mcp_tool-decorated functions with a FastMCP server."""

    for entry in _tools:
        tool_name: str = entry["name"]
        description: str = entry["description"]
        fn = entry["fn"]

        sig = inspect.signature(fn)
        try:
            hints = get_type_hints(fn)
        except Exception:
            hints = fn.__annotations__

        owner_cls = _resolve_owner(fn)

        skip = {"cls", "self", "conn"}
        exposed = [n for n in sig.parameters if n not in skip]

        coercions: dict[str, type[enum.Enum]] = {}
        new_params = []
        new_annotations: dict[str, Any] = {}
        for param_name in exposed:
            original = sig.parameters[param_name]
            annotation = hints.get(param_name, str)

            if _is_enum_type(annotation):
                coercions[param_name] = annotation

            schema_type = _schema_annotation(annotation)
            new_params.append(
                inspect.Parameter(
                    param_name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=original.default,
                    annotation=schema_type,
                )
            )
            new_annotations[param_name] = schema_type

        def _make_handler(fn, owner_cls, db_path, coercions):
            def handler(**kwargs):
                for param_name, enum_type in coercions.items():
                    if param_name in kwargs:
                        kwargs[param_name] = _coerce_enum(kwargs[param_name], enum_type)

                conn = sqlite3.connect(db_path)
                try:
                    if owner_cls is not None:
                        result = fn(owner_cls, conn, **kwargs)
                    else:
                        result = fn(conn, **kwargs)
                    return json.dumps(_serialize(result))
                finally:
                    conn.close()

            return handler

        handler = _make_handler(fn, owner_cls, db_path, coercions)
        handler.__name__ = tool_name
        handler.__qualname__ = tool_name
        handler.__doc__ = description
        handler.__signature__ = inspect.Signature(new_params)
        handler.__annotations__ = new_annotations
        handler.__module__ = fn.__module__

        mcp.tool(name=tool_name)(handler)
