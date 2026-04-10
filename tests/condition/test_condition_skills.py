"""Tests for skill level and combat level frames."""
from __future__ import annotations

import pytest

from ragger.dialogue.condition_parser import parse_condition
from tests.condition.conftest import atom


@pytest.mark.parametrize("text, expected", [
    ("if the player has 50 {skill}", [atom("skill_ge", level=50, neg=False)]),
    ("if the player has at least 70 {skill}", [atom("skill_ge", level=70, neg=False)]),
    ("{skill} level is 99", [atom("skill_ge", level=99, neg=False)]),
    ("{skill} level 40 or higher", [atom("skill_ge", level=40, neg=False)]),
    ("{skill} level is too low", [atom("skill_ge", level=0, neg=True)]),
    ("{skill} level is at least 30", [atom("skill_ge", level=30, neg=False)]),
])
def test_skill_ge(text, expected):
    assert parse_condition(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("if the player has a combat level less than 50", [atom("combat_level", level=50, cmp="lt")]),
    ("if the player has a combat level above 100", [atom("combat_level", level=100, cmp="ge")]),
    ("combat level of 70 or above", [atom("combat_level", level=70, cmp="ge")]),
])
def test_combat_level(text, expected):
    assert parse_condition(text) == expected
