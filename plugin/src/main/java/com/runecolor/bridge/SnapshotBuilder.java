package com.runecolor.bridge;

import java.awt.Canvas;
import java.awt.IllegalComponentStateException;
import java.awt.Rectangle;
import java.awt.Shape;
import net.runelite.api.Client;
import net.runelite.api.Actor;
import net.runelite.api.GameObject;
import net.runelite.api.Item;
import net.runelite.api.ItemComposition;
import net.runelite.api.ItemContainer;
import net.runelite.api.ItemLayer;
import net.runelite.api.NPC;
import net.runelite.api.ObjectComposition;
import net.runelite.api.Player;
import net.runelite.api.Scene;
import net.runelite.api.Skill;
import net.runelite.api.Tile;
import net.runelite.api.TileItem;
import net.runelite.api.coords.LocalPoint;
import net.runelite.api.coords.WorldPoint;
import net.runelite.api.gameval.InventoryID;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Turns the live client into an immutable {@link Snapshot}.
 *
 * <p>This class performs no I/O and starts no threads, so it must be called on the
 * client thread, where the {@code Client} API is safe to touch.
 */
public final class SnapshotBuilder {
    public static final int SCHEMA_VERSION = 1;

    /** What {@code Actor#getAnimation()} returns when nothing is playing. */
    static final int NO_ANIMATION = -1;

    /** How many tiles from the player to look for a fire. */
    static final int FIRE_RADIUS = 3;

    /** How many tiles from the player to look for items on the ground. */
    static final int GROUND_ITEM_RADIUS = 5;

    /** The most ground items a snapshot carries, nearest first. */
    static final int MAX_GROUND_ITEMS = 10;

    /** How many tiles from the player to look for NPCs. */
    static final int NPC_RADIUS = 10;

    /** The most NPCs a snapshot carries, nearest first. */
    static final int MAX_NPCS = 10;

    static final int INVENTORY_SIZE = 28;
    static final int EMPTY_SLOT = -1;

    private SnapshotBuilder() {
    }

    public static Snapshot build(Client client, long nowMillis) {
        return build(client, nowMillis, null);
    }

    public static Snapshot build(Client client, long nowMillis, String profile) {
        String gameState = client.getGameState() == null
                ? "UNKNOWN"
                : client.getGameState().toString();

        Player player = client.getLocalPlayer();
        if (player == null) {
            return new Snapshot(SCHEMA_VERSION, client.getTickCount(), nowMillis,
                    gameState, null, null, null, null, null, null, null, profile,
                    null, null, inventory(client), null);
        }

        WorldPoint tile = player.getWorldLocation();
        int animation = player.getAnimation();
        return new Snapshot(
                SCHEMA_VERSION,
                client.getTickCount(),
                nowMillis,
                gameState,
                new Snapshot.Stat(client.getBoostedSkillLevel(Skill.HITPOINTS),
                        client.getRealSkillLevel(Skill.HITPOINTS)),
                new Snapshot.Stat(client.getBoostedSkillLevel(Skill.PRAYER),
                        client.getRealSkillLevel(Skill.PRAYER)),
                normalizeEnergy(client.getEnergy()),
                tile == null
                        ? null
                        : new Snapshot.Point(tile.getX(), tile.getY(), tile.getPlane()),
                animation,
                isIdle(player, animation),
                nearestFire(client, player),
                profile,
                target(player),
                groundItems(client, player),
                inventory(client),
                npcs(client, player));
    }

    /**
     * Find the fire closest to the player and say where to click it on screen.
     *
     * <p>The click point is the middle of the fire's clickbox, falling back to its
     * base, offset by where the canvas sits on the screen.
     *
     * @return the screen point, or null if there is no fire within
     *     {@link #FIRE_RADIUS} tiles or the canvas is not on screen
     */
    static Snapshot.ScreenPoint nearestFire(Client client, Player player) {
        java.awt.Point origin = canvasOrigin(client);
        LocalPoint here = player.getLocalLocation();
        Scene scene = client.getScene();
        if (origin == null || here == null || scene == null) {
            return null;
        }
        Tile[][] tiles = scene.getTiles()[client.getPlane()];
        int sceneX = here.getSceneX();
        int sceneY = here.getSceneY();
        net.runelite.api.Point best = null;
        int bestDistance = Integer.MAX_VALUE;
        for (int dx = -FIRE_RADIUS; dx <= FIRE_RADIUS; dx++) {
            for (int dy = -FIRE_RADIUS; dy <= FIRE_RADIUS; dy++) {
                int x = sceneX + dx;
                int y = sceneY + dy;
                if (x < 0 || y < 0 || x >= tiles.length || y >= tiles[x].length
                        || tiles[x][y] == null) {
                    continue;
                }
                int distance = Math.max(Math.abs(dx), Math.abs(dy));
                for (GameObject object : tiles[x][y].getGameObjects()) {
                    if (object == null || distance >= bestDistance
                            || !isFire(client, object.getId())) {
                        continue;
                    }
                    net.runelite.api.Point point = clickPoint(object);
                    if (point != null) {
                        best = point;
                        bestDistance = distance;
                    }
                }
            }
        }
        return best == null
                ? null
                : new Snapshot.ScreenPoint(origin.x + best.getX(), origin.y + best.getY());
    }

