package com.runecolor.bridge;

import java.awt.Canvas;
import java.awt.Rectangle;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import net.runelite.api.Client;
import net.runelite.api.GameObject;
import net.runelite.api.Player;
import net.runelite.api.Scene;
import net.runelite.api.Tile;
import net.runelite.api.coords.LocalPoint;
import net.runelite.api.coords.WorldPoint;
import org.junit.Test;
import org.mockito.Mockito;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

public class ObjectScannerTest {
    private static final int TIN = 11361;
    private static final Set<Integer> WANT_TIN = new HashSet<>(Arrays.asList(TIN));

    private final Client client = Mockito.mock(Client.class);
    private final Player player = Mockito.mock(Player.class);
    private final Tile[][][] tiles = new Tile[1][104][104];

    public ObjectScannerTest() {
        Mockito.when(player.getLocalLocation()).thenReturn(LocalPoint.fromScene(50, 50));
        Canvas canvas = Mockito.mock(Canvas.class);
        Mockito.when(canvas.getLocationOnScreen()).thenReturn(new java.awt.Point(180, 30));
        Mockito.when(client.getCanvas()).thenReturn(canvas);
        Mockito.when(client.getPlane()).thenReturn(0);
        Scene scene = Mockito.mock(Scene.class);
        Mockito.when(scene.getTiles()).thenReturn(tiles);
        Mockito.when(client.getScene()).thenReturn(scene);
    }

    /** Put an object at an offset from the player, clickbox around canvas (300, 200). */
    private GameObject place(int id, int dx, int dy, boolean onScreen) {
        GameObject object = Mockito.mock(GameObject.class);
        Mockito.when(object.getId()).thenReturn(id);
        Mockito.when(object.getWorldLocation()).thenReturn(new WorldPoint(3200 + dx, 3200 + dy, 0));
        Mockito.when(object.getClickbox())
                .thenReturn(onScreen ? new Rectangle(290, 180, 20, 40) : null);
        putOnTile(object, dx, dy);
        return object;
    }

    /** Put an existing object on the tile at an offset from the player. */
    private void putOnTile(GameObject object, int dx, int dy) {
        Tile tile = tiles[0][50 + dx][50 + dy];
        if (tile == null) {
            tile = Mockito.mock(Tile.class);
            tiles[0][50 + dx][50 + dy] = tile;
        }
        GameObject[] existing = tile.getGameObjects();
        GameObject[] all = existing == null ? new GameObject[] {object}
                : appended(existing, object);
        Mockito.when(tile.getGameObjects()).thenReturn(all);
    }

    private static GameObject[] appended(GameObject[] objects, GameObject object) {
        GameObject[] all = Arrays.copyOf(objects, objects.length + 1);
        all[objects.length] = object;
        return all;
    }

    private List<Snapshot.SceneObject> scan(Set<Integer> ids) {
        return ObjectScanner.scan(client, player, ids);
    }

    @Test
    public void reportsOnlyRequestedObjectsNearestFirst() {
        place(TIN, 3, 0, true);
        place(TIN, 1, 0, true);
        place(999, 0, 1, true);
        List<Snapshot.SceneObject> found = scan(WANT_TIN);
        assertEquals(2, found.size());
        assertEquals(1, found.get(0).distance);
        assertEquals(3, found.get(1).distance);
        assertEquals(TIN, found.get(0).id);
        assertEquals(3201, found.get(0).tile.x);
        assertEquals(4, found.get(0).hull.size());
    }

    @Test
    public void skipsObjectsTooFarAway() {
        place(TIN, ObjectScanner.RADIUS + 1, 0, true);
        assertTrue(scan(WANT_TIN).isEmpty());
    }

    @Test
    public void skipsObjectsOffScreen() {
        place(TIN, 1, 0, false);
        assertTrue(scan(WANT_TIN).isEmpty());
    }

    @Test
    public void capsHowManyItReports() {
        for (int dx = -6; dx <= 5; dx++) {
            place(TIN, dx, 2, true);
        }
        assertEquals(ObjectScanner.MAX_OBJECTS, scan(WANT_TIN).size());
    }

    @Test
    public void reportsNothingWhenNothingIsRequested() {
        place(TIN, 1, 0, true);
        assertTrue(scan(Collections.emptySet()).isEmpty());
    }

    @Test
    public void unknownWithoutACanvas() {
        Mockito.when(client.getCanvas()).thenReturn(null);
        assertNull(scan(WANT_TIN));
    }

    @Test
    public void reportsALargeObjectOnlyOnceFromItsAnchorTile() {
        GameObject object = Mockito.mock(GameObject.class);
        Mockito.when(object.getId()).thenReturn(TIN);
        Mockito.when(object.getWorldLocation()).thenReturn(new WorldPoint(3201, 3200, 0));
        Mockito.when(object.getClickbox()).thenReturn(new Rectangle(290, 180, 20, 40));
        Mockito.when(object.getSceneMinLocation())
                .thenReturn(new net.runelite.api.Point(51, 50));
        putOnTile(object, 1, 0);
        putOnTile(object, 2, 0);

        List<Snapshot.SceneObject> found = scan(WANT_TIN);
        assertEquals(1, found.size());
        assertEquals(1, found.get(0).distance);
    }
}
