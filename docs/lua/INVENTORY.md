Read the player's inventory and equipment.

```lua
-- Inventory items — returns array of non-empty slots
local inv = inventory:items()
for i = 1, #inv do
    local item = inv[i]
    -- item.id        (int, item ID)
    -- item.name      (string)
    -- item.quantity   (int)
    -- item.slot       (int, 0-27)
end

-- Equipment — returns array of equipped items
local gear = inventory:equipment()
for i = 1, #gear do
    local item = gear[i]
    -- item.id         (int, item ID)
    -- item.name       (string)
    -- item.quantity    (int)
    -- item.slot        (int, raw slot index)
    -- item.slot_name   (string: "head", "cape", "amulet", "weapon", "body",
    --                   "shield", "legs", "gloves", "boots", "ring", "ammo")
end

-- Utility
inventory:contains(4151)    -- true if Abyssal whip is in inventory
inventory:count(4151)       -- how many Abyssal whips in inventory
```
