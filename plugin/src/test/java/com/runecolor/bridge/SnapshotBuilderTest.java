package com.runecolor.bridge;

import java.awt.Canvas;
import java.awt.Rectangle;
import java.awt.Shape;
import net.runelite.api.Client;
import net.runelite.api.GameObject;
import net.runelite.api.Item;
import net.runelite.api.ItemComposition;
import net.runelite.api.ItemContainer;
import net.runelite.api.ItemLayer;
import net.runelite.api.NPC;
import net.runelite.api.TileItem;
import net.runelite.api.gameval.InventoryID;
import net.runelite.api.ObjectComposition;
import net.runelite.api.Scene;
import net.runelite.api.Tile;
import net.runelite.api.coords.LocalPoint;
import net.runelite.api.GameState;
import net.runelite.api.Player;
import net.runelite.api.Skill;
import net.runelite.api.coords.WorldPoint;
import org.junit.Test;
import org.mockito.Mockito;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;

public class SnapshotBuilderTest {
    private Client loggedInClient() {
        Client client = Mockito.mock(Client.class);
        Player player = Mockito.mock(Player.class);
        Mockito.when(client.getGameState()).thenReturn(GameState.LOGGED_IN);
        Mockito.when(client.getTickCount()).thenReturn(123456);
        Mockito.when(client.getBoostedSkillLevel(Skill.HITPOINTS)).thenReturn(42);
        Mockito.when(client.getRealSkillLevel(Skill.HITPOINTS)).thenReturn(55);
        Mockito.when(client.getBoostedSkillLevel(Skill.PRAYER)).thenReturn(12);
        Mockito.when(client.getRealSkillLevel(Skill.PRAYER)).thenReturn(43);
        Mockito.when(client.getLocalPlayer()).thenReturn(player);
        Mockito.when(player.getWorldLocation()).thenReturn(new WorldPoint(3222, 3218, 0));
        standStill(player);
        return client;
    }

    /** Pose the mock as a player standing still with nothing playing. */
    private static void standStill(Player player) {
        Mockito.when(player.getAnimation()).thenReturn(-1);
        Mockito.when(player.getIdlePoseAnimation()).thenReturn(808);
        Mockito.when(player.getPoseAnimation()).thenReturn(808);
    }

    @Test
    public void standingStillWithNoAnimationIsIdle() {
        Snapshot snapshot = SnapshotBuilder.build(loggedInClient(), 0L);
        assertEquals(Integer.valueOf(-1), snapshot.animation);
        assertEquals(Boolean.TRUE, snapshot.idle);
    }

    @Test
    public void choppingIsNotIdle() {
        Client client = loggedInClient();
        Player player = client.getLocalPlayer();
        Mockito.when(player.getAnimation()).thenReturn(879);  // Bronze axe swing.
        Snapshot snapshot = SnapshotBuilder.build(client, 0L);
        assertEquals(Integer.valueOf(879), snapshot.animation);
        assertEquals(Boolean.FALSE, snapshot.idle);
    }

    /**
     * Put the player at scene tile (50, 50) with a canvas at screen (180, 30), and
     * the named object at the given offset with its clickbox around canvas (300, 200).
     */
    private static Client withObjectNearby(String name, int dx, int dy) {
        Client client = Mockito.mock(Client.class, Mockito.RETURNS_DEEP_STUBS);
        Player player = Mockito.mock(Player.class);
        Mockito.when(player.getLocalLocation()).thenReturn(LocalPoint.fromScene(50, 50));
        Canvas canvas = Mockito.mock(Canvas.class);
        Mockito.when(canvas.getLocationOnScreen()).thenReturn(new java.awt.Point(180, 30));
        Mockito.when(client.getCanvas()).thenReturn(canvas);
        Mockito.when(client.getPlane()).thenReturn(0);

        Tile[][][] tiles = new Tile[1][104][104];
        Tile tile = Mockito.mock(Tile.class);
        GameObject object = Mockito.mock(GameObject.class);
        Mockito.when(object.getId()).thenReturn(26185);
        Mockito.when(object.getClickbox()).thenReturn(new Rectangle(290, 180, 20, 40));
        Mockito.when(tile.getGameObjects()).thenReturn(new GameObject[] {object});
        tiles[0][50 + dx][50 + dy] = tile;
        Scene scene = Mockito.mock(Scene.class);
        Mockito.when(scene.getTiles()).thenReturn(tiles);
        Mockito.when(client.getScene()).thenReturn(scene);

        ObjectComposition composition = Mockito.mock(ObjectComposition.class);
        Mockito.when(composition.getName()).thenReturn(name);
        Mockito.when(client.getObjectDefinition(26185)).thenReturn(composition);
        Mockito.when(client.getLocalPlayer()).thenReturn(player);
        return client;
    }

