# Per-script RuneLite Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Selecting a script in the RuneColor UI switches the running RuneLite client to that script's committed profile, live, unless the user ticks "Use my own RuneLite profile".

**Architecture:** Python states the wanted profile in its JSON reply to each snapshot the RuneColor Bridge plug-in POSTs. A new `ProfileSwitcher` in the plug-in compares it with the active profile and, when they differ, imports the repo's `.properties` file into a "RuneColor - <title>" profile and switches to it, the same way RuneLite's Profiles panel does. The snapshot reports the active profile's name back, so the UI can confirm the switch.

**Tech Stack:** Python 3.10 (Flask, customtkinter, unittest), Java 11 plug-in against RuneLite client 1.12.38 (Gson, OkHttp, JUnit 4, Mockito 4), Gradle.

**Spec:** `docs/superpowers/specs/2026-09-27-runelite-profiles-design.md`

## Global Constraints

- Never resize the RuneLite client. Profiles must not contain `runelite.clientBounds` or `runelite.clientMaximized`.
- Every script profile contains `runelite.runecolorbridgeplugin=true`.
- RuneLite profile name: `RuneColor - <bot_title>`, e.g. `RuneColor - Power Chopper & Firemaking`.
- The snapshot schema stays at 1. New fields are optional.
- The opt-out setting key is `use_own_runelite_profile`, stored with `utilities.settings`.
- Confirmation timeout: 10 s.
- Commits: ask the user before committing. No `Co-Authored-By` or `Claude-Session` lines.
- Python checks: `venv/Scripts/python.exe -m unittest discover -s tests/unit -t .`, `venv/Scripts/flake8.exe <files>`, `venv/Scripts/black.exe --check <files>`.
- Java checks: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test shadowJar --no-daemon -q`.
- Comments explain why, never what. Match the surrounding code's docstring style.

---

### Task 1: The bridge states the wanted profile and reads the active one (Python)

**Files:**
- Modify: `src/utilities/api/bridge_api.py`
- Test: `tests/unit/test_bridge_api.py`

**Interfaces:**
- Produces: `BridgeAPI.request_profile(name: str, path: str) -> None`, `BridgeAPI.clear_profile() -> None`, `BridgeAPI.active_profile -> Optional[str]` (property). The snapshot POST reply becomes JSON `{"profile": {"name": str, "path": str}}` or `{"profile": null}`.

- [ ] **Step 1: Write the failing tests** (append to `BridgeAPITest`)

```python
    def test_replies_with_no_profile_by_default(self):
        self.assertEqual(self.post(payload()).get_json(), {"profile": None})

    def test_replies_with_the_requested_profile(self):
        self.bridge.request_profile("RuneColor - X", "C:/profiles/x.properties")
        reply = self.post(payload()).get_json()
        self.assertEqual(
            reply,
            {"profile": {"name": "RuneColor - X", "path": "C:/profiles/x.properties"}},
        )

    def test_a_cleared_profile_is_no_longer_requested(self):
        self.bridge.request_profile("RuneColor - X", "C:/profiles/x.properties")
        self.bridge.clear_profile()
        self.assertEqual(self.post(payload()).get_json(), {"profile": None})

    def test_exposes_the_active_profile(self):
        self.post(dict(payload(), profile="RuneColor - X"))
        self.assertEqual(self.bridge.active_profile, "RuneColor - X")

    def test_reports_no_active_profile_from_a_plugin_that_predates_it(self):
        self.post(payload())
        self.assertIsNone(self.bridge.active_profile)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python.exe -m unittest tests.unit.test_bridge_api -v`
Expected: the five new tests FAIL (`AttributeError: 'BridgeAPI' object has no attribute 'request_profile'`, and `get_json()` returning None for the plain-text reply).

- [ ] **Step 3: Implement**

In `bridge_api.py`, change the Flask import to `from flask import Flask, jsonify, request`. In `__init__`, after `self._idle_since = None`, add:

```python
        # The profile the plug-in should switch the client to, as the reply to every
        # snapshot states it. A stated wish rather than a one-off command, so a reply
        # that goes astray is simply corrected by the next one.
        self._wanted_profile: Optional[Dict[str, str]] = None
```

In `handle_snapshot`, replace `return "Snapshot received.", 200` with:

```python
                wanted = self._wanted_profile
            return jsonify(profile=wanted), 200
```

(`wanted = self._wanted_profile` goes inside the existing `with self._lock:` block, as its last line, so the reply and the stored snapshot are read under the same lock. Update the docstring's Returns to say it returns the JSON reply.)

Add these methods after `note_fallback`:

```python
    def request_profile(self, name: str, path: str) -> None:
        """Ask the plug-in to switch the client to a RuneLite profile.

        Args:
            name (str): The profile's name inside RuneLite.
            path (str): The absolute path of the `.properties` file to import.
        """
        with self._lock:
            self._wanted_profile = {"name": name, "path": path}

    def clear_profile(self) -> None:
        """Stop asking for a profile. The client stays on whichever it has."""
        with self._lock:
            self._wanted_profile = None
