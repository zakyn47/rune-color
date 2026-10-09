package com.runecolor.bridge;

import java.awt.Point;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import net.runelite.api.Client;
import net.runelite.api.MenuEntry;
import net.runelite.client.util.Text;

/** The client menu, so the bot can check what a click will do without OCR. Client thread only. */
final class MenuReader {
    static final int HEADER_HEIGHT = 19;
    static final int ROW_HEIGHT = 15;

    private MenuReader() {
    }

    static Snapshot.Menu read(Client client) {
        Point origin = SnapshotBuilder.canvasOrigin(client);
        MenuEntry[] entries = client.getMenuEntries();
        if (origin == null || entries == null) {
            return null;
        }
        Snapshot.MenuEntry top = entries.length == 0
                ? null
                : entry(entries[entries.length - 1], null);
        boolean open = client.isMenuOpen();
        return new Snapshot.Menu(open, top,
                open ? rows(client, origin, entries) : Collections.emptyList());
    }

    private static List<Snapshot.MenuEntry> rows(Client client, Point origin,
                                                 MenuEntry[] entries) {
        int x = origin.x + client.getMenuX();
        int y = origin.y + client.getMenuY() + HEADER_HEIGHT;
        int width = client.getMenuWidth();
        List<Snapshot.MenuEntry> rows = new ArrayList<>(entries.length);
        for (int row = 0; row < entries.length; row++) {
            rows.add(entry(entries[entries.length - 1 - row],
                    new int[] {x, y + row * ROW_HEIGHT, width, ROW_HEIGHT}));
        }
        return rows;
    }

    private static Snapshot.MenuEntry entry(MenuEntry entry, int[] rect) {
        return new Snapshot.MenuEntry(clean(entry.getOption()), clean(entry.getTarget()), rect);
    }

    private static String clean(String text) {
        return text == null ? "" : Text.removeTags(text);
    }
}
