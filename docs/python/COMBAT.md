# Combat

`ragger.combat` exposes combat-level calculation and attack-style XP modelling.

## `combat_level(**kwargs) -> int`

Compute the OSRS combat level for a given set of skill levels. All skills are keyword-only and default to the fresh-account starting values (`1` everywhere except `hitpoints=10`).

```python
from ragger.combat import combat_level

combat_level()                                      # 3  (fresh account)
combat_level(attack=40, strength=40, defence=40)    # 32
combat_level(magic=72, prayer=43, hitpoints=40)     # 50 (pure mage)
```

### Formula

```
base  = (defence + hitpoints + floor(prayer / 2)) / 4
melee = 13/40 * (attack + strength)
range = 13/40 * floor(3 * ranged / 2)
magic = 13/40 * floor(3 * magic / 2)
combat = floor(base + max(melee, range, magic))
```

Ranged and Magic use `floor(3 * level / 2)`, so an odd level contributes the same attack score as the even level below it. This matches in-game behaviour (not a Python rounding artifact).

## `AttackStyle` + `xp_from_combat(style, damage, *, spell_base_xp=0) -> dict[Skill, float]`

Returns the XP earned from a single combat action, split across the skills that the chosen attack style feeds.

```python
from ragger.combat import AttackStyle, xp_from_combat
from ragger.enums import Skill

# Water Bolt (16.5 base XP) hitting for 8 damage, defensive autocast:
xp_from_combat(AttackStyle.MAGIC_DEFENSIVE, damage=8, spell_base_xp=16.5)
# -> {Skill.HITPOINTS: 10.64, Skill.MAGIC: 27.14, Skill.DEFENCE: 8.0}
```

Hitpoints XP is always `1.33 × damage` regardless of style. For magic styles, the spell's base cast XP is awarded entirely to Magic on top of the per-damage split.

### XP table

Per point of damage dealt. HP is always `1.33`. Magic styles also receive the spell's base cast XP entirely in Magic.

| Category | Style | Attack | Strength | Defence | Ranged | Magic |
|----------|-------|-------:|---------:|--------:|-------:|------:|
| Melee | Accurate | 4 | — | — | — | — |
| Melee | Aggressive | — | 4 | — | — | — |
| Melee | Defensive | — | — | 4 | — | — |
| Melee | Controlled | 1.33 | 1.33 | 1.33 | — | — |
| Ranged | Accurate | — | — | — | 4 | — |
| Ranged | Rapid | — | — | — | 4 | — |
| Ranged | Longrange | — | — | 2 | 2 | — |
| Magic | Standard | — | — | — | — | 2 |
| Magic | Defensive | — | — | 1 | — | 1.33 |

Source: [OSRS Wiki — Attack styles](https://oldschool.runescape.wiki/w/Attack_styles)
