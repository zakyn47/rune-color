package com.runecolor.bridge;

import com.google.gson.Gson;
import com.google.gson.JsonParser;
import org.junit.Test;

import java.nio.charset.StandardCharsets;
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
        Snapshot snapshot = new Snapshot(1, 123456, 1757193600123L, "LOGGED_IN",
                new Snapshot.Stat(42, 55), new Snapshot.Stat(12, 43), 87,
                new Snapshot.Point(3222, 3218, 0), 879, false,
                new Snapshot.ScreenPoint(512, 300), "RuneColor - Test");

        Path fixture = Paths.get("..", "tests", "fixtures", "snapshot_v1.json");
        String expected = new String(Files.readAllBytes(fixture), StandardCharsets.UTF_8);

        // RuneLite bundles a Gson older than 2.8.6, where JsonParser.parseString
        // does not exist yet, so parse through an instance.
        JsonParser parser = new JsonParser();
        assertEquals(parser.parse(expected),
                parser.parse(new Gson().toJson(snapshot)));
    }
}
