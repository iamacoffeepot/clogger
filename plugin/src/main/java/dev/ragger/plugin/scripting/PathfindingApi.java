package dev.ragger.plugin.scripting;

import net.runelite.api.Client;
import net.runelite.api.CollisionData;
import net.runelite.api.CollisionDataFlag;
import party.iroiro.luajava.Lua;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;

/**
 * Lua binding for tile-level A* pathfinding within the loaded scene.
 * Exposed as the global "pathfinding" table in Lua scripts.
 *
 * Uses RuneLite's CollisionData to check walkability. Only works within
 * the currently loaded 104x104 scene region.
 */
public class PathfindingApi {

    private static final int SCENE_SIZE = 104;
    private static final int MAX_NODES = 5000;

    /** Directional movement flags — blocks movement INTO a tile from the given direction. */
    private static final int BLOCK_WEST = CollisionDataFlag.BLOCK_MOVEMENT_WEST;
    private static final int BLOCK_EAST = CollisionDataFlag.BLOCK_MOVEMENT_EAST;
    private static final int BLOCK_SOUTH = CollisionDataFlag.BLOCK_MOVEMENT_SOUTH;
    private static final int BLOCK_NORTH = CollisionDataFlag.BLOCK_MOVEMENT_NORTH;
    private static final int BLOCK_SW = CollisionDataFlag.BLOCK_MOVEMENT_SOUTH_WEST;
    private static final int BLOCK_SE = CollisionDataFlag.BLOCK_MOVEMENT_SOUTH_EAST;
    private static final int BLOCK_NW = CollisionDataFlag.BLOCK_MOVEMENT_NORTH_WEST;
    private static final int BLOCK_NE = CollisionDataFlag.BLOCK_MOVEMENT_NORTH_EAST;
    private static final int BLOCK_FULL = CollisionDataFlag.BLOCK_MOVEMENT_FULL;

    /** 8-directional neighbours: dx, dy, required clear flags on destination. */
    private static final int[][] DIRS = {
        { 0,  1, BLOCK_SOUTH},  // moving north: dst must not block from south
        { 0, -1, BLOCK_NORTH},  // moving south
        { 1,  0, BLOCK_WEST},   // moving east
        {-1,  0, BLOCK_EAST},   // moving west
        { 1,  1, BLOCK_SW},     // moving north-east
        {-1,  1, BLOCK_SE},     // moving north-west
        { 1, -1, BLOCK_NW},     // moving south-east
        {-1, -1, BLOCK_NE},     // moving south-west
    };

    private final Client client;

    public PathfindingApi(final Client client) {
        this.client = client;
    }

    public void register(final Lua lua) {
        lua.createTable(0, 3);

        lua.push(this::find_path);
        lua.setField(-2, "find_path");

        lua.push(this::can_reach);
        lua.setField(-2, "can_reach");

        lua.push(this::distance);
        lua.setField(-2, "distance");

        lua.setGlobal("pathfinding");
    }

    /**
     * pathfinding:find_path(fromX, fromY, toX, toY) -> array of {x, y} waypoints or nil
     */
    private int find_path(final Lua lua) {
        final int fromX = (int) lua.toInteger(2);
        final int fromY = (int) lua.toInteger(3);
        final int toX = (int) lua.toInteger(4);
        final int toY = (int) lua.toInteger(5);

        final List<int[]> path = astar(fromX, fromY, toX, toY);
        if (path == null) {
            lua.pushNil();
            return 1;
        }

        lua.createTable(path.size(), 0);
        for (int i = 0; i < path.size(); i++) {
            lua.createTable(0, 2);
            lua.push(path.get(i)[0]);
            lua.setField(-2, "x");
            lua.push(path.get(i)[1]);
            lua.setField(-2, "y");
            lua.rawSetI(-2, i + 1);
        }

        return 1;
    }

    /**
     * pathfinding:can_reach(fromX, fromY, toX, toY) -> boolean
     */
    private int can_reach(final Lua lua) {
        final int fromX = (int) lua.toInteger(2);
        final int fromY = (int) lua.toInteger(3);
        final int toX = (int) lua.toInteger(4);
        final int toY = (int) lua.toInteger(5);

        lua.push(astar(fromX, fromY, toX, toY) != null);
        return 1;
    }

    /**
     * pathfinding:distance(fromX, fromY, toX, toY) -> int tile count or -1
     */
    private int distance(final Lua lua) {
        final int fromX = (int) lua.toInteger(2);
        final int fromY = (int) lua.toInteger(3);
        final int toX = (int) lua.toInteger(4);
        final int toY = (int) lua.toInteger(5);

        final List<int[]> path = astar(fromX, fromY, toX, toY);
        lua.push(path != null ? path.size() - 1 : -1);
        return 1;
    }

