package com.runecolor.bridge;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** An immutable, serializable picture of the player at one game tick. */
public final class Snapshot {
    public final int schema;
    public final int tick;

    @SerializedName("sent_at")
    public final long sentAt;

    @SerializedName("game_state")
    public final String gameState;

    public final Stat hitpoints;
    public final Stat prayer;

    @SerializedName("run_energy")
    public final Integer runEnergy;

    /**
     * The player's tile.
     *
     * <p>Note that inside an instance this is instance-local, not a true world
     * coordinate. Stage A runs in the overworld so it does not matter, but anything
     * reading this inside an instance must convert first.
     */
    @SerializedName("world_point")
    public final Point worldPoint;

    /** The player's current animation ID, -1 when none is playing. */
    public final Integer animation;

    /**
     * Whether the player is doing nothing: no animation playing and standing still.
     *
     * <p>This is one tick's view. Woodcutting can drop its animation for a tick
     * between swings, so a caller deciding the player has stopped should want it to
     * hold for a moment first.
     */
    public final Boolean idle;

    /**
     * Where to click the nearest fire, in screen pixels, or null if none is close.
     *
     * <p>Screen rather than canvas coordinates, so the bot needs no idea where the
     * canvas sits inside the window. Only fires within a few tiles count, which is
     * where the player's own fire ends up after lighting it.
     */
    public final ScreenPoint fire;

    /** The name of the client's active RuneLite profile, or null if unknown. */
    public final String profile;

    /** The NPC the player is fighting, or null. */
    public final Target target;

    /** Items on the ground near the player, nearest first, or null if unknown. */
    @SerializedName("ground_items")
    public final List<GroundItem> groundItems;

    /** The item ID in each of the 28 inventory slots, -1 when empty, or null. */
    public final List<Integer> inventory;

    /** NPCs near the player and on screen, nearest first, or null if unknown. */
    public final List<Npc> npcs;

    Snapshot(int schema, int tick, long sentAt, String gameState, Stat hitpoints,
             Stat prayer, Integer runEnergy, Point worldPoint, Integer animation,
             Boolean idle, ScreenPoint fire, String profile, Target target,
             List<GroundItem> groundItems, List<Integer> inventory, List<Npc> npcs) {
        this.schema = schema;
        this.tick = tick;
        this.sentAt = sentAt;
        this.gameState = gameState;
        this.hitpoints = hitpoints;
        this.prayer = prayer;
        this.runEnergy = runEnergy;
        this.worldPoint = worldPoint;
        this.animation = animation;
        this.idle = idle;
        this.fire = fire;
        this.profile = profile;
        this.target = target;
        this.groundItems = groundItems;
        this.inventory = inventory;
        this.npcs = npcs;
    }

    /** A current and maximum pair, as the orbs show them. */
    public static final class Stat {
        public final int current;
        public final int max;

        Stat(int current, int max) {
            this.current = current;
            this.max = max;
        }
    }

    /** A point on the screen, in pixels. */
    public static final class ScreenPoint {
        public final int x;
        public final int y;

        ScreenPoint(int x, int y) {
            this.x = x;
            this.y = y;
        }
    }

    /** A tile coordinate. */
    public static final class Point {
        public final int x;
        public final int y;
        public final int plane;

        Point(int x, int y, int plane) {
            this.x = x;
            this.y = y;
            this.plane = plane;
        }
    }

    /** The NPC being fought: its health bar as the game draws it, and its tile. */
    public static final class Target {
        public final String name;

        /** -1 while no health bar is showing. */
        @SerializedName("health_ratio")
        public final int healthRatio;

        @SerializedName("health_scale")
        public final int healthScale;

        public final Point tile;

        Target(String name, int healthRatio, int healthScale, Point tile) {
            this.name = name;
            this.healthRatio = healthRatio;
            this.healthScale = healthScale;
            this.tile = tile;
        }
    }

    /** An item on the ground, with the screen point to click to take it. */
    public static final class GroundItem {
        public final int id;
        public final String name;
        public final int quantity;
        public final Point tile;
        public final int x;
        public final int y;

        GroundItem(int id, String name, int quantity, Point tile, int x, int y) {
            this.id = id;
            this.name = name;
            this.quantity = quantity;
            this.tile = tile;
            this.x = x;
            this.y = y;
        }
    }

    /**
     * An NPC near the player, with the screen point to click it.
     *
     * <p>The index identifies the same NPC from one snapshot to the next, so a
     * moving NPC can be followed while the cursor travels to it.
     */
    public static final class Npc {
        public final int index;
        public final String name;
        public final int level;
        public final Point tile;
        public final int x;
        public final int y;

        /** Whether it is fighting someone other than the player. */
        public final boolean busy;

        Npc(int index, String name, int level, Point tile, int x, int y, boolean busy) {
            this.index = index;
            this.name = name;
            this.level = level;
            this.tile = tile;
            this.x = x;
            this.y = y;
            this.busy = busy;
        }
    }
}
