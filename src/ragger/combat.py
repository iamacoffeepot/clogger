"""OSRS combat-level and attack-style XP utilities."""

from enum import Enum

from ragger.enums import Skill


def combat_level(
    *,
    attack: int = 1,
    strength: int = 1,
    defence: int = 1,
    hitpoints: int = 10,
    ranged: int = 1,
    magic: int = 1,
    prayer: int = 1,
) -> int:
    """Return the OSRS combat level for a given set of combat skill levels.

    Formula (from the OSRS combat level calculation):

        base  = (defence + hitpoints + floor(prayer / 2)) / 4
        melee = 13/40 * (attack + strength)
        range = 13/40 * floor(3 * ranged / 2)
        magic = 13/40 * floor(3 * magic / 2)
        combat = floor(base + max(melee, range, magic))

    All seven skills default to the fresh-account starting levels
    (all 1 except Hitpoints, which starts at 10).

    Ranged and Magic use floor(3 * level / 2) so an odd level contributes
    the same "attack score" as the even level below it — this matches the
    in-game rounding and is not a Python integer-division artifact.
    """
    base = (defence + hitpoints + prayer // 2) / 4
    melee_score = 13 / 40 * (attack + strength)
    ranged_score = 13 / 40 * (3 * ranged // 2)
    magic_score = 13 / 40 * (3 * magic // 2)
    return int(base + max(melee_score, ranged_score, magic_score))


class AttackStyle(Enum):
    """OSRS combat attack styles.

    Style names are prefixed by combat category (MELEE_/RANGED_/MAGIC_)
    because the wiki reuses "Accurate" and "Defensive" across categories
    with different XP splits.
    """

    MELEE_ACCURATE = "melee_accurate"
    MELEE_AGGRESSIVE = "melee_aggressive"
    MELEE_DEFENSIVE = "melee_defensive"
    MELEE_CONTROLLED = "melee_controlled"
    RANGED_ACCURATE = "ranged_accurate"
    RANGED_RAPID = "ranged_rapid"
    RANGED_LONGRANGE = "ranged_longrange"
    MAGIC_STANDARD = "magic_standard"
    MAGIC_DEFENSIVE = "magic_defensive"


HP_XP_PER_DAMAGE: float = 1.33
"""Hitpoints XP awarded per point of damage, identical across all styles."""

# XP per point of damage for each attack style (excluding Hitpoints, which is
# always HP_XP_PER_DAMAGE). Source: https://oldschool.runescape.wiki/w/Attack_styles
#
# Magic styles additionally award the spell's base XP entirely to Magic,
# regardless of defensive/standard — see xp_from_combat() for the full split.
_STYLE_DAMAGE_XP: dict[AttackStyle, dict[Skill, float]] = {
    AttackStyle.MELEE_ACCURATE:    {Skill.ATTACK: 4.0},
    AttackStyle.MELEE_AGGRESSIVE:  {Skill.STRENGTH: 4.0},
    AttackStyle.MELEE_DEFENSIVE:   {Skill.DEFENCE: 4.0},
    AttackStyle.MELEE_CONTROLLED:  {Skill.ATTACK: 1.33, Skill.STRENGTH: 1.33, Skill.DEFENCE: 1.33},
    AttackStyle.RANGED_ACCURATE:   {Skill.RANGED: 4.0},
    AttackStyle.RANGED_RAPID:      {Skill.RANGED: 4.0},
    AttackStyle.RANGED_LONGRANGE:  {Skill.RANGED: 2.0, Skill.DEFENCE: 2.0},
    AttackStyle.MAGIC_STANDARD:    {Skill.MAGIC: 2.0},
    AttackStyle.MAGIC_DEFENSIVE:   {Skill.MAGIC: 1.33, Skill.DEFENCE: 1.0},
}


def xp_from_combat(
    style: AttackStyle,
    damage: int,
    *,
    spell_base_xp: float = 0.0,
) -> dict[Skill, float]:
    """Return the XP earned from a single combat action.

    `damage` is the HP damage dealt this hit. Hitpoints XP is always 1.33 per damage.

    `spell_base_xp` is the cast-time XP awarded by the spell itself (e.g. Wind
    Strike = 5.5, Water Bolt = 16.5). It is awarded entirely to Magic on both
    Standard and Defensive autocasts, and is ignored for non-magic styles.
    """
    result: dict[Skill, float] = {Skill.HITPOINTS: damage * HP_XP_PER_DAMAGE}
    for skill, per_damage in _STYLE_DAMAGE_XP[style].items():
        result[skill] = result.get(skill, 0.0) + damage * per_damage
    if spell_base_xp and style in (AttackStyle.MAGIC_STANDARD, AttackStyle.MAGIC_DEFENSIVE):
        result[Skill.MAGIC] = result.get(Skill.MAGIC, 0.0) + spell_base_xp
    return result
