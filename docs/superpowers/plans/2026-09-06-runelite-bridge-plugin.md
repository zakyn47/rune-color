# RuneColor Bridge (Stage A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A sideloaded RuneLite plugin that pushes exact hitpoints, prayer, run energy, world point and game state to the Python bot every game tick, with OCR retained as an automatic fallback.

**Architecture:** A Gradle-built RuneLite plugin (`plugin/`) builds an immutable `Snapshot` on the client thread and POSTs it off-thread to a Flask server (`BridgeAPI`) inside the Python bot. `RuneLiteBot.get_hp`, `get_prayer` and `get_world_point` return the pushed value when it is fresh and fall through to their existing, untouched OCR bodies when it is not.

**Tech Stack:** Java 11, Gradle (wrapper from RuneLite's example-plugin template), `net.runelite:client` (compileOnly), Lombok, Gson and OkHttp (both provided by the client at runtime), JUnit 4 + Mockito for Java tests; Python 3.10, Flask, stdlib `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-06-runelite-bridge-plugin-design.md`

## Global Constraints

- **Java release target: 11.** `options.release.set(11)` — RuneLite plugins must be Java 11 bytecode.
- **No new Python dependencies.** Tests use stdlib `unittest`. `requirements.in` is not modified. Flask and requests are already present.
- **Python 3.10**, formatted with black (`line-length = 88`, `preview = true`) and isort (`profile = "black"`), passing the repo `.flake8` config. Run `pre-commit run --files <paths>` before every Python commit.
- **Schema version: 1.** The `schema` field is `1` for every stage A payload. Python rejects anything else.
- **Default port: 8099.** Avoids 8081 (`events_api.py`) and 9420 (`gi_tracker.py`).
- **Freshness threshold: 1.2 s** (two game ticks), configurable.
- **Run energy is normalized to 0-100** in `SnapshotBuilder`, never in Python.
- **Stage A only.** No animation ids, inventory, equipment or NPC fields. No reserved keys for them.
- **The plugin never throws out of `onGameTick`** and never blocks the client thread on I/O.
- **JDK location:** `C:\Users\win11\tools\jdk-11` (outside the repo). `JAVA_HOME` is set per-command, never persisted to the user's profile.
- **Docstrings** follow the existing Google style used throughout `src/` (Args/Returns sections).

---

### Task 1: Toolchain and the sideload spike

Nothing else in this plan matters if a sideloaded plugin cannot load. This task installs the toolchain the machine lacks and produces a hello-world plugin jar.

**Files:**
- Create: `plugin/build.gradle`, `plugin/settings.gradle`, `plugin/gradlew`, `plugin/gradlew.bat`, `plugin/gradle/wrapper/*`
- Create: `plugin/src/main/java/com/runecolor/bridge/RuneColorBridgePlugin.java`
- Create: `plugin/runelite-plugin.properties`
- Create: `plugin/README.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: a Gradle project at `plugin/` whose `./gradlew shadowJar` emits `plugin/build/libs/runecolor-bridge-1.0-all.jar`. Package root for all later tasks is `com.runecolor.bridge`.

- [ ] **Step 1: Install a JDK 11**

The machine has no `java` on PATH — only the JRE bundled with RuneLite, which cannot compile. Download a portable Temurin 11 and unpack it outside the repo.

```bash
mkdir -p "$HOME/tools"
curl -L -o "$HOME/tools/jdk11.zip" \
  "https://api.adoptium.net/v3/binary/latest/11/ga/windows/x64/jdk/hotspot/normal/eclipse"
unzip -q "$HOME/tools/jdk11.zip" -d "$HOME/tools/"
mv "$HOME/tools"/jdk-11* "$HOME/tools/jdk-11"
"$HOME/tools/jdk-11/bin/java" -version
```

Expected: `openjdk version "11.0.x"`.

- [ ] **Step 2: Scaffold from the RuneLite example-plugin template**

```bash
curl -L -o /tmp/example-plugin.zip \
  "https://github.com/runelite/example-plugin/archive/refs/heads/master.zip"
unzip -q /tmp/example-plugin.zip -d /tmp/
mkdir -p plugin
cp -r /tmp/example-plugin-master/gradle plugin/
cp /tmp/example-plugin-master/gradlew plugin/
cp /tmp/example-plugin-master/gradlew.bat plugin/
chmod +x plugin/gradlew
```

Do not copy the template's `src/` — the sources below replace it.

- [ ] **Step 3: Write `plugin/settings.gradle`**

```groovy
rootProject.name = 'runecolor-bridge'
```

- [ ] **Step 4: Write `plugin/build.gradle`**

```groovy
plugins {
    id 'java'
    id 'com.github.johnrengelman.shadow' version '7.1.2'
}

repositories {
    mavenLocal()
    maven { url = 'https://repo.runelite.net' }
    mavenCentral()
}

def runeLiteVersion = 'latest.release'

dependencies {
    compileOnly group: 'net.runelite', name: 'client', version: runeLiteVersion

    compileOnly 'org.projectlombok:lombok:1.18.30'
    annotationProcessor 'org.projectlombok:lombok:1.18.30'

    testImplementation 'junit:junit:4.13.2'
    testImplementation 'org.mockito:mockito-core:4.11.0'
    testImplementation group: 'net.runelite', name: 'client', version: runeLiteVersion
}

group = 'com.runecolor'
version = '1.0'

tasks.withType(JavaCompile).configureEach {
    options.encoding = 'UTF-8'
    options.release.set(11)
}

tasks.named('test') {
    testLogging {
        events 'passed', 'skipped', 'failed'
        exceptionFormat 'full'
    }
}

shadowJar {
    archiveFileName = "${rootProject.name}-${project.version}-all.jar"
}
```

- [ ] **Step 5: Write `plugin/runelite-plugin.properties`**

```properties
displayName=RuneColor Bridge
author=zakyn47
description=Pushes exact player vitals to the RuneColor bot over localhost.
plugins=com.runecolor.bridge.RuneColorBridgePlugin
```

- [ ] **Step 6: Write the hello-world plugin**

`plugin/src/main/java/com/runecolor/bridge/RuneColorBridgePlugin.java`:

```java
package com.runecolor.bridge;

import lombok.extern.slf4j.Slf4j;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;

@Slf4j
@PluginDescriptor(
        name = "RuneColor Bridge",
        description = "Pushes exact player vitals to the RuneColor bot over localhost.",
        enabledByDefault = false
)
public class RuneColorBridgePlugin extends Plugin {
    @Override
    protected void startUp() {
        log.info("RuneColor Bridge started.");
    }

    @Override
    protected void shutDown() {
        log.info("RuneColor Bridge stopped.");
    }
}
```

- [ ] **Step 7: Build the jar**

```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew shadowJar --no-daemon
```

Expected: `BUILD SUCCESSFUL` and `plugin/build/libs/runecolor-bridge-1.0-all.jar` exists.

- [ ] **Step 8: Ignore build output**

Append to `.gitignore`:

```gitignore
# RuneLite plugin build output
plugin/build/
plugin/.gradle/
```

- [ ] **Step 9: Write `plugin/README.md`**

Document, in prose matching the repo's existing README voice: what the plugin is, that it requires JDK 11, the exact build command from Step 7, the sideload procedure (copy the jar to `~/.runelite/sideloaded-plugins/`, launch RuneLite with `--developer-mode`, enable "RuneColor Bridge" in the sidebar), and an explicit note that whether the installed `RuneLite.exe` launcher forwards `--developer-mode` is **unverified** and is the first thing to check if the plugin does not appear.

- [ ] **Step 10: Commit**

```bash
git add plugin .gitignore
git commit -m "Scaffold a sideloadable RuneLite plugin"
```

---

### Task 2: Snapshot and SnapshotBuilder

The pure core: game state in, immutable value object out. No I/O, so it is fully unit-testable against a mocked `Client`.

**Files:**
- Create: `plugin/src/main/java/com/runecolor/bridge/Snapshot.java`
- Create: `plugin/src/main/java/com/runecolor/bridge/SnapshotBuilder.java`
- Test: `plugin/src/test/java/com/runecolor/bridge/SnapshotBuilderTest.java`

**Interfaces:**
- Consumes: the Gradle project from Task 1.
- Produces:
  - `Snapshot` with public final fields `schema` (int), `tick` (int), `sentAt` (long), `gameState` (String), `hitpoints` (`Snapshot.Stat`), `prayer` (`Snapshot.Stat`), `runEnergy` (Integer), `worldPoint` (`Snapshot.Point`).
  - `Snapshot.Stat` with `current` (int) and `max` (int).
  - `Snapshot.Point` with `x`, `y`, `plane` (all int).
  - `SnapshotBuilder.build(Client client, long nowMillis)` returning `Snapshot`.
  - `SnapshotBuilder.SCHEMA_VERSION` = `1`.
  - Gson serializes these with `@SerializedName` so the JSON uses `sent_at`, `game_state`, `run_energy`, `world_point`.

- [ ] **Step 1: Write the failing tests**

`plugin/src/test/java/com/runecolor/bridge/SnapshotBuilderTest.java`:

```java
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
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon
```

Expected: compilation failure — `Snapshot` and `SnapshotBuilder` do not exist.

- [ ] **Step 3: Write `Snapshot`**

```java
package com.runecolor.bridge;

import com.google.gson.annotations.SerializedName;

/** An immutable, serializable picture of the player at one game tick. */
public final class Snapshot {
    public final int schema;
    public final int tick;

    @SerializedName("sent_at")
    public final long sentAt;

    @SerializedName("game_state")
    public final String gameState;

    public final Stat hitpoints;
    public final Stat prayer;

    @SerializedName("run_energy")
    public final Integer runEnergy;

    /**
     * The player's tile.
     *
     * <p>Note that inside an instance this is instance-local, not a true world
     * coordinate. Stage A runs in the overworld so it does not matter, but anything
     * reading this inside an instance must convert first.
     */
    @SerializedName("world_point")
    public final Point worldPoint;

    Snapshot(int schema, int tick, long sentAt, String gameState, Stat hitpoints,
             Stat prayer, Integer runEnergy, Point worldPoint) {
        this.schema = schema;
        this.tick = tick;
        this.sentAt = sentAt;
        this.gameState = gameState;
        this.hitpoints = hitpoints;
        this.prayer = prayer;
        this.runEnergy = runEnergy;
        this.worldPoint = worldPoint;
    }

    /** A current and maximum pair, as the orbs show them. */
    public static final class Stat {
        public final int current;
        public final int max;

        Stat(int current, int max) {
            this.current = current;
            this.max = max;
        }
    }

    /** A tile coordinate. */
    public static final class Point {
        public final int x;
        public final int y;
        public final int plane;

        Point(int x, int y, int plane) {
            this.x = x;
            this.y = y;
            this.plane = plane;
        }
    }
}
```

- [ ] **Step 4: Write `SnapshotBuilder`**

```java
package com.runecolor.bridge;

import net.runelite.api.Client;
import net.runelite.api.Player;
import net.runelite.api.Skill;
import net.runelite.api.coords.WorldPoint;

/**
 * Turns the live client into an immutable {@link Snapshot}.
 *
 * <p>This class performs no I/O and starts no threads, so it must be called on the
 * client thread, where the {@code Client} API is safe to touch.
 */
public final class SnapshotBuilder {
    public static final int SCHEMA_VERSION = 1;

    private SnapshotBuilder() {
    }

    public static Snapshot build(Client client, long nowMillis) {
        String gameState = client.getGameState() == null
                ? "UNKNOWN"
                : client.getGameState().toString();

        Player player = client.getLocalPlayer();
        if (player == null) {
            return new Snapshot(SCHEMA_VERSION, client.getTickCount(), nowMillis,
                    gameState, null, null, null, null);
        }

        WorldPoint tile = player.getWorldLocation();
        return new Snapshot(
                SCHEMA_VERSION,
                client.getTickCount(),
                nowMillis,
                gameState,
                new Snapshot.Stat(client.getBoostedSkillLevel(Skill.HITPOINTS),
                        client.getRealSkillLevel(Skill.HITPOINTS)),
                new Snapshot.Stat(client.getBoostedSkillLevel(Skill.PRAYER),
                        client.getRealSkillLevel(Skill.PRAYER)),
                normalizeEnergy(client.getEnergy()),
                tile == null
                        ? null
                        : new Snapshot.Point(tile.getX(), tile.getY(), tile.getPlane()));
    }

    /**
     * Normalize run energy to 0-100.
     *
     * <p>{@code getEnergy()} returned 0-100 in older clients and 0-10000 in newer
     * ones. Normalizing here keeps the scale question out of Python entirely.
     */
    static int normalizeEnergy(int raw) {
        int percent = raw > 100 ? raw / 100 : raw;
        return Math.max(0, Math.min(100, percent));
    }
}
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon
```

Expected: all six tests pass.

- [ ] **Step 6: Commit**

```bash
git add plugin/src
git commit -m "Build an immutable snapshot from the live client"
```

---

### Task 3: SnapshotPublisher

The outbound pipe. Knows nothing about the game.

**Files:**
- Create: `plugin/src/main/java/com/runecolor/bridge/SnapshotPublisher.java`
- Test: `plugin/src/test/java/com/runecolor/bridge/SnapshotPublisherTest.java`

**Interfaces:**
- Consumes: `Snapshot` from Task 2.
- Produces:
  - `new SnapshotPublisher(OkHttpClient client, Gson gson, String url)`
  - `void publish(Snapshot snapshot)` — never blocks the caller, never throws.
  - `void close()` — shuts the executor down.
  - `SnapshotPublisher.toJson(Snapshot)` (package-private, for the fixture test in Task 4).

- [ ] **Step 1: Write the failing tests**

`plugin/src/test/java/com/runecolor/bridge/SnapshotPublisherTest.java`. Use a real `ServerSocket` on an ephemeral port as a throwaway HTTP sink rather than mocking OkHttp — it proves bytes actually leave the process.

```java
package com.runecolor.bridge;

import com.google.gson.Gson;
import okhttp3.OkHttpClient;
import org.junit.Test;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

public class SnapshotPublisherTest {
    private static Snapshot sample() {
        return new Snapshot(1, 5, 99L, "LOGGED_IN",
                new Snapshot.Stat(42, 55), new Snapshot.Stat(12, 43), 87,
                new Snapshot.Point(3222, 3218, 0));
    }

    @Test
    public void postsTheSnapshotAsJson() throws Exception {
        BlockingQueue<String> received = new ArrayBlockingQueue<>(1);
        try (ServerSocket server = new ServerSocket(0)) {
            Thread sink = new Thread(() -> {
                try (Socket socket = server.accept()) {
                    BufferedReader reader = new BufferedReader(
                            new InputStreamReader(socket.getInputStream()));
                    StringBuilder request = new StringBuilder();
                    String line;
                    int contentLength = 0;
                    while ((line = reader.readLine()) != null && !line.isEmpty()) {
                        request.append(line).append('\n');
                        if (line.toLowerCase().startsWith("content-length:")) {
                            contentLength =
                                    Integer.parseInt(line.split(":")[1].trim());
                        }
                    }
                    char[] body = new char[contentLength];
                    int read = 0;
                    while (read < contentLength) {
                        read += reader.read(body, read, contentLength - read);
                    }
                    request.append(new String(body));
                    OutputStream out = socket.getOutputStream();
                    out.write("HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
                            .getBytes("UTF-8"));
                    out.flush();
                    received.offer(request.toString());
                } catch (Exception ignored) {
                    // The test asserts on the queue; a failure here shows up as a
                    // timeout below.
                }
            });
            sink.setDaemon(true);
            sink.start();

            SnapshotPublisher publisher = new SnapshotPublisher(
                    new OkHttpClient(), new Gson(),
                    "http://127.0.0.1:" + server.getLocalPort() + "/api/snapshot/");
            publisher.publish(sample());

            String request = received.poll(5, TimeUnit.SECONDS);
            publisher.close();

            assertNotNull("no request arrived", request);
            assertTrue(request.startsWith("POST /api/snapshot/"));
            assertTrue(request.contains("\"schema\":1"));
            assertTrue(request.contains("\"run_energy\":87"));
            assertTrue(request.contains("\"world_point\""));
            assertTrue(request.contains("\"sent_at\":99"));
        }
    }

    @Test
    public void survivesAConnectionRefusal() throws Exception {
        int deadPort;
        try (ServerSocket probe = new ServerSocket(0)) {
            deadPort = probe.getLocalPort();
        }

        SnapshotPublisher publisher = new SnapshotPublisher(
                new OkHttpClient(), new Gson(),
                "http://127.0.0.1:" + deadPort + "/api/snapshot/");

        // Nobody is listening: this is the common case, not an error, and it must
        // neither throw nor block the caller.
        for (int i = 0; i < 20; i++) {
            publisher.publish(sample());
        }
        Thread.sleep(500);
        publisher.close();
    }

    @Test
    public void doesNotQueueABacklog() {
        SnapshotPublisher publisher = new SnapshotPublisher(
                new OkHttpClient(), new Gson(), "http://127.0.0.1:1/api/snapshot/");
        for (int i = 0; i < 1000; i++) {
            publisher.publish(sample());
        }
        assertTrue("queue must stay bounded", publisher.queueSize() <= 1);
        publisher.close();
    }
}
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon
```

Expected: compilation failure — `SnapshotPublisher` does not exist.

- [ ] **Step 3: Write `SnapshotPublisher`**

```java
package com.runecolor.bridge;

import com.google.gson.Gson;
import lombok.extern.slf4j.Slf4j;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Serializes snapshots and POSTs them to the bot.
 *
 * <p>Publishing is fire-and-forget on a queue of capacity one. If the path stalls,
 * the bot should receive the newest snapshot, never a replayed backlog of stale
 * ones, so a full queue drops the oldest entry rather than blocking or growing.
 *
 * <p>Nobody listening is the normal state: the plugin runs whenever RuneLite does,
 * while the bot's server runs only while a script runs. A connection refusal is
 * therefore logged once and then silenced until a success resets the latch, so the
 * client log does not gain a line every 600 ms forever.
 */
@Slf4j
public class SnapshotPublisher {
    private static final MediaType JSON = MediaType.get("application/json");

    private final OkHttpClient http;
    private final Gson gson;
    private final String url;
    private final ArrayBlockingQueue<Runnable> queue = new ArrayBlockingQueue<>(1);
    private final ThreadPoolExecutor executor;
    private final AtomicBoolean failureLogged = new AtomicBoolean(false);

    public SnapshotPublisher(OkHttpClient http, Gson gson, String url) {
        this.http = http;
        this.gson = gson;
        this.url = url;
        this.executor = new ThreadPoolExecutor(1, 1, 0L, TimeUnit.MILLISECONDS, queue,
                runnable -> {
                    Thread thread = new Thread(runnable, "runecolor-bridge-publisher");
                    thread.setDaemon(true);
                    return thread;
                },
                new ThreadPoolExecutor.DiscardOldestPolicy());
    }

    String toJson(Snapshot snapshot) {
        return gson.toJson(snapshot);
    }

    int queueSize() {
        return queue.size();
    }

    /** Hand a snapshot off for delivery. Never blocks, never throws. */
    public void publish(Snapshot snapshot) {
        final String body;
        try {
            body = toJson(snapshot);
        } catch (RuntimeException e) {
            logFailureOnce("Could not serialize a snapshot", e);
            return;
        }

        try {
            executor.execute(() -> send(body));
        } catch (RuntimeException e) {
            // Rejected because the executor is shutting down. Nothing to do.
            log.debug("Snapshot dropped: {}", e.toString());
        }
    }

    private void send(String body) {
        Request request = new Request.Builder()
                .url(url)
                .post(RequestBody.create(body, JSON))
                .build();
        try (Response response = http.newCall(request).execute()) {
            if (response.isSuccessful()) {
                failureLogged.set(false);
            } else {
                logFailureOnce("Bot rejected a snapshot: HTTP " + response.code(), null);
            }
        } catch (Exception e) {
            logFailureOnce("Could not reach the bot", e);
        }
    }

    private void logFailureOnce(String message, Exception cause) {
        if (failureLogged.compareAndSet(false, true)) {
            log.info("{} ({}). Further failures stay silent until one succeeds.",
                    message, cause == null ? "no exception" : cause.toString());
        }
    }

    public void close() {
        executor.shutdownNow();
    }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add plugin/src
git commit -m "Push snapshots without blocking the client thread"
```

---

### Task 4: Plugin wiring and the shared fixture

Connects builder to publisher, and freezes the wire format as a fixture that both languages test against.

**Files:**
- Modify: `plugin/src/main/java/com/runecolor/bridge/RuneColorBridgePlugin.java`
- Create: `plugin/src/main/java/com/runecolor/bridge/RuneColorBridgeConfig.java`
- Create: `tests/fixtures/snapshot_v1.json`
- Test: `plugin/src/test/java/com/runecolor/bridge/SnapshotFixtureTest.java`

**Interfaces:**
- Consumes: `SnapshotBuilder.build`, `SnapshotPublisher`.
- Produces: `tests/fixtures/snapshot_v1.json`, the canonical stage A payload, read by the Python tests in Task 5 and by the loopback test in Task 6.

- [ ] **Step 1: Write the fixture**

`tests/fixtures/snapshot_v1.json` — a single line is what the wire actually carries, but pretty-print it for readability; the test compares parsed trees, not bytes.

```json
{
  "schema": 1,
  "tick": 123456,
  "sent_at": 1757193600123,
  "game_state": "LOGGED_IN",
  "hitpoints": { "current": 42, "max": 55 },
  "prayer": { "current": 12, "max": 43 },
  "run_energy": 87,
  "world_point": { "x": 3222, "y": 3218, "plane": 0 }
}
```

- [ ] **Step 2: Write the failing fixture test**

`plugin/src/test/java/com/runecolor/bridge/SnapshotFixtureTest.java`:

```java
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
                new Snapshot.Point(3222, 3218, 0));

        Path fixture = Paths.get("..", "tests", "fixtures", "snapshot_v1.json");
        String expected = new String(Files.readAllBytes(fixture), StandardCharsets.UTF_8);

        assertEquals(JsonParser.parseString(expected),
                JsonParser.parseString(new Gson().toJson(snapshot)));
    }
}
```

- [ ] **Step 3: Run it to verify it fails**

```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --tests '*SnapshotFixtureTest*' --no-daemon
```

Expected: it fails only if serialization and fixture disagree. If it passes immediately, that is a valid result — Task 2's `@SerializedName` annotations already made it true. Record which happened.

- [ ] **Step 4: Write `RuneColorBridgeConfig`**

```java
package com.runecolor.bridge;