    /** Where the canvas sits on the screen, or null when it is not showing. */
    static java.awt.Point canvasOrigin(Client client) {
        Canvas canvas = client.getCanvas();
        if (canvas == null) {
            return null;
        }
        try {
            return canvas.getLocationOnScreen();
        } catch (IllegalComponentStateException e) {
            return null;  // Minimized, or not shown yet.
        }
    }

    /** The NPC the player is interacting with, or null for none or a player. */
    static Snapshot.Target target(Player player) {
        Actor other = player.getInteracting();
        if (!(other instanceof NPC)) {
            return null;
        }
        WorldPoint tile = other.getWorldLocation();
        return new Snapshot.Target(other.getName(), other.getHealthRatio(),
                other.getHealthScale(), tile == null ? null : point(tile));
    }

    /** The item ID in each inventory slot, or null before the inventory loads. */
    static List<Integer> inventory(Client client) {
        ItemContainer container = client.getItemContainer(InventoryID.INV);
        if (container == null) {
            return null;
        }
        Item[] items = container.getItems();
        List<Integer> ids = new ArrayList<>(INVENTORY_SIZE);
        for (int slot = 0; slot < INVENTORY_SIZE; slot++) {
            Item item = slot < items.length ? items[slot] : null;
            boolean empty = item == null || item.getId() < 0 || item.getQuantity() <= 0;
            ids.add(empty ? EMPTY_SLOT : item.getId());
        }
        return ids;
    }

    /**
     * List the items on the ground near the player, nearest first.
     *
     * @return up to {@link #MAX_GROUND_ITEMS} items within {@link #GROUND_ITEM_RADIUS}
     *     tiles, or null if the canvas is not on screen
     */
    static List<Snapshot.GroundItem> groundItems(Client client, Player player) {
        java.awt.Point origin = canvasOrigin(client);
        LocalPoint here = player.getLocalLocation();
        Scene scene = client.getScene();
        if (origin == null || here == null || scene == null) {
            return null;
        }
        Tile[][] tiles = scene.getTiles()[client.getPlane()];
        List<Nearby<Snapshot.GroundItem>> nearby = new ArrayList<>();
        for (int dx = -GROUND_ITEM_RADIUS; dx <= GROUND_ITEM_RADIUS; dx++) {
            for (int dy = -GROUND_ITEM_RADIUS; dy <= GROUND_ITEM_RADIUS; dy++) {
                int x = here.getSceneX() + dx;
                int y = here.getSceneY() + dy;
                if (x < 0 || y < 0 || x >= tiles.length || y >= tiles[x].length
                        || tiles[x][y] == null) {
                    continue;
                }
                int distance = Math.max(Math.abs(dx), Math.abs(dy));
                addItems(client, tiles[x][y], origin, distance, nearby);
            }
        }
        return nearestFirst(nearby, MAX_GROUND_ITEMS);
    }

    /**
     * List the NPCs near the player that are on screen, nearest first.
     *
     * @return up to {@link #MAX_NPCS} NPCs within {@link #NPC_RADIUS} tiles, or null
     *     if the canvas is not on screen
     */
    static List<Snapshot.Npc> npcs(Client client, Player player) {
        java.awt.Point origin = canvasOrigin(client);
        WorldPoint here = player.getWorldLocation();
        if (origin == null || here == null) {
            return null;
        }
        List<Nearby<Snapshot.Npc>> nearby = new ArrayList<>();
        for (NPC npc : client.getNpcs()) {
            WorldPoint tile = npc == null ? null : npc.getWorldLocation();
            Shape hull = npc == null ? null : npc.getConvexHull();
            if (tile == null || hull == null || tile.getPlane() != here.getPlane()) {
                continue;  // Gone, or off screen.
            }
            int distance = Math.max(Math.abs(tile.getX() - here.getX()),
                    Math.abs(tile.getY() - here.getY()));
            if (distance > NPC_RADIUS) {
                continue;
            }
            Rectangle bounds = hull.getBounds();
            Actor other = npc.getInteracting();
            boolean busy = other != null && other != player;
            nearby.add(new Nearby<>(distance, new Snapshot.Npc(npc.getIndex(),
                    npc.getName(), npc.getCombatLevel(), point(tile),
                    origin.x + (int) bounds.getCenterX(),
                    origin.y + (int) bounds.getCenterY(), busy)));
        }
        return nearestFirst(nearby, MAX_NPCS);
    }

