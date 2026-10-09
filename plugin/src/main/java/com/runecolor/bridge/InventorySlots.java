package com.runecolor.bridge;

import java.awt.Point;
import java.awt.Rectangle;
import java.util.ArrayList;
import java.util.List;
import net.runelite.api.Client;
import net.runelite.api.gameval.InterfaceID;
import net.runelite.api.widgets.Widget;

/**
 * Where each inventory slot is on screen. Client thread only.
 *
 * <p>An empty slot's own widget reports its bounds as (0, 0), so slots can't be
 * read from the dynamic children. Instead the grid is laid out from the
 * container widget's own bounds, which is always correct.
 *
 * <p>The slots sit inset from the container's own bounds; the offset was
 * measured live in Resizable-Classic layout.
 */
final class InventorySlots {
    private static final int COLUMNS = 4;
    private static final int SLOT_X_STEP = 42;
    private static final int SLOT_Y_STEP = 36;
    private static final int SLOT_WIDTH = 36;
    private static final int SLOT_HEIGHT = 32;
    private static final int GRID_OFFSET_X = 16;
    private static final int GRID_OFFSET_Y = 8;

    private InventorySlots() {
    }

    static List<int[]> read(Client client) {
        Point origin = SnapshotBuilder.canvasOrigin(client);
        Widget items = client.getWidget(InterfaceID.Inventory.ITEMS);
        if (origin == null || items == null || items.isHidden()) {
            return null;
        }
        Rectangle bounds = items.getBounds();
        int x0 = origin.x + bounds.x + GRID_OFFSET_X;
        int y0 = origin.y + bounds.y + GRID_OFFSET_Y;
        List<int[]> rects = new ArrayList<>(SnapshotBuilder.INVENTORY_SIZE);
        for (int i = 0; i < SnapshotBuilder.INVENTORY_SIZE; i++) {
            rects.add(new int[] {x0 + SLOT_X_STEP * (i % COLUMNS),
                    y0 + SLOT_Y_STEP * (i / COLUMNS), SLOT_WIDTH, SLOT_HEIGHT});
        }
        return rects;
    }
}