```

Add this property after `fire`:

```python
    @property
    def active_profile(self) -> Optional[str]:
        """Optional[str]: The name of the client's active RuneLite profile, or None.

        None if the feed is stale or the plug-in predates this field.
        """
        value = self._field("profile", None)
        return None if value is None else str(value)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m unittest tests.unit.test_bridge_api -v`
Expected: all PASS. Then run the full suite and flake8/black on both files.

- [ ] **Step 5: Commit** (after the user's go-ahead)

```bash
git add src/utilities/api/bridge_api.py tests/unit/test_bridge_api.py
git commit -m "Let the bridge ask for a RuneLite profile and read the active one"
```

---

### Task 2: The snapshot carries the active profile (Java)

**Files:**
- Modify: `plugin/src/main/java/com/runecolor/bridge/Snapshot.java`
- Modify: `plugin/src/main/java/com/runecolor/bridge/SnapshotBuilder.java`
- Modify: `plugin/src/test/java/com/runecolor/bridge/SnapshotFixtureTest.java`
- Modify: `plugin/src/test/java/com/runecolor/bridge/SnapshotPublisherTest.java:30-32`
- Modify: `plugin/src/test/java/com/runecolor/bridge/LoopbackMain.java:11`
- Modify: `plugin/src/test/java/com/runecolor/bridge/SnapshotBuilderTest.java`
- Modify: `tests/fixtures/snapshot_v1.json`
- Test: `tests/unit/test_bridge_api.py` (fixture now carries a profile)

**Interfaces:**
- Consumes: Task 1's `active_profile`.
- Produces: `Snapshot.profile` (String, JSON key `profile`, omitted when null); `SnapshotBuilder.build(Client client, long nowMillis, String profile)`. `build(Client, long)` stays and passes null.

- [ ] **Step 1: Write the failing tests**

In `SnapshotBuilderTest`, add:

```java
    @Test
    public void carriesTheActiveProfile() {
        assertEquals("RuneColor - X",
                SnapshotBuilder.build(loggedInClient(), 0L, "RuneColor - X").profile);
    }
```

In `tests/fixtures/snapshot_v1.json`, add `"profile": "RuneColor - Test"` as the last field (after `fire`). In `SnapshotFixtureTest`, pass `"RuneColor - Test"` as a new last constructor argument. In `test_bridge_api.py`, add:

```python
    def test_exposes_the_fixtures_active_profile(self):
        self.post(payload())
        self.assertEqual(self.bridge.active_profile, "RuneColor - Test")
