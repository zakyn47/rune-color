package com.runecolor.bridge;

import java.awt.Canvas;
import net.runelite.api.Client;
import net.runelite.api.MenuEntry;
import org.junit.Test;
import org.mockito.Mockito;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

public class MenuReaderTest {
    private final Client client = Mockito.mock(Client.class);

    public MenuReaderTest() {
        Canvas canvas = Mockito.mock(Canvas.class);
        Mockito.when(canvas.getLocationOnScreen()).thenReturn(new java.awt.Point(180, 30));
        Mockito.when(client.getCanvas()).thenReturn(canvas);
        // The client lists entries bottom-up: the last one is the top row.
        MenuEntry cancel = entry("Cancel", "");
        MenuEntry walkHere = entry("Walk here", "");
        MenuEntry mine = entry("<col=ffffff>Mine", "<col=ffff>Tin rocks");
        Mockito.when(client.getMenuEntries()).thenReturn(new MenuEntry[] {cancel, walkHere, mine});
    }

    private static MenuEntry entry(String option, String target) {
        MenuEntry entry = Mockito.mock(MenuEntry.class);
        Mockito.when(entry.getOption()).thenReturn(option);
        Mockito.when(entry.getTarget()).thenReturn(target);
        return entry;
    }

    @Test
    public void aClosedMenuReportsOnlyTheHoverEntry() {
        Snapshot.Menu menu = MenuReader.read(client);
        assertFalse(menu.open);
        assertEquals("Mine", menu.top.option);
        assertEquals("Tin rocks", menu.top.target);
        assertNull(menu.top.rect);
        assertTrue(menu.entries.isEmpty());
    }

    @Test
    public void anOpenMenuReportsItsRowsTopFirst() {
        Mockito.when(client.isMenuOpen()).thenReturn(true);
        Mockito.when(client.getMenuX()).thenReturn(100);
        Mockito.when(client.getMenuY()).thenReturn(50);
        Mockito.when(client.getMenuWidth()).thenReturn(120);
        Snapshot.Menu menu = MenuReader.read(client);
        assertTrue(menu.open);
        assertEquals(3, menu.entries.size());
        assertEquals("Mine", menu.entries.get(0).option);
        assertArrayEquals(new int[] {280, 99, 120, 15}, menu.entries.get(0).rect);
        assertEquals("Cancel", menu.entries.get(2).option);
        assertArrayEquals(new int[] {280, 129, 120, 15}, menu.entries.get(2).rect);
    }

    @Test
    public void noEntriesMeansNoTop() {
        Mockito.when(client.getMenuEntries()).thenReturn(new MenuEntry[0]);
        assertNull(MenuReader.read(client).top);
    }
}
