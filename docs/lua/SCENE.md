Query NPCs, objects, and items in the loaded scene area (~104x104 tiles around the player).

```lua
-- NPCs — returns array of tables
local npcs = scene:npcs()
for i = 1, #npcs do
    local npc = npcs[i]
    -- npc.name       (string)
    -- npc.id         (int)
    -- npc.x          (int, world X)
    -- npc.y          (int, world Y)
    -- npc.plane      (int)
    -- npc.combat     (int, combat level)
    -- npc.animation  (int, -1 if idle)
    -- npc.hp_ratio   (int)
    -- npc.hp_scale   (int)
    -- npc.is_dead    (bool)
end
```

Note: returns all NPCs loaded by the client, not just those visible on screen.

```lua
-- Ground items — returns array of tables
local items = scene:ground_items()
for i = 1, #items do
    local item = items[i]
    -- item.id         (int, item ID)
    -- item.quantity   (int)
    -- item.x          (int, world X)
    -- item.y          (int, world Y)
    -- item.plane      (int)
    -- item.ownership  (int: 0=none, 1=self, 2=other, 3=group)
    -- item.is_private (bool)
    -- item.name      (string, item name)
end
```

```lua
-- Game objects — returns array of tables (trees, rocks, doors, interactables, etc.)
local objs = scene:objects()              -- all objects (can be very large!)
local objs = scene:objects("bank booth")  -- single name filter (case-insensitive, partial match)
local objs = scene:objects({"bank booth", "tree"})  -- multiple name filters
for i = 1, #objs do
    local obj = objs[i]
    -- obj.name       (string)
    -- obj.id         (int, object ID)
    -- obj.type       (string: "game", "wall", "ground", "decorative")
    -- obj.x          (int, world X)
    -- obj.y          (int, world Y)
    -- obj.plane      (int)
    -- obj.actions     (array of strings, e.g. {"Mine", "Prospect"})
end
```

Always use a name filter when possible — the unfiltered list includes every object in the loaded scene (~104x104 tiles).

```lua
-- Players — returns array of tables
local players = scene:players()
for i = 1, #players do
    local p = players[i]
    -- p.name        (string)
    -- p.x           (int, world X)
    -- p.y           (int, world Y)
    -- p.plane       (int)
    -- p.combat      (int, combat level)
    -- p.animation   (int, -1 if idle)
    -- p.hp_ratio    (int)
    -- p.hp_scale    (int)
    -- p.is_dead     (bool)
    -- p.is_friend   (bool)
    -- p.is_clan     (bool)
    -- p.team        (int, team cape number)
end
```

```lua
-- NPC convex hull — returns polygon point array for rendering, or nil
local hull = scene:npc_hull("Guard")    -- by name (partial, case-insensitive)
local hull = scene:npc_hull(3010)       -- by NPC ID
if hull then
    g:polygon(hull, 0xFF0000)           -- outline
    g:fill_polygon(hull, 0x40FF0000)    -- translucent fill
end
```

```lua
-- Object convex hull — returns polygon point array for rendering, or nil
local hull = scene:object_hull(3200, 3200)              -- first object at tile
local hull = scene:object_hull(3200, 3200, "Bank booth") -- filtered by name
if hull then g:polygon(hull, 0x00FF00) end
```

```lua
-- Menu target — returns the top menu entry (what left-click would do), or nil
local target = scene:menu_target()
if target then
    -- target.option  (string, e.g. "Talk-to", "Attack", "Use")
    -- target.target  (string, e.g. "Guard", "Bank booth")
    -- target.id      (int, identifier — NPC index, object ID, etc.)
    -- target.type    (string, MenuAction name e.g. "NPC_FIRST_OPTION")
end

-- All menu entries — top-first order
local entries = scene:menu_entries()
for i = 1, #entries do
    local e = entries[i]
    -- Same fields as menu_target: option, target, id, type
end
```
