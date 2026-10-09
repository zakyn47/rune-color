# Bridge Scene Targets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The RuneColor Bridge plug-in reports requested game objects (as clickbox outlines), inventory slot rectangles and the client menu, and the Power Miner uses them instead of colour markers, template slots and mouseover OCR.

**Architecture:** The bot names the object IDs it wants in its reply to each snapshot. Small single-purpose Java classes build three new snapshot fields on the client thread. Python parses them into dataclasses, and a new `Polygon` gives a random point inside each outline. Python still moves the real mouse.

**Tech Stack:** Java 11 + RuneLite API 1.12.38, JUnit 4 + Mockito (plug-in); Python 3.10, Flask, unittest (bot).

**Spec:** `docs/superpowers/specs/2026-10-08-bridge-scene-targets-design.md`

## Global Constraints

- `SCHEMA_VERSION` becomes `2` in `SnapshotBuilder.java` and `bridge_api.py`, in the same change set.
- JSON keys are snake_case, as in the existing snapshot: `objects`, `inventory_slots`, `menu`.
- All coordinates are screen pixels with the canvas origin added.
- Objects: `GameObject`s only, within 15 tiles, nearest first (Chebyshev), at most 10, hull of 3 to 20 points.
- `inventory_slots`: exactly 28 `[x, y, w, h]` or null.
- The plug-in never clicks or invokes menu actions.
- No new Python dependencies. No `Any` types.
- Only comment on *why*, never on what. Match surrounding naming.
- Ask the user before every `git commit`. Never add `Co-Authored-By` or `Claude-Session` lines.

## Commands

- Java tests: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon`
- Java single test class: append `--tests com.runecolor.bridge.<Class>`
- Python tests: `venv/Scripts/python -m unittest discover -s tests/unit -t . -v`
- Python single module: `venv/Scripts/python -m unittest tests.unit.<module> -v`
- Lint: `venv/Scripts/flake8 --max-line-length 88 <changed .py files>` and `venv/Scripts/black --check <changed .py files>`

## File Map

| File | Change |
|---|---|
| `plugin/.../BotReply.java` | Create: parse a reply into profile and object IDs |
| `plugin/.../ObjectRequest.java` | Create: the latest requested ID set, shared across threads |
| `plugin/.../ProfileSwitcher.java` | Modify: take a `ProfileRequest`, stop parsing JSON |
| `plugin/.../HullOutline.java` | Create: `Shape` → short screen polygon |
| `plugin/.../ObjectScanner.java` | Create: find requested `GameObject`s near the player |
| `plugin/.../InventorySlots.java` | Create: 28 slot rects from the inventory widget |
| `plugin/.../MenuReader.java` | Create: top entry and open-menu rows |
| `plugin/.../Snapshot.java` | Modify: `SceneObject`, `MenuEntry`, `Menu`, three fields |
| `plugin/.../SnapshotBuilder.java` | Modify: schema 2, wire the new readers, share helpers |
| `plugin/.../RuneColorBridgePlugin.java` | Modify: dispatch replies, pass the ID set to `build` |
| `tests/fixtures/snapshot_v1.json` → `snapshot_v2.json` | Rename + new fields |
| `src/utilities/geometry.py` | Modify: add `Polygon` |
| `src/utilities/api/bridge_api.py` | Modify: schema 2, new dataclasses, properties, `request_objects` |
| `src/model/runelite_bot.py` | Modify: `move_to_scene_object`, `wait_for_hover_text`, `drop_items(rects=)` |
| `src/model/osrs/power_miner_rules.py` | Modify: `Ore.rock_ids` |
| `src/model/osrs/power_miner.py` | Modify: use the bridge targets, drop colour/OCR |
| `src/profiles/power_miner.properties` | Modify: remove the two `objectindicators.region_*` lines |

`plugin/...` = `plugin/src/main/java/com/runecolor/bridge`. Tests mirror it under `plugin/src/test/java/com/runecolor/bridge`.

---

### Task 1: Reply parsing and the object request

**Files:**
- Create: `plugin/src/main/java/com/runecolor/bridge/BotReply.java`
- Create: `plugin/src/main/java/com/runecolor/bridge/ObjectRequest.java`
- Modify: `plugin/src/main/java/com/runecolor/bridge/ProfileSwitcher.java`
- Modify: `plugin/src/main/java/com/runecolor/bridge/RuneColorBridgePlugin.java:84-91`
- Modify: `plugin/src/test/java/com/runecolor/bridge/ProfileSwitcherTest.java`
- Test: `plugin/src/test/java/com/runecolor/bridge/BotReplyTest.java`

**Interfaces:**
- Produces: `BotReply.parse(Gson, String) -> BotReply` with `ProfileRequest profile` (nullable) and `Set<Integer> objects` (never null). `ObjectRequest.update(BotReply)`, `ObjectRequest.ids() -> Set<Integer>`. `ProfileSwitcher(ProfileStore, Executor)` and `ProfileSwitcher.onProfile(ProfileRequest)`. Plug-in field `objectRequest` (used in Task 5).

- [ ] **Step 1: Write the failing test** `BotReplyTest.java`

```java
package com.runecolor.bridge;

import com.google.gson.Gson;
import org.junit.Test;

import java.util.Arrays;
import java.util.HashSet;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

public class BotReplyTest {
    private static BotReply parse(String body) {
        return BotReply.parse(new Gson(), body);
    }

    @Test
    public void readsTheProfileAndObjects() {
        BotReply reply = parse("{\"profile\":{\"name\":\"X\",\"path\":\"p\"},"
                + "\"objects\":[11361,11360,11361]}");
        assertEquals("X", reply.profile.name);
        assertEquals(new HashSet<>(Arrays.asList(11360, 11361)), reply.objects);
    }

    @Test
    public void missingObjectsMeansNone() {
        assertTrue(parse("{\"profile\":null}").objects.isEmpty());
    }

    @Test
    public void malformedBodyAsksForNothing() {
        BotReply reply = parse("Snapshot received.");
        assertNull(reply.profile);
        assertTrue(reply.objects.isEmpty());
    }

    @Test
    public void malformedObjectsAsksForNothing() {
        assertTrue(parse("{\"objects\":[\"rock\"]}").objects.isEmpty());
    }

    @Test
    public void theRequestHoldsTheLatestReply() {
        ObjectRequest request = new ObjectRequest();
        assertTrue(request.ids().isEmpty());
        request.update(parse("{\"objects\":[11361]}"));
        assertEquals(new HashSet<>(Arrays.asList(11361)), request.ids());
        request.update(parse("{}"));
        assertTrue(request.ids().isEmpty());
    }
}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon --tests com.runecolor.bridge.BotReplyTest`
Expected: compilation FAIL, `cannot find symbol: class BotReply`

- [ ] **Step 3: Implement `BotReply` and `ObjectRequest`**

```java
package com.runecolor.bridge;

import com.google.gson.Gson;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** The bot's reply to a snapshot: the profile it wants and the objects to report. */
public final class BotReply {
    static final BotReply EMPTY = new BotReply(null, Collections.emptySet());

    public final ProfileRequest profile;
    public final Set<Integer> objects;

    BotReply(ProfileRequest profile, Set<Integer> objects) {
        this.profile = profile;
        this.objects = objects;
    }

