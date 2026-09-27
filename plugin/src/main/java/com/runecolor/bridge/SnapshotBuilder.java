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
