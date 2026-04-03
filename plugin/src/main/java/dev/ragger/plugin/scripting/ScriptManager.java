package dev.ragger.plugin.scripting;

import net.runelite.api.Client;
import net.runelite.client.chat.ChatMessageManager;
import net.runelite.client.game.ItemManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ConcurrentHashMap;

/**
 * Manages Lua script lifecycles. Each script gets its own LuaJ runtime
 * with API bindings injected.
 */
public class ScriptManager {

    private static final Logger log = LoggerFactory.getLogger(ScriptManager.class);

    private final Client client;
    private final ChatMessageManager chatMessageManager;
    private final ItemManager itemManager;
    private final ConcurrentHashMap<String, LuaScript> scripts = new ConcurrentHashMap<>();

    public ScriptManager(Client client, ChatMessageManager chatMessageManager, ItemManager itemManager) {
        this.client = client;
        this.chatMessageManager = chatMessageManager;
        this.itemManager = itemManager;
    }

    /**
     * Load and start a Lua script from source.
     */
    public String load(String name, String source) {
        LuaScript existing = scripts.get(name);
        if (existing != null) {
            existing.stop();
        }

        LuaScript script = new LuaScript(name, source, client, chatMessageManager, itemManager);
        scripts.put(name, script);
        script.start();
        log.info("Loaded script: {}", name);
        return name;
    }

    /**
     * Called every game tick — dispatches to all active scripts with hooks.
     */
    public void tick() {
        var it = scripts.entrySet().iterator();
        while (it.hasNext()) {
            var entry = it.next();
            LuaScript script = entry.getValue();
            script.tick();
            if (script.shouldStop()) {
                script.stop();
                it.remove();
                log.info("Script self-stopped: {}", entry.getKey());
            }
        }
    }

    /**
     * Unload and stop a script.
     */
    public void unload(String name) {
        LuaScript script = scripts.remove(name);
        if (script != null) {
            script.stop();
            log.info("Unloaded script: {}", name);
        }
    }

    /**
     * Called during overlay render — dispatches to all active scripts with hooks.
     */
    public void render(java.awt.Graphics2D graphics) {
        for (LuaScript script : scripts.values()) {
            script.render(graphics);
        }
    }

    /**
     * List all active script names.
     */
    public java.util.List<String> list() {
        return new java.util.ArrayList<>(scripts.keySet());
    }

    /**
     * Shut down all scripts.
     */
    public void shutdown() {
        for (LuaScript script : scripts.values()) {
            script.stop();
        }
        scripts.clear();
    }
}
