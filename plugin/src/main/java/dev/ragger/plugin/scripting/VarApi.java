package dev.ragger.plugin.scripting;

import net.runelite.api.Client;
import party.iroiro.luajava.Lua;

import java.util.Map;

/**
 * Lua bindings for reading game variables.
 *
 * Registers two globals:
 *   varp — player variables (varps and varbits)
 *   varc — client variables (integers and strings)
 *
 * Named constants are resolved lazily via __index metatables backed by
 * static HashMaps in VarpConstants and VarcConstants.
 */
public class VarApi {

    private final Client client;

    public VarApi(Client client) {
        this.client = client;
    }

    public void register(Lua lua) {
        // varp: player variables
        lua.createTable(0, 2);

        lua.push(this::varpGet);
        lua.setField(-2, "get");

        lua.push(this::varpBit);
        lua.setField(-2, "bit");

        setConstantMetatable(lua, VarpConstants.CONSTANTS);
        lua.setGlobal("varp");

        // varc: client variables
        lua.createTable(0, 2);

        lua.push(this::varcInt);
        lua.setField(-2, "int");

        lua.push(this::varcStr);
        lua.setField(-2, "str");

        setConstantMetatable(lua, VarcConstants.CONSTANTS);
        lua.setGlobal("varc");
    }

    /**
     * Attach an __index metatable that resolves named constants from a map.
     * The target table must be on the top of the stack.
     */
    private void setConstantMetatable(Lua lua, Map<String, Integer> constants) {
        lua.createTable(0, 1);
        lua.push((Lua l) -> {
            String key = l.toString(2);
            Integer value = constants.get(key);
            if (value != null) {
                l.push((int) value);
            } else {
                l.pushNil();
            }
            return 1;
        });
        lua.setField(-2, "__index");
        lua.setMetatable(-2);
    }

    /**
     * varp:get(id) -> int
     * Read a raw varp (variable player) slot value.
     */
    private int varpGet(Lua lua) {
        int id = (int) lua.toInteger(2);
        lua.push(client.getVarpValue(id));
        return 1;
    }

    /**
     * varp:bit(id) -> int
     * Read a varbit value. RuneLite extracts the bit range from the
     * appropriate varp slot automatically.
     */
    private int varpBit(Lua lua) {
        int id = (int) lua.toInteger(2);
        lua.push(client.getVarbitValue(id));
        return 1;
    }

    /**
     * varc:int(id) -> int
     * Read a client integer variable.
     */
    private int varcInt(Lua lua) {
        int id = (int) lua.toInteger(2);
        lua.push(client.getVarcIntValue(id));
        return 1;
    }

    /**
     * varc:str(id) -> string | nil
     * Read a client string variable.
     */
    private int varcStr(Lua lua) {
        int id = (int) lua.toInteger(2);
        String value = client.getVarcStrValue(id);
        if (value == null) {
            lua.pushNil();
        } else {
            lua.push(value);
        }
        return 1;
    }
}