    /** Never throws: it runs on the publisher thread. Anything unreadable asks for nothing. */
    static BotReply parse(Gson gson, String body) {
        Wire wire;
        try {
            wire = gson.fromJson(body, Wire.class);
        } catch (RuntimeException e) {
            return EMPTY;
        }
        if (wire == null) {
            return EMPTY;
        }
        return new BotReply(wire.profile, ids(wire.objects));
    }

    private static Set<Integer> ids(List<Integer> objects) {
        if (objects == null) {
            return Collections.emptySet();
        }
        Set<Integer> ids = new HashSet<>();
        for (Integer id : objects) {
            if (id != null) {
                ids.add(id);
            }
        }
        return Collections.unmodifiableSet(ids);
    }

    private static final class Wire {
        ProfileRequest profile;
        List<Integer> objects;
    }
}
```

```java
package com.runecolor.bridge;

import java.util.Collections;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

/**
 * The object IDs the bot last asked for.
 *
 * <p>Written on the publisher thread when a reply arrives, read on the client thread
 * when the next snapshot is built.
 */
public final class ObjectRequest {
    private final AtomicReference<Set<Integer>> ids =
            new AtomicReference<>(Collections.emptySet());

    void update(BotReply reply) {
        ids.set(reply.objects);
    }

    Set<Integer> ids() {
        return ids.get();
    }
}
```

- [ ] **Step 4: Make `ProfileSwitcher` take a parsed request**

In `ProfileSwitcher.java`: remove the `gson` field, the `Gson` constructor parameter, the `parse` method, the `Reply` class and the `com.google.gson.Gson` import. Rename `onReply(String body)` to `onProfile(ProfileRequest wanted)` and delete its first line (`ProfileRequest wanted = parse(body);`). Update its javadoc to "Act on the profile one reply asked for. Never throws: it runs on the publisher thread."

In `ProfileSwitcherTest.java`, add this helper and rewrite every call:

```java
    private static ProfileRequest wanted(String body) {
        return BotReply.parse(new Gson(), body).profile;
    }
```

- `new ProfileSwitcher(store, X, new Gson())` → `new ProfileSwitcher(store, X)`
- `.onReply(BODY)` → `.onProfile(wanted(BODY))`

- [ ] **Step 5: Wire the plug-in**

In `RuneColorBridgePlugin.java`, add a field `private final ObjectRequest objectRequest = new ObjectRequest();` next to `profileStore`. In `startUp()`, replace the switcher and publisher construction with:

```java
        ProfileSwitcher switcher = new ProfileSwitcher(profileStore, profileExecutor);
        publisher = new SnapshotPublisher(http, gson,
                "http://127.0.0.1:" + config.port() + "/api/snapshot/",
                body -> {
                    BotReply reply = BotReply.parse(gson, body);
                    switcher.onProfile(reply.profile);
                    objectRequest.update(reply);
                });
```

- [ ] **Step 6: Run all Java tests**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon`
Expected: all PASS, including `BotReplyTest` and `ProfileSwitcherTest`.

- [ ] **Step 7: Commit (ask the user first)**

```bash
git add plugin/src
git commit -m "Parse bot replies once and keep the requested object IDs"
```

---

### Task 2: Clickbox outlines

**Files:**
- Create: `plugin/src/main/java/com/runecolor/bridge/HullOutline.java`
- Test: `plugin/src/test/java/com/runecolor/bridge/HullOutlineTest.java`

**Interfaces:**
- Produces: `HullOutline.of(Shape shape, java.awt.Point origin) -> List<int[]>` (screen `[x, y]` points, 3 to `HullOutline.MAX_POINTS` = 20, or null).

- [ ] **Step 1: Write the failing test**

```java
package com.runecolor.bridge;

import org.junit.Test;

import java.awt.Point;
import java.awt.Rectangle;
import java.awt.geom.Ellipse2D;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

public class HullOutlineTest {
    private static final Point ORIGIN = new Point(180, 30);

    private static boolean has(List<int[]> outline, int x, int y) {
        return outline.stream().anyMatch(p -> p[0] == x && p[1] == y);
    }

    @Test
    public void aRectangleBecomesItsCornersOnScreen() {
        List<int[]> outline = HullOutline.of(new Rectangle(290, 180, 20, 40), ORIGIN);
        assertEquals(4, outline.size());
        assertTrue(has(outline, 470, 210));
        assertTrue(has(outline, 490, 210));
        assertTrue(has(outline, 490, 250));
        assertTrue(has(outline, 470, 250));
    }

    @Test
    public void aRoundShapeIsCappedAndStaysInBounds() {
        List<int[]> outline = HullOutline.of(new Ellipse2D.Double(0, 0, 300, 200), ORIGIN);
        assertTrue(outline.size() >= 3);
        assertTrue(outline.size() <= HullOutline.MAX_POINTS);
        for (int[] p : outline) {
            assertTrue(p[0] >= 180 && p[0] <= 480);
            assertTrue(p[1] >= 30 && p[1] <= 230);
        }
    }

    @Test
    public void nothingToOutlineGivesNull() {
        assertNull(HullOutline.of(null, ORIGIN));
        assertNull(HullOutline.of(new Rectangle(5, 5, 0, 0), ORIGIN));
        assertNull(HullOutline.of(new Rectangle(5, 5, 10, 10), null));
    }
}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon --tests com.runecolor.bridge.HullOutlineTest`
Expected: compilation FAIL, `cannot find symbol: class HullOutline`

- [ ] **Step 3: Implement**

