package com.runecolor.bridge;

import java.awt.Canvas;
import java.awt.Rectangle;
import java.util.List;
import net.runelite.api.Client;
import net.runelite.api.gameval.InterfaceID;
import net.runelite.api.widgets.Widget;
import org.junit.Test;
import org.mockito.Mockito;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

public class InventorySlotsTest {
    private final Client client = Mockito.mock(Client.class);
    private final Widget items = Mockito.mock(Widget.class);

    public InventorySlotsTest() {
        Canvas canvas = Mockito.mock(Canvas.class);
        Mockito.when(canvas.getLocationOnScreen()).thenReturn(new java.awt.Point(180, 30));
        Mockito.when(client.getCanvas()).thenReturn(canvas);
        Mockito.when(client.getWidget(InterfaceID.Inventory.ITEMS)).thenReturn(items);
        Mockito.when(items.getBounds()).thenReturn(new Rectangle(560, 210, 168, 252));
    }

    @Test
    public void reportsEverySlotOnScreen() {
        List<int[]> rects = InventorySlots.read(client);
        assertEquals(28, rects.size());
        assertArrayEquals(new int[] {756, 248, 36, 32}, rects.get(0));
        assertArrayEquals(new int[] {756 + 42 * 3, 248 + 36 * 6, 36, 32}, rects.get(27));
    }

    @Test
    public void unknownWhileTheInventoryIsHidden() {
        Mockito.when(items.isHidden()).thenReturn(true);
        assertNull(InventorySlots.read(client));
    }

    @Test
    public void unknownWithoutTheWidget() {
        Mockito.when(client.getWidget(InterfaceID.Inventory.ITEMS)).thenReturn(null);
        assertNull(InventorySlots.read(client));
    }
}
