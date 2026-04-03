package dev.ragger.plugin;

import com.google.inject.Provides;
import dev.ragger.plugin.ui.ChatPanel;
import dev.ragger.plugin.ui.ConsoleOverlay;
import dev.ragger.plugin.scripting.ScriptManager;
import dev.ragger.plugin.scripting.ScriptOverlay;
import net.runelite.api.Client;
import net.runelite.client.chat.ChatMessageManager;
import net.runelite.client.game.ItemManager;
import net.runelite.api.events.GameTick;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.eventbus.Subscribe;
import net.runelite.client.input.KeyManager;
import net.runelite.client.input.MouseManager;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;
import net.runelite.client.ui.overlay.OverlayManager;
import net.runelite.client.ui.ClientToolbar;
import net.runelite.client.ui.NavigationButton;
import net.runelite.client.util.ImageUtil;

import javax.inject.Inject;
import java.awt.image.BufferedImage;
import java.util.AbstractMap;
import java.util.Map;
import java.util.concurrent.ConcurrentLinkedQueue;

@PluginDescriptor(
    name = "Ragger",
    description = "AI assistant powered by Claude with Lua scripting",
    tags = {"ai", "claude", "lua", "assistant"}
)
public class RaggerPlugin extends Plugin {

    @Inject
    private Client client;

    @Inject
    private ClientToolbar clientToolbar;

    @Inject
    private ChatMessageManager chatMessageManager;

    @Inject
    private OverlayManager overlayManager;

    @Inject
    private ItemManager itemManager;

    @Inject
    private KeyManager keyManager;

    @Inject
    private MouseManager mouseManager;

    @Inject
    private RaggerConfig config;

    @Provides
    RaggerConfig provideConfig(ConfigManager configManager) {
        return configManager.getConfig(RaggerConfig.class);
    }

    private ChatPanel chatPanel;
    private NavigationButton navButton;
    private ScriptManager scriptManager;
    private ScriptOverlay scriptOverlay;
    private ConsoleOverlay consoleOverlay;
    private ClaudeClient claude;
    private final ConcurrentLinkedQueue<Map.Entry<String, String>> pendingScripts = new ConcurrentLinkedQueue<>();
    private net.runelite.client.input.KeyListener consoleKeyListener;
    private net.runelite.client.input.MouseWheelListener consoleMouseWheelListener;

    @Override
    protected void startUp() {
        scriptManager = new ScriptManager(client, chatMessageManager, itemManager);
        scriptOverlay = new ScriptOverlay(scriptManager);
        overlayManager.add(scriptOverlay);
        claude = new ClaudeClient(config.claudePath(), config.claudeModel());
        chatPanel = new ChatPanel(this::onUserMessage);
        consoleOverlay = new ConsoleOverlay(client, this::onUserMessage);
        overlayManager.add(consoleOverlay);

        consoleKeyListener = new net.runelite.client.input.KeyListener() {
            @Override
            public void keyTyped(java.awt.event.KeyEvent e) {
                if (e.getKeyChar() == '`') {
                    consoleOverlay.toggle();
                    e.consume();
                    return;
                }
                consoleOverlay.handleKeyTyped(e);
            }

            @Override
            public void keyPressed(java.awt.event.KeyEvent e) {
                consoleOverlay.handleKeyPressed(e);
            }

            @Override
            public void keyReleased(java.awt.event.KeyEvent e) {}
        };
        keyManager.registerKeyListener(consoleKeyListener);

        consoleMouseWheelListener = e -> {
            if (consoleOverlay.isVisible()) {
                consoleOverlay.handleScroll(e.getWheelRotation());
                e.consume();
            }
            return e;
        };
        mouseManager.registerMouseWheelListener(consoleMouseWheelListener);

        BufferedImage icon = ImageUtil.loadImageResource(getClass(), "icon.png");
        navButton = NavigationButton.builder()
            .tooltip("Ragger")
            .icon(icon)
            .priority(5)
            .panel(chatPanel)
            .build();
        clientToolbar.addNavigation(navButton);
    }

    @Override
    protected void shutDown() {
        clientToolbar.removeNavigation(navButton);
        overlayManager.remove(scriptOverlay);
        overlayManager.remove(consoleOverlay);
        keyManager.unregisterKeyListener(consoleKeyListener);
        mouseManager.unregisterMouseWheelListener(consoleMouseWheelListener);
        scriptManager.shutdown();
    }

    @Subscribe
    public void onGameTick(GameTick event) {
        // Load pending scripts on the client thread
        Map.Entry<String, String> pending;
        while ((pending = pendingScripts.poll()) != null) {
            scriptManager.load(pending.getKey(), pending.getValue());
            addToolMessage("Loaded script: " + pending.getKey());
        }
        scriptManager.tick();
    }

    private void addMessage(String sender, String message) {
        chatPanel.addMessage(sender, message);
        consoleOverlay.addMessage(sender, message);
    }

    private void addToolMessage(String message) {
        chatPanel.addToolMessage(message);
        consoleOverlay.addToolMessage(message);
    }

    private void onUserMessage(String message) {
        if (message.equalsIgnoreCase("/reset")) {
            claude.resetSession();
            chatPanel.clear();
            consoleOverlay.clear();
            addMessage("Claude", "Session reset.");
            return;
        }

        if (message.equalsIgnoreCase("/stop")) {
            scriptManager.shutdown();
            addToolMessage("All scripts stopped.");
            return;
        }

        if (message.startsWith("/stop ")) {
            String name = message.substring(6).trim();
            scriptManager.unload(name);
            addToolMessage("Stopped: " + name);
            return;
        }

        if (message.equalsIgnoreCase("/scripts")) {
            var names = scriptManager.list();
            if (names.isEmpty()) {
                addToolMessage("No active scripts.");
            } else {
                addToolMessage("Active scripts: " + String.join(", ", names));
            }
            return;
        }

        addMessage("You", message);
        chatPanel.showThinking();
        consoleOverlay.addThinking();
        claude.send(message, "BASE", "ASSISTANT").thenAccept(response -> {
            consoleOverlay.removeThinking();

            // Display tool usage log
            for (String toolEntry : response.getToolLog()) {
                addToolMessage(toolEntry);
            }

            // Queue scripts to load on the client thread (next game tick)
            if (response.hasScripts()) {
                response.getScripts().forEach((name, source) -> {
                    pendingScripts.add(new AbstractMap.SimpleEntry<>(name, source));
                });
            }

            // Display Claude's chat response
            if (!response.getText().isEmpty()) {
                addMessage("Claude", response.getText());
            }
        });
    }
}