import net.runelite.client.config.Config;
import net.runelite.client.config.ConfigGroup;
import net.runelite.client.config.ConfigItem;
import net.runelite.client.config.Range;

@ConfigGroup("runecolorbridge")
public interface RuneColorBridgeConfig extends Config {
    @ConfigItem(
            keyName = "port",
            name = "Port",
            description = "Local port the RuneColor bot listens on.",
            position = 1
    )
    @Range(min = 1024, max = 65535)
    default int port() {
        return 8099;
    }

    @ConfigItem(
            keyName = "ticksPerPush",
            name = "Ticks per push",
            description = "Push every Nth game tick. 1 pushes every tick.",
            position = 2
    )
    @Range(min = 1, max = 10)
    default int ticksPerPush() {
        return 1;
    }
}
```

- [ ] **Step 5: Rewrite `RuneColorBridgePlugin`**

```java
package com.runecolor.bridge;

import com.google.gson.Gson;
import com.google.inject.Provides;
import lombok.extern.slf4j.Slf4j;
import net.runelite.api.Client;
import net.runelite.api.events.GameTick;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.eventbus.Subscribe;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;
import okhttp3.OkHttpClient;

import javax.inject.Inject;
import java.util.concurrent.TimeUnit;

@Slf4j
@PluginDescriptor(
        name = "RuneColor Bridge",
        description = "Pushes exact player vitals to the RuneColor bot over localhost.",
        enabledByDefault = false
)
public class RuneColorBridgePlugin extends Plugin {
    @Inject
    private Client client;

