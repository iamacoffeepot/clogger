package dev.ragger.plugin.scripting;

import net.runelite.api.Client;
import net.runelite.client.chat.ChatMessageManager;
import net.runelite.client.game.ItemManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import party.iroiro.luajava.Lua;
import party.iroiro.luajava.luaj.LuaJ;

import java.util.Map;

/**
 * A single Lua script instance executed via LuaJ.
 *
 * Scripts can be one-shot (just runs top-to-bottom) or persistent
 * (returns a table with lifecycle hooks: on_start, on_tick, on_stop).
 */
public class LuaScript {

    private static final Logger log = LoggerFactory.getLogger(LuaScript.class);

    private final String name;
    private final String source;
    private final Client client;
    private final ChatMessageManager chatMessageManager;
    private final ItemManager itemManager;
    private final ScriptManager scriptManager;
    private final Map<String, Object> args;
    private final OverlayApi overlayApi = new OverlayApi();
    private Lua lua;
    private boolean running = false;
    private boolean hasHooks = false;
    private boolean requestStop = false;

    public LuaScript(String name, String source, Client client, ChatMessageManager chatMessageManager, ItemManager itemManager, ScriptManager scriptManager, Map<String, Object> args) {
        this.name = name;
        this.source = source;
        this.client = client;
        this.chatMessageManager = chatMessageManager;
        this.itemManager = itemManager;
        this.scriptManager = scriptManager;
        this.args = args;
    }

    private void initLua() {
        lua = new LuaJ();
        lua.openLibrary("base");
        lua.openLibrary("string");
        lua.openLibrary("table");
        lua.openLibrary("math");

        lua.run("math.randomseed(" + System.currentTimeMillis() + ")");

        lua.set("chat", new ChatApi(chatMessageManager));
        lua.set("camera", new CameraApi(client));
        lua.set("client", new ClientApi(client));
        lua.set("player", new PlayerApi(client));
        lua.set("skill", new SkillApi());
        new SceneApi(client).register(lua);
        new CoordsApi(client).register(lua);
        new ItemsApi(itemManager).register(lua);
        new InventoryApi(client, itemManager).register(lua);
        new CombatApi(client).register(lua);
        lua.set("prayer", new PrayerApi());
        new ScriptsApi(name, scriptManager).register(lua);

        // Inject args table if provided
        if (args != null && !args.isEmpty()) {
            pushArgsTable(lua, args);
            lua.setGlobal("args");
        }
    }

    public void start() {
        if (running) return;

        try {
            initLua();

            lua.run(source);

            // Check if the script returned a hooks table
            if (lua.type(-1) == Lua.LuaType.TABLE) {
                lua.setGlobal("__hooks");
                hasHooks = true;
                callHook("on_start");
            }

            running = true;
            log.info("Script started: {} (hooks={})", name, hasHooks);
        } catch (Exception e) {
            log.error("Failed to start script: {}", name, e);
            stop();
        }
    }

    public void tick() {
        if (!running || !hasHooks) return;
        if (!callHook("on_tick")) {
            requestStop = true;
        }
    }

    public void render(java.awt.Graphics2D graphics) {
        if (!running || !hasHooks) return;
        callHookWithArg("on_render", overlayApi);
        overlayApi.flush(graphics);
    }

    /**
     * Returns true if the script has requested to stop itself.
     */
    public boolean shouldStop() {
        return requestStop;
    }