```

and change `test_reports_no_active_profile_from_a_plugin_that_predates_it` to post `{k: v for k, v in payload().items() if k != "profile"}`.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon -q`
Expected: compilation FAILS (`build(Client,long,String)` and the 12-argument constructor don't exist).

- [ ] **Step 3: Implement**

In `Snapshot.java`, add after `fire`:

```java
    /** The name of the client's active RuneLite profile, or null if unknown. */
    public final String profile;
```

Add `String profile` as the constructor's last parameter and `this.profile = profile;`. In `SnapshotBuilder`, rename `build(Client, long)` to `build(Client client, long nowMillis, String profile)`, pass `profile` as the last argument in both `new Snapshot(...)` calls (the logged-out one too), and add:

```java
    public static Snapshot build(Client client, long nowMillis) {
        return build(client, nowMillis, null);
    }
```

Add `, null` as the last constructor argument in `SnapshotPublisherTest.sample()` and in `LoopbackMain`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon -q`, then the Python suite.
Expected: both PASS.

- [ ] **Step 5: Commit** (after the user's go-ahead)

```bash
git add plugin/src tests/fixtures/snapshot_v1.json tests/unit/test_bridge_api.py
git commit -m "Report the active RuneLite profile in every snapshot"
```

---

### Task 3: ProfileSwitcher decides when to switch (Java)

**Files:**
- Create: `plugin/src/main/java/com/runecolor/bridge/ProfileStore.java`
- Create: `plugin/src/main/java/com/runecolor/bridge/ProfileRequest.java`
- Create: `plugin/src/main/java/com/runecolor/bridge/ProfileSwitcher.java`
- Test: `plugin/src/test/java/com/runecolor/bridge/ProfileSwitcherTest.java`

**Interfaces:**
- Produces: `interface ProfileStore { String activeName(); void apply(String name, File file) throws Exception; }`, `ProfileSwitcher(ProfileStore store, Executor executor, Gson gson)` with `void onReply(String body)`.

- [ ] **Step 1: Write the failing tests**

```java
package com.runecolor.bridge;

import com.google.gson.Gson;
import org.junit.Test;

import java.io.File;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Queue;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class ProfileSwitcherTest {
    private static final String WANT_X =
            "{\"profile\":{\"name\":\"RuneColor - X\",\"path\":\"C:/p/x.properties\"}}";

    private static final class FakeStore implements ProfileStore {
        String active = "Mine";
        boolean fail;
        final List<String> applied = new ArrayList<>();

        @Override
        public String activeName() {
            return active;
        }

        @Override
        public void apply(String name, File file) throws Exception {
            applied.add(name + "@" + file.getPath());
            if (fail) {
                throw new Exception("broken file");
            }
            active = name;
        }
    }

    @Test
    public void switchesWhenTheWantedProfileIsNotActive() {
        FakeStore store = new FakeStore();
        new ProfileSwitcher(store, Runnable::run, new Gson()).onReply(WANT_X);
        assertEquals(1, store.applied.size());
        assertTrue(store.applied.get(0).startsWith("RuneColor - X@"));
        assertEquals("RuneColor - X", store.active);
    }

    @Test
    public void doesNothingWhenTheProfileIsAlreadyActive() {
        FakeStore store = new FakeStore();
        store.active = "RuneColor - X";
        new ProfileSwitcher(store, Runnable::run, new Gson()).onReply(WANT_X);
        assertTrue(store.applied.isEmpty());
    }

    @Test
    public void ignoresANullProfile() {
        FakeStore store = new FakeStore();
        new ProfileSwitcher(store, Runnable::run, new Gson()).onReply("{\"profile\":null}");
        assertTrue(store.applied.isEmpty());
    }

    @Test
    public void ignoresAReplyFromABotThatPredatesProfiles() {
        FakeStore store = new FakeStore();
        new ProfileSwitcher(store, Runnable::run, new Gson()).onReply("Snapshot received.");
        assertTrue(store.applied.isEmpty());
    }

    @Test
    public void doesNotRetryAFailedFileUntilTheRequestChanges() {
        FakeStore store = new FakeStore();
        store.fail = true;
        ProfileSwitcher switcher = new ProfileSwitcher(store, Runnable::run, new Gson());
        switcher.onReply(WANT_X);
        switcher.onReply(WANT_X);
        assertEquals(1, store.applied.size());

        switcher.onReply("{\"profile\":null}");
        switcher.onReply(WANT_X);
        assertEquals(2, store.applied.size());
    }

    @Test
    public void ignoresRepeatsWhileASwitchIsInFlight() {
        FakeStore store = new FakeStore();
        Queue<Runnable> pending = new ArrayDeque<>();
        ProfileSwitcher switcher = new ProfileSwitcher(store, pending::add, new Gson());
        switcher.onReply(WANT_X);
        switcher.onReply(WANT_X);
        assertEquals(1, pending.size());
        pending.remove().run();
        assertEquals(1, store.applied.size());
    }
}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon -q`
Expected: compilation FAILS (`ProfileStore`, `ProfileSwitcher` missing).

- [ ] **Step 3: Implement**

`ProfileStore.java`:

```java
package com.runecolor.bridge;

import java.io.File;

/** Where RuneLite profiles are read and switched, kept apart so the rules can be tested. */
public interface ProfileStore {
    /** The name of the active profile, or null if there is none. */
    String activeName();

    /** Import the file into a profile of this name and make it the active one. */
    void apply(String name, File file) throws Exception;
}
```

`ProfileRequest.java`:

```java
package com.runecolor.bridge;

import java.util.Objects;

/** The profile the bot wants, as stated in its reply to a snapshot. */
public final class ProfileRequest {
    public final String name;
    public final String path;

    ProfileRequest(String name, String path) {
        this.name = name;
        this.path = path;
    }

    boolean isComplete() {
        return name != null && path != null;
    }

    @Override
    public boolean equals(Object other) {
        if (!(other instanceof ProfileRequest)) {
            return false;
        }
        ProfileRequest that = (ProfileRequest) other;
        return Objects.equals(name, that.name) && Objects.equals(path, that.path);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, path);
    }
}
```

`ProfileSwitcher.java`:

```java
package com.runecolor.bridge;

import com.google.gson.Gson;
import lombok.extern.slf4j.Slf4j;

import java.io.File;
import java.util.concurrent.Executor;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Switches the client to the profile the bot asks for in its snapshot replies.
 *
 * <p>The bot states its wish on every reply, so this sees the same request about
 * twice a second. It acts only when the wanted profile is not the active one, never
 * runs two switches at once, and does not retry a file that failed until the bot asks
 * for something else, so a broken file cannot turn into a switch loop.
 */
@Slf4j
public class ProfileSwitcher {
    private final ProfileStore store;
    private final Executor executor;
    private final Gson gson;
    private final AtomicBoolean inFlight = new AtomicBoolean(false);
    private volatile ProfileRequest failed;

    public ProfileSwitcher(ProfileStore store, Executor executor, Gson gson) {
        this.store = store;
        this.executor = executor;
        this.gson = gson;
    }

    /** Act on one reply body. Never throws: it runs on the publisher thread. */
    public void onReply(String body) {
        ProfileRequest wanted = parse(body);
        if (wanted != null && wanted.equals(failed)) {
            return;
        }
        failed = null;
        if (wanted == null || !wanted.isComplete()
                || wanted.name.equals(store.activeName())) {
            return;
        }
        if (!inFlight.compareAndSet(false, true)) {
            return;
        }
        try {
            executor.execute(() -> apply(wanted));
        } catch (RuntimeException e) {
            inFlight.set(false);
            log.debug("Profile switch not scheduled: {}", e.toString());
        }
    }

    private ProfileRequest parse(String body) {
        try {
            Reply reply = gson.fromJson(body, Reply.class);
            return reply == null ? null : reply.profile;
        } catch (RuntimeException e) {
            return null;
        }
    }

    private void apply(ProfileRequest wanted) {
        try {
            store.apply(wanted.name, new File(wanted.path));
            log.info("Switched to RuneLite profile {}.", wanted.name);
        } catch (Exception e) {
            failed = wanted;
            log.warn("Could not switch to RuneLite profile {} from {}: {}",
                    wanted.name, wanted.path, e.toString());
        } finally {
            inFlight.set(false);
        }
    }

