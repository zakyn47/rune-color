# RuneColor Bridge: a sideloaded RuneLite plugin for exact game state

## Problem

The bot reads its own vital signs off the screen. `get_hp` and `get_prayer`
OCR the orb text, and `get_world_point` OCRs the World Location overlay. The
position read is unreliable enough that it needed `get_world_point_reliably`,
a six-attempt retry wrapper, because a hover tooltip drawn over the overlay or
a redraw caught mid-frame produces the same `(-1, -1, -1)` sentinel as a
missing overlay.

Every one of these values exists as an integer inside the client. A sideloaded
RuneLite plugin can push them out directly, exactly, every game tick.

## Scope

Staged, and this spec covers stage A only.

**Stage A** replaces flaky reads: hitpoints, prayer, run energy, world point,
game state. **Stage B** adds data the screen cannot give — animation id,
interaction target, inventory item ids, worn equipment, nearby NPCs — and gets
its own spec. Stage A ships no scaffolding for stage B: no reserved keys, no
placeholder fields.

## Decisions

These were settled during brainstorming and are recorded with their reasoning,
because each one rules out an approach a reader might otherwise reach for.

**The plugin pushes; Python receives.** The client process holds no listening
socket. The plugin POSTs to a local Flask server, the same shape as the
existing `events_api.py` and `gi_tracker.py`. Push also fits the bot better
than pull: a tick-driven push delivers fresh state every 600 ms with no
polling loop.

**Existing OCR reads stay as the fallback.** `get_hp`, `get_prayer` and
`get_world_point` keep their signatures and return the pushed value when the
feed is fresh, falling through to the untouched OCR body when it is not. A
plugin that fails to load degrades the bot to today's behavior instead of
stopping a live run. This also means no call site changes.

**During stage A, disagreement is logged.** When the API value and the OCR
value differ, that is a warning with both values. This turns the first live
run into a correctness test of the payload: the plugin is right because the
two agree, not because the numbers looked plausible.

**Plugin source lives in `plugin/` in this public repo.** The trade-off was
raised explicitly — publishing the source publishes the payload shape, port
and cadence, which is the "known signature" half of what got the Morg HTTP
Client and Status Socket detected (see `src/utilities/api/deprecated/README.md`).
The convenience of a single repo and a contract that cannot drift was judged
worth it. A consequence follows: obscured naming would be theater, so the
plugin is named plainly and no design effort goes into hiding it.

