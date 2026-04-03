package dev.ragger.plugin.scripting;

import net.runelite.client.ui.overlay.Overlay;
import net.runelite.client.ui.overlay.OverlayLayer;
import net.runelite.client.ui.overlay.OverlayPosition;

import java.awt.*;

/**
 * Renders draw commands queued by Lua scripts via OverlayApi.
 */
public class ScriptOverlay extends Overlay {

    private final ScriptManager scriptManager;

    public ScriptOverlay(ScriptManager scriptManager) {
        this.scriptManager = scriptManager;
        setPosition(OverlayPosition.DYNAMIC);
        setLayer(OverlayLayer.ABOVE_SCENE);
    }

    @Override
    public Dimension render(Graphics2D graphics) {
        scriptManager.render(graphics);
        return null;
    }
}
