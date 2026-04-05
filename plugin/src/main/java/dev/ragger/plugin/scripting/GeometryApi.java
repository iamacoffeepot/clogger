package dev.ragger.plugin.scripting;

import net.runelite.api.Client;
import party.iroiro.luajava.Lua;

import java.util.List;

/**
 * Lua binding for the "geometry" global table.
 * Delegates all computation to {@link SilhouetteComputer}.
 */
public class GeometryApi {

    private final SilhouetteComputer computer;

    public GeometryApi(Client client) {
        this.computer = new SilhouetteComputer(client);
    }

    public void register(Lua lua) {
        lua.createTable(0, 3);

        lua.push(this::npc_outline);
        lua.setField(-2, "npc_outline");

        lua.push(this::player_outline);
        lua.setField(-2, "player_outline");

        lua.push(this::object_outline);
        lua.setField(-2, "object_outline");

        lua.setGlobal("geometry");
    }

    /**
     * geometry:npc_outline(name, [index]) -> array of contours or nil
     */
    private int npc_outline(Lua lua) {
        String name = lua.toString(2);
        int index = lua.getTop() >= 3 ? (int) lua.toInteger(3) : 1;

        List<SilhouetteComputer.Contour> contours = computer.npcOutline(name, index);
        return pushContours(lua, contours);
    }

    /**
     * geometry:player_outline(name) -> array of contours or nil
     */
    private int player_outline(Lua lua) {
        String name = lua.toString(2);

        List<SilhouetteComputer.Contour> contours = computer.playerOutline(name);
        return pushContours(lua, contours);
    }

    /**
     * geometry:object_outline(worldX, worldY, [name]) -> array of contours or nil
     */
    private int object_outline(Lua lua) {
        int worldX = (int) lua.toInteger(2);
        int worldY = (int) lua.toInteger(3);
        String name = lua.getTop() >= 4 ? lua.toString(4) : null;

        List<SilhouetteComputer.Contour> contours = computer.objectOutline(worldX, worldY, name);
        return pushContours(lua, contours);
    }

    /**
     * Push a list of contours as a Lua array of {x, y} point arrays, or nil if null.
     */
    private static int pushContours(Lua lua, List<SilhouetteComputer.Contour> contours) {
        if (contours == null) {
            lua.pushNil();
            return 1;
        }

        lua.createTable(contours.size(), 0);
        for (int c = 0; c < contours.size(); c++) {
            List<int[]> points = contours.get(c).points();
            lua.createTable(points.size(), 0);
            for (int p = 0; p < points.size(); p++) {
                lua.createTable(0, 2);
                lua.push(points.get(p)[0]);
                lua.setField(-2, "x");
                lua.push(points.get(p)[1]);
                lua.setField(-2, "y");
                lua.rawSetI(-2, p + 1);
            }
            lua.rawSetI(-2, c + 1);
        }

        return 1;
    }
}
