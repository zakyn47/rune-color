package com.runecolor.bridge;

import net.runelite.api.Client;
import net.runelite.api.GameState;
import net.runelite.api.Player;
import net.runelite.api.Skill;
import net.runelite.api.coords.WorldPoint;
import org.junit.Test;
import org.mockito.Mockito;

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
        return client;
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
}
