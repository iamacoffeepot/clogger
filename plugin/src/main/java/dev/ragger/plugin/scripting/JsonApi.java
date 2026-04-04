package dev.ragger.plugin.scripting;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonParser;
import party.iroiro.luajava.Lua;

/**
 * Lua binding for JSON encode/decode.
 * Exposed as the global "json" table in Lua scripts.
 *
 * Usage in Lua:
 *   local s = json.encode({ key = "value", list = {1, 2, 3} })
 *   local t = json.decode('{"key":"value","list":[1,2,3]}')
 */
public class JsonApi {

    private static final Gson GSON = new GsonBuilder().disableHtmlEscaping().create();

    public void register(Lua lua) {
        lua.createTable(0, 2);

        lua.push(this::encode);
        lua.setField(-2, "encode");

        lua.push(this::decode);
        lua.setField(-2, "decode");

        lua.setGlobal("json");
    }

    /**
     * json.encode(value) → JSON string
     * Reads any Lua value (table, string, number, boolean, nil) and returns its JSON representation.
     */
    private int encode(Lua lua) {
        Object value = LuaUtils.readValue(lua, LuaUtils.abs(lua, 1), 0);

        lua.push(GSON.toJson(value));
        return 1;
    }

    /**
     * json.decode(string) → Lua value
     * Parses a JSON string and pushes the resulting Lua value onto the stack.
     */
    private int decode(Lua lua) {
        String json = lua.toString(1);
        if (json == null || json.isEmpty()) {
            lua.pushNil();
            return 1;
        }

        try {
            var element = new JsonParser().parse(json);
            Object value = fromJsonElement(element);
            LuaUtils.pushValue(lua, value);
        } catch (Exception e) {
            lua.error("json.decode: " + e.getMessage());
        }
        return 1;
    }

    @SuppressWarnings("unchecked")
    static Object fromJsonElement(com.google.gson.JsonElement element) {
        if (element.isJsonObject()) {
            java.util.Map<String, Object> map = new java.util.HashMap<>();
            for (var kv : element.getAsJsonObject().entrySet()) {
                map.put(kv.getKey(), fromJsonElement(kv.getValue()));
            }
            return map;
        } else if (element.isJsonArray()) {
            java.util.List<Object> list = new java.util.ArrayList<>();
            for (var item : element.getAsJsonArray()) {
                list.add(fromJsonElement(item));
            }
            return list;
        } else if (element.isJsonPrimitive()) {
            var prim = element.getAsJsonPrimitive();
            if (prim.isBoolean()) return prim.getAsBoolean();
            if (prim.isNumber()) {
                double num = prim.getAsDouble();
                if (num == Math.floor(num) && !Double.isInfinite(num)
                        && num >= Integer.MIN_VALUE && num <= Integer.MAX_VALUE) {
                    return (int) num;
                }
                return num;
            }
            return prim.getAsString();
        }
        return null;
    }
}
