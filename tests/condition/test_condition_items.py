"""Tests for item possession, currency, and related frames."""
from __future__ import annotations

import pytest

from ragger.dialogue.condition_parser import parse_condition
from tests.condition.conftest import atom


@pytest.mark.parametrize("text, expected", [
    # Basic has_item
    ("if the player has a {item}", [atom("has_item", count=1, neg=False, qual="any")]),
    ("if the player does not have a {item}", [atom("has_item", count=1, neg=True, qual="any")]),
    ("if the player has 5 {item}", [atom("has_item", count=5, neg=False, qual="any")]),

    # Container qualifier
    ("if the player has a {item} in their inventory", [atom("has_item", count=1, neg=False, qual="inventory")]),
    ("if the player has a {item} in their bank", [atom("has_item", count=1, neg=False, qual="bank")]),

    # Lost item
    ("if the player has lost the {item}", [atom("has_item", count=1, neg=True, qual="any")]),
    ("if the player lost the {item}", [atom("has_item", count=1, neg=True, qual="any")]),
    ("if the player has lost/banked the {item}", [atom("has_item", count=1, neg=True, qual="any")]),

    # Missing
    ("if the player is missing the {item}", [atom("has_item", count=1, neg=True, qual="any")]),
    ("if the player is missing only the {item}", [atom("has_item", count=1, neg=True, qual="any")]),

    # Holding/carrying
    ("if the player is holding a {item}", [atom("has_item", count=1, neg=False, qual="any")]),
    ("if the player is not carrying a {item}", [atom("has_item", count=1, neg=True, qual="any")]),

    # Prepositional (pre-strip)
    ("with the {item}", [atom("has_item", count=1, neg=False, qual="any")]),
    ("without the {item}", [atom("has_item", count=1, neg=True, qual="any")]),
    ("while having the {item}", [atom("has_item", count=1, neg=False, qual="any")]),

    # Subject-first
    ("{item} is in the player's inventory", [atom("has_item", count=1, neg=False, qual="inventory")]),
    ("{item} is not with the player", [atom("has_item", count=1, neg=True, qual="any")]),

    # Adjective-qualified
    ("if the player has the enchanted {item}", [atom("has_item", count=1, neg=False, qual="any")]),

    # Brought / acquired / still has
    ("if the player brought their {item}", [atom("has_item", count=1, neg=False, qual="any")]),
    ("if the player has not acquired the {item}", [atom("has_item", count=1, neg=True, qual="any")]),
    ("if the player still has the {item}", [atom("has_item", count=1, neg=False, qual="any")]),

    # has_all_items
    ("if the player has all the items", [atom("has_all_items", neg=False)]),
    ("if the player does not have all the required materials", [atom("has_all_items", neg=True)]),
])
def test_has_item(text, expected):
    assert parse_condition(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("if the player has 500 coins", [atom("has_coins", amount=500, cmp="ge", neg=False)]),
    ("if the player does not have enough coins", [atom("has_coins", amount=None, cmp="enough", neg=True)]),
    ("if the player has at least 1,000 coins", [atom("has_coins", amount=1000, cmp="at least", neg=False)]),
])
def test_has_coins(text, expected):
    assert parse_condition(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("if the player has enough {currency}", [atom("has_currency", amount=None, cmp="enough", neg=False)]),
    ("if the player does not have enough {currency}", [atom("has_currency", amount=None, cmp="enough", neg=True)]),
    ("if the player has 500 {currency}", [atom("has_currency", amount=500, cmp="ge", neg=False)]),
])
def test_has_currency(text, expected):
    assert parse_condition(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("if the player is showing the {item}", [atom("showing_item", neg=False)]),
    ("if the player has read the {item}", [atom("has_read", neg=False)]),
])
def test_misc_item_frames(text, expected):
    assert parse_condition(text) == expected


def test_received_reward():
    assert parse_condition("given a {item}") == [atom("received_reward")]
    assert parse_condition("if the result is {item}") == [atom("received_reward")]


def test_reward_is():
    assert parse_condition("if the player's reward is a {item}") == [atom("reward_is")]
