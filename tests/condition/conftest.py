"""Shared fixtures for condition parser tests.

All frame tests are pure — no DB needed. The parser operates on
pre-normalized text (entity slots already replaced), so tests pass
normalized strings directly to parse_condition().
"""
from __future__ import annotations

import pytest

from ragger.dialogue.condition_parser import parse_atom, parse_condition
from ragger.dialogue.condition_types import Atom, make_atom


def atom(frame: str, **kwargs: object) -> Atom:
    """Shorthand for building expected atoms in tests."""
    return make_atom(frame, **kwargs)
