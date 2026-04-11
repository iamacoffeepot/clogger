Read game interface (widget) state — bank, inventory grid, dialogs, skill tab, prayer orbs, etc.

```lua
-- Get a widget by interface group ID and child index
local w = widget:get(widget.BANK, 0)

-- Get a widget by packed component ID (groupId << 16 | childId)
local w = widget:component(componentId)

-- Quick text read (returns string or nil)
local txt = widget:text(widget.DIALOG_NPC, 4)

-- Get all children of a widget (dynamic + static + nested)
local kids = widget:children(widget.BANK, 0)
for i = 1, #kids do
    local child = kids[i]
    -- child.id, child.text, child.item_id, child.item_quantity, ...
end

-- Root widgets (all currently loaded interfaces)
local roots = widget:roots()

-- Get parent widget (traverse up the tree)
local p = widget:parent(componentId)

-- Get a specific child by widget index (works for dynamic children)
local c = widget:child(componentId, childIndex)

-- Deep traversal — flat array of ALL descendants (recursive)
local all = widget:descendants(componentId)
for i = 1, #all do
    -- every widget in the subtree, depth-first
end

-- Search descendants with filters
local results = widget:find(componentId, {
    text = "attack",            -- text contains (case-insensitive)
    name = "close",             -- name/tooltip contains (case-insensitive)
    type = widget.TYPE_TEXT,    -- exact widget type
    item_id = 4151,             -- exact item ID
    has_text = true,            -- has any non-empty text
    has_item = true,            -- has item_id > 0
    has_action = "Withdraw",    -- has an action containing this string
    limit = 10                  -- max results (default unlimited)
})

-- Set text on a dynamic child by widget index
widget:set_text(componentId, "new text", childIndex)

-- Set width/height (uses setOriginalWidth/Height + revalidate)
widget:set_width(componentId, 300)
widget:set_width(componentId, 300, childIndex)
widget:set_height(componentId, 40)
widget:set_height(componentId, 40, childIndex)

-- Set scroll height on a scrollable container (revalidates scroll)
widget:set_scroll_height(componentId, 800)
widget:set_scroll_height(componentId, 800, childIndex)
```

All methods accepting a component ID also accept `(groupId, childId)` form (except `set_width`, `set_height`, `set_scroll_height` which use `componentId` only).

#### Widget table shape

`widget:get()`, `widget:component()`, and entries in `widget:children()` / `widget:roots()` all return tables with this shape:

```lua
{
    id            = 786432,     -- packed component ID (groupId << 16 | childId)
    type          = 4,          -- WidgetType (e.g. widget.TYPE_TEXT)
    content_type  = 0,
    index         = 0,          -- index within parent's children
    parent_id     = -1,         -- -1 if root
    text          = "Bank of RuneScape",  -- omitted if empty
    name          = "Close",              -- omitted if empty (tooltip/op-base name)
    hidden        = false,      -- true if widget or any parent is hidden
    self_hidden   = false,      -- true if this widget itself is hidden
    item_id       = 4151,       -- omitted if <= 0
    item_quantity = 1,          -- omitted if no item_id
    sprite_id     = 535,        -- omitted if <= 0
    model_id      = 100,        -- omitted if <= 0
    model_type    = 1,          -- omitted if no model_id
    width         = 200,
    height        = 30,
    x             = 10,         -- relative to parent
    y             = 5,
    canvas_x      = 310,        -- absolute screen X
    canvas_y      = 205,        -- absolute screen Y
    scroll_x      = 0,          -- omitted if both scroll_x and scroll_y are 0
    scroll_y      = 120,
    scroll_width  = 200,
    scroll_height = 800,
    child_count   = 12,         -- omitted if 0 (dynamic + static + nested)
    text_color    = 0xFF981F,   -- omitted if 0 (RGB24)
    font_id       = 495,        -- omitted if <= 0
    text_shadowed = true,        -- omitted if false
    opacity       = 0,          -- 0=opaque, 255=transparent
    actions       = {"Withdraw-1", "Withdraw-5", "Withdraw-All"}  -- omitted if none
}
```

Fields with zero/nil/empty values are omitted to keep tables compact. A simple text widget might only have `id`, `type`, `index`, `parent_id`, `text`, `hidden`, `self_hidden`, `width`, `height`, `x`, `y`.

Returns `nil` if the widget doesn't exist or is hidden.

#### InterfaceID constants

Access via `widget.NAME`:

```
widget.BANK                widget.INVENTORY           widget.EQUIPMENT
widget.PRAYER              widget.SPELLBOOK           widget.SKILLS
widget.QUEST_LIST          widget.COMBAT              widget.MINIMAP
widget.CHATBOX             widget.SHOP                widget.GRAND_EXCHANGE
widget.DIALOG_NPC          widget.DIALOG_PLAYER       widget.DIALOG_OPTION
widget.LEVEL_UP            widget.COLLECTION_LOG      widget.WORLD_MAP
widget.DEPOSIT_BOX         widget.SEED_VAULT          widget.RUNE_POUCH
widget.LOOTING_BAG         widget.FRIEND_LIST         widget.CLAN
widget.MUSIC               widget.EMOTES              widget.SETTINGS
```

(Full list mirrors RuneLite's `InterfaceID` class — all constants are available.)

#### WidgetType constants

```
widget.TYPE_LAYER          widget.TYPE_RECTANGLE      widget.TYPE_TEXT
widget.TYPE_GRAPHIC        widget.TYPE_MODEL          widget.TYPE_TEXT_INVENTORY
widget.TYPE_LINE
```
