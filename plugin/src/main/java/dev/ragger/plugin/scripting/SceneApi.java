package dev.ragger.plugin.scripting;

import net.runelite.api.*;
import net.runelite.api.coords.WorldPoint;
import party.iroiro.luajava.Lua;

import java.util.List;

/**
 * Builds the "scene" Lua table with JFunction entries.
 * Each function returns Lua tables with primitive fields.
 */
public class SceneApi {

    private final Client client;

    public SceneApi(Client client) {
        this.client = client;
    }

    /**
     * Register the scene table and all its functions on the Lua state.
     */
    public void register(Lua lua) {
        lua.createTable(0, 3);

        lua.push(this::npcs);
        lua.setField(-2, "npcs");

        lua.push(this::players);
        lua.setField(-2, "players");

        lua.push(this::ground_items);
        lua.setField(-2, "ground_items");

        lua.setGlobal("scene");
    }

    private int npcs(Lua lua) {
        List<NPC> npcs = client.getNpcs();

        lua.createTable(npcs.size(), 0);
        int index = 1;

        for (NPC npc : npcs) {
            if (npc == null || npc.getName() == null) continue;

            lua.createTable(0, 10);

            pushString(lua, "name", npc.getName());
            pushInt(lua, "id", npc.getId());
            pushInt(lua, "combat", npc.getCombatLevel());
            pushInt(lua, "animation", npc.getAnimation());
            pushInt(lua, "hp_ratio", npc.getHealthRatio());
            pushInt(lua, "hp_scale", npc.getHealthScale());
            pushBool(lua, "is_dead", npc.isDead());

            WorldPoint wp = npc.getWorldLocation();
            if (wp != null) {
                pushInt(lua, "x", wp.getX());
                pushInt(lua, "y", wp.getY());
                pushInt(lua, "plane", wp.getPlane());
            }

            lua.rawSetI(-2, index++);
        }

        return 1;
    }

    private int players(Lua lua) {
        List<Player> players = client.getPlayers();

        lua.createTable(players.size(), 0);
        int index = 1;

        for (Player player : players) {
            if (player == null || player.getName() == null) continue;

            lua.createTable(0, 10);

            pushString(lua, "name", player.getName());
            pushInt(lua, "combat", player.getCombatLevel());
            pushInt(lua, "animation", player.getAnimation());
            pushInt(lua, "hp_ratio", player.getHealthRatio());
            pushInt(lua, "hp_scale", player.getHealthScale());
            pushBool(lua, "is_dead", player.isDead());
            pushBool(lua, "is_friend", player.isFriend());
            pushBool(lua, "is_clan", player.isClanMember());
            pushInt(lua, "team", player.getTeam());

            WorldPoint wp = player.getWorldLocation();
            if (wp != null) {
                pushInt(lua, "x", wp.getX());
                pushInt(lua, "y", wp.getY());
                pushInt(lua, "plane", wp.getPlane());
            }

            lua.rawSetI(-2, index++);
        }

        return 1;
    }

    private int ground_items(Lua lua) {
        Scene scene = client.getScene();
        Tile[][][] tiles = scene.getTiles();
        int plane = client.getPlane();

        lua.createTable(0, 0);
        int index = 1;

        for (int x = 0; x < tiles[plane].length; x++) {
            for (int y = 0; y < tiles[plane][x].length; y++) {
                Tile tile = tiles[plane][x][y];
                if (tile == null) continue;

                List<TileItem> items = tile.getGroundItems();
                if (items == null) continue;

                WorldPoint wp = tile.getWorldLocation();

                for (TileItem item : items) {
                    if (item == null) continue;

                    lua.createTable(0, 7);

                    pushInt(lua, "id", item.getId());
                    pushInt(lua, "quantity", item.getQuantity());
                    pushInt(lua, "ownership", item.getOwnership());
                    pushBool(lua, "is_private", item.isPrivate());

                    if (wp != null) {
                        pushInt(lua, "x", wp.getX());
                        pushInt(lua, "y", wp.getY());
                        pushInt(lua, "plane", wp.getPlane());
                    }

                    lua.rawSetI(-2, index++);
                }
            }
        }

        return 1;
    }

    private static void pushString(Lua lua, String key, String value) {
        lua.push(value);
        lua.setField(-2, key);
    }

    private static void pushInt(Lua lua, String key, int value) {
        lua.push(value);
        lua.setField(-2, key);
    }

    private static void pushBool(Lua lua, String key, boolean value) {
        lua.push(value);
        lua.setField(-2, key);
    }
}
