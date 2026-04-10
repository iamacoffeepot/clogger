"""Tests for the parser engine: compound splitting, unknown fallback, etc."""
from __future__ import annotations

import pytest

from ragger.dialogue.condition_parser import parse_condition
from ragger.dialogue.condition_normalize import split_compound
from tests.condition.conftest import atom


def test_compound_and():
    """Compound conditions connected by 'and' produce multiple atoms.

    Note: many frames have trailing-junk tolerance ``(?:\\s+.*)?$`` so a
    single frame can swallow the full string. True compounds only split
    when no single-atom match succeeds.
    """
    # "gender is male" has no trailing junk tolerance, so "and ..." forces split.
    result = parse_condition("gender is male and is a member")
    assert len(result) == 2
    assert result[0].frame == "gender"
    assert result[1].frame == "member_only"


def test_single_atom_with_trailing_junk():
    """Trailing junk after a frame match is absorbed — no compound split."""
    result = parse_condition(
        "if the player has a {item} and some extra text"
    )
    assert len(result) == 1
    assert result[0].frame == "has_item"


def test_unknown_fallback():
    result = parse_condition("if bob is secretly a wizard", allow_unknown=True)
    assert len(result) == 1
    assert result[0].frame == "unknown"
    assert result[0].get("text") is not None


def test_unknown_not_returned_by_default():
    result = parse_condition("if bob is secretly a wizard")
    assert result == []


def test_known_not_affected_by_allow_unknown():
    result = parse_condition("if the player has a {item}", allow_unknown=True)
    assert len(result) == 1
    assert result[0].frame == "has_item"


class TestSplitCompound:
    def test_simple_and(self):
        assert split_compound("A and B") == ["A", "B"]

    def test_comma_and(self):
        assert split_compound("A, and B") == ["A", "B"]

    def test_or_more_preserved(self):
        """'or more' should NOT split."""
        assert split_compound("3 or more items") == ["3 or more items"]

    def test_or_fewer_preserved(self):
        assert split_compound("5 or fewer slots") == ["5 or fewer slots"]

    def test_simple_or_splits(self):
        assert split_compound("A or B") == ["A", "B"]
