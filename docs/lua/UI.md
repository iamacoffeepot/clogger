Create native Jagex widget-based HUD panels. Panels are LAYER widgets rendered by the game client (not Java overlays), so they look and behave like real game interfaces.

```lua
-- Create a panel
local panel = ui:create({
    title = "My Panel",          -- optional title bar
    x = 100, y = 50,            -- position on screen
    width = 220, height = 160,  -- size in pixels
    closeable = true,            -- show X button (default false)
    draggable = true,            -- drag title bar to move (default false)
    on_close = function()        -- called when X clicked
        chat:game("Closed!")
    end
})

-- Add text
local label = panel:text({ x = 10, y = 10, text = "Hello", color = 0xFFFF00 })

-- Add button with left-click callback
panel:button({
    x = 10, y = 30, w = 80, h = 24,
    text = "Click me",
    on_click = function()
        panel:set(label, { text = "Clicked!" })
    end
})

-- Add button with right-click menu actions
panel:button({
    x = 10, y = 60, w = 80, h = 24,
    text = "Options",
    actions = {
        { label = "Reset",  on_click = function() ... end },
        { label = "Config", on_click = function() ... end },
    }
})

-- Add rectangle (divider, background, etc.)
panel:rect({ x = 0, y = 55, w = 200, h = 1, color = 0xFF981F, filled = true })

-- Add game sprite
panel:sprite({ x = 10, y = 80, sprite = 56, w = 20, h = 20 })

-- Add item icon
panel:item({ x = 40, y = 80, item_id = 4151, quantity = 1 })

-- Update element properties
panel:set(label, { text = "Updated!", color = 0x00FF00 })

-- Show/hide elements
panel:hide(label)
panel:show(label)

-- Remove an element
panel:remove(label)

-- Move or resize the panel
panel:move(200, 100)
panel:resize(300, 200)

-- Destroy the panel
panel:close()

-- List all active panel IDs
local ids = ui:list()
```

Element positions are relative to the panel's content area (below the title bar if present). Colors are RGB24 hex values. Panels auto-destroy when the actor stops. Panels survive viewport mode switches (fixed/resizable) via automatic rebuild.
