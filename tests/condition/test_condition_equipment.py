"""Tests for wearing / equipment frames."""
from __future__ import annotations

import pytest

from ragger.dialogue.condition_parser import parse_condition
from tests.condition.conftest import atom


@pytest.mark.parametrize("text, expected", [
    ("if the player is wearing a {item}", [atom("wearing", neg=False)]),
    ("if the player is not wearing a {item}", [atom("wearing", neg=True)]),
    ("if the player is wielding a {equipment}", [atom("wearing", neg=False)]),
    ("if the player has a {equipment} equipped", [atom("wearing", neg=False)]),
    ("if the player is wearing nothing", [atom("wearing", neg=True)]),
])
def test_wearing(text, expected):
    assert parse_condition(text) == expected


def test_wearing_slot():
    result = parse_condition("if the player is wearing something in the head slot")
    assert len(result) == 1
    assert result[0].frame == "wearing"
    assert result[0].get("slot") == "head"


def test_wearing_category():
    result = parse_condition("if the player is wearing a vyre {item}")
    assert len(result) == 1
    assert result[0].frame == "wearing"
    assert result[0].get("category") == "vyre"


def test_passive_wearing():
    result = parse_condition("a {item} is worn")
    assert result == [atom("wearing", neg=False)]

    result = parse_condition("a {item} is not worn")
    assert result == [atom("wearing", neg=True)]


def test_with_equipped():
    assert parse_condition("with the full jester outfit equipped") == [atom("wearing", neg=False)]
    assert parse_condition("without the full jester outfit equipped") == [atom("wearing", neg=True)]
