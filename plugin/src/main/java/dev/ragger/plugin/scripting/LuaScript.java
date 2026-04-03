package dev.ragger.plugin.scripting;

import net.runelite.client.chat.ChatMessageManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import party.iroiro.luajava.Lua;
import party.iroiro.luajava.luaj.LuaJ;

/**
 * A single Lua script instance executed via LuaJ.
 * Scripts have access to injected API bindings.
 */
public class LuaScript {

    private static final Logger log = LoggerFactory.getLogger(LuaScript.class);

    private final String name;
    private final String source;
    private final ChatMessageManager chatMessageManager;
    private Lua lua;
    private boolean running = false;

    public LuaScript(String name, String source, ChatMessageManager chatMessageManager) {
        this.name = name;
        this.source = source;
        this.chatMessageManager = chatMessageManager;
    }

    public void start() {
        if (running) return;

        try {
            lua = new LuaJ();
            lua.openLibrary("base");
            lua.openLibrary("string");
            lua.openLibrary("table");
            lua.openLibrary("math");

            lua.set("chat", new ChatApi(chatMessageManager));

            lua.run(source);
            running = true;
            log.info("Script started: {}", name);
        } catch (Exception e) {
            log.error("Failed to start script: {}", name, e);
            stop();
        }
    }

    public void stop() {
        if (lua != null) {
            lua.close();
            lua = null;
        }
        running = false;
        log.info("Script stopped: {}", name);
    }

    public String getName() {
        return name;
    }

    public boolean isRunning() {
        return running;
    }
}
