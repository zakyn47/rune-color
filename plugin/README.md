# RuneColor Bridge

- A sideloaded RuneLite plugin that pushes exact player vitals to the RuneColor bot over localhost.
- Exists because computer-vision automation is inherently approximate; this plugin is the exact-state channel that later tasks in this plan read from.
- Disabled by default (`enabledByDefault = false` in the plugin descriptor) — it must be turned on explicitly in the RuneLite sidebar after sideloading.

# Requirements
- JDK 11. The bundled RuneLite JRE cannot compile the plugin.

# Build
```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew shadowJar --no-daemon
```
Produces `plugin/build/libs/runecolor-bridge-1.0-all.jar`.

# Sideload
1. Copy the built jar to `~/.runelite/sideloaded-plugins/`.
2. Launch RuneLite with `--developer-mode`.
3. Enable "RuneColor Bridge" in the plugin sidebar.

**The official launcher cannot run developer mode, by design.** From
`RuneLite.main` in client 1.12.38:

```java
developerMode = options.has("developer-mode")
        && RuneLiteProperties.getLauncherVersion() == null;
```

and `getLauncherVersion()` is just `System.getProperty("runelite.launcher.version")`,
which `RuneLite.exe` always sets (`-Drunelite.launcher.version=2.8.0`). So the flag is
ignored whenever the official launcher started the client, silently. Only once
developer mode is on does the client additionally require assertions, failing with a
dialog that says "Developers should enable assertions; Add `-ea` to your JVM
arguments". Two further dead ends, both checked here: the launcher forwards client
arguments only from `RUNELITE_ARGS`, `--debug` and `--safe-mode`, and it rewrites
`%LOCALAPPDATA%\RuneLite\config.json` on every start, so its `vmArgs` cannot be
edited to add `-ea`. `_JAVA_OPTIONS` cannot help either: it can set a system property
but not unset one, and an empty value is still non-null.

Run the client directly instead, which sets no launcher version:

```powershell
& "$env:LOCALAPPDATA\RuneLite\jrein\java.exe" `
  -ea `
  --add-opens=java.base/java.net=ALL-UNNAMED `
  --add-opens=java.base/java.io=ALL-UNNAMED `
  -Xmx768m -Xss2m -Dsun.java2d.d3d=true -Dsun.java2d.opengl=false `
  -cp "$env:USERPROFILE\.runeliteepository2\*" `
  net.runelite.client.RuneLite --developer-mode
```

Confirm it worked by looking for this line in `~/.runelite/logs/client.log`:

```
INFO n.r.client.plugins.PluginManager - Side-loading plugin ...runecolor-bridge-1.0-all.jar
```

**Jagex accounts collide with this.** A Jagex account authenticates using session
values the Jagex Launcher injects into the client's environment, and the command above
starts the client without them, so it cannot log in. Developer mode needs the launcher
out of the way; a Jagex account needs it involved. Anyone hitting this has to relay
those environment values into a direct launch, or test on an account that still uses a
plain username and password.

# Why there is no @Subscribe

The obvious way to sample every tick is `@Subscribe onGameTick`. It does not work for
a side-loaded plugin. `PluginClassLoader` is a plain `URLClassLoader` and does not
implement RuneLite's `ReflectUtil.PrivateLookupableClassLoader`, so the event bus
cannot get the private lookup `LambdaMetafactory` requires, and registration fails:

```
WARN EventBus - Unable to create lambda for method ...onGameTick(GameTick)
java.lang.invoke.LambdaConversionException: Invalid caller: com.runecolor.bridge.RuneColorBridgePlugin
```

The plugin still starts and logs that it is pushing, so the only symptom is one
warning and a feed that never sends anything. Plugin Hub plugins take a different
load path and are unaffected, which is why `world-location` works and this did not.

The plugin therefore drives itself from a scheduled timer and hops onto the client
thread with `ClientThread.invoke`. That costs exact tick alignment, which this design
does not need: the bot asks whether a reading is younger than two ticks, not which
tick produced it.

# Configuration
Both settings live under "RuneColor Bridge" in the RuneLite sidebar.

| Setting | Default | Notes |
| --- | --- | --- |
| **Port** | 8099 | The port the bot listens on. Chosen to avoid 8081 (`events_api.py`) and 9420 (`gi_tracker.py`), so all three can run at once. |
| **Ticks per push** | 1 | Push every Nth game tick. 1 pushes every tick, roughly every 600 ms. |

# What it sends
One JSON object per tick, POSTed to `http://127.0.0.1:<port>/api/snapshot/`. The
canonical example is [`tests/fixtures/snapshot_v1.json`](../tests/fixtures/snapshot_v1.json),
which both test suites pin, so a change on one side that isn't mirrored on the other
fails a suite rather than failing silently in a live run:

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

Notes on the fields:
- `run_energy` is 0-100. RuneLite reports run energy in hundredths of a percent, and
  the plugin converts it so the scale question never reaches Python.
- `world_point` is instance-local inside instances, not a true world coordinate.
- The plugin keeps pushing while logged out, with `game_state` set and the player
  fields omitted. Going quiet instead would leave the bot unable to tell "logged out"
  from "plugin dead".

# Troubleshooting

**The bot logs a schema mismatch and disables the bridge.** `schema` has to match
`BridgeAPI.SCHEMA_VERSION`. The usual cause is a stale jar: the built artifact lives in
`~/.runelite/sideloaded-plugins/` and does **not** rebuild when you `git pull`. Rebuild
and copy it across.

**Nothing arrives at all.** Check, in order: the plugin is enabled in the sidebar; its
port matches the bot's; and the client was launched with `--developer-mode` (see the
Unverified note above).

**The build fails after a RuneLite update.** `net.runelite:client` is pinned to
`1.12.38` in `build.gradle` rather than tracking `latest.release`, so the API the
plugin compiles against cannot change under you without a visible one-line edit. Bump
that version deliberately.
