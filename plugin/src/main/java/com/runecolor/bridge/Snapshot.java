package com.runecolor.bridge;

import com.google.gson.annotations.SerializedName;

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

    Snapshot(int schema, int tick, long sentAt, String gameState, Stat hitpoints,
             Stat prayer, Integer runEnergy, Point worldPoint) {
        this.schema = schema;
        this.tick = tick;
        this.sentAt = sentAt;
        this.gameState = gameState;
        this.hitpoints = hitpoints;
        this.prayer = prayer;
        this.runEnergy = runEnergy;
        this.worldPoint = worldPoint;
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
}
