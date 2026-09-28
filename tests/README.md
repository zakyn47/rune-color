# Live tests

Runecolor's bots are driven entirely by what's on screen, so the failures that
matter are rarely exceptions. They're the quiet ones, where the bot reports
success and the game disagrees. Burning logs once reported 25 logs burned while
consuming exactly 1, and every log line looked healthy throughout.

These tests drive the real bot against a live RuneLite client and check its
reporting against the game state. They are not unit tests, they need a running
client and an account, and they take real time to run.

## Prerequisites

The client has to be set up correctly or the tests measure nothing useful. The
required RuneLite configuration is committed as
[`src/rscolorprofile.properties`](../src/rscolorprofile.properties) — importing
that profile is the quickest way to get all of the below at once. Scripts with their own profile in `src/profiles/` load it automatically when
selected in the UI; see `plugin/README.md`, "Script profiles".

| Requirement | Why it matters |
| --- | --- |
| **Stretched Mode disabled** | `cv2.matchTemplate` is not scale invariant, so every pixel template fails if the client is scaled. |
| **Resizable - Classic layout** | Region locations are computed per layout. |
| **World Location plugin, with Grid Info ticked** | Draws the `Tile x, y, plane` box that `get_world_point` reads. Without it that call returns `(-1, -1, -1)` and every position-based behavior silently does nothing. It's a Plugin Hub plugin, so it must be installed, not merely enabled. |
| **Object Markers plugin** | The bot finds trees by their cyan marker colour. |
| **Idle Notifier plugin** | Used for idle detection elsewhere in the framework. |
| **No screen dimming** | Night Light and f.lux shift colours enough to break colour matching. |
| **Character next to marked trees, axe and tinderbox in the inventory** | The tinderbox is assumed to be in inventory slot 1. |

A quick way to confirm the overlay is live: crop the top left of the game view
and look for `Tile x, y, plane`. If it isn't rendered, don't bother debugging
walking behavior — nothing position-based can work.

**Nothing may cover the client.** Every reading comes from a screenshot of that
screen region, so anything drawn on top is what gets measured. A full screen
Windows overlay is the one that really bites: a Task View or alt-tab switcher
left open covers the whole screen, and the run fails at startup with `Failed to
find chatbox` while the client itself looks perfectly fine underneath. If a
session won't start, check what actually owns those pixels before suspecting the
bot:

```python
# What is really on top of the chatbox right now?
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
point = wintypes.POINT(608, 579)  # somewhere inside the chatbox
name = ctypes.create_unicode_buffer(256)
user32.GetClassNameW(user32.WindowFromPoint(point), name, 256)
print(name.value)  # "SunAwtCanvas" is the client; anything else is in the way
```

`XamlExplorerHostIslandWindow` means Task View is open — dismiss it with
Win+Tab. Tray popups and notification toasts cause the same class of failure,
which is a good reason not to turn on notification-heavy plugin options.

## Running

```bash
python tests/live_power_chopper.py --runs 3 --minutes 35
```

| Flag | Default | Notes |
| --- | --- | --- |
| `--runs` | 3 | Sessions to run back to back. |
| `--minutes` | 35 | Minutes per session. |
| `--out` | `live_power_chopper.json` | Where per-session results are written. |

The script logs in on its own if the client is sitting on the login splash, and
each session logs out when it ends, so consecutive runs need no babysitting.

**Give each session enough time to burn.** The bot only burns once its inventory
is full, and chopping 26 logs takes roughly 20-25 minutes. Anything under about
30 minutes usually measures chopping alone and never exercises the burn at all.

## Reading the output

Each burn prints a line as it happens:

```
[BURN] {'logs_before': 26, 'logs_after': 0, 'actual_burned': 26,
        'claimed_burned': 26, 'returned': True, 'secs': 176.0,
        'grove_return': {'grove': (3201, 3245, 0), 'drift_before': 14.0,
                         'drift_after': 1.4, 'arrived': True},
        'mismatch': False}
```

The three numbers that decide whether a run passed:

- **`mismatch`** must be `False`. It compares logs that actually left the
  inventory against the tally the bot added to `logs_burned`. `True` means the
  bot is claiming work it did not do, which is the exact class of bug these
  tests exist to catch.
