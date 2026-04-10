-- cooks-assistant-guide: step-by-step quest overlay for Cook's Assistant
--
-- Tracks quest progress via varp 29, monitors inventory for required items,
-- highlights NPCs/objects with convex hulls, marks locations on minimap and
-- world map, renders walkable paths to objectives, and shows a checklist panel.
--
-- Mail API:
--   {action="status"} -> mails back {stage, has_egg, has_milk, has_flour, step}

local VARP_COOK = 29

local EGG    = 1944
local MILK   = 1927
local FLOUR  = 1933
local BUCKET = 1925
local POT    = 1931

local COOK_POS = { x = 3208, y = 3214 }
local MILL_POS = { x = 3166, y = 3306 }
local COW_POS  = { x = 3253, y = 3270 }
local EGG_POS  = { x = 3235, y = 3295 }

local C_TITLE = 0xFFD700
local C_DONE  = 0x00FF00
local C_TODO  = 0xFF6666
local C_HINT  = 0x00CCFF
local C_NPC   = 0xFFFF00
local C_OBJ   = 0xFF981F
local C_PATH  = 0x4000FF00
local C_BG    = 0xC0000000

local stage = 0
local has_egg = false
local has_milk = false
local has_flour = false
local has_bucket = false
local has_pot = false

local panel = nil
local lbl_step = nil
local lbl_egg = nil
local lbl_milk = nil
local lbl_flour = nil
local lbl_hint = nil

local cached_path = nil
local path_target = nil
local path_tick = 0

local function update_state()
    stage = varp:get(VARP_COOK)
    has_egg = inventory:contains(EGG)
    has_milk = inventory:contains(MILK)
    has_flour = inventory:contains(FLOUR)
    has_bucket = inventory:contains(BUCKET)
    has_pot = inventory:contains(POT)
end

local function current_step()
    if stage == 0 then
        return "Talk to the Cook"
    elseif stage == 2 then
        return "Quest complete!"
    end
    if has_egg and has_milk and has_flour then
        return "Return to the Cook"
    end
    if not has_egg then
        return "Get an egg"
    elseif not has_milk then
        return has_bucket and "Use bucket on Dairy cow" or "Get a bucket, then milk a cow"
    else
        return has_pot and "Make flour at the mill" or "Get a pot, then make flour"
    end
end

local function hint_text()
    if stage == 0 then
        return "Ground floor, Lumbridge Castle"
    elseif stage == 2 then
        return "+1 QP, +300 Cooking XP"
    end
    if has_egg and has_milk and has_flour then
        return "All items collected!"
    end
    if not has_egg then
        return "Pick up an egg near the chickens"
    elseif not has_milk then
        return "Farm north-east of Lumbridge"
    else
        return "Use grain on hopper upstairs, then collect flour"
    end
end

local function target_location()
    if stage == 0 or (stage == 1 and has_egg and has_milk and has_flour) then
        return COOK_POS, "Cook"
    elseif stage == 1 then
        if not has_egg then return EGG_POS, "Egg"
        elseif not has_milk then return COW_POS, "Dairy cow"
        else return MILL_POS, "Mill"
        end
    end
    return nil, nil
end

local function check_mark(ok)
    return ok and "[x] " or "[ ] "
end

local function check_color(ok)
    return ok and C_DONE or C_TODO
end

local function dist_to(target)
    local dx = target.x - player:x()
    local dy = target.y - player:y()
    return math.sqrt(dx * dx + dy * dy)
end

local function direction_to(target)
    local dx = target.x - player:x()
    local dy = target.y - player:y()
    if math.abs(dx) < 5 and math.abs(dy) < 5 then return "here" end
    local angle = math.atan2(dy, dx) * 180 / math.pi
    if angle < 0 then angle = angle + 360 end
    local dirs = { "E", "NE", "N", "NW", "W", "SW", "S", "SE" }
    return dirs[math.floor((angle + 22.5) / 45) % 8 + 1]
end

local function update_path()
    local target = target_location()
    if not target or stage == 2 then
        cached_path = nil
        path_target = nil
        return
    end

    local px, py = player:x(), player:y()
    if path_target and path_target.x == target.x and path_target.y == target.y
       and cached_path and path_tick > client:tick_count() - 3 then
        return
    end

    path_target = target
    path_tick = client:tick_count()
    cached_path = pathfinding:find_path(px, py, target.x, target.y)
end

