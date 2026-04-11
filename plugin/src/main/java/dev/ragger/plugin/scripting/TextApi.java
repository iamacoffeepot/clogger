package dev.ragger.plugin.scripting;

import net.runelite.api.Client;
import net.runelite.api.FontTypeFace;
import net.runelite.api.widgets.Widget;
import net.runelite.api.widgets.WidgetType;
import party.iroiro.luajava.Lua;

import java.util.HashMap;
import java.util.Map;

/**
 * Lua binding for measuring text using the game's bitmap fonts.
 * Exposed as the global "text" table in Lua scripts.
 *
 * Unlike the overlay g:text_width() which uses Java AWT fonts,
 * this API uses the actual OSRS FontTypeFace for pixel-perfect
 * measurements matching what the game renders in widgets.
 */
public class TextApi {

    private final Client client;
    private final Map<Integer, FontTypeFace> fontCache = new HashMap<>();

    public TextApi(final Client client) {
        this.client = client;
    }

    public void register(final Lua lua) {
        lua.createTable(0, 4);

        lua.push(this::width);
        lua.setField(-2, "width");

        lua.push(this::height);
        lua.setField(-2, "height");

        lua.push(this::fit);
        lua.setField(-2, "fit");

        lua.push(this::ascii);
        lua.setField(-2, "ascii");

        lua.setGlobal("text");
    }

    /**
     * text:width("string", fontId) -> int
     * Returns pixel width of the string using the game's bitmap font.
     * fontId defaults to 495 (PLAIN_12) if omitted.
     */
    private int width(final Lua lua) {
        final String text = lua.toString(2);
        final int fontId = lua.getTop() >= 3 ? (int) lua.toInteger(3) : 495;

        if (text == null) {
            lua.push(0);
            return 1;
        }

        final FontTypeFace font = resolveFont(fontId);
        lua.push(font != null ? font.getTextWidth(text) : 0);
        return 1;
    }

    /**
     * text:height(fontId) -> int
     * Returns the baseline (line height) of the game's bitmap font.
     * fontId defaults to 495 (PLAIN_12) if omitted.
     */
    private int height(final Lua lua) {
        final int fontId = lua.getTop() >= 2 ? (int) lua.toInteger(2) : 495;

        final FontTypeFace font = resolveFont(fontId);
        lua.push(font != null ? font.getBaseline() : 0);
        return 1;
    }

    /**
     * text:fit("string", fontId, maxWidth) -> string
     * text:fit("string", fontId, maxWidth, "suffix") -> string
     * Truncates the string to fit within maxWidth pixels using the game font.
     * Appends suffix (default "...") if truncated. Strips color/br tags for
     * measurement but preserves them in the output.
     */
    private int fit(final Lua lua) {
        final String text = lua.toString(2);
        final int fontId = (int) lua.toInteger(3);
        final int maxWidth = (int) lua.toInteger(4);
        final String suffix = lua.getTop() >= 5 ? lua.toString(5) : "...";

        if (text == null) {
            lua.push("");
            return 1;
        }

        final FontTypeFace font = resolveFont(fontId);
        if (font == null) {
            lua.push(text);
            return 1;
        }

        final String plain = stripTags(text);
        if (font.getTextWidth(plain) <= maxWidth) {
            lua.push(text);
            return 1;
        }

        final int suffixWidth = font.getTextWidth(suffix);
        final int target = maxWidth - suffixWidth;
        if (target <= 0) {
            lua.push(suffix);
            return 1;
        }

        // Binary search for the longest prefix that fits
        int lo = 0;
        int hi = plain.length();
        while (lo < hi) {
            final int mid = (lo + hi + 1) / 2;
            if (font.getTextWidth(plain.substring(0, mid)) <= target) {
                lo = mid;
            } else {
                hi = mid - 1;
            }
        }

        // Map the plain-text cut position back to the tagged string
        final int cutPos = mapPlainIndexToTagged(text, lo);
        lua.push(text.substring(0, cutPos) + suffix);
        return 1;
    }