```java
package com.runecolor.bridge;

import java.awt.Point;
import java.awt.Shape;
import java.awt.geom.PathIterator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * Turns a clickbox into a short screen-space outline.
 *
 * <p>The bot picks its own random point inside the outline, so every click lands
 * somewhere new but always on the object. A convex hull is enough for that and keeps
 * the payload small; clickboxes can have hundreds of path points.
 */
final class HullOutline {
    static final int MAX_POINTS = 20;

    private HullOutline() {
    }

    static List<int[]> of(Shape shape, Point origin) {
        if (shape == null || origin == null) {
            return null;
        }
        List<Point> hull = convexHull(flatten(shape));
        if (hull.size() < 3) {
            return null;
        }
        int step = (hull.size() + MAX_POINTS - 1) / MAX_POINTS;
        List<int[]> outline = new ArrayList<>();
        for (int i = 0; i < hull.size(); i += step) {
            Point p = hull.get(i);
            outline.add(new int[] {origin.x + p.x, origin.y + p.y});
        }
        return outline.size() < 3 ? null : outline;
    }

    private static List<Point> flatten(Shape shape) {
        List<Point> points = new ArrayList<>();
        double[] coords = new double[6];
        for (PathIterator it = shape.getPathIterator(null, 1.0); !it.isDone(); it.next()) {
            if (it.currentSegment(coords) != PathIterator.SEG_CLOSE) {
                points.add(new Point((int) Math.round(coords[0]), (int) Math.round(coords[1])));
            }
        }
        return points;
    }

    /** Andrew's monotone chain. */
    private static List<Point> convexHull(List<Point> points) {
        List<Point> sorted = new ArrayList<>(new LinkedHashSet<>(points));
        if (sorted.size() < 3) {
            return sorted;
        }
        sorted.sort(Comparator.<Point>comparingInt(p -> p.x).thenComparingInt(p -> p.y));
        List<Point> hull = new ArrayList<>();
        for (int pass = 0; pass < 2; pass++) {
            int start = hull.size();
            for (Point p : sorted) {
                while (hull.size() >= start + 2
                        && cross(hull.get(hull.size() - 2), hull.get(hull.size() - 1), p) <= 0) {
                    hull.remove(hull.size() - 1);
                }
                hull.add(p);
            }
            hull.remove(hull.size() - 1);
            Collections.reverse(sorted);
        }
        return hull;
    }

    private static long cross(Point o, Point a, Point b) {
        return (long) (a.x - o.x) * (b.y - o.y) - (long) (a.y - o.y) * (b.x - o.x);
    }
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: same as Step 2. Expected: 3 tests PASS.

- [ ] **Step 5: Commit (ask the user first)**

```bash
git add plugin/src
git commit -m "Outline clickboxes as short screen polygons"
```

---

### Task 3: Scanning for requested objects

**Files:**
- Create: `plugin/src/main/java/com/runecolor/bridge/ObjectScanner.java`
- Modify: `plugin/src/main/java/com/runecolor/bridge/Snapshot.java` (add `SceneObject`)
- Modify: `plugin/src/main/java/com/runecolor/bridge/SnapshotBuilder.java` (widen `nearestFirst`, `Nearby`, `point` from `private` to package-private)
- Test: `plugin/src/test/java/com/runecolor/bridge/ObjectScannerTest.java`

**Interfaces:**
- Consumes: `HullOutline.of` (Task 2); `SnapshotBuilder.canvasOrigin(Client)`.
- Produces: `ObjectScanner.scan(Client, Player, Set<Integer>) -> List<Snapshot.SceneObject>` (empty when nothing is requested, null when the canvas or scene is unknown). `ObjectScanner.RADIUS = 15`, `MAX_OBJECTS = 10`. `Snapshot.SceneObject(int id, Snapshot.Point tile, int distance, List<int[]> hull)`.

- [ ] **Step 1: Add `SceneObject` to `Snapshot.java`** (after `Npc`)

```java
    /** A game object the bot asked for, with its clickbox outline on screen. */
    public static final class SceneObject {
        public final int id;
        public final Point tile;
        public final int distance;
        public final List<int[]> hull;

        SceneObject(int id, Point tile, int distance, List<int[]> hull) {
            this.id = id;
            this.tile = tile;
            this.distance = distance;
            this.hull = hull;
        }
    }
```

- [ ] **Step 2: Write the failing test**

```java
package com.runecolor.bridge;

import java.awt.Canvas;
import java.awt.Rectangle;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import net.runelite.api.Client;
import net.runelite.api.GameObject;
import net.runelite.api.Player;
import net.runelite.api.Scene;
import net.runelite.api.Tile;
import net.runelite.api.coords.LocalPoint;
import net.runelite.api.coords.WorldPoint;
import org.junit.Test;
import org.mockito.Mockito;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

public class ObjectScannerTest {
    private static final int TIN = 11361;
    private static final Set<Integer> WANT_TIN = new HashSet<>(Arrays.asList(TIN));

    private final Client client = Mockito.mock(Client.class);
    private final Player player = Mockito.mock(Player.class);
    private final Tile[][][] tiles = new Tile[1][104][104];

    public ObjectScannerTest() {
        Mockito.when(player.getLocalLocation()).thenReturn(LocalPoint.fromScene(50, 50));
        Canvas canvas = Mockito.mock(Canvas.class);
        Mockito.when(canvas.getLocationOnScreen()).thenReturn(new java.awt.Point(180, 30));
        Mockito.when(client.getCanvas()).thenReturn(canvas);
        Mockito.when(client.getPlane()).thenReturn(0);
        Scene scene = Mockito.mock(Scene.class);
        Mockito.when(scene.getTiles()).thenReturn(tiles);
        Mockito.when(client.getScene()).thenReturn(scene);
    }

    /** Put an object at an offset from the player, clickbox around canvas (300, 200). */
    private GameObject place(int id, int dx, int dy, boolean onScreen) {
        GameObject object = Mockito.mock(GameObject.class);
        Mockito.when(object.getId()).thenReturn(id);
        Mockito.when(object.getWorldLocation()).thenReturn(new WorldPoint(3200 + dx, 3200 + dy, 0));
        Mockito.when(object.getClickbox())
                .thenReturn(onScreen ? new Rectangle(290, 180, 20, 40) : null);
        Tile tile = tiles[0][50 + dx][50 + dy];
        if (tile == null) {
            tile = Mockito.mock(Tile.class);
            tiles[0][50 + dx][50 + dy] = tile;
        }
        GameObject[] existing = tile.getGameObjects();
        GameObject[] all = existing == null ? new GameObject[] {object}
                : appended(existing, object);
        Mockito.when(tile.getGameObjects()).thenReturn(all);
        return object;
    }

    private static GameObject[] appended(GameObject[] objects, GameObject object) {
        GameObject[] all = Arrays.copyOf(objects, objects.length + 1);
        all[objects.length] = object;
        return all;
    }

    private List<Snapshot.SceneObject> scan(Set<Integer> ids) {
        return ObjectScanner.scan(client, player, ids);
    }

    @Test
    public void reportsOnlyRequestedObjectsNearestFirst() {
        place(TIN, 3, 0, true);
        place(TIN, 1, 0, true);
        place(999, 0, 1, true);
        List<Snapshot.SceneObject> found = scan(WANT_TIN);
        assertEquals(2, found.size());
        assertEquals(1, found.get(0).distance);
        assertEquals(3, found.get(1).distance);
        assertEquals(TIN, found.get(0).id);
        assertEquals(3201, found.get(0).tile.x);
        assertEquals(4, found.get(0).hull.size());
    }

    @Test
    public void skipsObjectsTooFarAway() {
        place(TIN, ObjectScanner.RADIUS + 1, 0, true);
        assertTrue(scan(WANT_TIN).isEmpty());
    }

    @Test
    public void skipsObjectsOffScreen() {
        place(TIN, 1, 0, false);
        assertTrue(scan(WANT_TIN).isEmpty());
    }

    @Test
    public void capsHowManyItReports() {
        for (int dx = -6; dx <= 5; dx++) {
            place(TIN, dx, 2, true);
        }
        assertEquals(ObjectScanner.MAX_OBJECTS, scan(WANT_TIN).size());
    }

    @Test
    public void reportsNothingWhenNothingIsRequested() {
        place(TIN, 1, 0, true);
        assertTrue(scan(Collections.emptySet()).isEmpty());
    }

    @Test
    public void unknownWithoutACanvas() {
        Mockito.when(client.getCanvas()).thenReturn(null);
        assertNull(scan(WANT_TIN));
    }
}
```

- [ ] **Step 3: Run it to verify it fails**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon --tests com.runecolor.bridge.ObjectScannerTest`
Expected: compilation FAIL, `cannot find symbol: class ObjectScanner`

- [ ] **Step 4: Implement**

In `SnapshotBuilder.java`, change `private static <T> List<T> nearestFirst`, `private static Snapshot.Point point(WorldPoint tile)` and `private static final class Nearby<T>` (and its constructor) to package-private (drop `private`).

