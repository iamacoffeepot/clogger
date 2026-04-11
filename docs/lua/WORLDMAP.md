Place markers on the world map. Markers are cleaned up automatically when the actor stops.

```lua
worldmap:add(3200, 3200, "Quest NPC")             -- add marker with tooltip
worldmap:add(3200, 3200, "Quest NPC", 0x00FF00)   -- with custom color (RGB)
worldmap:remove(3200, 3200)                        -- remove marker at coords
worldmap:clear()                                   -- remove all markers owned by this actor
```

Markers snap to the world map edge when the target is off-screen and jump to the location on click.