local function place_worldmap_markers()
    worldmap:clear()
    if stage == 2 then return end

    worldmap:add(COOK_POS.x, COOK_POS.y, "Cook", C_NPC)
    if stage == 1 then
        if not has_egg then
            worldmap:add(EGG_POS.x, EGG_POS.y, "Egg spawn", C_OBJ)
        end
        if not has_milk then
            worldmap:add(COW_POS.x, COW_POS.y, "Dairy cow", C_HINT)
        end
        if not has_flour then
            worldmap:add(MILL_POS.x, MILL_POS.y, "Mill Lane Mill", C_OBJ)
        end
    end
end

local function build_panel()
    panel = ui:create({
        title = "Cook's Assistant",
        x = 10, y = 40,
        width = 210, height = 130,
        closeable = true,
        draggable = true,
        on_close = function() panel = nil end
    })

    lbl_step  = panel:text({ x = 8, y = 6,  text = "", color = C_TITLE })
    panel:rect({ x = 4, y = 22, w = 200, h = 1, color = 0x554433, filled = true })
    lbl_egg   = panel:text({ x = 8, y = 28, text = "", color = C_TODO })
    lbl_milk  = panel:text({ x = 8, y = 44, text = "", color = C_TODO })
    lbl_flour = panel:text({ x = 8, y = 60, text = "", color = C_TODO })
    panel:rect({ x = 4, y = 78, w = 200, h = 1, color = 0x554433, filled = true })
    lbl_hint  = panel:text({ x = 8, y = 84, text = "", color = C_HINT })
end

local function update_panel()
    if not panel then return end

    panel:set(lbl_step, { text = current_step(), color = stage == 2 and C_DONE or C_TITLE })

    if stage == 1 then
        panel:set(lbl_egg,   { text = check_mark(has_egg) .. "Egg",            color = check_color(has_egg) })
        panel:set(lbl_milk,  { text = check_mark(has_milk) .. "Bucket of milk", color = check_color(has_milk) })
        panel:set(lbl_flour, { text = check_mark(has_flour) .. "Pot of flour",  color = check_color(has_flour) })
        panel:show(lbl_egg)
        panel:show(lbl_milk)
        panel:show(lbl_flour)
    else
        panel:hide(lbl_egg)
        panel:hide(lbl_milk)
        panel:hide(lbl_flour)
    end

    local hint = hint_text()
    local target = target_location()
    if target and stage ~= 2 then
        local d = math.floor(dist_to(target))
        if d > 5 then
            hint = hint .. " (" .. d .. " " .. direction_to(target) .. ")"
        end
    end
    panel:set(lbl_hint, { text = hint, color = C_HINT })
end