    @Inject
    private RuneColorBridgeConfig config;

    private SnapshotPublisher publisher;
    private int tickCounter;

    @Provides
    RuneColorBridgeConfig provideConfig(ConfigManager configManager) {
        return configManager.getConfig(RuneColorBridgeConfig.class);
    }

    @Override
    protected void startUp() {
        // A short timeout keeps a wedged connection from occupying the single
        // publisher thread for longer than the data stays useful.
        OkHttpClient http = new OkHttpClient.Builder()
                .connectTimeout(500, TimeUnit.MILLISECONDS)
                .readTimeout(500, TimeUnit.MILLISECONDS)
                .writeTimeout(500, TimeUnit.MILLISECONDS)
                .build();
        publisher = new SnapshotPublisher(http, new Gson(),
                "http://127.0.0.1:" + config.port() + "/api/snapshot/");
        tickCounter = 0;
        log.info("RuneColor Bridge started, pushing to port {}.", config.port());
    }

    @Override
    protected void shutDown() {
        if (publisher != null) {
            publisher.close();
            publisher = null;
        }
        log.info("RuneColor Bridge stopped.");
    }

    @Subscribe
    public void onGameTick(GameTick event) {
        // Nothing may escape this method. An exception thrown from an event handler
        // risks the client disabling the plugin mid-session, which would strand a
        // running bot on its OCR fallback without saying why.
        try {
            if (publisher == null) {
                return;
            }
            if (++tickCounter < config.ticksPerPush()) {
                return;
            }
            tickCounter = 0;
            publisher.publish(SnapshotBuilder.build(client, System.currentTimeMillis()));
        } catch (Exception e) {
            log.warn("Skipped a snapshot: {}", e.toString());
        }
    }
}
```

- [ ] **Step 6: Run the full Java suite and rebuild the jar**

```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test shadowJar --no-daemon
```

Expected: all tests pass, jar rebuilt.

- [ ] **Step 7: Commit**

```bash
git add plugin/src tests/fixtures
git commit -m "Push a snapshot every tick and pin the wire format"
```

---

### Task 5: BridgeAPI on the Python side

**Files:**
- Create: `src/utilities/api/bridge_api.py`
- Test: `tests/unit/__init__.py`, `tests/unit/test_bridge_api.py`

**Interfaces:**
- Consumes: `tests/fixtures/snapshot_v1.json`.
- Produces:
  - `BridgeAPI(port: int = 8099, max_age: float = 1.2, verbose: bool = False)`
  - `BridgeAPI.shared(port=8099, max_age=1.2) -> BridgeAPI` — process-wide instance, started on first call, so several bots in one process do not each try to bind the port.
  - Properties: `hitpoints -> Tuple[int, int]`, `prayer -> Tuple[int, int]`, `run_energy -> int`, `world_point -> Tuple[int, int, int]`, `game_state -> str`, `tick -> int`.
    Each returns the sentinel (`(-1, -1)`, `-1`, `(-1, -1, -1)`, `""`, `-1`) when no fresh snapshot is available.
  - `is_fresh() -> bool`, `age() -> float`, `fallback_count -> int`, `note_fallback() -> None`, `stop() -> None`
  - `SCHEMA_VERSION = 1`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_bridge_api.py`. Use Flask's test client where possible so no port is bound, and one real-server test to prove the bind works.