    @Test
    public void reportsTheScreenPointOfANearbyFire() {
        Client client = withObjectNearby("Fire", 1, 0);
        Snapshot.ScreenPoint fire = SnapshotBuilder.nearestFire(client, client.getLocalPlayer());
        assertNotNull(fire);
        assertEquals(180 + 300, fire.x);
        assertEquals(30 + 200, fire.y);
    }

    @Test
    public void ignoresObjectsThatAreNotFires() {
        Client client = withObjectNearby("Willow tree", 1, 0);
        assertNull(SnapshotBuilder.nearestFire(client, client.getLocalPlayer()));
    }

    @Test
    public void ignoresAFireTooFarAway() {
        Client client = withObjectNearby("Fire", SnapshotBuilder.FIRE_RADIUS + 1, 0);
        assertNull(SnapshotBuilder.nearestFire(client, client.getLocalPlayer()));
    }

    @Test
    public void reportsNoFireWithoutAScene() {
        // The default logged-in mock has no scene or canvas.
        Client client = loggedInClient();
        assertNull(SnapshotBuilder.build(client, 0L).fire);
    }

    @Test
    public void walkingIsNotIdle() {
        // Walking and running play a pose animation, not an action animation, so
        // an animation of -1 alone is not enough.
        Client client = loggedInClient();
        Player player = client.getLocalPlayer();
        Mockito.when(player.getPoseAnimation()).thenReturn(819);
        assertEquals(Boolean.FALSE, SnapshotBuilder.build(client, 0L).idle);
    }

    @Test
    public void buildsAFullSnapshotWhenLoggedIn() {
        Client client = loggedInClient();
        Mockito.when(client.getEnergy()).thenReturn(8700);

        Snapshot snapshot = SnapshotBuilder.build(client, 1757193600123L);

        assertEquals(1, snapshot.schema);
        assertEquals(123456, snapshot.tick);
        assertEquals(1757193600123L, snapshot.sentAt);
        assertEquals("LOGGED_IN", snapshot.gameState);
        assertEquals(42, snapshot.hitpoints.current);
        assertEquals(55, snapshot.hitpoints.max);
        assertEquals(12, snapshot.prayer.current);
        assertEquals(43, snapshot.prayer.max);
        assertEquals(Integer.valueOf(87), snapshot.runEnergy);
        assertEquals(3222, snapshot.worldPoint.x);
        assertEquals(3218, snapshot.worldPoint.y);
        assertEquals(0, snapshot.worldPoint.plane);
    }

    /**
     * {@code Client#getEnergy()} in RuneLite 1.12.38 is documented (see the
     * evidence comment on {@link SnapshotBuilder#normalizeEnergy}) to always return
     * "the run energy in units of 1/100th of an percentage" — a 0-10000 scale, not a
     * value-dependent mix of 0-100 and 0-10000. This test pins that single fixed
     * division.
     */
    @Test
    public void normalizesHundredthsOfAPercentScaleToWholePercent() {
        Client client = loggedInClient();
        Mockito.when(client.getEnergy()).thenReturn(8700);

        assertEquals(Integer.valueOf(87), SnapshotBuilder.build(client, 0L).runEnergy);
    }

    /**
     * Regression test for the bug in the original brief-supplied heuristic
     * ({@code raw > 100 ? raw / 100 : raw}): under that rule a raw reading of 50 —
     * which on the documented 0-10000 scale means 0.5% run energy, i.e. nearly
     * empty — was passed through unchanged and misreported as 50% (half a bar).
     * That is precisely the "quiet wrong answer" this normalization exists to
     * prevent. If a future client genuinely changes {@code getEnergy()}'s scale
     * back to 0-100, this test is the one that will fail and point here — do not
     * "fix" it by reintroducing a value-dependent guess; re-verify the new
     * client's own javadoc/sources first and update the documented conversion
     * (and this test) accordingly.
     */
    @Test
    public void lowRawEnergyDoesNotGetMisreadAsAHighPercentage() {
        Client client = loggedInClient();
        Mockito.when(client.getEnergy()).thenReturn(50);

        assertEquals(Integer.valueOf(0), SnapshotBuilder.build(client, 0L).runEnergy);
    }

    @Test
    public void clampsEnergyToOneHundred() {
        Client client = loggedInClient();
        Mockito.when(client.getEnergy()).thenReturn(10000);

        assertEquals(Integer.valueOf(100), SnapshotBuilder.build(client, 0L).runEnergy);
    }

