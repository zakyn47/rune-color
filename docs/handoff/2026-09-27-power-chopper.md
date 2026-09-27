# Handoff: Power Chopper on the RuneColor Bridge (2026-09-27)

Branch: `feature/campfire-tending` (pushed, **not merged**). Everything before it is
merged into `main` at `4f40600`.

## Your task

1. **Verify the untested campfire changes live** (commit `469e138`), then merge the
   branch into `main`.
2. **Fix the remaining chopper issues** listed under "Open issues".
3. Only after the chopper is done: **add combat and target data to the bridge** (see
   "Next feature").

Definition of done for step 1: a 30-minute run that starts logged out passes with
`burn mismatches: 0`, `wrong verdicts: 0`, `run errors: 0`, every burn uses a single
fire, and there are no "There's a Forester's Campfire nearby" messages in the chat.

## What the bot does now

`OSRSPowerChopper` (`src/model/osrs/power_chopper.py`) with the bridge attached:

1. **Chop.** It clicks the nearest cyan-marked tree. `chop_until_idle` waits for the
   plug-in to report the player busy (5 s to start), then idle for 3 ticks
   (`IDLE_SECONDS = 1.8`). Then it returns to `main_loop`.
2. **Burn** when the inventory is full (`burn_all_logs` → `burn_on_one_fire`):
   - If the plug-in reports a fire within 3 tiles, use it, never light beside it:
     - `tend_campfire`: a Forester's Campfire's left-click is "Tend-to".
     - otherwise `add_log_to_fire`: select a log, then `click_fire` (a left-click, or
       the right-click menu when a tree canopy covers the fire).
   - If no fire is reported, `light_with_retry` with the tinderbox (slot 1), then
     `wait_until_idle` for the lighting and the step off the fire to finish.
   - `tend_fire`: the player feeds the campfire by itself until the logs run out. It
     waits for idle.
3. **Walk back** to the grove through the pathfinder, then repeat.

Without the bridge it falls back to the old screen-only behaviour: chat-line OCR to
tell whether it's chopping, and one fire per log.

### Verified live

Run 7 and run 10 (burns 1–2) on the previous design, which added one log to a fire:

- 78 logs over 3 inventories, 0 mismatches, 0 errors.
- Login from logged out to in game in about 16 s.

### NOT verified live

Commit `469e138`, which covers:

- `tend_campfire`
- the right-click fallback in `click_fire`
- the count-based consumption check
- never lighting a fire while one is reported nearby
- `START_TIMEOUT = 5`

Run 11, the test of these, was stopped before it reached the game.

## How to run it

**Client** (developer mode, needed to load the side-loaded plug-in):

```powershell
powershell -ExecutionPolicy Bypass -File plugin\run-dev.ps1
```

- The Jagex account logs in from `~/.runelite/credentials.properties`. See
  `plugin/README.md`, section "Jagex accounts".
- If the direct launch stops logging in, the session has expired. The user must start
  the game once from the Jagex Launcher.
- Never read, print or copy that file. It holds live session tokens, and the auto-mode
  classifier blocks it anyway.

**Plug-in changes:**

```bash
cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test shadowJar --no-daemon -q
```

Then copy `build/libs/runecolor-bridge-1.0-all.jar` to `~/.runelite/sideloaded-plugins/`
and restart the client. The fixture `tests/fixtures/snapshot_v1.json` is shared by the
Java and Python suites.

**Unit tests** (43, no client needed):

```bash
venv/Scripts/python.exe -m unittest discover -s tests/unit -t .
```

**Live run.** It moves the real mouse, so the user must not touch it:

```bash
venv/Scripts/python.exe -u tests/live_power_chopper.py --runs 1 --minutes 30 --bridge --trace --out <scratch>/chopper.json > <scratch>/chopper.log 2>&1
```

- `--trace` prints each plug-in snapshot whose values changed, plus every pathfinder
  request and response.