    /**
     * Evaluate the script and return the top-of-stack result as a string.
     * Used by eval requests — runs once and returns the result.
     */
    public String evalAndReturn() {
        try {
            initLua();
            lua.run(source);

            // Convert top-of-stack to string
            if (lua.type(-1) == Lua.LuaType.TABLE) {
                // Serialize table to JSON-like string via Lua
                lua.run("function __to_json(t) " +
                    "if type(t) ~= 'table' then return tostring(t) end " +
                    "local parts = {} " +
                    "local is_array = #t > 0 " +
                    "if is_array then " +
                    "  for i, v in ipairs(t) do parts[#parts+1] = __to_json(v) end " +
                    "  return '[' .. table.concat(parts, ',') .. ']' " +
                    "else " +
                    "  for k, v in pairs(t) do parts[#parts+1] = '\"' .. tostring(k) .. '\":' .. __to_json(v) end " +
                    "  return '{' .. table.concat(parts, ',') .. '}' " +
                    "end end");
                lua.getGlobal("__to_json");
                lua.pushValue(-2); // push the table
                lua.pCall(1, 1);
                String result = lua.toString(-1);
                return result != null ? result : "null";
            } else if (lua.type(-1) == Lua.LuaType.NIL) {
                return "null";
            } else if (lua.type(-1) == Lua.LuaType.BOOLEAN) {
                return lua.toBoolean(-1) ? "true" : "false";
            } else if (lua.type(-1) == Lua.LuaType.NUMBER) {
                return String.valueOf(lua.toNumber(-1));
            } else {
                String result = lua.toString(-1);
                return result != null ? "\"" + result.replace("\"", "\\\"") + "\"" : "null";
            }
        } catch (Exception e) {
            log.error("Eval error: {}", e.getMessage());
            return "{\"error\":\"" + e.getMessage().replace("\"", "'") + "\"}";
        }
    }

    public void stop() {
        if (running && hasHooks) {
            callHook("on_stop");
        }
        if (lua != null) {
            lua.close();
            lua = null;
        }
        running = false;
        hasHooks = false;
        log.info("Script stopped: {}", name);
    }

    /**
     * Call a hook function. Returns false if the hook explicitly returned false (request stop).
     */
    private boolean callHook(String hookName) {
        if (lua == null) return true;

        try {
            lua.getGlobal("__hooks");
            lua.getField(-1, hookName);
            if (lua.type(-1) == Lua.LuaType.FUNCTION) {
                lua.pCall(0, 1);
                // Only stop if the hook explicitly returned false
                boolean keepRunning = lua.type(-1) != Lua.LuaType.BOOLEAN || lua.toBoolean(-1);
                lua.pop(2); // pop return value + __hooks
                return keepRunning;
            } else {
                lua.pop(2); // pop non-function + __hooks
                return true;
            }
        } catch (Exception e) {
            log.error("Script '{}' hook '{}' error: {}", name, hookName, e.getMessage());
            return true;
        }
    }

    private void callHookWithArg(String hookName, Object arg) {
        if (lua == null) return;

        try {
            lua.getGlobal("__hooks");
            lua.getField(-1, hookName);
            if (lua.type(-1) == Lua.LuaType.FUNCTION) {
                lua.push(arg, Lua.Conversion.FULL);
                lua.pCall(1, 0);
            } else {
                lua.pop(1);
            }
            lua.pop(1); // pop __hooks
        } catch (Exception e) {
            log.error("Script '{}' hook '{}' error: {}", name, hookName, e.getMessage());
        }
    }

    public String getName() {
        return name;
    }

    public boolean isRunning() {
        return running;
    }

    public boolean hasHooks() {
        return hasHooks;
    }

    public String getSource() {
        return source;
    }

    /**
     * Manually push a Map as a Lua table onto the stack.
     * Handles String, Number, and Boolean values.
     */
    private static void pushArgsTable(Lua lua, Map<String, Object> map) {
        lua.createTable(0, map.size());
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            Object value = entry.getValue();
            if (value instanceof String) {
                lua.push((String) value);
            } else if (value instanceof Integer) {
                lua.push((int) value);
            } else if (value instanceof Double) {
                lua.push((double) value);
            } else if (value instanceof Boolean) {
                lua.push((boolean) value);
            } else if (value instanceof Number) {
                lua.push(((Number) value).doubleValue());
            } else {
                lua.push(String.valueOf(value));
            }
            lua.setField(-2, entry.getKey());
        }
    }
}
