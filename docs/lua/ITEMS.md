Look up item information and prices by item ID.

```lua
items:name(4151)                    -- "Abyssal whip"
items:grand_exchange_price(4151)    -- current GE price
items:high_alchemy_price(4151)      -- high alchemy value
items:base_price(4151)              -- store/base value
items:is_stackable(4151)            -- true/false
items:is_members(4151)              -- true/false

-- Full lookup returns a table
local item = items:lookup(4151)
-- item.name, item.grand_exchange_price, item.high_alchemy_price,
-- item.base_price, item.stackable, item.members
```