    @Test
    public void omitsPlayerFieldsWhenLoggedOut() {
        Client client = Mockito.mock(Client.class);
        Mockito.when(client.getGameState()).thenReturn(GameState.LOGIN_SCREEN);
        Mockito.when(client.getTickCount()).thenReturn(7);
        Mockito.when(client.getLocalPlayer()).thenReturn(null);

        Snapshot snapshot = SnapshotBuilder.build(client, 99L);

        assertEquals("LOGIN_SCREEN", snapshot.gameState);
        assertEquals(7, snapshot.tick);
        assertNull(snapshot.hitpoints);
        assertNull(snapshot.prayer);
        assertNull(snapshot.runEnergy);
        assertNull(snapshot.worldPoint);
    }

    @Test
    public void omitsPlayerFieldsWhenLocalPlayerIsNullDespiteLoggedInState() {
        Client client = Mockito.mock(Client.class);
        Mockito.when(client.getGameState()).thenReturn(GameState.LOGGED_IN);
        Mockito.when(client.getTickCount()).thenReturn(8);
        Mockito.when(client.getLocalPlayer()).thenReturn(null);

        Snapshot snapshot = SnapshotBuilder.build(client, 0L);

        assertNull(snapshot.worldPoint);
        assertNull(snapshot.hitpoints);
        assertNull(snapshot.prayer);
        assertNull(snapshot.runEnergy);
    }

    /**
     * A non-null player can still return a null {@code getWorldLocation()} (for
     * example between login and the first tile becoming known). Only the tile
     * should be omitted in that case — the stats, which don't depend on it, must
     * still populate.
     */
    @Test
    public void omitsWorldPointButKeepsStatsWhenWorldLocationIsNull() {
        Client client = Mockito.mock(Client.class);
        Player player = Mockito.mock(Player.class);
        Mockito.when(client.getGameState()).thenReturn(GameState.LOGGED_IN);
        Mockito.when(client.getTickCount()).thenReturn(9);
        Mockito.when(client.getBoostedSkillLevel(Skill.HITPOINTS)).thenReturn(30);
        Mockito.when(client.getRealSkillLevel(Skill.HITPOINTS)).thenReturn(40);
        Mockito.when(client.getBoostedSkillLevel(Skill.PRAYER)).thenReturn(5);
        Mockito.when(client.getRealSkillLevel(Skill.PRAYER)).thenReturn(20);
        Mockito.when(client.getEnergy()).thenReturn(5000);
        Mockito.when(client.getLocalPlayer()).thenReturn(player);
        Mockito.when(player.getWorldLocation()).thenReturn(null);

        Snapshot snapshot = SnapshotBuilder.build(client, 0L);

        assertNull(snapshot.worldPoint);
        assertNotNull(snapshot.hitpoints);
        assertEquals(30, snapshot.hitpoints.current);
        assertEquals(40, snapshot.hitpoints.max);
        assertNotNull(snapshot.prayer);
        assertEquals(5, snapshot.prayer.current);
        assertEquals(20, snapshot.prayer.max);
        assertEquals(Integer.valueOf(50), snapshot.runEnergy);
    }

    @Test
    public void carriesTheActiveProfile() {
        assertEquals("RuneColor - X",
                SnapshotBuilder.build(loggedInClient(), 0L, "RuneColor - X").profile);
    }

    @Test
    public void reportsTheNpcBeingFought() {
        Player player = Mockito.mock(Player.class);
        NPC goblin = Mockito.mock(NPC.class);
        Mockito.when(goblin.getName()).thenReturn("Goblin");
        Mockito.when(goblin.getHealthRatio()).thenReturn(0);
        Mockito.when(goblin.getHealthScale()).thenReturn(30);
        Mockito.when(goblin.getWorldLocation()).thenReturn(new WorldPoint(3250, 3230, 0));
        Mockito.when(player.getInteracting()).thenReturn(goblin);

        Snapshot.Target target = SnapshotBuilder.target(player);
        assertEquals("Goblin", target.name);
        assertEquals(0, target.healthRatio);
        assertEquals(30, target.healthScale);
        assertEquals(3250, target.tile.x);
        assertEquals(3230, target.tile.y);
    }

    @Test
    public void reportsNoTargetWhenNotFighting() {
        assertNull(SnapshotBuilder.target(Mockito.mock(Player.class)));
    }

    @Test
    public void listsTheInventoryWithEmptySlots() {
        Client client = Mockito.mock(Client.class);
        ItemContainer container = Mockito.mock(ItemContainer.class);
        Mockito.when(container.getItems())
                .thenReturn(new Item[] {new Item(526, 1), new Item(-1, 0)});
        Mockito.when(client.getItemContainer(InventoryID.INV)).thenReturn(container);

        List<Integer> inventory = SnapshotBuilder.inventory(client);
        assertEquals(28, inventory.size());
        assertEquals(Integer.valueOf(526), inventory.get(0));
        assertEquals(Integer.valueOf(-1), inventory.get(1));
        assertEquals(Integer.valueOf(-1), inventory.get(27));
    }

    @Test
    public void reportsNoInventoryWhenItIsNotLoaded() {
        assertNull(SnapshotBuilder.inventory(Mockito.mock(Client.class)));
    }

