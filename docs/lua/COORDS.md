Convert between coordinate systems. Returns nil if the point is off-screen or outside the loaded scene.

```lua
-- World tile to canvas (screen) pixel
local sx, sy = coords:world_to_canvas(3200, 3400)

-- Local tile (0-103 scene offset) to canvas pixel
local sx, sy = coords:local_to_canvas(52, 52)

-- World tile to local tile
local lx, ly = coords:world_to_local(3200, 3400)

-- World tile to minimap pixel
local mx, my = coords:world_to_minimap(3200, 3400)

-- World tile to text position (x, y above tile at given height)
local tx, ty = coords:world_text_pos(3200, 3400, 150)  -- height optional, default 0

-- World tile to screen polygon (array of {x, y} points)
local poly = coords:world_tile_poly(3200, 3400)
```

Multi-return functions return two values (x, y). Check for nil before using:
```lua
local sx, sy = coords:world_to_canvas(3200, 3400)
if sx then
    g:text(sx, sy, "Here!", 0xFFFF00)
end
```
