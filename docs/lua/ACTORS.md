Manage child actors from within an actor. All operations are scoped — an actor can only manage its own children, not siblings or parents. Child names are automatically namespaced (e.g. parent `quest-guide` spawning `step-1` creates `quest-guide/step-1`). Stopping a parent cascade-stops all children. Max depth is 3 levels.

```lua
-- Spawn a child actor from raw source
actors:run("child-name", [[
    chat:game("Hello from child!")
]])

-- Stop a child (and its descendants)
actors:stop("child-name")

-- List direct children (short names)
local children = actors:list()    -- {"step-1", "step-2"}

-- Read a child's source
local src = actors:source("child-name")

-- Check if a child is running
actors:is_running("child-name")   -- true/false

-- List all registered templates
actors:templates()                -- {"counter-display", "tile-marker"}
```

#### Templates

Register reusable actor blueprints, then spawn parameterized instances:

```lua
-- Define a template (global — any actor can define or use)
actors:define("tile-marker", [[
    local color = args and args.color or 0xFFFFFF
    local tx, ty = args and args.x or 0, args and args.y or 0
    return {
        on_render = function(g)
            local poly = coords:world_tile_poly(tx, ty)
            if poly and #poly >= 3 then
                for j = 1, #poly do
                    local next = j < #poly and j + 1 or 1
                    g:line(poly[j].x, poly[j].y, poly[next].x, poly[next].y, color)
                end
            end
        end
    }
]])

-- Create children from the template with different args
actors:create("marker-1", "tile-marker", { x = 3200, y = 3400, color = 0xFF0000 })
actors:create("marker-2", "tile-marker", { x = 3201, y = 3400, color = 0x00FF00 })
```

The `args` table is injected as a global in the child actor's Lua environment.