```python
"""Unit tests for the RuneColor Bridge receiver.

Run with:
    python -m unittest discover -s tests/unit -t . -v
"""

import json
import time
import unittest
from pathlib import Path

import requests

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from utilities.api.bridge_api import BridgeAPI  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "snapshot_v1.json"


def payload() -> dict:
    return json.loads(FIXTURE.read_text())


class BridgeAPITest(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = BridgeAPI(port=0, start=False)
        self.client = self.bridge.app.test_client()

    def post(self, body: dict):
        return self.client.post("/api/snapshot/", json=body)

    def test_reports_no_data_before_any_snapshot(self):
        self.assertFalse(self.bridge.is_fresh())
        self.assertEqual(self.bridge.hitpoints, (-1, -1))
        self.assertEqual(self.bridge.prayer, (-1, -1))
        self.assertEqual(self.bridge.run_energy, -1)
        self.assertEqual(self.bridge.world_point, (-1, -1, -1))
        self.assertEqual(self.bridge.game_state, "")

    def test_exposes_a_received_snapshot(self):
        self.assertEqual(self.post(payload()).status_code, 200)
        self.assertTrue(self.bridge.is_fresh())
        self.assertEqual(self.bridge.hitpoints, (42, 55))
        self.assertEqual(self.bridge.prayer, (12, 43))
        self.assertEqual(self.bridge.run_energy, 87)
        self.assertEqual(self.bridge.world_point, (3222, 3218, 0))
        self.assertEqual(self.bridge.game_state, "LOGGED_IN")
        self.assertEqual(self.bridge.tick, 123456)

    def test_goes_stale_after_max_age(self):
        self.bridge.max_age = 0.05
        self.post(payload())
        self.assertTrue(self.bridge.is_fresh())
        time.sleep(0.1)
        self.assertFalse(self.bridge.is_fresh())
        # Stale means every field falls back together, never a mixed picture.
        self.assertEqual(self.bridge.hitpoints, (-1, -1))
        self.assertEqual(self.bridge.world_point, (-1, -1, -1))

    def test_rejects_a_mismatched_schema_and_stays_disabled(self):
        body = payload()
        body["schema"] = 2
        self.assertEqual(self.post(body).status_code, 409)
        self.assertFalse(self.bridge.is_fresh())
        # A stale jar disables the bridge for the session rather than letting a
        # later good payload paper over the mismatch.
        self.assertEqual(self.post(payload()).status_code, 409)
        self.assertFalse(self.bridge.is_fresh())

    def test_ignores_a_malformed_payload(self):
        response = self.client.post(
            "/api/snapshot/", data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.bridge.is_fresh())

    def test_serves_partial_fields_when_logged_out(self):
        self.post(
            {
                "schema": 1,
                "tick": 7,
                "sent_at": 99,
                "game_state": "LOGIN_SCREEN",
                "hitpoints": None,
                "prayer": None,
                "run_energy": None,
                "world_point": None,
            }
        )
        self.assertTrue(self.bridge.is_fresh())
        self.assertEqual(self.bridge.game_state, "LOGIN_SCREEN")
        self.assertEqual(self.bridge.hitpoints, (-1, -1))
        self.assertEqual(self.bridge.world_point, (-1, -1, -1))

    def test_counts_fallbacks(self):
        self.assertEqual(self.bridge.fallback_count, 0)
        self.bridge.note_fallback()
        self.bridge.note_fallback()
        self.assertEqual(self.bridge.fallback_count, 2)

    def test_rejects_a_get(self):
        self.assertEqual(self.client.get("/api/snapshot/").status_code, 405)


class BridgeAPIServerTest(unittest.TestCase):
    """Proves the real server binds and answers, which the test client cannot."""

    def test_binds_a_port_and_receives_over_the_wire(self):
        bridge = BridgeAPI(port=8123)
        try:
            response = requests.post(
                "http://127.0.0.1:8123/api/snapshot/", json=payload(), timeout=5
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(bridge.hitpoints, (42, 55))
        finally:
            bridge.stop()

    def test_raises_when_the_port_is_taken(self):
        first = BridgeAPI(port=8124)
        try:
            with self.assertRaises(OSError):
                BridgeAPI(port=8124)
        finally:
            first.stop()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m unittest discover -s tests/unit -t . -v
```

