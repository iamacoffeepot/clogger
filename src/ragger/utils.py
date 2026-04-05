"""Shared string utilities."""

import re


def snake_case(name: str) -> str:
    """Convert a display name to snake_case.

    >>> snake_case("Dragon Slayer I")
    'dragon_slayer_i'
    >>> snake_case("Cook's Assistant")
    'cooks_assistant'
    """
    s = name.lower()
    s = re.sub(r"['''\u2019]s\b", "s", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")
