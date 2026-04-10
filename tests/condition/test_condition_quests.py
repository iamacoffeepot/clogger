"""Tests for quest state and quest decision frames."""
from __future__ import annotations

import pytest

from ragger.dialogue.condition_parser import parse_condition
from tests.condition.conftest import atom


@pytest.mark.parametrize("text, expected", [
    ("if the player has completed {quest}", [atom("quest_state", state="completed", neg=False)]),
    ("if the player has not completed {quest}", [atom("quest_state", state="completed", neg=True)]),
    ("if the player has started {quest}", [atom("quest_state", state="started", neg=False)]),
    ("if the player has not started {quest}", [atom("quest_state", state="started", neg=True)]),
    ("{quest} is started", [atom("quest_state", state="started", neg=False)]),
    ("before {quest}", [atom("quest_state", state="completed", neg=True)]),
    ("after {quest}", [atom("quest_state", state="completed", neg=False)]),
    ("during {quest}", [atom("quest_state", state="in_progress", neg=False)]),
])
def test_quest_state(text, expected):
    assert parse_condition(text) == expected


def test_quest_decision():
    assert parse_condition("if the player has helped {npc}") == [atom("quest_decision", action="helped")]
    assert parse_condition("if the player sided with {npc}") == [atom("quest_decision", action="sided")]