    /**
     * A* pathfinding over the scene collision map.
     * Coordinates are world tile coords. Returns path as world coords, or null if unreachable.
     */
    private List<int[]> astar(final int fromWorldX, final int fromWorldY, final int toWorldX, final int toWorldY) {
        final CollisionData[] collisionData = client.getCollisionMaps();
        if (collisionData == null) {
            return null;
        }

        final int plane = client.getPlane();
        final int[][] flags = collisionData[plane].getFlags();
        final int baseX = client.getBaseX();
        final int baseY = client.getBaseY();

        final int sx = fromWorldX - baseX;
        final int sy = fromWorldY - baseY;
        final int gx = toWorldX - baseX;
        final int gy = toWorldY - baseY;

        if (!inBounds(sx, sy) || !inBounds(gx, gy)) {
            return null;
        }

        if ((flags[sx][sy] & BLOCK_FULL) != 0 || (flags[gx][gy] & BLOCK_FULL) != 0) {
            return null;
        }

        final Map<Long, Long> cameFrom = new HashMap<>();
        final Map<Long, Integer> gScore = new HashMap<>();
        final long startKey = packKey(sx, sy);
        final long goalKey = packKey(gx, gy);

        gScore.put(startKey, 0);

        final PriorityQueue<long[]> open = new PriorityQueue<>(Comparator.comparingLong(a -> a[1]));
        open.add(new long[]{startKey, chebyshev(sx, sy, gx, gy)});

        int expanded = 0;

        while (!open.isEmpty() && expanded < MAX_NODES) {
            final long[] current = open.poll();
            final long currentKey = current[0];

            if (currentKey == goalKey) {
                return reconstructPath(cameFrom, goalKey, baseX, baseY);
            }

            expanded++;
            final int cx = unpackX(currentKey);
            final int cy = unpackY(currentKey);
            final int currentG = gScore.getOrDefault(currentKey, Integer.MAX_VALUE);

            for (final int[] dir : DIRS) {
                final int nx = cx + dir[0];
                final int ny = cy + dir[1];

                if (!inBounds(nx, ny)) {
                    continue;
                }

                if ((flags[nx][ny] & BLOCK_FULL) != 0) {
                    continue;
                }

                if ((flags[nx][ny] & dir[2]) != 0) {
                    continue;
                }

                // For diagonal movement, also check that the two adjacent cardinal tiles are clear
                if (dir[0] != 0 && dir[1] != 0) {
                    if ((flags[cx + dir[0]][cy] & BLOCK_FULL) != 0 ||
                        (flags[cx][cy + dir[1]] & BLOCK_FULL) != 0) {
                        continue;
                    }
                }

                final int tentativeG = currentG + 1;
                final long neighborKey = packKey(nx, ny);
                final int prevG = gScore.getOrDefault(neighborKey, Integer.MAX_VALUE);

                if (tentativeG < prevG) {
                    cameFrom.put(neighborKey, currentKey);
                    gScore.put(neighborKey, tentativeG);
                    final int f = tentativeG + chebyshev(nx, ny, gx, gy);
                    open.add(new long[]{neighborKey, f});
                }
            }
        }

        return null;
    }

    private static List<int[]> reconstructPath(
        final Map<Long, Long> cameFrom,
        final long goalKey,
        final int baseX,
        final int baseY
    ) {
        final List<int[]> path = new ArrayList<>();
        long key = goalKey;

        while (key != -1L) {
            path.add(new int[]{unpackX(key) + baseX, unpackY(key) + baseY});
            final Long parent = cameFrom.get(key);
            key = parent != null ? parent : -1L;
        }

        // Reverse to get start->goal order
        final int size = path.size();
        for (int i = 0; i < size / 2; i++) {
            final int[] tmp = path.get(i);
            path.set(i, path.get(size - 1 - i));
            path.set(size - 1 - i, tmp);
        }

        return path;
    }

    private static boolean inBounds(final int x, final int y) {
        return x >= 0 && x < SCENE_SIZE && y >= 0 && y < SCENE_SIZE;
    }

    private static int chebyshev(final int x1, final int y1, final int x2, final int y2) {
        return Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1));
    }

    private static long packKey(final int x, final int y) {
        return ((long) x << 16) | (y & 0xFFFFL);
    }

    private static int unpackX(final long key) {
        return (int) (key >> 16);
    }

    private static int unpackY(final long key) {
        return (int) (key & 0xFFFF);
    }
}