return {
    on_start = function()
        update_state()
        build_panel()
        update_panel()
        place_worldmap_markers()
    end,

    on_tick = function()
        update_state()
        update_panel()
        update_path()
    end,

    on_varp_changed = function(data)
        if data.varp_id ~= VARP_COOK then return end
        update_state()
        update_panel()
        place_worldmap_markers()
        if data.value == 1 then
            chat:game("Cook's Assistant started! Collect egg, milk, and flour.")
        elseif data.value == 2 then
            chat:game("Cook's Assistant complete! +1 QP, +300 Cooking XP")
            worldmap:clear()
            cached_path = nil
        end
    end,

    on_inventory_changed = function(data)
        local prev_egg, prev_milk, prev_flour = has_egg, has_milk, has_flour
        update_state()
        update_panel()
        place_worldmap_markers()
        if stage ~= 1 then return end
        if has_egg and not prev_egg then chat:game("Got the egg!") end
        if has_milk and not prev_milk then chat:game("Got the bucket of milk!") end
        if has_flour and not prev_flour then chat:game("Got the pot of flour!") end
        if has_egg and has_milk and has_flour then
            chat:game("All items collected! Return to the Cook.")
        end
    end,

    on_menu_opened = function(data)
        if stage ~= 1 then return end
        for _, e in ipairs(data.entries) do
            if e.target == "Dairy cow" and not has_milk then
                if not has_bucket then
                    chat:game("You need an empty bucket to milk the cow.")
                end
            elseif e.target == "Hopper" and not has_flour then
                chat:game("Use grain on the hopper, then operate the controls.")
            end
        end
    end,

    on_mail = function(from, data)
        if data.action == "status" then
            update_state()
            mail:send(from, {
                stage = stage,
                has_egg = has_egg,
                has_milk = has_milk,
                has_flour = has_flour,
                step = current_step(),
                hint = hint_text()
            })
        end
    end,

    on_render = function(g)
        if stage == 2 then return end
        g:font("Arial", "bold", 11)

        -- hull highlights on relevant NPCs/objects
        if stage == 0 or stage == 1 then
            local cook_hull = scene:npc_hull("Cook")
            if cook_hull then
                g:fill_polygon(cook_hull, 0x40FFFF00)
                g:polygon(cook_hull, C_NPC)
            end
        end

        if stage == 1 then
            if not has_egg then
                local npcs = scene:npcs()
                for i = 1, #npcs do
                    if npcs[i].name == "Chicken" then
                        local hull = scene:npc_hull(npcs[i].id)
                        if hull then g:polygon(hull, C_HINT) end
                    end
                end

                local items = scene:ground_items()
                for i = 1, #items do
                    if items[i].name == "Egg" then
                        local poly = coords:world_tile_poly(items[i].x, items[i].y)
                        if poly then
                            g:fill_polygon(poly, 0x40FF981F)
                            g:polygon(poly, C_OBJ)
                        end
                        local tx, ty = coords:world_text_pos(items[i].x, items[i].y, 100)
                        if tx then g:text(tx - 10, ty, "Egg", C_OBJ) end
                    end
                end
            end

            if not has_milk then
                local cow_hull = scene:npc_hull("Dairy cow")
                if cow_hull then
                    g:fill_polygon(cow_hull, 0x4000CCFF)
                    g:polygon(cow_hull, C_HINT)
                end
            end

            if not has_flour then
                local objs = scene:objects("hopper")
                for i = 1, #objs do
                    local hull = scene:object_hull(objs[i].x, objs[i].y, "hopper")
                    if hull then
                        g:fill_polygon(hull, 0x40FF981F)
                        g:polygon(hull, C_OBJ)
                    end
                end
                local bins = scene:objects("flour bin")
                for i = 1, #bins do
                    local hull = scene:object_hull(bins[i].x, bins[i].y, "flour bin")
                    if hull then
                        g:fill_polygon(hull, 0x40FF981F)
                        g:polygon(hull, C_OBJ)
                    end
                end
            end
        end

        -- pathfinding overlay: draw walkable path to current objective
        if cached_path then
            for i = 1, #cached_path do
                local poly = coords:world_tile_poly(cached_path[i].x, cached_path[i].y)
                if poly then g:fill_polygon(poly, C_PATH) end
            end
        end

        -- off-screen direction indicator
        local target, name = target_location()
        if target then
            local sx, sy = coords:world_to_canvas(target.x, target.y)
            if not sx then
                local dx = target.x - player:x()
                local dy = target.y - player:y()
                local dist = math.floor(math.sqrt(dx * dx + dy * dy))
                local label = name .. " " .. dist .. " tiles " .. direction_to(target)

                local vw = client:viewport_width()
                local vh = client:viewport_height()
                local vx = client:viewport_x()
                local vy = client:viewport_y()
                local angle = math.atan2(dy, dx)
                local ix = vx + vw / 2 + math.cos(angle) * (vw / 2 - 60)
                local iy = vy + vh / 2 - math.sin(angle) * (vh / 2 - 30)
                ix = math.max(vx + 40, math.min(vx + vw - 40, ix))
                iy = math.max(vy + 20, math.min(vy + vh - 20, iy))

                local w = g:text_width(label)
                g:fill_rect(ix - w / 2 - 6, iy - 10, w + 12, 20, C_BG)
                g:text(ix - w / 2, iy + 4, label, C_HINT)
                g:fill_circle(ix + math.cos(angle) * 20, iy - math.sin(angle) * 20, 4, C_HINT)
            end
        end
    end,

    on_render_minimap = function(g)
        if stage == 2 then return end

        -- red dot on current objective
        local target = target_location()
        if target then
            local mx, my = coords:world_to_minimap(target.x, target.y)
            if mx then
                g:fill_circle(mx, my, 5, 0xFF0000)
                g:circle(mx, my, 5, 0xCC0000)
            end
        end

        -- green dots on other relevant locations
        local marks = {}
        if stage == 0 then
            marks = { COOK_POS }
        elseif stage == 1 then
            if not has_egg then marks[#marks + 1] = EGG_POS end
            if not has_milk then marks[#marks + 1] = COW_POS end
            if not has_flour then marks[#marks + 1] = MILL_POS end
            if not (has_egg and has_milk and has_flour) then
                marks[#marks + 1] = COOK_POS
            end
        end

        for _, pos in ipairs(marks) do
            if not target or pos.x ~= target.x or pos.y ~= target.y then
                local mx, my = coords:world_to_minimap(pos.x, pos.y)
                if mx then
                    g:fill_circle(mx, my, 3, C_DONE)
                end
            end
        end
    end,

    on_stop = function()
        worldmap:clear()
        if panel then
            panel:close()
            panel = nil
        end
    end
}
