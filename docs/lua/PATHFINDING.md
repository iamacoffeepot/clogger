Tile-level A* pathfinding within the loaded 104x104 scene using collision data.

```lua
-- Find a walkable path between two world coordinate tiles
local path = pathfinding:find_path(player:x(), player:y(), 3200, 3200)
if path then
    for i, wp in ipairs(path) do
        local poly = coords:world_tile_poly(wp.x, wp.y)
        if poly then g:polygon(poly, 0x40FF00) end
    end
end

-- Check if a tile is reachable
local ok = pathfinding:can_reach(player:x(), player:y(), 3200, 3200)

-- Get tile distance (path length), or -1 if unreachable
local dist = pathfinding:distance(player:x(), player:y(), 3200, 3200)
```

Only works within the currently loaded scene. Returns nil/-1 for tiles outside the scene or unreachable destinations. Supports 8-directional movement with diagonal collision checks.
