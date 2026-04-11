Read combat state — spec energy, prayers, attack style, and current target.

```lua
-- Special attack
combat:spec()                           -- spec energy (0-1000, divide by 10 for %)
combat:spec_enabled()                   -- true if spec orb is toggled on

-- Attack style
combat:attack_style()                   -- 0-3, weapon-dependent index

-- Prayers
combat:prayer_active("protect_from_melee")  -- true/false for a specific prayer
combat:active_prayers()                 -- array of active prayer name strings

-- Target (returns nil if not interacting)
local t = combat:target()
if t then
    -- t.name       (string)
    -- t.type       (string: "npc" or "player")
    -- t.id         (int, NPC ID — only for NPCs)
    -- t.hp_ratio   (int)
    -- t.hp_scale   (int)
    -- t.animation  (int)
end
```

Use `prayer.NAME` constants (same pattern as `skill.NAME`):

```lua
combat:prayer_active(prayer.PROTECT_FROM_MELEE)
```