    private static <T> List<T> nearestFirst(List<Nearby<T>> nearby, int max) {
        nearby.sort(Comparator.comparingInt(n -> n.distance));
        List<T> nearest = new ArrayList<>();
        for (Nearby<T> n : nearby.subList(0, Math.min(max, nearby.size()))) {
            nearest.add(n.value);
        }
        return nearest;
    }

    private static void addItems(Client client, Tile tile, java.awt.Point origin,
                                 int distance, List<Nearby<Snapshot.GroundItem>> into) {
        List<TileItem> items = tile.getGroundItems();
        ItemLayer layer = tile.getItemLayer();
        net.runelite.api.Point canvasPoint = layer == null ? null : layer.getCanvasLocation();
        if (items == null || canvasPoint == null) {
            return;
        }
        for (TileItem item : items) {
            into.add(new Nearby<>(distance, new Snapshot.GroundItem(item.getId(),
                    itemName(client, item.getId()), item.getQuantity(),
                    point(tile.getWorldLocation()),
                    origin.x + canvasPoint.getX(), origin.y + canvasPoint.getY())));
        }
    }

    private static String itemName(Client client, int id) {
        ItemComposition composition = client.getItemDefinition(id);
        return composition == null ? null : composition.getName();
    }

    private static Snapshot.Point point(WorldPoint tile) {
        return new Snapshot.Point(tile.getX(), tile.getY(), tile.getPlane());
    }

    /** Something near the player, with its distance, for sorting. */
    private static final class Nearby<T> {
        final int distance;
        final T value;

        Nearby(int distance, T value) {
            this.distance = distance;
            this.value = value;
        }
    }

    private static net.runelite.api.Point clickPoint(GameObject object) {
        Shape clickbox = object.getClickbox();
        if (clickbox != null) {
            Rectangle bounds = clickbox.getBounds();
            return new net.runelite.api.Point((int) bounds.getCenterX(),
                    (int) bounds.getCenterY());
        }
        return object.getCanvasLocation();
    }

    /** Whether an object is a fire, including one that has become a campfire. */
    static boolean isFire(Client client, int objectId) {
        ObjectComposition composition = client.getObjectDefinition(objectId);
        if (composition != null && composition.getImpostorIds() != null) {
            composition = composition.getImpostor();
        }
        if (composition == null || composition.getName() == null) {
            return false;
        }
        String name = composition.getName();
        return name.equalsIgnoreCase("Fire") || name.equalsIgnoreCase("Forester's campfire");
    }

    /**
     * Whether the player is doing nothing.
     *
     * <p>An animation covers chopping, lighting fires and every other action; the
     * pose animation covers walking and running, which play no action animation. The
     * player is idle only when neither is happening.
     */
    static boolean isIdle(Player player, int animation) {
        return animation == NO_ANIMATION
                && player.getPoseAnimation() == player.getIdlePoseAnimation();
    }

    /**
     * Normalize run energy to 0-100.
     *
     * <p><b>Evidence:</b> the javadoc on {@code Client#getEnergy()} in
     * {@code runelite-api-1.12.38-sources.jar!/net/runelite/api/Client.java} (fetched
     * from {@code https://repo.runelite.net/net/runelite/runelite-api/1.12.38/
     * runelite-api-1.12.38-sources.jar} since the Gradle cache only held the binary
     * jar) reads verbatim:
     *
     * <pre>
     * /**
     *  * Gets the current run energy of the logged in player.
     *  *
     *  * &#64;return the run energy in units of 1/100th of an percentage
     *  *&#47;
     * int getEnergy();
     * </pre>
     *
     * <p>So in the 1.12.38 API this class compiles and tests against, {@code
     * getEnergy()} is <em>always</em> on a 0-10000 scale, one unit being one
     * hundredth of one percent. There is no reachable 0-100 "legacy" scale to guess
     * at through this interface in this version, so the conversion is a single fixed
     * division by 100 &mdash; not a value-dependent heuristic. (The brief's original
     * {@code raw > 100 ? raw / 100 : raw} guess is wrong for low readings: a
     * just-drained {@code raw = 50}, i.e. 0.5% energy, would be reported as 50%.)
     *
     * <p>If a future RuneLite version changes this scale, that must be re-verified
     * from that version's own sources the same way, not assumed.
     */
    static int normalizeEnergy(int raw) {
        int percent = raw / 100;
        return Math.max(0, Math.min(100, percent));
    }
}
