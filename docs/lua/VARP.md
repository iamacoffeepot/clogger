Read player variables (varps) and varbits. Look up variable IDs from the `game_vars` table in the ragger database using `GameVariable.search()` or `GameVariable.by_name()`.

```lua
-- Read a raw varp slot by ID
varp:get(43)                          -- attack style varp (COM_MODE)
varp:get(46)                          -- combat stance (COM_STANCE)

-- Read a varbit value
varp:bit(24)                          -- stamina duration (STAMINA_DURATION)
varp:bit(25)                          -- stamina active (STAMINA_ACTIVE)
```
