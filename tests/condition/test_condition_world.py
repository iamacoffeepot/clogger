"""Tests for world state, location, inventory, and misc frames."""
from __future__ import annotations

import pytest

from ragger.dialogue.condition_parser import parse_condition
from tests.condition.conftest import atom


@pytest.mark.parametrize("text, expected", [
    ("if the player has enough inventory space",
     [atom("inventory_space", count=1, neg=False)]),
    ("if the player does not have enough inventory space",
     [atom("inventory_space", count=1, neg=True)]),
    ("if the player's inventory is full",
     [atom("inventory_space", count=0, neg=False)]),
    ("if the player has no inventory space",
     [atom("inventory_space", count=0, neg=False)]),
    ("if the player has 2 free inventory spaces",
     [atom("inventory_space", count=2, neg=False)]),
])
def test_inventory_space(text, expected):
    assert parse_condition(text) == expected


def test_location_at():
    # "is in {location}" matches location_at (post-strip)
    result = parse_condition("if the player is in the {location}")
    assert result == [atom("location_at", neg=False)]


def test_member_only():
    assert parse_condition("if the player is a member") == [atom("member_only", neg=False)]
    assert parse_condition("if the player is not a member") == [atom("member_only", neg=True)]


def test_world_type():
    result = parse_condition("if the player is on a pvp world")
    assert len(result) == 1
    assert result[0].frame == "world_type"
    assert result[0].get("wtype") == "pvp"


def test_gender():
    assert parse_condition("gender is male") == [atom("gender", gender="male")]
    assert parse_condition("is female") == [atom("gender", gender="female")]


def test_non_predicate():
    assert parse_condition("otherwise") == [atom("non_predicate", kind="marker")]
    assert parse_condition("beckon") == [atom("non_predicate", kind="emote")]


def test_time_out():
    assert parse_condition("if the player does not respond in time") == [atom("time_out")]
