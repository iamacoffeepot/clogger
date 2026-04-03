package dev.ragger.plugin.wasm;

import net.runelite.api.Client;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * A single Wasm script instance with lifecycle hooks.
 * Wraps a Chicory module with host functions bound to RuneLite.
 */
public class WasmScript {

    private static final Logger log = LoggerFactory.getLogger(WasmScript.class);

    private final String name;
    private final byte[] wasmBytes;
    private final Client client;
    private boolean running = false;

    // TODO: Chicory Instance and Module fields

    public WasmScript(String name, byte[] wasmBytes, Client client) {
        this.name = name;
        this.wasmBytes = wasmBytes;
        this.client = client;
    }

    /**
     * Initialize the Wasm module and call the exported on_start function.
     */
    public void start() {
        if (running) return;

        try {
            // TODO: parse wasmBytes with Chicory, bind host functions, instantiate
            // Module module = Module.parse(wasmBytes);
            // Instance instance = Instance.create(module, hostFunctions);
            // instance.export("on_start").apply();
            running = true;
            log.info("Script started: {}", name);
        } catch (Exception e) {
            log.error("Failed to start script: {}", name, e);
        }
    }

    /**
     * Called every game tick. Invokes the exported on_tick function if present.
     */
    public void tick() {
        if (!running) return;

        try {
            // TODO: instance.export("on_tick").apply();
        } catch (Exception e) {
            log.error("Script tick error: {}", name, e);
        }
    }

    /**
     * Stop the script and call the exported on_stop function.
     */
    public void stop() {
        if (!running) return;

        try {
            // TODO: instance.export("on_stop").apply();
        } catch (Exception e) {
            log.error("Script stop error: {}", name, e);
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