    private static Tile itemTile(Client client, int id, int quantity, String name,
                                 WorldPoint world) {
        Tile tile = Mockito.mock(Tile.class);
        TileItem item = Mockito.mock(TileItem.class);
        Mockito.when(item.getId()).thenReturn(id);
        Mockito.when(item.getQuantity()).thenReturn(quantity);
        Mockito.when(tile.getGroundItems()).thenReturn(Collections.singletonList(item));
        ItemLayer layer = Mockito.mock(ItemLayer.class);
        Mockito.when(layer.getCanvasLocation())
                .thenReturn(new net.runelite.api.Point(100, 50));
        Mockito.when(tile.getItemLayer()).thenReturn(layer);
        Mockito.when(tile.getWorldLocation()).thenReturn(world);
        ItemComposition composition = Mockito.mock(ItemComposition.class);
        Mockito.when(composition.getName()).thenReturn(name);
        Mockito.when(client.getItemDefinition(id)).thenReturn(composition);
        return tile;
    }

    @Test
    public void listsNearbyGroundItemsNearestFirst() {
        Client client = Mockito.mock(Client.class);
        Player player = Mockito.mock(Player.class);
        Mockito.when(player.getLocalLocation()).thenReturn(LocalPoint.fromScene(50, 50));
        Canvas canvas = Mockito.mock(Canvas.class);
        Mockito.when(canvas.getLocationOnScreen()).thenReturn(new java.awt.Point(10, 20));
        Mockito.when(client.getCanvas()).thenReturn(canvas);
        Mockito.when(client.getPlane()).thenReturn(0);
        Tile[][][] tiles = new Tile[1][104][104];
        tiles[0][48][50] = itemTile(client, 995, 25, "Coins", new WorldPoint(3248, 3230, 0));
        tiles[0][50][50] = itemTile(client, 526, 1, "Bones", new WorldPoint(3250, 3230, 0));
        Scene scene = Mockito.mock(Scene.class);
        Mockito.when(scene.getTiles()).thenReturn(tiles);
        Mockito.when(client.getScene()).thenReturn(scene);

        List<Snapshot.GroundItem> items = SnapshotBuilder.groundItems(client, player);
        assertEquals(2, items.size());
        assertEquals("Bones", items.get(0).name);
        assertEquals("Coins", items.get(1).name);
        assertEquals(25, items.get(1).quantity);
        assertEquals(3248, items.get(1).tile.x);
        assertEquals(110, items.get(0).x);
        assertEquals(70, items.get(0).y);
    }

    private static NPC npc(int index, String name, WorldPoint tile, Shape hull) {
        NPC npc = Mockito.mock(NPC.class);
        Mockito.when(npc.getIndex()).thenReturn(index);
        Mockito.when(npc.getName()).thenReturn(name);
        Mockito.when(npc.getCombatLevel()).thenReturn(2);
        Mockito.when(npc.getWorldLocation()).thenReturn(tile);
        Mockito.when(npc.getConvexHull()).thenReturn(hull);
        return npc;
    }

    @Test
    public void listsOnScreenNpcsNearestFirstAndFlagsBusyOnes() {
        Client client = Mockito.mock(Client.class);
        Player player = Mockito.mock(Player.class);
        Mockito.when(player.getWorldLocation()).thenReturn(new WorldPoint(3250, 3230, 0));
        Canvas canvas = Mockito.mock(Canvas.class);
        Mockito.when(canvas.getLocationOnScreen()).thenReturn(new java.awt.Point(10, 20));
        Mockito.when(client.getCanvas()).thenReturn(canvas);
        NPC far = npc(1, "Goblin", new WorldPoint(3254, 3230, 0), new Rectangle(90, 40, 20, 20));
        NPC near = npc(2, "Goblin", new WorldPoint(3251, 3230, 0), new Rectangle(40, 40, 20, 20));
        NPC offScreen = npc(3, "Goblin", new WorldPoint(3252, 3230, 0), null);
        NPC tooFar = npc(4, "Goblin", new WorldPoint(3270, 3230, 0), new Rectangle(0, 0, 2, 2));
        Mockito.when(near.getInteracting()).thenReturn(Mockito.mock(Player.class));
        Mockito.when(client.getNpcs()).thenReturn(Arrays.asList(far, near, offScreen, tooFar));

        List<Snapshot.Npc> npcs = SnapshotBuilder.npcs(client, player);
        assertEquals(2, npcs.size());
        assertEquals(2, npcs.get(0).index);
        assertEquals(10 + 50, npcs.get(0).x);
        assertEquals(20 + 50, npcs.get(0).y);
        assertEquals(true, npcs.get(0).busy);
        assertEquals(false, npcs.get(1).busy);
    }
}