```java
package com.runecolor.bridge;

import java.awt.Point;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import net.runelite.api.Client;
import net.runelite.api.GameObject;
import net.runelite.api.Player;
import net.runelite.api.Scene;
import net.runelite.api.Tile;
import net.runelite.api.coords.LocalPoint;
import net.runelite.api.coords.WorldPoint;

/** Finds the game objects the bot asked for near the player. Client thread only. */
final class ObjectScanner {
    static final int RADIUS = 15;
    static final int MAX_OBJECTS = 10;

    private ObjectScanner() {
    }

    static List<Snapshot.SceneObject> scan(Client client, Player player, Set<Integer> ids) {
        if (ids.isEmpty()) {
            return Collections.emptyList();
        }
        Point origin = SnapshotBuilder.canvasOrigin(client);
        LocalPoint here = player.getLocalLocation();
        Scene scene = client.getScene();
        if (origin == null || here == null || scene == null) {
            return null;
        }
        Tile[][] tiles = scene.getTiles()[client.getPlane()];
        List<SnapshotBuilder.Nearby<Snapshot.SceneObject>> nearby = new ArrayList<>();
        for (int dx = -RADIUS; dx <= RADIUS; dx++) {
            for (int dy = -RADIUS; dy <= RADIUS; dy++) {
                int x = here.getSceneX() + dx;
                int y = here.getSceneY() + dy;
                if (x < 0 || y < 0 || x >= tiles.length || y >= tiles[x].length
                        || tiles[x][y] == null) {
                    continue;
                }
                int distance = Math.max(Math.abs(dx), Math.abs(dy));
                for (GameObject object : tiles[x][y].getGameObjects()) {
                    Snapshot.SceneObject found = sceneObject(object, x, y, ids, origin, distance);
                    if (found != null) {
                        nearby.add(new SnapshotBuilder.Nearby<>(distance, found));
                    }
                }
            }
        }
        return SnapshotBuilder.nearestFirst(nearby, MAX_OBJECTS);
    }

    private static Snapshot.SceneObject sceneObject(GameObject object, int x, int y,
                                                    Set<Integer> ids, Point origin,
                                                    int distance) {
        if (object == null || !ids.contains(object.getId()) || !anchoredAt(object, x, y)) {
            return null;
        }
        List<int[]> hull = HullOutline.of(object.getClickbox(), origin);
        WorldPoint tile = object.getWorldLocation();
        if (hull == null || tile == null) {
            return null;
        }
        return new Snapshot.SceneObject(object.getId(), SnapshotBuilder.point(tile),
                distance, hull);
    }

    /** A large object, a tree say, sits on several tiles; report it from one of them. */
    private static boolean anchoredAt(GameObject object, int x, int y) {
        net.runelite.api.Point min = object.getSceneMinLocation();
        return min == null || (min.getX() == x && min.getY() == y);
    }
}
```

- [ ] **Step 5: Run it to verify it passes**

Run: same as Step 3. Expected: 6 tests PASS. Then run the full Java suite; all PASS.

- [ ] **Step 6: Commit (ask the user first)**

```bash
git add plugin/src
git commit -m "Scan the scene for the objects the bot asked for"
```

---

### Task 4: Inventory slots and the menu

**Files:**
- Create: `plugin/src/main/java/com/runecolor/bridge/InventorySlots.java`
- Create: `plugin/src/main/java/com/runecolor/bridge/MenuReader.java`
- Modify: `plugin/src/main/java/com/runecolor/bridge/Snapshot.java` (add `MenuEntry`, `Menu`)
- Test: `plugin/src/test/java/com/runecolor/bridge/InventorySlotsTest.java`, `MenuReaderTest.java`

**Interfaces:**
- Produces: `InventorySlots.read(Client) -> List<int[]>` (28 `[x, y, w, h]` or null). `MenuReader.read(Client) -> Snapshot.Menu` (null without a canvas). `Snapshot.MenuEntry(String option, String target, int[] rect)`, `Snapshot.Menu(boolean open, Snapshot.MenuEntry top, List<Snapshot.MenuEntry> entries)`. `MenuReader.HEADER_HEIGHT = 19`, `ROW_HEIGHT = 15`.

- [ ] **Step 1: Add the menu types to `Snapshot.java`**

```java
    /** One menu option. {@code rect} is null for the hover entry of a closed menu. */
    public static final class MenuEntry {
        public final String option;
        public final String target;
        public final int[] rect;

        MenuEntry(String option, String target, int[] rect) {
            this.option = option;
            this.target = target;
            this.rect = rect;
        }
    }

    /** The client menu: what a left-click would do, and the rows of an open menu. */
    public static final class Menu {
        public final boolean open;
        public final MenuEntry top;
        public final List<MenuEntry> entries;

        Menu(boolean open, MenuEntry top, List<MenuEntry> entries) {
            this.open = open;
            this.top = top;
            this.entries = entries;
        }
    }
```

- [ ] **Step 2: Write the failing tests**

```java
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
        Widget[] slots = new Widget[28];
        for (int i = 0; i < slots.length; i++) {
            slots[i] = Mockito.mock(Widget.class);
            Mockito.when(slots[i].getBounds())
                    .thenReturn(new Rectangle(560 + 42 * (i % 4), 210 + 36 * (i / 4), 36, 32));
        }
        Mockito.when(items.getDynamicChildren()).thenReturn(slots);
    }

    @Test
    public void reportsEverySlotOnScreen() {
        List<int[]> rects = InventorySlots.read(client);
        assertEquals(28, rects.size());
        assertArrayEquals(new int[] {740, 240, 36, 32}, rects.get(0));
        assertArrayEquals(new int[] {740 + 42 * 3, 240 + 36 * 6, 36, 32}, rects.get(27));
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
```

```java
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
        Mockito.when(client.getMenuEntries()).thenReturn(new MenuEntry[] {
                entry("Cancel", ""),
                entry("Walk here", ""),
                entry("<col=ffffff>Mine", "<col=ffff>Tin rocks")});
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
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon --tests com.runecolor.bridge.InventorySlotsTest --tests com.runecolor.bridge.MenuReaderTest`
Expected: compilation FAIL, missing `InventorySlots` / `MenuReader`.

- [ ] **Step 4: Implement**

```java
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
```

```java
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
```

- [ ] **Step 5: Run them to verify they pass**

Run: same as Step 3. Expected: 6 tests PASS.

- [ ] **Step 6: Commit (ask the user first)**

```bash
git add plugin/src
git commit -m "Read inventory slot bounds and the client menu"
```

---

### Task 5: Schema 2 snapshot and shared fixture

**Files:**
- Modify: `plugin/src/main/java/com/runecolor/bridge/Snapshot.java` (three fields + constructor)
- Modify: `plugin/src/main/java/com/runecolor/bridge/SnapshotBuilder.java` (schema 2, `build` overloads)
- Modify: `plugin/src/main/java/com/runecolor/bridge/RuneColorBridgePlugin.java:142-143`
- Modify: `plugin/src/test/java/com/runecolor/bridge/SnapshotFixtureTest.java`, `SnapshotPublisherTest.java:30`, `LoopbackMain.java:11`
- Rename: `tests/fixtures/snapshot_v1.json` → `tests/fixtures/snapshot_v2.json`

**Interfaces:**
- Consumes: `ObjectScanner.scan`, `InventorySlots.read`, `MenuReader.read`, `ObjectRequest.ids()`.
- Produces: `SnapshotBuilder.SCHEMA_VERSION = 2`; `SnapshotBuilder.build(Client, long, String, Set<Integer>)`; JSON keys `objects`, `inventory_slots`, `menu`; fixture `tests/fixtures/snapshot_v2.json` (used by Task 7).

