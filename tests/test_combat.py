from ragger.combat import AttackStyle, combat_level, xp_from_combat
from ragger.enums import Skill


def test_fresh_account() -> None:
    assert combat_level() == 3


def test_maxed_account() -> None:
    assert combat_level(
        attack=99, strength=99, defence=99, hitpoints=99,
        ranged=99, magic=99, prayer=99,
    ) == 126


def test_pure_melee_takes_max_style() -> None:
    # Melee beats range/magic when only melee stats are trained
    assert combat_level(attack=60, strength=60, defence=1) > combat_level(magic=60)


def test_odd_magic_level_floors() -> None:
    # floor(3 * 41 / 2) == floor(3 * 40 / 2) == 60
    assert combat_level(magic=41) == combat_level(magic=40)


def test_prayer_half_floors() -> None:
    # floor(43/2) == floor(42/2) == 21
    assert combat_level(prayer=43) == combat_level(prayer=42)


def test_pure_mage_cb_50() -> None:
    # Pure mage with Prayer 43, HP 40: Magic 72 is the threshold for CB 50
    assert combat_level(magic=71, prayer=43, hitpoints=40) == 49
    assert combat_level(magic=72, prayer=43, hitpoints=40) == 50


def test_xp_melee_accurate() -> None:
    xp = xp_from_combat(AttackStyle.MELEE_ACCURATE, damage=10)
    assert xp == {Skill.ATTACK: 40.0, Skill.HITPOINTS: 13.3}


def test_xp_melee_controlled_splits_three_ways() -> None:
    xp = xp_from_combat(AttackStyle.MELEE_CONTROLLED, damage=10)
    assert xp[Skill.ATTACK] == 13.3
    assert xp[Skill.STRENGTH] == 13.3
    assert xp[Skill.DEFENCE] == 13.3
    assert xp[Skill.HITPOINTS] == 13.3


def test_xp_ranged_longrange_splits_defence() -> None:
    xp = xp_from_combat(AttackStyle.RANGED_LONGRANGE, damage=5)
    assert xp == {Skill.RANGED: 10.0, Skill.DEFENCE: 10.0, Skill.HITPOINTS: 6.65}


def test_xp_magic_standard_includes_spell_base() -> None:
    # Water Bolt base XP 16.5, 8 damage
    xp = xp_from_combat(AttackStyle.MAGIC_STANDARD, damage=8, spell_base_xp=16.5)
    assert xp[Skill.MAGIC] == 8 * 2.0 + 16.5  # 32.5
    assert xp[Skill.HITPOINTS] == 8 * 1.33


def test_xp_magic_defensive_splits_magic_and_defence() -> None:
    xp = xp_from_combat(AttackStyle.MAGIC_DEFENSIVE, damage=8, spell_base_xp=16.5)
    assert xp[Skill.MAGIC] == 8 * 1.33 + 16.5
    assert xp[Skill.DEFENCE] == 8 * 1.0
    assert xp[Skill.HITPOINTS] == 8 * 1.33


def test_xp_spell_base_ignored_for_non_magic() -> None:
    # spell_base_xp is a no-op for melee/ranged styles
    xp = xp_from_combat(AttackStyle.MELEE_ACCURATE, damage=5, spell_base_xp=99.0)
    assert Skill.MAGIC not in xp
    assert xp[Skill.ATTACK] == 20.0


def test_xp_zero_damage() -> None:
    xp = xp_from_combat(AttackStyle.MELEE_ACCURATE, damage=0)
    assert xp == {Skill.ATTACK: 0.0, Skill.HITPOINTS: 0.0}
