Encode and decode JSON strings.

```lua
-- Encode a Lua value (table, string, number, boolean, nil) to a JSON string
local s = json.encode({ name = "Goblin", hp = 50, tags = {"monster", "green"} })
-- '{"name":"Goblin","hp":50,"tags":["monster","green"]}'

-- Decode a JSON string to a Lua value
local t = json.decode('{"name":"Goblin","hp":50}')
-- t.name == "Goblin", t.hp == 50

-- Indexed tables encode as JSON arrays, string-keyed tables as objects
json.encode({1, 2, 3})          -- '[1,2,3]'
json.encode({a = 1, b = 2})     -- '{"a":1,"b":2}'
```