**A full RuneLite source checkout is not needed.** Everything stage A reads is
exposed to external plugins, so the standalone
[example-plugin](https://github.com/runelite/example-plugin) template is
enough.

## Architecture

Four units. Each is understandable alone, and each can be replaced without
touching the other two sides.

### Java, in `plugin/`

Gradle project from the RuneLite example-plugin template: JDK 11
(`options.release.set(11)`), `compileOnly net.runelite:client:latest.release`,
Lombok, and a `shadowJar` task producing the sideloadable jar.

- **`SnapshotBuilder`** takes RuneLite's `Client` and returns an immutable
  `Snapshot`. No I/O, no network, no threads. Every "which API call gives me
  prayer points" decision lives here, and purity makes it unit-testable
  against a mocked `Client` with no game running.
- **`SnapshotPublisher`** takes a `Snapshot`, serializes it with Gson and
  POSTs it with OkHttp — both already on the RuneLite classpath. It knows
  nothing about the game. It owns the background executor.
- **`RuneColorBridgePlugin`** is the RuneLite entry point. It subscribes to
  `onGameTick`, calls the builder, hands the result to the publisher.
  Deliberately thin, because it is the only class that is awkward to test.
- **`RuneColorBridgeConfig`** holds the port (default 8099, chosen to avoid
  the 8081 that `events_api.py` uses and the 9420 that `gi_tracker.py` uses),
  an enabled toggle, and ticks-per-push (default 1).

The split between builder and publisher is forced by the runtime, not chosen
for taste. `onGameTick` runs on the client thread and RuneLite's `Client` API
is only safe to touch there, but blocking that thread on a network call
stutters the game. So the snapshot is built on the client thread and published
off it. That the same boundary makes the builder testable is a bonus.

### Python, in `src/utilities/api/bridge_api.py`

**`BridgeAPI`** is a Flask server in the shape of `events_api.py` with one
route, `POST /api/snapshot/`. It stores the latest snapshot and its arrival
timestamp, and exposes typed accessors plus `is_fresh(max_age)`. It knows
nothing about OCR or about bots.

### Wiring, in `src/model/runelite_bot.py`

`get_hp`, `get_prayer` and `get_world_point` each gain the same shape: if a
bridge is attached and fresh, return its value; otherwise fall through to the
existing OCR body, unchanged. The OCR code is preceded, never edited.

## Data contract

One JSON object per tick:

```json
{
  "schema": 1,
  "tick": 123456,
  "sent_at": 1757193600123,
  "game_state": "LOGGED_IN",
  "hitpoints":  { "current": 42, "max": 55 },
  "prayer":     { "current": 12, "max": 43 },
  "run_energy": 87,
  "world_point": { "x": 3222, "y": 3218, "plane": 0 }
}
```

Sources: `getBoostedSkillLevel` and `getRealSkillLevel` for hitpoints and
prayer, `getEnergy()` for run energy, `getLocalPlayer().getWorldLocation()`
for position, `getGameState()` and `getTickCount()` for the rest.

**Run energy is normalized to 0-100 by `SnapshotBuilder`.** `getEnergy()`
returned 0-100 historically and 0-10000 in later clients. A unit test asserts
the normalization, so a client update that changes the scale fails the build
instead of quietly convincing the bot it cannot run.

**`world_point` is instance-local inside instances.** `getWorldLocation()`
does not return true world coordinates inside an instance. Stage A does not
care, because the scripts run in the overworld, but the field carries a
comment saying so because it is a real trap for stage B.

**`schema` guards against a stale jar.** Plugin and Python live in one repo,
but the built jar lives in `~/.runelite/sideloaded-plugins/` and does not
rebuild on `git pull`. New Python will eventually meet an old jar. Python
rejects a mismatched schema loudly instead of reading fields that moved.

**Freshness is measured on arrival, not from `sent_at`.** Python stamps its
own arrival time: clock-skew-free, and it measures the thing that matters, how
long since anything was heard. `sent_at` and `tick` are kept for diagnostics —
if arrival gaps grow while tick deltas stay at 1, the network path is at
fault, not the game.

**The freshness threshold is 1.2 s (two ticks), configurable.** One global
threshold, not per-field. A dropped push must bounce every field to OCR
together, so the bot never pairs a fresh HP with a stale position and acts on
an inconsistent picture of the world.

## Error handling

**The normal state is that nobody is listening.** The plugin runs whenever
RuneLite runs; Flask runs only when the bot runs. Connection-refused is the
common case, not a fault, and three decisions follow from that:

- Publishing is fire-and-forget on a **queue of capacity one, drop-oldest**.
  If the path stalls, the bot should get the newest snapshot, never a backlog
  of stale ones replayed at it.
- The first failure logs, and further failures stay silent until a success
  resets the latch. Otherwise the client logs a line every 600 ms forever.
- **`onGameTick` never throws.** Anything escaping the builder is caught and
  rate-limited, because an exception there risks the client disabling the
  plugin mid-session.

**Logged out still pushes**, carrying `game_state: "LOGGED_OUT"` and no player
fields. Going quiet instead would leave Python unable to distinguish "logged
out" from "bridge dead", and both would fall back to OCR, which also fails
when logged out. Pushing lets the bot know.

**Python fails safe, never dead.** No snapshot yet, a stale snapshot, or
malformed JSON all mean `is_fresh()` is False and OCR runs, which is today's
behavior. A schema mismatch logs once at ERROR and disables the bridge for the
session. One fix to the pattern inherited from `events_api.py`: Flask starts
in a daemon thread, where a port-in-use bind error dies silently, so startup
waits for the bind to confirm and raises if it did not happen.

**Fallbacks are counted.** A bridge that is dead 40% of the time still looks
like it works while buying nothing, so the session log reports the count.

## Testing

This project's testing culture is live tests that check the bot's claims
against actual game state, because as `tests/README.md` puts it, the failures
that matter are "the quiet ones, where the bot reports success and the game
disagrees." A bridge returning confidently wrong numbers is exactly that
failure, so it is validated the same way.

**Step 0, the sideload spike, comes before any real code.** A hello-world
plugin that logs one line. It settles the single unverified assumption in this
design — whether the installed `RuneLite.exe` launcher forwards
`--developer-mode` to the client, or whether a locally built client jar is
required — and it forces the JDK 11 and Gradle setup the machine does not
have. If it fails, the design needs rethinking, so it is cheap and it is
first.

**Java unit tests** cover `SnapshotBuilder` against a mocked `Client`: energy
normalization, null local player, logged-out state. No game required.

**Python unit tests** cover `BridgeAPI`: accessors, freshness expiry, schema
rejection, malformed payloads, and the bind-error surfacing.

**A loopback contract test** posts a recorded payload fixture — the same
fixture the Java tests serialize against — to a running `BridgeAPI`, proving
both halves agree on the contract without a game.

**`tests/live_bridge.py`** follows `live_power_chopper.py`: run both paths
against a live client, sample hitpoints, prayer and world point from the API
and from OCR, and report an agreement table with every disagreement's two
values. This is the test that catches a plausible-looking payload reading the
wrong thing.

Moving off OCR requires zero unexplained disagreements across a full session,
and bridge availability above 99% of samples.

## Rollout

| Stage | What happens | Done when |
| --- | --- | --- |
| 0 | Hello-world sideload | Plugin appears in the sidebar and logs its line |
| 1 | Plugin pushes, Python receives, nothing consumes it | `live_bridge.py` shows agreement |
| 2 | Fallback wired into `get_hp`, `get_prayer`, `get_world_point` | A live `power_chopper` run behaves as before |
| 3 | OCR crutches retired | Position reads stop being flaky |
| 4 | Stage B | Separate spec |

Stage 1 consuming nothing is the point. It makes stage 2 a change backed by
evidence rather than one discovered mid-run.

At stage 3 the six-attempt retry in `get_world_point_reliably` and the World
Location plugin requirement in the `tests/README.md` prerequisites table both
come out. `src/rscolorprofile.properties` gains the bridge configuration if
that belongs in the committed profile.

## Out of scope

Stage B fields. Any attempt to make the plugin undetectable — RuneLite is open
source and the client's memory is the client's memory; this design only avoids
matching a known public signature, and the public-repo decision gives up even
that. Publishing to the Plugin Hub.