- [ ] **Step 1: Write the new fixture**

```bash
git mv tests/fixtures/snapshot_v1.json tests/fixtures/snapshot_v2.json
venv/Scripts/python - <<'EOF'
import json
from pathlib import Path

path = Path("tests/fixtures/snapshot_v2.json")
data = json.loads(path.read_text())
data["schema"] = 2
data["objects"] = [{
    "id": 11361,
    "tile": {"x": 3229, "y": 3148, "plane": 0},
    "distance": 2,
    "hull": [[812, 401], [840, 398], [851, 430]],
}]
data["inventory_slots"] = [
    [560 + 42 * (i % 4), 210 + 36 * (i // 4), 36, 32] for i in range(28)
]
data["menu"] = {
    "open": True,
    "top": {"option": "Mine", "target": "Tin rocks"},
    "entries": [
        {"option": "Mine", "target": "Tin rocks", "rect": [280, 99, 120, 15]},
        {"option": "Cancel", "target": "", "rect": [280, 114, 120, 15]},
    ],
}
path.write_text(json.dumps(data, indent=2) + "\n")
EOF
```

- [ ] **Step 2: Update the fixture test to expect the new fields** (fails to compile until Step 4)

In `SnapshotFixtureTest.serializesToTheSharedFixture`, change `new Snapshot(1, ...` to `new Snapshot(2, ...` and append three arguments after the `npcs` list:

```java
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
```

Change the fixture path to `"snapshot_v2.json"`, add `import java.util.Arrays;`, and add:

```java
    private static List<int[]> slots() {
        List<int[]> rects = new ArrayList<>();
        for (int i = 0; i < 28; i++) {
            rects.add(new int[] {560 + 42 * (i % 4), 210 + 36 * (i / 4), 36, 32});
        }
        return rects;
    }
```

- [ ] **Step 3: Run it to verify it fails**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon --tests com.runecolor.bridge.SnapshotFixtureTest`
Expected: compilation FAIL, the `Snapshot` constructor takes 16 arguments, not 19.

- [ ] **Step 4: Add the fields and wire the builder**

`Snapshot.java`: add the fields after `npcs`, add the three constructor parameters `List<SceneObject> objects, List<int[]> inventorySlots, Menu menu` at the end, and assign them.

```java
    /** The objects the bot asked for, nearest first, or null if unknown. */
    public final List<SceneObject> objects;

    /** Each inventory slot on screen as [x, y, w, h], or null while hidden. */
    @SerializedName("inventory_slots")
    public final List<int[]> inventorySlots;

    /** The client menu, or null if unknown. */
    public final Menu menu;
```

`SnapshotBuilder.java`:
- `SCHEMA_VERSION = 2`.
- Keep `build(client, now)` and change `build(client, now, profile)` to delegate: `return build(client, nowMillis, profile, Collections.emptySet());`.
- New 4-argument `build(Client client, long nowMillis, String profile, Set<Integer> objectIds)` holding the current body. The logged-out return gets `null, null, null` appended. The logged-in return appends:

```java
                orNull(() -> ObjectScanner.scan(client, player, objectIds)),
                orNull(() -> InventorySlots.read(client)),
                orNull(() -> MenuReader.read(client)));
```

- Add the helper and imports (`java.util.Collections`, `java.util.Set`, `java.util.function.Supplier`):

```java
    /** A new field that fails to build must not cost the bot the rest of the snapshot. */
    private static <T> T orNull(Supplier<T> read) {
        try {
            return read.get();
        } catch (RuntimeException e) {
            return null;
        }
    }
```

`RuneColorBridgePlugin.tick()`: pass `objectRequest.ids()` as the fourth argument to `SnapshotBuilder.build`.

`SnapshotPublisherTest.java:30` and `LoopbackMain.java:11`: change the schema literal `1` to `2` and append `, null, null, null` to the `new Snapshot(...)` arguments.

- [ ] **Step 5: Run all Java tests**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon`
Expected: all PASS. (The Python suite now fails on the missing `snapshot_v1.json` until Task 7, which is expected.)

- [ ] **Step 6: Commit (ask the user first)**

```bash
git add plugin/src tests/fixtures
git commit -m "Send objects, inventory slots and the menu in schema 2"
```

---

### Task 6: Polygon

**Files:**
- Modify: `src/utilities/geometry.py` (add `Polygon` after `Rectangle`)
- Test: `tests/unit/test_polygon.py`

**Interfaces:**
- Produces: `Polygon(points: Sequence[Tuple[int, int]])` with `.points: List[Point]`, `.bounds: Rectangle`, `.contains(point: Point) -> bool`, `.center -> Point` (property), `.random_point() -> Point`. Raises `ValueError` for fewer than 3 points.

- [ ] **Step 1: Write the failing test**

```python
"""Polygon: the clickbox outline the bridge sends for a scene object."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from utilities.geometry import Point, Polygon  # noqa: E402

SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]
TRIANGLE = [(0, 0), (40, 0), (0, 40)]


class PolygonTest(unittest.TestCase):
    def test_needs_three_points(self):
        with self.assertRaises(ValueError):
            Polygon([(0, 0), (1, 1)])

    def test_contains_inside_points_only(self):
        square = Polygon(SQUARE)
        self.assertTrue(square.contains(Point(5, 5)))
        self.assertFalse(square.contains(Point(15, 5)))
        self.assertFalse(Polygon(TRIANGLE).contains(Point(35, 35)))

    def test_center_is_the_vertex_mean(self):
        self.assertEqual(Polygon(SQUARE).center, Point(5, 5))

    def test_random_points_stay_inside(self):
        triangle = Polygon(TRIANGLE)
        for _ in range(300):
            self.assertTrue(triangle.contains(triangle.random_point()))

    def test_bounds_cover_every_point(self):
        bounds = Polygon(TRIANGLE).bounds
        self.assertEqual((bounds.left, bounds.top), (0, 0))
        self.assertEqual((bounds.width, bounds.height), (41, 41))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `venv/Scripts/python -m unittest tests.unit.test_polygon -v`
Expected: FAIL, `ImportError: cannot import name 'Polygon'`

- [ ] **Step 3: Implement** (in `geometry.py`, after the `Rectangle` class; add `Sequence, Tuple` to the `typing` import)

```python
class Polygon:
    """A screen-space outline, such as a scene object's clickbox from the bridge."""

    def __init__(self, points: Sequence[Tuple[int, int]]) -> None:
        if len(points) < 3:
            raise ValueError(f"A polygon needs at least 3 points, got {len(points)}.")
        self.points = [Point(int(x), int(y)) for x, y in points]
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        self.bounds = Rectangle(
            min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        )

    def contains(self, point: Point) -> bool:
        """Even-odd ray cast."""
        inside = False
        for a, b in zip(self.points, self.points[-1:] + self.points[:-1]):
            if (a.y > point.y) != (b.y > point.y):
                crossing = a.x + (point.y - a.y) * (b.x - a.x) / (b.y - a.y)
                if point.x < crossing:
                    inside = not inside
        return inside

    @property
    def center(self) -> Point:
        n = len(self.points)
        return Point(
            sum(p.x for p in self.points) // n, sum(p.y for p in self.points) // n
        )

    def random_point(self, tries: int = 30) -> Point:
        # Sampling the bounds keeps Rectangle's centre bias; the vertex mean of a
        # convex hull is always inside, so it is a safe last resort.
        for _ in range(tries):
            point = self.bounds.random_point()
            if self.contains(point):
                return point
        return self.center