Expected: `ModuleNotFoundError: No module named 'utilities.api.bridge_api'`.

- [ ] **Step 3: Write `src/utilities/api/bridge_api.py`**

Follow `events_api.py`'s structure and the repo's Google-style docstrings. Requirements the tests pin:

- A `Flask` app with one route, `POST /api/snapshot/`, returning 200 on success, 409 on schema mismatch, 400 on malformed JSON, 405 on any other method.
- Constructor signature `__init__(self, port=8099, max_age=1.2, verbose=False, start=True)`. `start=False` builds the app without binding, for tests.
- Serve with `werkzeug.serving.make_server` rather than `app.run`, so the socket binds on the calling thread and a port collision raises `OSError` to the caller instead of dying silently in a daemon thread. Hold the server object and serve in a daemon thread; `stop()` calls `shutdown()`.
- Store `self._snapshot` and `self._arrived_at = time.time()` on receipt. Freshness is measured from arrival, never from the payload's `sent_at`, which avoids clock skew and measures the thing that matters.
- On schema mismatch, log once at ERROR, set `self._disabled = True`, and reject every subsequent payload with 409.
- Every accessor returns its sentinel unless `is_fresh()`, so a stale feed retires all fields together.
- `shared()` is a classmethod holding a module-level instance guarded by a `threading.Lock`.
- `stop()` is idempotent.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m unittest discover -s tests/unit -t . -v
```

Expected: all tests pass.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files src/utilities/api/bridge_api.py tests/unit/test_bridge_api.py
```

