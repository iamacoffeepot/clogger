package dev.ragger.plugin.scripting;

import net.runelite.api.*;
import party.iroiro.luajava.Lua;

import java.util.HashMap;
import java.util.Map;

/**
 * Lua binding for combat state — spec energy, prayers, attack style, target.
 * Exposed as the global "combat" table in Lua scripts.
 */
public class CombatApi {

    private static final int VARP_SPEC_ENERGY = 300;
    private static final int VARP_SPEC_ENABLED = 301;
    private static final int VARP_ATTACK_STYLE = 43;

    private static final Map<String, Prayer> PRAYER_LOOKUP = new HashMap<>();

    static {
        for (Prayer p : Prayer.values()) {
            PRAYER_LOOKUP.put(p.name().toLowerCase(), p);
        }
    }

    private final Client client;

    public CombatApi(Client client) {
        this.client = client;
    }

    public void register(Lua lua) {
        lua.createTable(0, 6);

        lua.push(this::spec);
        lua.setField(-2, "spec");

        lua.push(this::spec_enabled);
        lua.setField(-2, "spec_enabled");

        lua.push(this::attack_style);
        lua.setField(-2, "attack_style");

        lua.push(this::prayer_active);
        lua.setField(-2, "prayer_active");

        lua.push(this::active_prayers);
        lua.setField(-2, "active_prayers");

        lua.push(this::target);
        lua.setField(-2, "target");

        lua.setGlobal("combat");
    }

    /**
     * combat:spec() -> int (0-1000, divide by 10 for percentage)
     */
    private int spec(Lua lua) {
        lua.push(client.getVarpValue(VARP_SPEC_ENERGY));
        return 1;
    }

    /**
     * combat:spec_enabled() -> bool (is spec orb toggled on)
     */
    private int spec_enabled(Lua lua) {
        lua.push(client.getVarpValue(VARP_SPEC_ENABLED) == 1);
        return 1;
    }

    /**
     * combat:attack_style() -> int (0-3, weapon-dependent)
     */
    private int attack_style(Lua lua) {
        lua.push(client.getVarpValue(VARP_ATTACK_STYLE));
        return 1;
    }

    /**
     * combat:prayer_active("protect_from_melee") -> bool
     */
    private int prayer_active(Lua lua) {
        String name = lua.toString(2);
        if (name == null) {
            lua.push(false);
            return 1;
        }
        Prayer prayer = PRAYER_LOOKUP.get(name.toLowerCase());
        if (prayer == null) {
            lua.push(false);
            return 1;
        }
        lua.push(client.isPrayerActive(prayer));
        return 1;
    }

    /**
     * combat:active_prayers() -> array of prayer name strings
     */
    private int active_prayers(Lua lua) {
        lua.createTable(0, 0);
        int index = 1;
        for (Prayer prayer : Prayer.values()) {
            if (client.isPrayerActive(prayer)) {
                lua.push(prayer.name().toLowerCase());
                lua.rawSetI(-2, index++);
            }
        }
        return 1;
    }

    /**
     * combat:target() -> table {name, type, hp_ratio, hp_scale, animation} or nil
     */
    private int target(Lua lua) {
        Player local = client.getLocalPlayer();
        if (local == null) {
            lua.pushNil();
            return 1;
        }

        Actor interacting = local.getInteracting();
        if (interacting == null) {
            lua.pushNil();
            return 1;
        }

        lua.createTable(0, 5);

        String name = interacting.getName();
        lua.push(name != null ? name : "Unknown");
        lua.setField(-2, "name");

        if (interacting instanceof NPC) {
            lua.push("npc");
            lua.setField(-2, "type");
            lua.push(((NPC) interacting).getId());
            lua.setField(-2, "id");
        } else if (interacting instanceof Player) {
            lua.push("player");
            lua.setField(-2, "type");
        }

        lua.push(interacting.getHealthRatio());
        lua.setField(-2, "hp_ratio");

        lua.push(interacting.getHealthScale());
        lua.setField(-2, "hp_scale");

        lua.push(interacting.getAnimation());
        lua.setField(-2, "animation");

        return 1;
    }
}