    private static final class Reply {
        ProfileRequest profile;
    }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon -q`
Expected: PASS.

- [ ] **Step 5: Commit** (after the user's go-ahead)

```bash
git add plugin/src
git commit -m "Decide when the plug-in should switch RuneLite profiles"
```

---

### Task 4: Wire the switcher into the plug-in and RuneLite (Java)

**Files:**
- Create: `plugin/src/main/java/com/runecolor/bridge/RuneLiteProfileStore.java`
- Modify: `plugin/src/main/java/com/runecolor/bridge/SnapshotPublisher.java`
- Modify: `plugin/src/main/java/com/runecolor/bridge/RuneColorBridgePlugin.java`
- Test: `plugin/src/test/java/com/runecolor/bridge/SnapshotPublisherTest.java`

**Interfaces:**
- Consumes: Task 2's `SnapshotBuilder.build(Client, long, String)`, Task 3's `ProfileSwitcher`, `ProfileStore`.
- Produces: `SnapshotPublisher(OkHttpClient http, Gson gson, String url, Consumer<String> onReply)`. The 3-argument constructor stays and passes a no-op.

- [ ] **Step 1: Write the failing test** (in `SnapshotPublisherTest`)

```java
    @Test
    public void handsTheReplyBodyToItsHandler() throws Exception {
        BlockingQueue<String> replies = new ArrayBlockingQueue<>(1);
        Interceptor reply = chain -> new Response.Builder()
                .request(chain.request())
                .protocol(Protocol.HTTP_1_1)
                .code(200)
                .message("OK")
                .body(ResponseBody.create(MediaType.get("application/json"),
                        "{\"profile\":null}"))
                .build();
        SnapshotPublisher publisher = new SnapshotPublisher(
                new OkHttpClient.Builder().addInterceptor(reply).build(), new Gson(),
                "http://127.0.0.1:1/api/snapshot/", replies::offer);
        try {
            publisher.publish(sample());
            assertEquals("{\"profile\":null}", replies.poll(2, TimeUnit.SECONDS));
        } finally {
            publisher.close();
        }
    }
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test --no-daemon -q`
Expected: compilation FAILS (no 4-argument constructor).

- [ ] **Step 3: Implement**

In `SnapshotPublisher`: add `import java.util.function.Consumer;` and a field `private final Consumer<String> onReply;`. The existing constructor becomes:

```java
    public SnapshotPublisher(OkHttpClient http, Gson gson, String url) {
        this(http, gson, url, body -> { });
    }