Expected: all hooks pass (black may reformat; re-run until clean).

- [ ] **Step 6: Commit**

```bash
git add src/utilities/api/bridge_api.py tests/unit
git commit -m "Receive pushed snapshots and expire them together"
```

---

### Task 6: Cross-language loopback test

Proves the Java publisher and the Python receiver agree on the wire, without a game.

**Files:**
- Create: `plugin/src/test/java/com/runecolor/bridge/LoopbackMain.java`
- Create: `tests/loopback_bridge.py`
- Modify: `plugin/build.gradle`

**Interfaces:**
- Consumes: `SnapshotPublisher`, `BridgeAPI`.
- Produces: `python tests/loopback_bridge.py` exits 0 when the real Java publisher's bytes are parsed correctly by the real Python receiver.

- [ ] **Step 1: Write `LoopbackMain`**

A tiny main that publishes one hardcoded snapshot to a URL given on the command line, then exits.

```java
package com.runecolor.bridge;

import com.google.gson.Gson;
import okhttp3.OkHttpClient;

/** Publishes one snapshot to the URL in {@code args[0]}, for the loopback test. */
public final class LoopbackMain {
    public static void main(String[] args) throws Exception {
        SnapshotPublisher publisher =
                new SnapshotPublisher(new OkHttpClient(), new Gson(), args[0]);
        publisher.publish(new Snapshot(1, 123456, 1757193600123L, "LOGGED_IN",
                new Snapshot.Stat(42, 55), new Snapshot.Stat(12, 43), 87,
                new Snapshot.Point(3222, 3218, 0)));
        Thread.sleep(2000);
        publisher.close();
    }
}
```

- [ ] **Step 2: Add a Gradle task to run it**

Append to `plugin/build.gradle`:

```groovy
tasks.register('loopback', JavaExec) {
    group = 'verification'
    description = 'Publishes one snapshot to the URL in -Purl, for the loopback test.'
    classpath = sourceSets.test.runtimeClasspath
    mainClass = 'com.runecolor.bridge.LoopbackMain'
    args = [project.findProperty('url') ?: 'http://127.0.0.1:8099/api/snapshot/']
}
```

- [ ] **Step 3: Write `tests/loopback_bridge.py`**

```python
"""Prove the Java plugin and the Python receiver agree on the wire.

This needs no game and no account. It starts the real `BridgeAPI`, runs the real
`SnapshotPublisher` in a JVM, and checks that what arrives parses into the values
the publisher sent. It is the widest test that can run without a live client.

Usage:
    python tests/loopback_bridge.py
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from utilities.api.bridge_api import BridgeAPI  # noqa: E402

PORT = 8131
JAVA_HOME = Path.home() / "tools" / "jdk-11"


def main() -> int:
    bridge = BridgeAPI(port=PORT)
    try:
        result = subprocess.run(
            [
                str(ROOT / "plugin" / "gradlew.bat"),
                "loopback",
                f"-Purl=http://127.0.0.1:{PORT}/api/snapshot/",
                "--no-daemon",
                "-q",
            ],
            cwd=str(ROOT / "plugin"),
            env={**__import__("os").environ, "JAVA_HOME": str(JAVA_HOME)},
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            print("FAIL: the publisher did not run")
            return 1

        deadline = time.time() + 10
        while time.time() < deadline and not bridge.is_fresh():
            time.sleep(0.1)

        checks = {
            "is_fresh": (bridge.is_fresh(), True),
            "hitpoints": (bridge.hitpoints, (42, 55)),
            "prayer": (bridge.prayer, (12, 43)),
            "run_energy": (bridge.run_energy, 87),
            "world_point": (bridge.world_point, (3222, 3218, 0)),
            "game_state": (bridge.game_state, "LOGGED_IN"),
            "tick": (bridge.tick, 123456),
        }
        failed = {k: v for k, v in checks.items() if v[0] != v[1]}
        for name, (actual, expected) in checks.items():
            mark = "FAIL" if name in failed else "ok"
            print(f"[{mark}] {name}: {actual!r} (expected {expected!r})")

        print("FAIL" if failed else "PASS")
        return 1 if failed else 0
    finally:
        bridge.stop()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run it**

```bash
python tests/loopback_bridge.py
```

Expected: every line `[ok]`, final line `PASS`, exit code 0.

- [ ] **Step 5: Lint and commit**

```bash
pre-commit run --files tests/loopback_bridge.py
git add plugin tests/loopback_bridge.py
git commit -m "Prove both halves agree on the wire without a game"
```

---

### Task 7: Wire the fallback into RuneLiteBot

**Files:**
- Modify: `src/model/runelite_bot.py` (`__init__` at :53, `get_hp` at :1986, `get_prayer` at :1998, `get_run_energy`, `get_world_point` at :2119)
- Test: `tests/unit/test_bridge_fallback.py`

**Interfaces:**
- Consumes: `BridgeAPI` from Task 5.
- Produces:
  - `RuneLiteBot.bridge` — `None` by default.
  - `RuneLiteBot.attach_bridge(port: int = 8099, max_age: float = 1.2) -> None`
  - `RuneLiteBot.detach_bridge() -> None`
  - `get_hp`, `get_prayer`, `get_run_energy` and `get_world_point` keep their existing signatures and return values.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_bridge_fallback.py`. `RuneLiteBot` is abstract and drags in the whole window stack, so test the decision logic through a small stand-in that holds the same helper. Extract that helper as `RuneLiteBot._from_bridge` so the test targets real code rather than a copy.