- To start logged out, call the bot's `logout()` first. The harness logs in by itself.
- Watch it with a Monitor that greps `Burning|Tending|covered|Aimed at|isn't under|wasn't consumed|\[BURN\]|Traceback|SUMMARY`.
- Never poll with `sleep`.

## Bridge snapshot (schema 1)

The plug-in POSTs this JSON to `http://127.0.0.1:8099/api/snapshot/` every tick.

| field | meaning |
|---|---|
| `tick` | game tick counter |
| `sent_at` | send time, in ms |
| `game_state` | e.g. `LOGGED_IN` |
| `hitpoints`, `prayer` | `{current, max}` |
| `run_energy` | 0–100 |
| `world_point` | `{x, y, plane}` |
| `animation` | animation ID, -1 for none |
| `idle` | no animation and the idle pose |
| `fire` | `{x, y}` screen pixels of the nearest Fire or Forester's campfire within 3 tiles, or null |

Animation IDs seen: 877 chop, 733 light, 10572 tend a campfire.

The Python side is `src/utilities/api/bridge_api.py`: `BridgeAPI.idle_for`, `.fire`,
`.animation`, and so on. The new fields are optional, so an older jar still works.

## Open issues

1. **Campfire flow untested.** Watch the first burn closely.
2. **Walking away from a fire may not be far enough.** `walk_to_random_point_nearby` may
   stay inside the plug-in's 3-tile fire radius. In that case `burn_on_one_fire` gives
   up after `max_failed_lights` (3) tries.
3. **The pathfinder is sent `"members": true`** (`src/utilities/api/pathfinder.py`), but
   the account is free-to-play. Long routes could go through members' areas.
4. **The 90 s chop timeout** in `chop_until_idle` is short for willows. It only causes a
   harmless re-click.
5. **Idle for 3 ticks mid-tending** made it tend twice per inventory: the second use
   finishes the last log or so. This is harmless; it could wait longer.
6. **Unmatched login art.** `play-now.png` and `click-here-to-play.png` are whole-button
   captures from specific login themes. If a login stalls, recapture them as text on a
   transparent background.

## Next feature: combat and target data

Agreed with the user as a general bridge feature for other bot scripts. The chopper
doesn't need it.

- `target` from `player.getInteracting()`: name, id, combat level, tile, and the health
  bar (`getHealthRatio` / `getHealthScale`).
- `attackers`: NPCs whose `getInteracting()` is the player.
- `in_combat`, derived: the player has a target, is targeted, or its own health bar is
  showing.
- Side-loaded plug-ins cannot use the event bus (see `plugin/README.md`, "Why there is
  no @Subscribe"), so there are no hitsplat events. Read damage from `hitpoints` per
  tick.

Other candidate fields: inventory item IDs per slot (would replace the sprite matching
that broke on willows), the nearest tree's click point, XP, chat messages, the camera,
world and membership.

## Rules from the user

- **Never resize the RuneLite client.** It runs at whatever size the user sets. The bot
  re-measures its screen regions when the window moves or is resized.
- **No mention of Claude or Claude Code in commits.** No `Co-Authored-By` or
  `Claude-Session` lines.
- **Commit and merge only when asked.** Pushing to `main` bypasses two GitHub rules
  (signed commits, pull requests only). The user accepted that for direct merges before.
- Test live with 30-minute runs. When login matters, start logged out.

## Gotchas learned the hard way

- The RuneLite launcher reads `settings.json` from `%LOCALAPPDATA%\RuneLite`, not from
  `~/.runelite`.
- PowerShell 5.1 splits `-Dfoo.bar=x` arguments, so `run-dev.ps1` quotes them.
- The wiki returns 403 to python-requests' default User-Agent. `sprite_scraper.py` now
  sends its own.
- Inventory sprites from the wiki lack the in-game outline. `willow-logs.png` was cut
  from the live inventory instead.
- The OCR colour for "Fire" is (0, 194, 194), so `OFF_CYAN_TEXT` starts at 180. Mouseover
  matching is case-sensitive: "Campfire" does not contain "Fire".
- With the camera looking straight down, tree canopies cover objects next to them.
