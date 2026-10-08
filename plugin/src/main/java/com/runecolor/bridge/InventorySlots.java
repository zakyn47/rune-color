package com.runecolor.bridge;

import java.awt.Point;
import java.awt.Rectangle;
import java.util.ArrayList;
import java.util.List;
import net.runelite.api.Client;
import net.runelite.api.gameval.InterfaceID;
import net.runelite.api.widgets.Widget;

/** Where each inventory slot is on screen. Client thread only. */
final class InventorySlots {
    private InventorySlots() {
    }

    static List<int[]> read(Client client) {
        Point origin = SnapshotBuilder.canvasOrigin(client);
        Widget items = client.getWidget(InterfaceID.Inventory.ITEMS);
        if (origin == null || items == null || items.isHidden()) {
            return null;
        }
        Widget[] slots = items.getDynamicChildren();
        if (slots == null || slots.length < SnapshotBuilder.INVENTORY_SIZE) {
            return null;
        }
        List<int[]> rects = new ArrayList<>(SnapshotBuilder.INVENTORY_SIZE);
        for (int i = 0; i < SnapshotBuilder.INVENTORY_SIZE; i++) {
            Rectangle bounds = slots[i].getBounds();
            rects.add(new int[] {origin.x + bounds.x, origin.y + bounds.y,
                    bounds.width, bounds.height});
        }
        return rects;
    }
}
