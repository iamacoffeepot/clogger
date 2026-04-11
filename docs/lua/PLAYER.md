Read local player state.

```lua
-- Identity
player:name()                 -- player name
player:combat_level()         -- combat level

-- Position
player:x()                    -- world X coordinate
player:y()                    -- world Y coordinate
player:plane()                -- current plane/level

-- Skills (use skill.NAME constants)
player:level(skill.MINING)    -- real level
player:boosted_level(skill.STRENGTH) -- boosted level (potions etc)
player:xp(skill.ATTACK)      -- experience points
player:total_level()          -- total level

-- Health/prayer
player:hp()                   -- current hitpoints
player:max_hp()               -- max hitpoints
player:prayer()               -- current prayer
player:max_prayer()           -- max prayer

-- State
player:animation()            -- current animation ID (-1 if idle)
player:is_dead()              -- true if dead
player:is_interacting()       -- true if interacting with something
player:orientation()          -- facing direction

-- Overhead text
player:overhead_text()        -- get overhead text
player:set_overhead_text("!") -- set overhead text
```