- **`wrong_verdicts`** must be `0`. Every `light_fire` verdict is compared
  against whether that slot really emptied.
- **`errors`** should be empty, but see the caveat below.

`grove_return` shows how far burning walked the character from where it started
and how far away it ended up after walking back. Lighting a fire steps the
character back a tile each time, so `drift_before` in the tens of tiles is
normal; `drift_after` should be small.

### Caveats

An exception raised inside the bot's own thread does not propagate to the
harness, so an empty `errors` list is not on its own proof that a run went
cleanly. Check the captured log for a traceback as well.

Lines like `Failed to find minimap`, `Failed to find chatbox` and `Couldn't
orient itself` at the start of a session are the harness probing whether the
client is logged out. They're expected, and are not bot errors.

# RuneColor Bridge

The bridge plugin pushes exact hitpoints, Prayer, run energy and world point out of
the client, so the bot no longer has to read them off the screen. `live_bridge.py`
is what decides whether to trust it.

## Setup

1. Build and sideload the plugin — see [`plugin/README.md`](../plugin/README.md).
   In short: build the jar with JDK 11, copy it to `~/.runelite/sideloaded-plugins/`,
   launch RuneLite with `--developer-mode`, then enable "RuneColor Bridge" in the
   sidebar. It's disabled by default, so sideloading alone isn't enough.
2. Leave port 8099 free.

| Requirement | Why it matters |
| --- | --- |
| **RuneColor Bridge plugin sideloaded and enabled** | Nothing is measured without it; `live_bridge.py` reports 0% availability and fails. |
| **World Location plugin, with Grid Info ticked** | Still required. `live_bridge.py` measures the bridge *against* that overlay, so the overlay is what makes the comparison possible. It only becomes optional once this test passes. |

## Running

```bash
venv/Scripts/python.exe tests/live_bridge.py --minutes 10
```

| Flag | Default | Notes |
| --- | --- | --- |
| `--minutes` | 10 | How long to sample, one sample per second. |
| `--out` | `live_bridge.json` | Where per-field results are written. |

Move around, take some damage, drain some Prayer, and run until your energy drops.
A test taken standing still only proves the two agree on numbers that never changed.

## Reading the output

```
samples: 600  availability: 99.83%
field            agree  (later)  disagree  ocr failed     rate
hitpoints          598        0         0           1  100.00%
prayer             599        0         0           0  100.00%
run_energy         597       14         0           2  100.00%
world_point        580       11         0          19  100.00%
```

- **`disagree` must be 0.** Each one prints with both values. A disagreement means the
  plugin and the screen describe different worlds, and the plugin is the one to
  distrust until proven otherwise.
- **`availability` must be above 99%.** Lower means the feed is dropping, and a bot
  that falls back to OCR half the time gains nothing from the plugin.
- **`(later)`** is the part of `agree` that needed the next snapshot. The plug-in
  samples once per tick, but the screen redraws every frame and OCR takes a few
  hundred milliseconds, so while you move the Grid Info tile can be up to two
  squares past the last snapshot. Each screen read is therefore bracketed by the
  snapshot before it and the first one from a later tick, and agrees if it lies
  between them on the same plane. Non-zero is expected while running or
  regenerating; standing still it must be an exact match.
- **The window may move.** Each sample re-measures the client if it was dragged or
  resized, and so does every bot between actions.
- **`ocr failed`** counts samples where the *screen* read failed — a hover tooltip over
  the overlay, a redraw caught mid-frame. Those are excluded from the agreement rate
  because they measure the screen reader, not the bridge. A high count here is the
  original problem the bridge exists to solve, not a bridge fault.

A passing run is what licensed turning `COMPARE_BRIDGE_WITH_OCR` off in
`src/model/runelite_bot.py`. Turn it back on to audit the plug-in again. The retry
loop in `get_world_point_reliably` stays: the plug-in only loads in developer mode, so
a client started normally still reads the overlay, and that path still needs it.

## The loopback test

`loopback_bridge.py` needs no client and no account. It runs the real Java publisher
against the real Python receiver and checks that what arrives parses into what was
sent — the one test that catches the two halves disagreeing about the wire format.

```bash
venv/Scripts/python.exe tests/loopback_bridge.py
```

Run it after changing either side of the payload.