```

- [ ] **Step 4: Run it to verify it passes**

Run: same as Step 2. Expected: 5 tests PASS.

- [ ] **Step 5: Lint and commit (ask the user first)**

```bash
venv/Scripts/flake8 --max-line-length 88 src/utilities/geometry.py tests/unit/test_polygon.py
venv/Scripts/black --check src/utilities/geometry.py tests/unit/test_polygon.py
git add src/utilities/geometry.py tests/unit/test_polygon.py
git commit -m "Add Polygon for clickbox outlines"
```

---

### Task 7: Bridge API schema 2

**Files:**
- Modify: `src/utilities/api/bridge_api.py`
- Modify: `tests/unit/test_bridge_api.py`

**Interfaces:**
- Consumes: `Polygon`, `Rectangle` from `utilities.geometry` (Task 6); fixture `snapshot_v2.json` (Task 5).
- Produces: `SceneObject(id: int, tile: Tile, distance: int, hull: Polygon)`, `MenuEntry(option: str, target: str, rect: Optional[Rectangle])`, `Menu(open: bool, top: Optional[MenuEntry], entries: List[MenuEntry])` with `Menu.top_text -> str`. `BridgeAPI.request_objects(ids: Iterable[int])`, `BridgeAPI.clear_objects()`, properties `objects -> List[SceneObject]`, `inventory_slots -> Optional[List[Rectangle]]`, `menu -> Optional[Menu]`.

- [ ] **Step 1: Write the failing tests**

In `test_bridge_api.py`: change `FIXTURE` to `snapshot_v2.json`; import `Menu, SceneObject` too. In `test_rejects_a_mismatched_schema_and_stays_disabled` change `body["schema"] = 2` to `body["schema"] = 3`; in `test_serves_partial_fields_when_logged_out` change `"schema": 1` to `"schema": 2`. Every `{"profile": ...}` reply assertion gains `"objects": []`, e.g. `{"profile": None, "objects": []}`. Add:

```python
    def test_exposes_the_requested_objects(self):
        self.post(payload())
        (rock,) = self.bridge.objects
        self.assertIsInstance(rock, SceneObject)
        self.assertEqual((rock.id, rock.tile, rock.distance), (11361, (3229, 3148, 0), 2))
        self.assertEqual(rock.hull.points[0], (812, 401))

    def test_reports_no_objects_from_an_older_plugin(self):
        self.post({k: v for k, v in payload().items() if k != "objects"})
        self.assertEqual(self.bridge.objects, [])

    def test_exposes_the_inventory_slots(self):
        self.post(payload())
        slots = self.bridge.inventory_slots
        self.assertEqual(len(slots), 28)
        self.assertEqual((slots[0].left, slots[0].top), (560, 210))
        self.assertEqual((slots[27].width, slots[27].height), (36, 32))

    def test_reports_no_inventory_slots_while_hidden(self):
        self.post(dict(payload(), inventory_slots=None))
        self.assertIsNone(self.bridge.inventory_slots)

    def test_exposes_the_menu(self):
        self.post(payload())
        menu = self.bridge.menu
        self.assertIsInstance(menu, Menu)
        self.assertTrue(menu.open)
        self.assertEqual(menu.top_text, "Mine Tin rocks")
        self.assertEqual(menu.entries[1].option, "Cancel")
        self.assertEqual(menu.entries[0].rect.left, 280)

    def test_reports_no_menu_before_any_snapshot(self):
        self.assertIsNone(self.bridge.menu)

    def test_replies_with_the_requested_objects(self):
        self.bridge.request_objects([11361, 11360, 11361])
        self.assertEqual(
            self.post(payload()).get_json(),
            {"profile": None, "objects": [11360, 11361]},
        )

    def test_cleared_objects_are_no_longer_requested(self):
        self.bridge.request_objects([11361])
        self.bridge.clear_objects()
        self.assertEqual(self.post(payload()).get_json()["objects"], [])
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python -m unittest tests.unit.test_bridge_api -v`
Expected: FAIL, `ImportError: cannot import name 'Menu'`

- [ ] **Step 3: Implement**

In `bridge_api.py`:
- `SCHEMA_VERSION = 2`.
- `from typing import Dict, Iterable, List, Optional, Tuple, Union` and `from utilities.geometry import Polygon, Rectangle`.
- Dataclasses after `Npc`:

```python
@dataclass(frozen=True)
class SceneObject:
    """A game object the bot asked for, with its clickbox outline on screen."""

    id: int
    tile: Tile
    distance: int
    hull: Polygon


@dataclass(frozen=True)
class MenuEntry:
    """One menu option. `rect` is None for the hover entry of a closed menu."""

    option: str
    target: str
    rect: Optional[Rectangle]


@dataclass(frozen=True)
class Menu:
    """The client menu: what a left-click would do, and the rows of an open menu."""

    open: bool
    top: Optional[MenuEntry]
    entries: List[MenuEntry]

    @property
    def top_text(self) -> str:
        """str: The hover text, as the game shows it top left (e.g. "Mine Tin rocks")."""
        if self.top is None:
            return ""
        return f"{self.top.option} {self.top.target}".strip()


def _rect(value: object) -> Optional[Rectangle]:
    """Turn an `[x, y, w, h]` list into a `Rectangle`, or None."""
    if not isinstance(value, list) or len(value) != 4:
        return None
    return Rectangle(*(int(v) for v in value))


def _menu_entry(value: Dict) -> MenuEntry:
    return MenuEntry(
        str(value.get("option", "")),
        str(value.get("target", "")),
        _rect(value.get("rect")),
    )
```

- In `__init__`, next to `_wanted_profile`: `self._wanted_objects: List[int] = []`.
- In `handle_snapshot`, read `objects = self._wanted_objects` inside the lock and `return jsonify(profile=wanted, objects=objects), 200`. Update the docstring's Returns to "naming the wanted profile and objects".
- After `clear_profile`:

```python
    def request_objects(self, ids: Iterable[int]) -> None:
        """Ask the plug-in to report these game object IDs in every snapshot.

        Args:
            ids (Iterable[int]): The object IDs, e.g. the live rocks of one ore.
        """
        with self._lock:
            self._wanted_objects = sorted({int(i) for i in ids})

    def clear_objects(self) -> None:
        """Stop asking for objects."""
        with self._lock:
            self._wanted_objects = []
```

- After `inventory`:

```python
    @property
    def objects(self) -> List[SceneObject]:
        """List[SceneObject]: The requested objects in view, nearest first.

        Empty when none are in view, when nothing is requested, when the feed is
        stale, or when the plug-in predates this field.
        """
        values = self._field("objects", None)
        if not isinstance(values, list):
            return []
        return [
            SceneObject(
                int(v["id"]), _tile(v["tile"]), int(v["distance"]), Polygon(v["hull"])
            )
            for v in values
        ]

    @property
    def inventory_slots(self) -> Optional[List[Rectangle]]:
        """Optional[List[Rectangle]]: Each of the 28 inventory slots on screen.

        None while the inventory tab is hidden, when the feed is stale, or when the
        plug-in predates this field.
        """
        values = self._field("inventory_slots", None)
        if not isinstance(values, list) or len(values) != 28:
            return None
        rects = [_rect(v) for v in values]
        return None if None in rects else rects

    @property
    def menu(self) -> Optional[Menu]:
        """Optional[Menu]: The client menu, or None if unknown."""
        value = self._field("menu", None)
        if not isinstance(value, dict):
            return None
        top = value.get("top")
        return Menu(
            bool(value.get("open", False)),
            _menu_entry(top) if isinstance(top, dict) else None,
            [_menu_entry(e) for e in value.get("entries") or []],
        )
