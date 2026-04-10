package dev.ragger.plugin.scripting;

import net.runelite.client.ui.overlay.Overlay;
import net.runelite.client.ui.overlay.OverlayLayer;
import net.runelite.client.ui.overlay.OverlayPosition;

import java.awt.Dimension;
import java.awt.Graphics2D;

/**
 * Renders draw commands queued by Lua actors' on_render_minimap hooks.
 * Uses ABOVE_WIDGETS layer so draws are visible over the minimap.
 */
public class MinimapOverlay extends Overlay {

    private final ActorManager actorManager;

    public MinimapOverlay(final ActorManager actorManager) {
        this.actorManager = actorManager;
        setPosition(OverlayPosition.DYNAMIC);
        setLayer(OverlayLayer.ABOVE_WIDGETS);
    }

    @Override
    public Dimension render(final Graphics2D graphics) {
        actorManager.renderMinimap(graphics);
        return null;
    }
}