```python
"""The bridge-versus-OCR decision, tested without a client or a window."""

import logging
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.runelite_bot import RuneLiteBot  # noqa: E402


class FakeBridge:
    def __init__(self, fresh: bool, value):
        self._fresh = fresh
        self._value = value
        self.fallbacks = 0

    def is_fresh(self) -> bool:
        return self._fresh

    def note_fallback(self) -> None:
        self.fallbacks += 1


class BridgeFallbackTest(unittest.TestCase):
    def test_uses_the_bridge_when_fresh(self):
        bridge = FakeBridge(fresh=True, value=42)
        self.assertEqual(
            RuneLiteBot._from_bridge(bridge, lambda: 42, lambda: 41, "hp", -1), 42
        )

    def test_falls_back_to_ocr_when_stale(self):
        bridge = FakeBridge(fresh=False, value=None)
        self.assertEqual(
            RuneLiteBot._from_bridge(bridge, lambda: 42, lambda: 41, "hp", -1), 41
        )
        self.assertEqual(bridge.fallbacks, 1)

    def test_falls_back_to_ocr_when_no_bridge_attached(self):
        self.assertEqual(
            RuneLiteBot._from_bridge(None, lambda: 42, lambda: 41, "hp", -1), 41
        )

    def test_warns_when_the_two_disagree(self):
        bridge = FakeBridge(fresh=True, value=42)
        with self.assertLogs(level=logging.WARNING) as captured:
            RuneLiteBot._from_bridge(bridge, lambda: 42, lambda: 41, "hp", -1)
        self.assertTrue(any("hp" in line for line in captured.output))

    def test_does_not_warn_when_ocr_simply_failed(self):
        # A failed OCR read is the sentinel, not a disagreement worth reporting.
        bridge = FakeBridge(fresh=True, value=42)
        RuneLiteBot._from_bridge(bridge, lambda: 42, lambda: -1, "hp", -1)

    def test_survives_an_ocr_comparison_that_raises(self):
        bridge = FakeBridge(fresh=True, value=42)

        def explode():
            raise RuntimeError("no window")

        # The comparison is diagnostics; it must never break the read it audits.
        self.assertEqual(
            RuneLiteBot._from_bridge(bridge, lambda: 42, explode, "hp", -1), 42
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m unittest discover -s tests/unit -t . -v
```

Expected: `AttributeError: type object 'RuneLiteBot' has no attribute '_from_bridge'`.

- [ ] **Step 3: Add `_from_bridge` and the attach helpers to `RuneLiteBot`**

Add `bridge: BridgeAPI = None` beside the existing `win` class attribute, set `self.bridge = None` in `__init__`, and add:

```python
    # --- Bridge ---
    def attach_bridge(self, port: int = 8099, max_age: float = 1.2) -> None:
        """Start receiving exact game state from the RuneColor Bridge plug-in.

        Attaching is opt-in because it binds a port. Once attached, `get_hp`,
        `get_prayer`, `get_run_energy` and `get_world_point` prefer the plug-in's
        exact values and fall back to OCR whenever the feed goes stale, so a plug-in
        that is not running costs nothing but the fallbacks it logs.

        Args:
            port (int, optional): The local port to listen on. Defaults to 8099.
            max_age (float, optional): How many seconds a snapshot stays usable.
                Defaults to 1.2, two game ticks.
        """
        self.bridge = BridgeAPI.shared(port=port, max_age=max_age)

    def detach_bridge(self) -> None:
        """Stop preferring plug-in values, reverting every read to OCR."""
        self.bridge = None

    @staticmethod
    def _from_bridge(bridge, read_bridge, read_ocr, label: str, sentinel):
        """Return the plug-in's value if it is fresh, otherwise the OCR value.

        A stale or absent feed is not an error. It is the state the bot runs in
        whenever the plug-in is not loaded, so it falls through to the OCR read that
        has always been there.

        Args:
            bridge (Optional[BridgeAPI]): The attached bridge, or None.
            read_bridge (Callable): Reads the value from the bridge.
            read_ocr (Callable): Reads the value from the screen.
            label (str): Name of the value, for the disagreement warning.
            sentinel: The value an OCR read returns when it fails.

        Returns:
            The plug-in's value when fresh, otherwise the OCR value.
        """
        if bridge is None or not bridge.is_fresh():
            if bridge is not None:
                bridge.note_fallback()
            return read_ocr()

        value = read_bridge()
        try:
            seen = read_ocr()
            # A failed OCR read is the sentinel, not a disagreement worth reporting.
            if seen != sentinel and seen != value:
                log.warning(
                    "Bridge and OCR disagree on %s: bridge=%r, screen=%r.",
                    label, value, seen,
                )
        except Exception as e:  # noqa: BLE001
            # The comparison is diagnostics. It must never break the read it audits.
            log.debug("Could not compare %s against the screen: %s", label, e)
        return value
```

If `runelite_bot.py` has no module logger, add one (`log = logging.getLogger(__name__)`) next to the existing imports, matching however the rest of `src/` obtains loggers — check `src/model/bot.py` first and follow it.

The disagreement comparison runs on every read during stage A. Guard it behind a module-level `_COMPARE_WITH_OCR = True` constant with a comment saying it is a stage A measurement to be turned off at stage 3, so the cost is deliberate and easy to remove.

- [ ] **Step 4: Rewrite the four readers to go through the helper**

Each keeps its docstring and its OCR body; the OCR body moves into a nested function. For example, `get_hp` becomes:

