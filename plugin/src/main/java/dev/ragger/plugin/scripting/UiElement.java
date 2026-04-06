package dev.ragger.plugin.scripting;

import net.runelite.api.widgets.Widget;

import java.util.HashMap;
import java.util.Map;

/**
 * Tracks a single UI element (text, rect, button, sprite, item) within a panel.
 * Stores the widget reference, callback refs, and config for viewport rebuild.
 */
final class UiElement {

    /** Element types matching Lua API method names. */
    static final int TEXT = 0;
    static final int RECT = 1;
    static final int BUTTON = 2;
    static final int SPRITE = 3;
    static final int ITEM = 4;

    static final int NO_REF = 0;

    final int id;
    final int elementType;
    final Map<String, Object> config;

    Widget widget;
    int clickRef = NO_REF;
    final Map<Integer, Integer> actionRefs = new HashMap<>();

    UiElement(final int id, final int elementType, final Map<String, Object> config) {
        this.id = id;
        this.elementType = elementType;
        this.config = config;
    }
}