    public SnapshotPublisher(OkHttpClient http, Gson gson, String url,
                             Consumer<String> onReply) {
```

with the old body plus `this.onReply = onReply;`. In `send`, inside `if (response.isSuccessful())`, after `failureLogged.set(false);`, add:

```java
                    handReply(response);
```

and add the method:

```java
    private void handReply(Response response) {
        // The reply's reader must not be able to stop snapshots from flowing.
        try {
            onReply.accept(response.body() == null ? "" : response.body().string());
        } catch (Exception e) {
            log.debug("Ignored a reply: {}", e.toString());
        }
    }
```

`RuneLiteProfileStore.java`. This follows RuneLite's own `ProfilePanel`: import creates a profile and calls `importAndMigrate`; switching marks it active, calls `dirty()`, and then `switchProfile` outside the lock.

```java
package com.runecolor.bridge;

import net.runelite.client.config.ConfigManager;
import net.runelite.client.config.ConfigProfile;
import net.runelite.client.config.ProfileManager;

import java.io.File;

/** Reads and switches profiles the way RuneLite's own Profiles panel does. */
public class RuneLiteProfileStore implements ProfileStore {
    private final ProfileManager profileManager;
    private final ConfigManager configManager;

    public RuneLiteProfileStore(ProfileManager profileManager, ConfigManager configManager) {
        this.profileManager = profileManager;
        this.configManager = configManager;
    }

    @Override
    public String activeName() {
        ConfigProfile profile = configManager.getProfile();
        return profile == null ? null : profile.getName();
    }

    @Override
    public void apply(String name, File file) throws Exception {
        if (!file.isFile()) {
            throw new java.io.FileNotFoundException(file.getPath());
        }
        ConfigProfile profile;
        try (ProfileManager.Lock lock = profileManager.lock()) {
            // The repo file is the source of truth, so a stale copy of this profile
            // is replaced rather than merged into.
            ConfigProfile stale = lock.findProfile(name);
            if (stale != null) {
                lock.removeProfile(stale.getId());
            }
            profile = lock.createProfile(name);
            configManager.importAndMigrate(lock, file, profile);
            lock.getProfiles().forEach(p -> p.setActive(false));
            profile.setActive(true);
            lock.dirty();
        }
        configManager.switchProfile(profile);
    }
}
```

In `RuneColorBridgePlugin`: add imports `net.runelite.client.config.ProfileManager`, `java.util.concurrent.ExecutorService`. Add injected fields:

```java
    @Inject
    private ConfigManager configManager;

    @Inject
    private ProfileManager profileManager;

    private ExecutorService profileExecutor;
```

In `startUp`, replace the publisher construction with:

```java
        Gson gson = new Gson();
        profileExecutor = Executors.newSingleThreadExecutor(runnable -> {
            Thread thread = new Thread(runnable, "runecolor-bridge-profiles");
            thread.setDaemon(true);
            return thread;
        });
        ProfileSwitcher switcher = new ProfileSwitcher(
                new RuneLiteProfileStore(profileManager, configManager),
                profileExecutor, gson);
        publisher = new SnapshotPublisher(http, gson,
                "http://127.0.0.1:" + config.port() + "/api/snapshot/",
                switcher::onReply);
```

In `shutDown`, add:

```java
        if (profileExecutor != null) {
            // shutdown, not shutdownNow: a profile switch can restart plug-ins, this
            // one included, and interrupting it halfway would leave the profile
            // half-applied.
            profileExecutor.shutdown();
            profileExecutor = null;
        }
```

In `tick`, inside the `clientThread.invoke` lambda, pass the active profile:

```java
                        current.publish(SnapshotBuilder.build(
                                client, System.currentTimeMillis(), activeProfileName()));
```

and add:

```java
    private String activeProfileName() {
        ConfigProfile profile = configManager.getProfile();
        return profile == null ? null : profile.getName();
    }
```

(import `net.runelite.client.config.ConfigProfile`).

- [ ] **Step 4: Run the tests and build the jar**

Run: `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test shadowJar --no-daemon -q`
Expected: PASS, and `plugin/build/libs/runecolor-bridge-1.0-all.jar` is rebuilt.

- [ ] **Step 5: Commit** (after the user's go-ahead)

```bash
git add plugin/src
git commit -m "Switch RuneLite profiles from the bridge plug-in"
```

---

### Task 4b (added during the live check): keep the window size across a switch

The first live switch shrank the client from 1750x1073 to 1074x585: RuneLite re-applies
the new profile's `runelite.clientBounds`, and without any it falls back to
`runelite.gameSize`. `ProfileFiles.withWindowBounds(File, String)` copies the script
profile to a temporary file carrying the active profile's `clientBounds`, and
`RuneLiteProfileStore.apply` imports that copy (tests: `ProfileFilesTest`).
`ProfileSwitcher.apply` also catches `LinkageError`, so a RuneLite API change is
logged instead of silently killing the switch thread.

---

### Task 5: Script profiles in the repo

**Files:**
- Create: `src/profiles/power_chopper.properties`
- Create: `src/utilities/runelite_profiles.py`
- Modify: `src/model/bot.py` (class attribute on `Bot`)
- Modify: `src/model/osrs/power_chopper.py` (class attribute)
- Modify: `src/model/osrs/yew_banker.py` (class attribute, so it doesn't inherit the chopper's)
- Test: `tests/unit/test_runelite_profiles.py`

**Interfaces:**
- Produces: `runelite_profiles.PROFILES_DIR: Path`, `profile_path(key: str) -> Path`, `profile_name(bot_title: str) -> str`, `USE_OWN_PROFILE_SETTING = "use_own_runelite_profile"`, `Bot.runelite_profile: Optional[str] = None`, `OSRSPowerChopper.runelite_profile = "power_chopper"`.

- [ ] **Step 1: Write the failing tests**

```python
"""Checks every committed RuneLite profile against the rules loading depends on."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.osrs.power_chopper import OSRSPowerChopper  # noqa: E402
from utilities import runelite_profiles  # noqa: E402

GEOMETRY_KEYS = ("runelite.clientBounds=", "runelite.clientMaximized=")


def profile_files():
    return sorted(runelite_profiles.PROFILES_DIR.glob("*.properties"))


class RuneLiteProfilesTest(unittest.TestCase):
    def test_the_power_chopper_has_a_profile(self):
        path = runelite_profiles.profile_path(OSRSPowerChopper.runelite_profile)
        self.assertTrue(path.is_file(), path)

    def test_names_profiles_after_the_script(self):
        self.assertEqual(
            runelite_profiles.profile_name("Power Chopper & Firemaking"),
            "RuneColor - Power Chopper & Firemaking",
        )

    def test_no_profile_resizes_the_client(self):
        for path in profile_files():
            lines = path.read_text(encoding="utf-8").splitlines()
            for key in GEOMETRY_KEYS:
                self.assertFalse(
                    any(line.startswith(key) for line in lines), f"{path.name}: {key}"
                )

    def test_every_profile_keeps_the_bridge_enabled(self):
        # Switching profiles also switches plug-ins, so a profile without the bridge
        # would turn off the very plug-in that asked for the switch.
        for path in profile_files():
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertIn("runelite.runecolorbridgeplugin=true", lines, path.name)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python.exe -m unittest tests.unit.test_runelite_profiles -v`
Expected: ERROR (`cannot import name 'runelite_profiles'`).

- [ ] **Step 3: Implement**

Capture the profile from the live client, minus the window geometry:

```bash
mkdir -p src/profiles
grep -v -E '^runelite\.(clientBounds|clientMaximized)=' \
  "$HOME/.runelite/profiles2/Imported Profile-1248817826300.properties" \
  > src/profiles/power_chopper.properties
grep -c "runelite.runecolorbridgeplugin=true" src/profiles/power_chopper.properties
```

Expected: `1`. If the active profile's file name differs, find it with `grep '"active":true' ~/.runelite/profiles2/profiles.json`.

`src/utilities/runelite_profiles.py`:

```python
"""Where each script's RuneLite profile lives, and what RuneLite calls it."""

from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parents[1] / "profiles"
USE_OWN_PROFILE_SETTING = "use_own_runelite_profile"


def profile_path(key: str) -> Path:
    """Return the committed profile file for a script.

    Args:
        key (str): The script's `runelite_profile`, e.g. "power_chopper".

    Returns:
        Path: The absolute path of `src/profiles/<key>.properties`.
    """
    return PROFILES_DIR / f"{key}.properties"


def profile_name(bot_title: str) -> str:
    """Return the name the profile gets inside RuneLite.

    Args:
        bot_title (str): The script's title as the UI shows it.

    Returns:
        str: For example "RuneColor - Power Chopper & Firemaking".
    """
    return f"RuneColor - {bot_title}"
```

In `src/model/bot.py`, add to the class attributes of `Bot` (next to `options_set`, `progress`):

```python
    # The script's RuneLite profile in `src/profiles/`, or None to leave the client's
    # profile alone.
    runelite_profile: Optional[str] = None
```

(add `Optional` to the `typing` import if missing). In `OSRSPowerChopper`, add the class attribute `runelite_profile = "power_chopper"` directly under `class OSRSPowerChopper(OSRSBot):`. In `OSRSYewBanker`, add `runelite_profile = None` directly under its class line, since it subclasses the chopper and must not load the chopper's profile.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m unittest discover -s tests/unit -t .`
Expected: PASS. flake8/black on the new and changed Python files.

- [ ] **Step 5: Commit** (after the user's go-ahead)

```bash
git add src/profiles src/utilities/runelite_profiles.py src/model/bot.py src/model/osrs/power_chopper.py src/model/osrs/yew_banker.py tests/unit/test_runelite_profiles.py
git commit -m "Ship the Power Chopper with its RuneLite profile"
```

---

### Task 6: ProfileSelector applies the rules for a selected script

**Files:**
- Create: `src/controller/profile_selector.py`
- Test: `tests/unit/test_profile_selector.py`

**Interfaces:**
- Consumes: Task 1's `request_profile`, `clear_profile`, `active_profile`; Task 5's `profile_path`, `profile_name`, `USE_OWN_PROFILE_SETTING`.
- Produces: `ProfileSelector(bridge, get_setting: Callable[[str], Any], set_setting: Callable[[str, Any], None], log: Callable[[str], None], confirm_timeout: float = 10, poll: float = 0.5)`, `select(model: Optional[Bot]) -> None`, `use_own -> bool` (property), `set_use_own(value: bool) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
"""The rules for which RuneLite profile a selected script asks for."""

import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from controller.profile_selector import ProfileSelector  # noqa: E402
from utilities import runelite_profiles  # noqa: E402


class FakeBridge:
    def __init__(self, active=None):
        self.wanted = "unset"
        self.active_profile = active

    def request_profile(self, name, path):
        self.wanted = (name, path)

    def clear_profile(self):
        self.wanted = None


def script(profile="power_chopper", title="Chopper"):
    return SimpleNamespace(runelite_profile=profile, bot_title=title)


class ProfileSelectorTest(unittest.TestCase):
    def setUp(self):
        self.settings = {}
        self.logged = []
        self.bridge = FakeBridge()

    def selector(self, timeout=0.05):
        return ProfileSelector(
            self.bridge,
            self.settings.get,
            self.settings.__setitem__,
            self.logged.append,
            confirm_timeout=timeout,
            poll=0.005,
        )

    def test_requests_the_scripts_profile(self):
        self.selector().select(script())
        name, path = self.bridge.wanted
        self.assertEqual(name, "RuneColor - Chopper")
        self.assertEqual(path, str(runelite_profiles.profile_path("power_chopper")))

    def test_clears_the_request_for_a_script_without_a_profile(self):
        self.selector().select(script(profile=None))
        self.assertIsNone(self.bridge.wanted)

    def test_clears_the_request_when_nothing_is_selected(self):
        self.selector().select(None)
        self.assertIsNone(self.bridge.wanted)

    def test_opting_out_clears_the_request_and_is_remembered(self):
        selector = self.selector()
        selector.select(script())
        selector.set_use_own(True)
        self.assertIsNone(self.bridge.wanted)
        self.assertIs(self.settings[runelite_profiles.USE_OWN_PROFILE_SETTING], True)
        self.assertTrue(self.selector().use_own)

    def test_opting_back_in_requests_the_selected_scripts_profile(self):
        self.settings[runelite_profiles.USE_OWN_PROFILE_SETTING] = True
        selector = self.selector()
        selector.select(script())
        self.assertIsNone(self.bridge.wanted)
        selector.set_use_own(False)
        self.assertEqual(self.bridge.wanted[0], "RuneColor - Chopper")

    def test_logs_once_the_client_has_switched(self):
        self.bridge.active_profile = "RuneColor - Chopper"
        self.selector().select(script())
        self.wait_for_log()
        self.assertEqual(
            self.logged, ["Switched RuneLite to profile RuneColor - Chopper."]
        )

    def test_warns_when_the_client_never_switches(self):
        self.selector().select(script())
        self.wait_for_log()
        self.assertIn("didn't switch", self.logged[0])

    def wait_for_log(self):
        deadline = time.time() + 2
        while not self.logged and time.time() < deadline:
            time.sleep(0.005)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python.exe -m unittest tests.unit.test_profile_selector -v`
Expected: ERROR (`No module named 'controller.profile_selector'`).

- [ ] **Step 3: Implement** `src/controller/profile_selector.py`

```python
"""Ask the RuneLite client for the selected script's profile, through the bridge."""

import threading
import time
from typing import Any, Callable, Optional

from utilities import runelite_profiles


class ProfileSelector:
    """Decides which RuneLite profile to ask for, and reports whether it took.

    The bridge is duck-typed: anything with `request_profile`, `clear_profile` and
    `active_profile` will do, which keeps this testable without a client.
    """

    def __init__(
        self,
        bridge,
        get_setting: Callable[[str], Any],
        set_setting: Callable[[str, Any], None],
        log: Callable[[str], None],
        confirm_timeout: float = 10,
        poll: float = 0.5,
    ) -> None:
        """Instantiate a `ProfileSelector`.

        Args:
            bridge: The shared `BridgeAPI`.
            get_setting (Callable[[str], Any]): Reads a persisted setting.
            set_setting (Callable[[str, Any], None]): Persists a setting.
            log (Callable[[str], None]): Writes a line to the UI's log.
            confirm_timeout (float, optional): Seconds to wait for the client to
                switch before warning. Defaults to 10.
            poll (float, optional): Seconds between checks. Defaults to 0.5.
        """
        self._bridge = bridge
        self._get = get_setting
        self._set = set_setting
        self._log = log
        self._timeout = confirm_timeout
        self._poll = poll
        self._model = None
        self._requested: Optional[str] = None

    @property
    def use_own(self) -> bool:
        """bool: Whether the user keeps their own RuneLite profile."""
        return bool(self._get(runelite_profiles.USE_OWN_PROFILE_SETTING))

    def set_use_own(self, value: bool) -> None:
        """Remember the user's choice and apply it to the selected script.

        Args:
            value (bool): True to keep the user's own profile.
        """
        self._set(runelite_profiles.USE_OWN_PROFILE_SETTING, value)
        self.select(self._model)

    def select(self, model) -> None:
        """Ask for the profile of the newly selected script, or for none.

        Args:
            model (Optional[Bot]): The selected script, or None.
        """
        self._model = model
        key = getattr(model, "runelite_profile", None)
        if self.use_own or key is None:
            self._requested = None
            self._bridge.clear_profile()
            return
        name = runelite_profiles.profile_name(model.bot_title)
        self._requested = name
        self._bridge.request_profile(name, str(runelite_profiles.profile_path(key)))
        threading.Thread(target=self._confirm, args=(name,), daemon=True).start()

    def _confirm(self, name: str) -> None:
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            if self._requested != name:
                return  # Another script was selected meanwhile.
            if self._bridge.active_profile == name:
                self._log(f"Switched RuneLite to profile {name}.")
                return
            time.sleep(self._poll)
        if self._requested == name:
            self._log(
                f"RuneLite didn't switch to profile {name} within"
                f" {self._timeout:g} s. Is the RuneColor Bridge plug-in on?"
            )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m unittest tests.unit.test_profile_selector -v`, then the full suite, flake8 and black.
Expected: PASS.

- [ ] **Step 5: Commit** (after the user's go-ahead)

```bash
git add src/controller/profile_selector.py tests/unit/test_profile_selector.py
git commit -m "Choose the RuneLite profile for the selected script"
```

---

### Task 7: Start the bridge with the UI and add the opt-out checkbox

**Files:**
- Modify: `src/runecolor.py` (`_initialize_script_view`, around line 326)
- Modify: `src/controller/bot_controller.py` (`__init__`, `change_model`, new `set_use_own_profile`)
- Modify: `src/views/info_frame.py` (new checkbox at grid row 3, column 0)

**Interfaces:**
- Consumes: Task 6's `ProfileSelector`, Task 5's `USE_OWN_PROFILE_SETTING`, `BridgeAPI.shared`.
- Produces: `BotController.bridge` and `BotController.profiles` attributes (None when the bridge couldn't start), `BotController.set_use_own_profile(value: bool) -> None`.

- [ ] **Step 1: Implement the controller**

In `BotController.__init__`, add:

```python
        # Set by the app once the bridge is up. None means the port was taken, and
        # scripts then read the screen only.
        self.bridge = None
        self.profiles = None
```

In `change_model`, after `self.view.frame_info.start_keyboard_listener()` (inside `if self.model is not None:`), add:

```python
            if self.bridge is not None and isinstance(model, RuneLiteBot):
                model.attach_bridge()
```

and at the very end of `change_model` (after `self.clear_log()`, so the confirmation isn't wiped):

```python
        if self.profiles is not None:
            self.profiles.select(self.model)
```

Add the method:

```python
    def set_use_own_profile(self, value: bool) -> None:
        """Keep the user's own RuneLite profile, or go back to the script's.

        Args:
            value (bool): True to keep the user's own profile.
        """
        if self.profiles is not None:
            self.profiles.set_use_own(value)
```

Import `from model.runelite_bot import RuneLiteBot` at the top.

- [ ] **Step 2: Start the bridge with the app**

In `src/runecolor.py`, add imports `from controller.profile_selector import ProfileSelector` and `from utilities.api.bridge_api import BridgeAPI`. At the end of `_initialize_script_view`, add:

```python
        try:
            self.controller.bridge = BridgeAPI.shared()
        except OSError as exc:
            # A live test harness may already hold the port. The UI still works,
            # but scripts then read the screen and profiles are left alone.
            print(f"RuneColor Bridge not started: {exc}")
            return
        self.controller.profiles = ProfileSelector(
            self.controller.bridge,
            settings.get,
            settings.set,
            self.controller.update_log,
        )
```

- [ ] **Step 3: Add the checkbox**

In `InfoFrame.__init__`, call `self._create_profile_checkbox()` after `self._create_description_text()`. Import `from utilities.runelite_profiles import USE_OWN_PROFILE_SETTING`. Add:

```python
    def _create_profile_checkbox(self) -> None:
        """Create the opt-out from the script's own RuneLite profile."""
        self.chk_own_profile = ctk.CTkCheckBox(
            master=self,
            text="Use my own RuneLite profile",
            font=fnt.body_med_font(),
            command=self.__on_own_profile_toggled,
        )
        if settings.get(USE_OWN_PROFILE_SETTING):
            self.chk_own_profile.select()
        self.chk_own_profile.grid(column=0, row=3, sticky="w", padx=20, pady=(5, 0))
```

and next to the other button handlers:

```python
    def __on_own_profile_toggled(self) -> None:
        """Tell the controller whether to keep the user's own RuneLite profile."""
        self.controller.set_use_own_profile(bool(self.chk_own_profile.get()))
```

- [ ] **Step 4: Check it**

Run the unit suite, flake8 and black on the three files. Then launch the UI: `venv/Scripts/python.exe src/runecolor.py`. Expected: the app opens, the Power Chopper's info panel shows the checkbox under the description, and nothing prints "RuneColor Bridge not started".

- [ ] **Step 5: Commit** (after the user's go-ahead)

```bash
git add src/runecolor.py src/controller/bot_controller.py src/views/info_frame.py
git commit -m "Start the bridge with the UI and let the user keep their own profile"
```

---

### Task 8: Live verification and docs

**Files:**
- Modify: `plugin/README.md` (new section "Script profiles")
- Modify: `tests/README.md` (point to `src/profiles/` next to `rscolorprofile.properties`)

- [ ] **Step 1: Install the new jar.** Copy `plugin/build/libs/runecolor-bridge-1.0-all.jar` to `~/.runelite/sideloaded-plugins/`, then ask the user to close RuneLite and start it with `powershell -ExecutionPolicy Bypass -File plugin\run-dev.ps1`. Before the test, the user switches the client to a different profile (e.g. "default") in the Profiles panel.

- [ ] **Step 2: Record the window size before the switch.**

```bash
venv/Scripts/python.exe -c "import pywinctl as w; x=[a for a in w.getAllWindows() if a.title.startswith('RuneLite')][0]; print(x.size)"
```

- [ ] **Step 3: Select the script in the UI.** Launch `venv/Scripts/python.exe src/runecolor.py` and pick the Power Chopper. Expected in the log within 10 s: "Switched RuneLite to profile RuneColor - Power Chopper & Firemaking." In the client, the Profiles panel shows that profile as active.

- [ ] **Step 4: Check nothing else moved.** Re-run the Step 2 command: same size. Tick "Use my own RuneLite profile", switch the client back to "default" by hand, pick the script again: the client stays on "default". Untick it: the client switches back to the RuneColor profile.

- [ ] **Step 5: Check the bridge survived the switch.** With the bot's bridge running, `BridgeAPI.shared().is_fresh()` stays True: run the chopper from the UI for one burn, and the log shows "Burning 26 logs…" then "Tending the fire…" (the one-fire path, which needs the bridge).

- [ ] **Step 6: Docs.** In `plugin/README.md`, add:

```markdown
## Script profiles

Each script can ship a RuneLite profile in `src/profiles/<script>.properties` and
name it with `runelite_profile = "<script>"` on its class. When the script is
selected in the UI, the bot asks the plug-in for it in its reply to every snapshot,
and the plug-in imports the file into a profile called "RuneColor - <script title>"
and switches to it. Ticking "Use my own RuneLite profile" stops the requests.

To capture a profile, copy the active one from `~/.runelite/profiles2/` without the
window geometry, so loading it never resizes the client:

    grep -v -E '^runelite\.(clientBounds|clientMaximized)=' "<active>.properties" > src/profiles/<script>.properties

The profile must keep `runelite.runecolorbridgeplugin=true`: switching profiles also
switches plug-ins, and without it the switch turns the bridge off.
`tests/unit/test_runelite_profiles.py` checks both rules.
```

In `tests/README.md`, after the sentence about `rscolorprofile.properties`, add: "Scripts with their own profile in `src/profiles/` load it automatically when selected in the UI; see `plugin/README.md`, 'Script profiles'."

- [ ] **Step 7: Commit** (after the user's go-ahead)

```bash
git add plugin/README.md tests/README.md
git commit -m "Document per-script RuneLite profiles"
```