    /**
     * text:ascii("string") -> string
     * Transliterates Unicode characters to ASCII equivalents.
     * Strips diacritics and replaces non-ASCII with '?'.
     */
    private int ascii(final Lua lua) {
        final String text = lua.toString(2);
        if (text == null) {
            lua.push("");
            return 1;
        }

        lua.push(transliterate(text));
        return 1;
    }

    /**
     * Resolve a FontTypeFace by font ID. Searches loaded widgets
     * for one with the target font, then caches the result.
     */
    FontTypeFace resolveFont(final int fontId) {
        final FontTypeFace cached = fontCache.get(fontId);
        if (cached != null) {
            return cached;
        }

        // Search loaded widgets for one with this font ID
        final Widget[] roots = client.getWidgetRoots();
        if (roots != null) {
            for (final Widget root : roots) {
                if (root == null || root.isHidden()) {
                    continue;
                }
                final FontTypeFace found = searchForFont(root, fontId, 0);
                if (found != null) {
                    fontCache.put(fontId, found);
                    return found;
                }
            }
        }

        return null;
    }

    private FontTypeFace searchForFont(final Widget parent, final int fontId, final int depth) {
        if (depth > 8) {
            return null;
        }

        if (parent.getType() == WidgetType.TEXT && parent.getFontId() == fontId) {
            final FontTypeFace font = parent.getFont();
            if (font != null) {
                return font;
            }
        }

        final Widget[][] groups = {
            parent.getDynamicChildren(),
            parent.getStaticChildren(),
            parent.getNestedChildren()
        };

        for (final Widget[] group : groups) {
            if (group == null) {
                continue;
            }
            for (final Widget child : group) {
                if (child == null) {
                    continue;
                }
                final FontTypeFace found = searchForFont(child, fontId, depth + 1);
                if (found != null) {
                    return found;
                }
            }
        }

        return null;
    }

    /**
     * Clear the font cache. Called when the player logs out or
     * the game state changes, since FontTypeFace references may
     * become stale.
     */
    public void clearCache() {
        fontCache.clear();
    }

    /**
     * Strip HTML-like tags (color, br, etc.) from widget text.
     */
    private static String stripTags(final String text) {
        final StringBuilder sb = new StringBuilder(text.length());
        int i = 0;
        while (i < text.length()) {
            final char c = text.charAt(i);
            if (c == '<') {
                final int end = text.indexOf('>', i);
                if (end >= 0) {
                    i = end + 1;
                    continue;
                }
            }
            sb.append(c);
            i++;
        }
        return sb.toString();
    }

    /**
     * Map a plain-text character index back to the corresponding
     * position in the tagged string, skipping over tags.
     */
    private static int mapPlainIndexToTagged(final String tagged, final int plainIndex) {
        int plainCount = 0;
        int i = 0;
        while (i < tagged.length() && plainCount < plainIndex) {
            final char c = tagged.charAt(i);
            if (c == '<') {
                final int end = tagged.indexOf('>', i);
                if (end >= 0) {
                    i = end + 1;
                    continue;
                }
            }
            plainCount++;
            i++;
        }
        return i;
    }

    /**
     * Transliterate Unicode to ASCII — strips diacritics, replaces
     * unmappable characters with '?'.
     */
    private static String transliterate(final String text) {
        // Use Java's Normalizer to decompose, then strip combining marks
        final String normalized = java.text.Normalizer.normalize(text, java.text.Normalizer.Form.NFD);
        final StringBuilder sb = new StringBuilder(normalized.length());
        for (int i = 0; i < normalized.length(); i++) {
            final char c = normalized.charAt(i);
            if (c <= 0x7F) {
                sb.append(c);
            } else if (Character.getType(c) == Character.NON_SPACING_MARK) {
                // Skip combining diacritical marks (accents, tildes, etc.)
            } else {
                // Handle common ligatures and special chars
                switch (c) {
                    case '\u0153': sb.append("oe"); break; // œ
                    case '\u0152': sb.append("OE"); break; // Œ
                    case '\u00E6': sb.append("ae"); break; // æ
                    case '\u00C6': sb.append("AE"); break; // Æ
                    case '\u00DF': sb.append("ss"); break; // ß
                    default: sb.append('?');
                }
            }
        }
        return sb.toString();
    }
}
