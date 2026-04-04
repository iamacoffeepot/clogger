-- radar: snapshots nearby NPCs, players, and ground items each tick
--
-- Mail API:
--   {action="report"}                -> replies with {npcs=..., players=..., items=...}
--   {action="report", filter="npcs"} -> replies with just {npcs=...}

local snapshot = { npcs = {}, players = {}, items = {} }

local function take_snapshot()
    local npcs = scene:npcs()
    local snap_npcs = {}
    for i = 1, #npcs do
        local n = npcs[i]
        snap_npcs[i] = {
            name = n.name, id = n.id,
            x = n.x, y = n.y,
            combat = n.combat,
            hp_ratio = n.hp_ratio, hp_scale = n.hp_scale,
            is_dead = n.is_dead
        }
    end

    local players = scene:players()
    local snap_players = {}
    for i = 1, #players do
        local p = players[i]
        snap_players[i] = {
            name = p.name,
            x = p.x, y = p.y,
            combat = p.combat,
            is_friend = p.is_friend, is_clan = p.is_clan
        }
    end

    local items = scene:ground_items()
    local snap_items = {}
    for i = 1, #items do
        local it = items[i]
        snap_items[i] = {
            id = it.id,
            quantity = it.quantity,
            x = it.x, y = it.y,
            is_private = it.is_private
        }
    end

    snapshot = { npcs = snap_npcs, players = snap_players, items = snap_items }
end

return {
    on_tick = function()
        take_snapshot()
    end,

    on_mail = function(from, data)
        if data.action == "report" then
            if data.filter == "npcs" then
                mail:send(from, { npcs = snapshot.npcs })
            elseif data.filter == "players" then
                mail:send(from, { players = snapshot.players })
            elseif data.filter == "items" then
                mail:send(from, { items = snapshot.items })
            else
                mail:send(from, snapshot)
            end
        end
    end
}
