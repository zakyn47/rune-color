package com.runecolor.bridge;

import java.awt.Point;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import net.runelite.api.Client;
import net.runelite.api.GameObject;
import net.runelite.api.Player;
import net.runelite.api.Scene;
import net.runelite.api.Tile;
import net.runelite.api.coords.LocalPoint;
import net.runelite.api.coords.WorldPoint;

/** Finds the game objects the bot asked for near the player. Client thread only. */
final class ObjectScanner {
    static final int RADIUS = 15;
    static final int MAX_OBJECTS = 10;

    private ObjectScanner() {
    }

    static List<Snapshot.SceneObject> scan(Client client, Player player, Set<Integer> ids) {
        if (ids.isEmpty()) {
            return Collections.emptyList();
        }
        Point origin = SnapshotBuilder.canvasOrigin(client);
        LocalPoint here = player.getLocalLocation();
        Scene scene = client.getScene();
        if (origin == null || here == null || scene == null) {
            return null;
        }
        Tile[][] tiles = scene.getTiles()[client.getPlane()];
        List<SnapshotBuilder.Nearby<Snapshot.SceneObject>> nearby = new ArrayList<>();
        for (int dx = -RADIUS; dx <= RADIUS; dx++) {
            for (int dy = -RADIUS; dy <= RADIUS; dy++) {
                int x = here.getSceneX() + dx;
                int y = here.getSceneY() + dy;
                if (x < 0 || y < 0 || x >= tiles.length || y >= tiles[x].length
                        || tiles[x][y] == null) {
                    continue;
                }
                int distance = Math.max(Math.abs(dx), Math.abs(dy));
                for (GameObject object : tiles[x][y].getGameObjects()) {
                    Snapshot.SceneObject found = sceneObject(object, x, y, ids, origin, distance);
                    if (found != null) {
                        nearby.add(new SnapshotBuilder.Nearby<>(distance, found));
                    }
                }
            }
        }
        return SnapshotBuilder.nearestFirst(nearby, MAX_OBJECTS);
    }

    private static Snapshot.SceneObject sceneObject(GameObject object, int x, int y,
                                                    Set<Integer> ids, Point origin,
                                                    int distance) {
        if (object == null || !ids.contains(object.getId()) || !anchoredAt(object, x, y)) {
            return null;
        }
        List<int[]> hull = HullOutline.of(object.getClickbox(), origin);
        WorldPoint tile = object.getWorldLocation();
        if (hull == null || tile == null) {
            return null;
        }
        return new Snapshot.SceneObject(object.getId(), SnapshotBuilder.point(tile),
                distance, hull);
    }

    /** A large object, a tree say, sits on several tiles; report it from one of them. */
    private static boolean anchoredAt(GameObject object, int x, int y) {
        net.runelite.api.Point min = object.getSceneMinLocation();
        return min == null || (min.getX() == x && min.getY() == y);
    }
}
