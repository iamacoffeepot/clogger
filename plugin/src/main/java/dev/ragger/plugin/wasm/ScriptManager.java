package dev.ragger.plugin.wasm;

import net.runelite.api.Client;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ConcurrentHashMap;

/**
 * Manages Wasm script lifecycles. Each script gets its own Chicory instance
 * with host functions bound to RuneLite's API.
 */
public class ScriptManager {

    private static final Logger log = LoggerFactory.getLogger(ScriptManager.class);

    private final Client client;
    private final ConcurrentHashMap<String, WasmScript> scripts = new ConcurrentHashMap<>();

    public ScriptManager(Client client) {
        this.client = client;
    }

    /**
     * Load and start a Wasm script from raw bytes.
     */
    public String load(String name, byte[] wasmBytes) {
        WasmScript existing = scripts.get(name);
        if (existing != null) {
            existing.stop();
        }

        WasmScript script = new WasmScript(name, wasmBytes, client);
        scripts.put(name, script);
        script.start();
        log.info("Loaded script: {}", name);
        return name;
    }

    /**
     * Unload and stop a script.
     */
    public void unload(String name) {
        WasmScript script = scripts.remove(name);
        if (script != null) {
            script.stop();
            log.info("Unloaded script: {}", name);
        }
    }

    /**
     * Called every game tick — dispatches to all active scripts.
     */
    public void tick() {
        for (WasmScript script : scripts.values()) {
            script.tick();
        }
    }

    /**
     * Shut down all scripts.
     */
    public void shutdown() {
        for (WasmScript script : scripts.values()) {
            script.stop();
        }
        scripts.clear();
    }
}
