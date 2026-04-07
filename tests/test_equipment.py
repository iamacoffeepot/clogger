import sqlite3

from ragger.enums import Skill
from ragger.equipment import Equipment
from ragger.requirements import RequirementGroup
from ragger.wiki import link_group_requirement

# Import the parsing function from the fetch script
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from fetch_equipment import parse_equipment_requirements


def _seed(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO items (name) VALUES ('Abyssal whip')")
    conn.execute("INSERT INTO quests (name, points) VALUES ('Dragon Slayer I', 2)")
    conn.execute("INSERT INTO quests (name, points) VALUES ('Monkey Madness I', 3)")
    conn.execute("INSERT INTO quests (name, points) VALUES ('Roving Elves', 1)")
    conn.execute(
        "INSERT INTO equipment (name, version, slot, two_handed) VALUES ('Abyssal whip', NULL, 'weapon', 0)"
    )
    conn.commit()


# ── Prose parsing tests ──────────────────────────────────────────────────


def test_parse_single_skill(conn: sqlite3.Connection) -> None:
    """'requires 70 [[Attack]] to wield'"""
    skills, quests = parse_equipment_requirements(
        "The '''abyssal whip''' requires 70 [[Attack]] to wield.\n==Drop sources=="
    )
    assert skills == [(Skill.ATTACK, 70)]
    assert quests == []


def test_parse_skill_level_of(conn: sqlite3.Connection) -> None:
    """'[[Attack]] level of 70'"""
    skills, quests = parse_equipment_requirements(
        "It requires an [[Attack]] level of 70 to wield.\n==Sources=="
    )
    assert skills == [(Skill.ATTACK, 70)]
    assert quests == []


def test_parse_multiple_skills_same_level(conn: sqlite3.Connection) -> None:
    """'requires 70 [[Defence]] and [[Ranged]] to wear'"""
    skills, quests = parse_equipment_requirements(
        "The armour requires 70 [[Defence]] and [[Ranged]] to wear.\n==Stats=="
    )
    assert len(skills) == 2
    assert (Skill.DEFENCE, 70) in skills
    assert (Skill.RANGED, 70) in skills


def test_parse_different_skill_levels(conn: sqlite3.Connection) -> None:
    """'requires 50 [[Magic]] and 50 [[Attack]] to wield'"""
    skills, quests = parse_equipment_requirements(
        "Iban's staff requires 50 [[Magic]] and 50 [[Attack]] to wield.\n==Charges=="
    )
    assert len(skills) == 2
    assert (Skill.MAGIC, 50) in skills
    assert (Skill.ATTACK, 50) in skills


def test_parse_quest_completion(conn: sqlite3.Connection) -> None:
    """'completion of [[Dragon Slayer I]]'"""
    skills, quests = parse_equipment_requirements(
        "It requires 40 [[Defence]] and completion of the [[quest]] [[Dragon Slayer I]] to equip.\n==Stats=="
    )
    assert skills == [(Skill.DEFENCE, 40)]
    assert quests == ["Dragon Slayer I"]


def test_parse_quest_completed(conn: sqlite3.Connection) -> None:
    """'completed the [[Monkey Madness I]] quest'"""
    skills, quests = parse_equipment_requirements(
        "Players who have 60 [[Attack]] and have completed the [[Monkey Madness I]] quest can wield it.\n==Stats=="
    )
    assert skills == [(Skill.ATTACK, 60)]
    assert quests == ["Monkey Madness I"]


def test_parse_quest_from_infobox(conn: sqlite3.Connection) -> None:
    """Quest from |quest = [[Roving Elves]] in Infobox Item."""
    wikitext = (
        "{{Infobox Item\n|name = Crystal bow\n|quest = [[Roving Elves]]\n}}\n"
        "It requires 50 [[Agility]] and 70 [[Ranged]].\n==Stats=="
    )
    skills, quests = parse_equipment_requirements(wikitext)
    assert (Skill.AGILITY, 50) in skills
    assert (Skill.RANGED, 70) in skills
    assert quests == ["Roving Elves"]


def test_parse_quest_infobox_no_false_positive(conn: sqlite3.Connection) -> None:
    """|quest = No should not produce a quest requirement."""
    wikitext = (
        "{{Infobox Item\n|name = Whip\n|quest = No\n}}\n"
        "It requires 70 [[Attack]].\n==Stats=="
    )
    skills, quests = parse_equipment_requirements(wikitext)
    assert skills == [(Skill.ATTACK, 70)]
    assert quests == []


def test_parse_no_requirements(conn: sqlite3.Connection) -> None:
    """Page with no requirement text."""
    skills, quests = parse_equipment_requirements(
        "{{Infobox Item\n|name = Bronze sword\n}}\nA basic sword.\n==Stats=="
    )
    assert skills == []
    assert quests == []


def test_parse_many_skills_same_level(conn: sqlite3.Connection) -> None:
    """Void knight: 42 [[Attack]], [[Strength]], [[Defence]], ..., 22 [[Prayer]]"""
    skills, quests = parse_equipment_requirements(
        "A player must have at least 42 [[Attack]], [[Strength]], [[Defence]], "
        "[[Hitpoints]], [[Ranged]], and [[Magic]], along with 22 [[Prayer]].\n==Obtaining=="
    )
    assert len(skills) == 7
    for skill in [Skill.ATTACK, Skill.STRENGTH, Skill.DEFENCE, Skill.HITPOINTS, Skill.RANGED, Skill.MAGIC]:
        assert (skill, 42) in skills
    assert (Skill.PRAYER, 22) in skills


def test_parse_dedup_quest(conn: sqlite3.Connection) -> None:
    """Quest mentioned in both infobox and prose should only appear once."""
    wikitext = (
        "{{Infobox Item\n|name = Crystal bow\n|quest = [[Roving Elves]]\n}}\n"
        "It requires completion of [[Roving Elves]].\n==Stats=="
    )
    _, quests = parse_equipment_requirements(wikitext)
    assert quests == ["Roving Elves"]


# ── DB integration tests ─────────────────────────────────────────────────


def test_equipment_skill_requirements(conn: sqlite3.Connection) -> None:
    """Equipment linked to skill requirements via group system."""
    _seed(conn)
    equip_id = conn.execute("SELECT id FROM equipment WHERE name = 'Abyssal whip'").fetchone()[0]

    link_group_requirement(
        conn,
        "group_skill_requirements",
        {"skill": Skill.ATTACK.value, "level": 70},
        "equipment_requirement_groups",
        "equipment_id",
        equip_id,
    )
    conn.commit()

    equip = Equipment.by_name(conn, "Abyssal whip")
    assert equip is not None
    groups = equip.requirement_groups(conn)
    assert len(groups) == 1
    reqs = equip.skill_requirements(conn)
    assert len(reqs) == 1
    assert reqs[0].skill == Skill.ATTACK
    assert reqs[0].level == 70


def test_equipment_quest_requirements(conn: sqlite3.Connection) -> None:
    """Equipment linked to quest requirements via group system."""
    _seed(conn)
    equip_id = conn.execute("SELECT id FROM equipment WHERE name = 'Abyssal whip'").fetchone()[0]
    quest_id = conn.execute("SELECT id FROM quests WHERE name = 'Dragon Slayer I'").fetchone()[0]

    link_group_requirement(
        conn,
        "group_quest_requirements",
        {"required_quest_id": quest_id},
        "equipment_requirement_groups",
        "equipment_id",
        equip_id,
    )
    conn.commit()

    equip = Equipment.by_name(conn, "Abyssal whip")
    assert equip is not None
    reqs = equip.quest_requirements(conn)
    assert len(reqs) == 1
    assert reqs[0].required_quest_id == quest_id


def test_equipment_no_requirements(conn: sqlite3.Connection) -> None:
    """Equipment with no linked requirements returns empty lists."""
    _seed(conn)
    equip = Equipment.by_name(conn, "Abyssal whip")
    assert equip is not None
    assert equip.requirement_groups(conn) == []
    assert equip.skill_requirements(conn) == []
    assert equip.quest_requirements(conn) == []