```

- [ ] **Step 4: Run the whole Python suite**

Run: `venv/Scripts/python -m unittest discover -s tests/unit -t . -v`
Expected: all PASS. If another test module still names `snapshot_v1.json`, point it at `snapshot_v2.json` (`grep -rn snapshot_v1 tests src`).

- [ ] **Step 5: Lint and commit (ask the user first)**

```bash
venv/Scripts/flake8 --max-line-length 88 src/utilities/api/bridge_api.py tests/unit/test_bridge_api.py
venv/Scripts/black --check src/utilities/api/bridge_api.py tests/unit/test_bridge_api.py
git add src/utilities/api/bridge_api.py tests/unit/test_bridge_api.py
git commit -m "Read scene objects, inventory slots and the menu from the bridge"
```

---

### Task 8: Bot helpers

**Files:**
- Modify: `src/model/runelite_bot.py` (bridge section, near `attach_bridge`; and `drop_items` at ~line 1321)
- Test: `tests/unit/test_scene_targets.py`

**Interfaces:**
- Consumes: `SceneObject`, `Menu` (Task 7).
- Produces: `RuneLiteBot.move_to_scene_object(obj: SceneObject) -> None`; `RuneLiteBot.wait_for_hover_text(contains: str, timeout: float = 1.5) -> bool`; `RuneLiteBot.drop_items(slots, verbose=True, rects: Optional[List[Rectangle]] = None)`.

- [ ] **Step 1: Write the failing test**

```python
"""The bot helpers that act on the bridge's scene targets, tested without a client."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.runelite_bot import RuneLiteBot  # noqa: E402
from utilities.api.bridge_api import Menu, MenuEntry  # noqa: E402


class FakeBridge:
    def __init__(self, menus):
        self._menus = list(menus)

    @property
    def menu(self):
        return self._menus.pop(0) if len(self._menus) > 1 else self._menus[0]


def hover(target):
    return Menu(False, MenuEntry("Mine", target, None), [])


class FakeBot:
    wait_for_hover_text = RuneLiteBot.wait_for_hover_text
    game_tick = 0.003

    def __init__(self, menus):
        self.bridge = FakeBridge(menus)


class WaitForHoverTextTest(unittest.TestCase):
    def test_waits_for_the_snapshot_to_catch_up_with_the_mouse(self):
        bot = FakeBot([None, hover("Rocks"), hover("Tin rocks")])
        self.assertTrue(bot.wait_for_hover_text("Tin", timeout=0.2))

    def test_gives_up_on_the_wrong_object(self):
        bot = FakeBot([hover("Iron rocks")])
        self.assertFalse(bot.wait_for_hover_text("Tin", timeout=0.05))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `venv/Scripts/python -m unittest tests.unit.test_scene_targets -v`
Expected: FAIL, `AttributeError: type object 'RuneLiteBot' has no attribute 'wait_for_hover_text'`

- [ ] **Step 3: Implement**

In `runelite_bot.py`, import `SceneObject` from `utilities.api.bridge_api` beside `BridgeAPI`, and add after `detach_bridge`:

```python
    def move_to_scene_object(self, obj: SceneObject) -> None:
        """Move the mouse to a random point on a scene object the bridge reported.

        Args:
            obj (SceneObject): An entry of `self.bridge.objects`.
        """
        self.mouse.move_to(obj.hull.random_point())

    def wait_for_hover_text(self, contains: str, timeout: float = 1.5) -> bool:
        """Wait until the client's hover text names what is under the mouse.

        A snapshot is up to a tick older than the mouse, so the first one after a
        move can still describe whatever was under the cursor before.

        Args:
            contains (str): Case-sensitive text the hover text must contain.
            timeout (float, optional): Seconds to wait. Defaults to 1.5.

        Returns:
            bool: True once the hover text contains it.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            menu = self.bridge.menu
            if menu is not None and contains in menu.top_text:
                return True
            time.sleep(self.game_tick / 3)
        return False
```

In `drop_items`, add the parameter `rects: Optional[List[Rectangle]] = None` after `verbose`, document it ("Slot rectangles to click, e.g. `self.bridge.inventory_slots`. Defaults to the ones measured from the window."), and before the loop add `rects = rects or self.win.inventory_slots`; use `rects[slot]` instead of `self.win.inventory_slots[slot]`. Make sure `Optional` and `Rectangle` are imported (check the existing imports first).

- [ ] **Step 4: Run all Python tests**

Run: `venv/Scripts/python -m unittest discover -s tests/unit -t . -v`
Expected: all PASS.

- [ ] **Step 5: Lint and commit (ask the user first)**

```bash
venv/Scripts/flake8 --max-line-length 88 tests/unit/test_scene_targets.py
venv/Scripts/black --check tests/unit/test_scene_targets.py
git add src/model/runelite_bot.py tests/unit/test_scene_targets.py
git commit -m "Add bot helpers for bridge scene targets"
```

`runelite_bot.py` is large and older: run flake8 on it too, but only fix findings on lines this task added.

---

### Task 9: Power Miner on bridge targets

**Files:**
- Modify: `src/model/osrs/power_miner_rules.py`
- Modify: `src/model/osrs/power_miner.py`
- Modify: `src/profiles/power_miner.properties` (delete the two `objectindicators.region_*` lines, 2478-2479)
- Modify: `tests/unit/test_power_miner.py`

**Interfaces:**
- Consumes: `bridge.objects`, `bridge.inventory_slots`, `bridge.request_objects`, `bridge.clear_objects` (Task 7); `move_to_scene_object`, `wait_for_hover_text`, `drop_items(rects=)` (Task 8).
- Produces: `rules.Ore(name, item_id, rock_word, rock_ids: FrozenSet[int])`; `OSRSPowerMiner._pick_rock() -> Optional[SceneObject]`.

- [ ] **Step 1: Update the tests first**

In `test_power_miner.py`:
- `test_an_ore_needs_a_name_rock_word_and_item`: give each `rules.Ore(...)` call a fourth argument `frozenset({11366})`, and add `rules.Ore("Coal", 453, "Coal", frozenset())` inside an `assertRaises(ValueError)` too.
- Add to `RulesTest`:

```python
    def test_each_ore_names_its_live_rocks(self):
        self.assertEqual(rules.TIN.rock_ids, frozenset({11360, 11361}))
        self.assertEqual(rules.IRON.rock_ids, frozenset({11364, 11365}))
```

- In `FakeBridge.__init__` add `self.objects = []` and `self.inventory_slots = None`.
- In `FakeMiner`: add `_pick_rock = OSRSPowerMiner._pick_rock`; replace `find_colors` and `get_mouseover_text` with:

```python
    def move_to_scene_object(self, obj):
        self.moved_to.append(obj)

    def wait_for_hover_text(self, contains, timeout=1.5):
        self.mouseover_words.append(contains)
        return self.says_tin
