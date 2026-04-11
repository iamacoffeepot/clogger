Read client variables (integers and strings). Look up variable IDs from the `game_vars` table in the ragger database.

```lua
-- Read a client integer variable
varc:int(171)                         -- top-level panel (TOPLEVEL_PANEL)

-- Read a client string variable
varc:str(335)                         -- chatbox input text (CHATINPUT, returns nil if empty)
```
