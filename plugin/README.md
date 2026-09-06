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

**Unverified:** whether the installed `RuneLite.exe` launcher actually forwards `--developer-mode` through to the client has not been checked on this machine. If the plugin doesn't show up in the sidebar after sideloading, that's the first thing to check — e.g. by launching the client jar directly with the flag instead of going through `RuneLite.exe`.
