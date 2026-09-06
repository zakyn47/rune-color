package com.runecolor.bridge;

import net.runelite.api.Client;
import net.runelite.api.GameState;
import net.runelite.api.Player;
import net.runelite.api.Skill;
import net.runelite.api.coords.WorldPoint;
import org.junit.Test;
import org.mockito.Mockito;

import static org.junit.Assert.assertEquals;
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
        Mockito.when(client.getEnergy()).thenReturn(87);

        Snapshot snapshot = SnapshotBuilder.build(client, 1757193600123L);

        assertEquals(1, snapshot.schema);
        assertEquals(123456, snapshot.tick);
        assertEquals(1757193600123L, snapshot.sentAt);
        assertEquals("LOGGED_IN", snapshot.gameState);
        assertEquals(42, snapshot.hitpoints.current);
        assertEquals(55, snapshot.hitpoints.max);
        assertEquals(12, snapshot.prayer.current);
        assertEquals(43, snapshot.prayer.max);
        assertEquals(3222, snapshot.worldPoint.x);
        assertEquals(3218, snapshot.worldPoint.y);
        assertEquals(0, snapshot.worldPoint.plane);
    }

    @Test
    public void normalizesLegacyEnergyScale() {
        Client client = loggedInClient();
        Mockito.when(client.getEnergy()).thenReturn(87);

        assertEquals(Integer.valueOf(87), SnapshotBuilder.build(client, 0L).runEnergy);
    }

    @Test
    public void normalizesModernEnergyScale() {
        Client client = loggedInClient();
        Mockito.when(client.getEnergy()).thenReturn(8700);

        assertEquals(Integer.valueOf(87), SnapshotBuilder.build(client, 0L).runEnergy);
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
    }
}
