package com.runecolor.bridge;

import com.google.gson.Gson;
import com.google.gson.JsonParser;
import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import static org.junit.Assert.assertEquals;

/**
 * Pins the wire format.
 *
 * <p>The Python side tests against this same file, so a change here that is not
 * mirrored there fails one of the two suites instead of failing silently in a live
 * run.
 */
public class SnapshotFixtureTest {
    @Test
    public void serializesToTheSharedFixture() throws Exception {
        Snapshot snapshot = new Snapshot(2, 123456, 1757193600123L, "LOGGED_IN",
                new Snapshot.Stat(42, 55), new Snapshot.Stat(12, 43), 87,
                new Snapshot.Point(3222, 3218, 0), 879, false,
                new Snapshot.ScreenPoint(512, 300), "RuneColor - Test",
                new Snapshot.Target("Goblin", 12, 30, new Snapshot.Point(3250, 3230, 0)),
                Collections.singletonList(new Snapshot.GroundItem(526, "Bones", 1,
                        new Snapshot.Point(3250, 3230, 0), 600, 410)),
                inventory(),
                Collections.singletonList(new Snapshot.Npc(17, "Goblin", 2,
                        new Snapshot.Point(3251, 3231, 0), 640, 380, false)),
                Collections.singletonList(new Snapshot.SceneObject(11361,
                        new Snapshot.Point(3229, 3148, 0), 2, Arrays.asList(
                                new int[] {812, 401}, new int[] {840, 398},
                                new int[] {851, 430}))),
                slots(),
                new Snapshot.Menu(true, new Snapshot.MenuEntry("Mine", "Tin rocks", null),
                        Arrays.asList(
                                new Snapshot.MenuEntry("Mine", "Tin rocks",
                                        new int[] {280, 99, 120, 15}),
                                new Snapshot.MenuEntry("Cancel", "",
                                        new int[] {280, 114, 120, 15}))));

        Path fixture = Paths.get("..", "tests", "fixtures", "snapshot_v2.json");
        String expected = new String(Files.readAllBytes(fixture), StandardCharsets.UTF_8);

        // RuneLite bundles a Gson older than 2.8.6, where JsonParser.parseString
        // does not exist yet, so parse through an instance.
        JsonParser parser = new JsonParser();
        assertEquals(parser.parse(expected),
                parser.parse(new Gson().toJson(snapshot)));
    }

    private static List<Integer> inventory() {
        List<Integer> ids = new ArrayList<>(Collections.nCopies(28, -1));
        ids.set(0, 995);
        return ids;
    }

    private static List<int[]> slots() {
        List<int[]> rects = new ArrayList<>();
        for (int i = 0; i < 28; i++) {
            rects.add(new int[] {560 + 42 * (i % 4), 210 + 36 * (i / 4), 36, 32});
        }
        return rects;
    }
}