```python
    def get_hp(self) -> int:
        """Get our character's HP value.

        Prefers the RuneColor Bridge plug-in's exact value when a bridge is attached
        and its feed is fresh, falling back to reading the HP orb off the screen.

        Returns:
            int: The HP of the player, or -1 if the value couldn't be read.
        """

        def from_screen() -> int:
            if hp := ocr.scrape_text(
                self.win.hp_orb_text, ocr.PLAIN_11, [self.cp.bgr.GREEN, self.cp.bgr.RED]
            ):
                return int("".join(re.findall(r"\d", hp)))
            return -1

        return self._from_bridge(
            self.bridge, lambda: self.bridge.hitpoints[0], from_screen, "hp", -1
        )
```

Apply the same shape to `get_prayer` (`self.bridge.prayer[0]`, label `"prayer"`, sentinel `-1`), `get_run_energy` (`self.bridge.run_energy`, label `"run energy"`, sentinel `-1`) and `get_world_point` (`self.bridge.world_point`, label `"world point"`, sentinel `(-1, -1, -1)`).

Do not touch `get_world_point_reliably`. Its retry loop becomes harmless once reads succeed on the first attempt, and removing it is stage 3 work that needs live evidence first.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
python -m unittest discover -s tests/unit -t . -v
```

Expected: all tests pass.

- [ ] **Step 6: Verify nothing regressed at import time**

```bash
python -c "import sys; sys.path.insert(0, 'src'); import model.runelite_bot; print('ok')"
```

Expected: `ok`.

- [ ] **Step 7: Lint and commit**

```bash
pre-commit run --files src/model/runelite_bot.py tests/unit/test_bridge_fallback.py
git add src/model/runelite_bot.py tests/unit/test_bridge_fallback.py
git commit -m "Prefer the plug-in's numbers, keep OCR as the fallback"
```

---

### Task 8: The live test and the documentation

The test that actually decides whether the plugin is right. It cannot run unattended — it needs a client and an account — so it is written, committed, and left ready.

**Files:**
- Create: `tests/live_bridge.py`
- Modify: `tests/README.md`
- Modify: `plugin/README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: `python tests/live_bridge.py --minutes 10` writing an agreement report.

- [ ] **Step 1: Write `tests/live_bridge.py`**

Follow `tests/live_power_chopper.py` for structure, argument style and output format: a module docstring explaining what is measured and why, `argparse` with `--minutes` and `--out`, per-sample printing, and a JSON summary written at the end.

What it must do:

1. Attach a bridge (`BridgeAPI(port=8099)`).
2. Instantiate a concrete bot so the OCR readers work — reuse whatever `live_power_chopper.py` does to get a usable bot against a live client, and follow its login handling.
3. Sample once per second for `--minutes`: read hitpoints, prayer, run energy and world point from the bridge, and read each one off the screen, recording both.
4. Track per-field `agreements`, `disagreements` (with both values and a timestamp), `bridge_unavailable` (samples where `is_fresh()` was False), and `ocr_failed` (samples where OCR returned its sentinel — these are excluded from agreement counts, since they measure OCR, not the bridge).
5. Print a table at the end: per field, agreement percentage, disagreement count, and the first five disagreements in full.
6. Report `availability` — the share of samples where the bridge was fresh.
7. Exit non-zero if there were any disagreements or if availability is below 99%, so it can gate stage 3.

The docstring must state the exit criteria from the spec explicitly: zero unexplained disagreements across a full session and availability above 99%.

- [ ] **Step 2: Lint it**

```bash
pre-commit run --files tests/live_bridge.py
```

Expected: all hooks pass.

- [ ] **Step 3: Check it runs far enough to fail honestly**

```bash
python tests/live_bridge.py --minutes 0.05
```

With no client running this must exit non-zero with a clear message about the client, not a traceback from an unrelated layer. It must not report success.

- [ ] **Step 4: Update `tests/README.md`**

Add a "RuneColor Bridge" section covering: building and sideloading the jar (pointing at `plugin/README.md`), that the plugin must be enabled in the sidebar, that port 8099 must be free, and how to run `live_bridge.py` and read its output. Add a row to the prerequisites table for the plugin.

Keep the World Location plugin row exactly as it is, and say why: `live_bridge.py` compares the bridge against that overlay, so the overlay is required for stage A and only becomes optional at stage 3.

- [ ] **Step 5: Finish `plugin/README.md`**

Add the config options (port, ticks per push), the payload example from `tests/fixtures/snapshot_v1.json`, and a note that `schema` must match `BridgeAPI.SCHEMA_VERSION` — a stale jar in `~/.runelite/sideloaded-plugins/` is the likely cause of a schema rejection, because the jar does not rebuild on `git pull`.

- [ ] **Step 6: Commit**

```bash
git add tests/live_bridge.py tests/README.md plugin/README.md
git commit -m "Measure the plug-in against the screen on a live client"
```

---

## Self-Review

**Spec coverage.** Architecture → Tasks 2, 3, 4, 5, 7. Data contract → Tasks 2 and 4 (fixture), verified from both sides in Tasks 4, 5, 6. Error handling: queue of one and the log latch → Task 3; `onGameTick` never throws → Task 4; logged-out pushes → Tasks 2 and 5; fail-safe Python and the bind fix → Task 5; fallback counting → Tasks 5 and 7. Testing: sideload spike → Task 1; Java units → Task 2; Python units → Task 5; loopback → Task 6; `live_bridge.py` → Task 8. Rollout stages 0-2 → Tasks 1-7; stage 3 is deliberately excluded, as it needs live evidence; stage 4 has its own spec.

**Placeholders.** None. Task 5 Step 3 and Task 8 Step 1 give requirements rather than complete listings — deliberate: `bridge_api.py` closely follows the existing `events_api.py`, and `live_bridge.py` follows `live_power_chopper.py`, so both are better written against the file in front of the implementer than transcribed here. Every behavior either is pinned by a test written out in full, or is an enumerated requirement.

**Type consistency.** `Snapshot` field names match between Task 2 (definition), Task 3 (test construction), Task 4 (fixture and `LoopbackMain`) and Task 6. `BridgeAPI`'s accessors are named identically in Tasks 5, 6 and 7. `_from_bridge`'s five-argument signature matches between its tests in Task 7 Step 1 and its four call sites in Task 7 Step 4. The JSON keys in the fixture match the `@SerializedName` annotations in Task 2.

**Known risk, carried deliberately.** Task 1 Step 7 is the first point where an unverified assumption can fail: `net.runelite:client` must resolve from `repo.runelite.net`. And whether the installed `RuneLite.exe` forwards `--developer-mode` cannot be settled without a human at the client — Task 1 Step 9 documents it as the first thing to check.
