package com.runecolor.bridge;

import net.runelite.api.Client;
import net.runelite.api.Player;
import net.runelite.api.Skill;
import net.runelite.api.coords.WorldPoint;

/**
 * Turns the live client into an immutable {@link Snapshot}.
 *
 * <p>This class performs no I/O and starts no threads, so it must be called on the
 * client thread, where the {@code Client} API is safe to touch.
 */
public final class SnapshotBuilder {
    public static final int SCHEMA_VERSION = 1;

    private SnapshotBuilder() {
    }

    public static Snapshot build(Client client, long nowMillis) {
        String gameState = client.getGameState() == null
                ? "UNKNOWN"
                : client.getGameState().toString();

        Player player = client.getLocalPlayer();
        if (player == null) {
            return new Snapshot(SCHEMA_VERSION, client.getTickCount(), nowMillis,
                    gameState, null, null, null, null);
        }

        WorldPoint tile = player.getWorldLocation();
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
                        : new Snapshot.Point(tile.getX(), tile.getY(), tile.getPlane()));
    }

    /**
     * Normalize run energy to 0-100.
     *
     * <p>{@code getEnergy()} returned 0-100 in older clients and 0-10000 in newer
     * ones. Normalizing here keeps the scale question out of Python entirely.
     */
    static int normalizeEnergy(int raw) {
        int percent = raw > 100 ? raw / 100 : raw;
        return Math.max(0, Math.min(100, percent));
    }
}