```

  In `__init__`, drop `mark_color` and `win`, add `self.moved_to = []`, and fill rocks into the bridge: `bridge.objects = [SimpleNamespace(id=11361, distance=d) for d in range(1, rocks + 1)]`.
- Change `drop_items(self, slots, verbose=True)` to `drop_items(self, slots, verbose=True, rects=None)` and record `self.drop_rects = rects`.
- Add:

```python
    def test_mines_the_nearest_rock_most_of_the_time(self):
        miner = FakeMiner(FakeBridge(EMPTY), rocks=3)
        with unittest.mock.patch("random.random", return_value=0.9):
            self.assertEqual(miner._pick_rock().distance, 1)
        with unittest.mock.patch("random.random", return_value=0.0):
            self.assertEqual(miner._pick_rock().distance, 2)

    def test_no_rock_in_view_means_nothing_to_mine(self):
        miner = FakeMiner(FakeBridge(EMPTY), rocks=0)
        self.assertFalse(miner.mine())
```

  (add `import unittest.mock` at the top). Existing tests that assert on `mouseover_words` keep working; the word passed is still `self.ore.rock_word`.

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python -m unittest tests.unit.test_power_miner -v`
Expected: FAIL (`Ore` takes 4 arguments / `_pick_rock` missing).

- [ ] **Step 3: Implement the rules**

```python
@dataclass(frozen=True)
class Ore:
    """An ore the Power Miner can mine, and how to recognise its rock."""

    name: str
    item_id: int
    # The rock's hover text reads "Mine <rock_word> rocks".
    rock_word: str
    # Object IDs of the rock while it still has ore. A depleted rock changes ID, so
    # asking the bridge for these alone skips depleted rocks.
    rock_ids: FrozenSet[int]

    def __post_init__(self) -> None:
        if (
            not self.name
            or not self.rock_word
            or self.item_id < 0
            or not self.rock_ids
        ):
            raise ValueError(f"Incomplete ore: {self!r}")
```

```python
TIN = Ore("Tin", 438, "Tin", frozenset({11360, 11361}))
IRON = Ore("Iron", 440, "Iron", frozenset({11364, 11365}))
```

- [ ] **Step 4: Implement the miner**

In `power_miner.py`:
- Imports: drop `from utilities.geometry import RuneLiteObject`; add `import random`, `from typing import Callable, Optional` and `from utilities.api.bridge_api import SceneObject`.
- Constant: `SECOND_ROCK_CHANCE = 0.2  # Sometimes the next rock, so the route between rocks varies.`
- Description: replace the setup bullets about marking rocks with `"- Stand in a tin or iron mine.\n"`; change the first line to "Mine tin or iron rocks until the inventory is full, ...".
- `__init__`: delete `self.mark_color = self.cp.hsv.CYAN_MARK`.
- `main_loop`: after the bridge check, wrap the rest:

```python
        self.bridge.request_objects(self.ore.rock_ids)
        try:
            self._mine_for_run_time()
        finally:
            self.bridge.clear_objects()
```

  and move everything from `self.log_msg(f"[START] ...` to the end of the old `main_loop` into `def _mine_for_run_time(self) -> None:`. In it, change the stop message `f"No marked {self.ore.name.lower()} rocks in sight."` to `f"No {self.ore.name.lower()} rocks in sight."`.
- `mine`: replace its first five lines (from `rocks = self.find_colors(...)` to the `get_mouseover_text` check) with:

```python
        rock = self._pick_rock()
        if rock is None:
            return False
        self.move_to_scene_object(rock)
        # Guards against a wrong rock ID: its ore would never be dropped and would
        # fill the inventory for good.
        if not self.wait_for_hover_text(self.ore.rock_word):
            return False
```

  and update its docstring to "Click a rock of our ore and wait until it is mined out."
- Add:

```python
    def _pick_rock(self) -> Optional[SceneObject]:
        rocks = self.bridge.objects
        if not rocks:
            return None
        if len(rocks) > 1 and random.random() < SECOND_ROCK_CHANCE:
            return rocks[1]
        return rocks[0]
```

- `drop_ore`: `self.drop_items(slots, verbose=False, rects=self.bridge.inventory_slots)`.

- [ ] **Step 5: Remove the rock markers from the profile**

```bash
sed -i '/^objectindicators\.region_12849=/d;/^objectindicators\.region_13108=/d' src/profiles/power_miner.properties
grep -c "objectindicators.region_" src/profiles/power_miner.properties
```
Expected: `0`.

- [ ] **Step 6: Run all Python tests**

Run: `venv/Scripts/python -m unittest discover -s tests/unit -t . -v`
Expected: all PASS (including `test_runelite_profiles`, which checks every profile still enables the bridge).

- [ ] **Step 7: Lint and commit (ask the user first)**

```bash
venv/Scripts/flake8 --max-line-length 88 src/model/osrs/power_miner.py src/model/osrs/power_miner_rules.py tests/unit/test_power_miner.py
venv/Scripts/black --check src/model/osrs/power_miner.py src/model/osrs/power_miner_rules.py tests/unit/test_power_miner.py
git add src/model/osrs src/profiles/power_miner.properties tests/unit/test_power_miner.py
git commit -m "Mine from bridge scene targets instead of colour markers and OCR"
```

---

### Task 10: Live verification

Needs the user's client. **Do not start it while another bot run is using the client.** Restarting RuneLite ends any run in progress.

- [ ] **Step 1: Build and side-load the jar**

```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test shadowJar --no-daemon
cp build/libs/runecolor-bridge-1.0-all.jar ~/.runelite/sideloaded-plugins/
```

Close RuneLite and start it again with `powershell -ExecutionPolicy Bypass -File plugin\run-dev.ps1`. Log in at the Lumbridge Swamp tin rocks.

- [ ] **Step 2: Probe the three fields live** (throwaway script in the scratchpad, not committed)

```python
import sys, time
sys.path.insert(0, r"C:\Users\win11\rune-color\src")
from utilities.api.bridge_api import BridgeAPI

bridge = BridgeAPI()
bridge.request_objects([11360, 11361])
for _ in range(15):
    time.sleep(1)
    slots = bridge.inventory_slots
    print(
        [(o.id, o.distance, len(o.hull.points)) for o in bridge.objects],
        None if slots is None else (slots[0].left, slots[0].top, slots[0].width),
        bridge.menu and (bridge.menu.open, bridge.menu.top_text),
        flush=True,
    )
bridge.stop()
```

Check by hand while it runs:
- Rocks are listed with hulls of 3 or more points, and their IDs match 11360/11361. If the live IDs differ, correct `rules.TIN.rock_ids` and its test.
- Slot 0's rectangle matches the top-left inventory slot. Take a screenshot crop at that rectangle to confirm. With an empty inventory, check the slots are still reported. If they're not, stop and re-plan (fall back to the container bounds).
- Hovering a rock shows `Mine Tin rocks`. Right-clicking shows `open=True`; check one entry rect against a screenshot.

- [ ] **Step 3: Short and long runs**

```bash
venv/Scripts/python -u tests/live_power_miner.py --minutes 5 --ore Tin
venv/Scripts/python -u tests/live_power_miner.py --minutes 30 --ore Tin
```

Expected for each: "other items kept: PASS", ore mined and dropped, and no `Failed to find` or mouseover lines after "Logged in".

- [ ] **Step 4: Finish**

Run the full Java and Python suites and the lint once more, then use superpowers:finishing-a-development-branch.
