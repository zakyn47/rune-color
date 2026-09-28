# Handoff: Cow Fighter (2026-09-28)

Branch `feature/goblin-fighter`, merged into `main`. The script started as a Goblin
Fighter and became the Cow Fighter mid-way (cows move slower). Spec and plan:
`docs/superpowers/specs/2026-09-28-cow-fighter-design.md`,
`docs/superpowers/plans/2026-09-28-cow-fighter.md` (their text was renamed from
goblins to cows; the design is unchanged).

## Status

**Built and unit-tested, NOT verified live.** Nothing has been killed yet.

- The first live run (still goblins) attacked nothing. The script found targets by
  scanning for their cyan outline and then checking the mouseover, but a moving NPC
  had left by the time the cursor arrived, and each miss triggered
  `find_and_mouse_to_marked_object`'s camera and zoom resets (10–50 s each). Fixed
  by aiming with the plug-in's live NPC positions instead (see "How it works").
- The second live run (cows, the fix above) never reached the fighting: the walk
  to the cow field stalled at step 17/18 for over two minutes, most likely at the
  field's fence or gate. It was stopped there.

## Your task

1. **Get into the cow field.** Either stand the character inside the field by hand
   and run without `--walk`, or fix the walk: `tests/live_cow_fighter.py` walks to
   `COWS = Point(3256, 3272)` through the DAX pathfinder, and the path stalls at
   its last step. Check whether that tile is inside the fence and whether the
   gate needs opening.
2. **Verify live with 5-minute runs** (the user's rule for the fighter):
   `venv/Scripts/python.exe -u tests/live_cow_fighter.py --minutes 5 [--walk]`.
   Pass: kills > 0, bones buried > 0, no tracebacks.
3. Tune what the live run shows: attack timing, loot pickup, burying.

## How it works

`OSRSCowFighter` (`src/model/osrs/cow_fighter.py`), with its decisions in
`src/model/osrs/cow_fighter_rules.py` (pure functions, unit-tested). Each pass:

1. **Loot:** after a kill, wait up to 3 s for drops, then take Bones or Coins lying
   within 2 tiles of the death tile, one at a time, re-reading the ground after
   each take. It clicks only when the mouseover reads "Take".
2. **Bury:** click every Bones slot (item 526), and wait for the slot to empty.
3. **Fight:** if there's no target, pick the nearest cow nobody else is fighting,
   follow it by its index for two aiming passes at "fastest" mouse speed, click
   when the mouseover reads "Attack", and wait until the plug-in reports a target.
   Then wait until the target's health bar reads 0 (a kill, with its tile kept as
   the death tile) or the target disappears (no kill).

It needs the RuneColor Bridge. Without an inventory from the plug-in within 5 s, it
stops with a message. HP is ignored by design.

## Bridge snapshot additions (schema still 1, all optional)

| field | meaning |
|---|---|
| `target` | `{name, health_ratio, health_scale, tile}` of the NPC the player interacts with; ratio -1 while no health bar shows |
| `ground_items` | up to 10 items within 5 tiles, nearest first: `{id, name, quantity, tile, x, y}` (x, y = screen click point) |
| `inventory` | 28 item IDs, -1 for empty |
| `npcs` | up to 10 on-screen NPCs within 10 tiles, nearest first: `{index, name, level, tile, x, y, busy}`; `busy` = fighting someone else |

Python: `BridgeAPI.target`, `.ground_items`, `.inventory`, `.npcs` with the
`Target`, `GroundItem`, `Npc` dataclasses in `utilities/api/bridge_api.py`.

## Profile

`src/profiles/cow_fighter.properties`, derived from the chopper's profile:
NPC Indicators tags `Cow` in cyan (`-16711681`), and Ground Items no longer hides
Coins and Bones. The cyan tag is now only a visual marker; aiming uses the
plug-in's positions.

Leftover: RuneLite still has a "RuneColor - Goblin Fighter" profile from the first
run. Delete it in RuneLite's Profiles panel.

## Tests

- Java: `SnapshotBuilderTest` covers target, inventory, ground items and NPCs; the
  shared fixture `tests/fixtures/snapshot_v1.json` carries all four fields.
- Python: `tests/unit/test_cow_fighter.py` (fight, aim, loot, bury on a fake
  host), `test_cow_fighter_rules.py`, `test_bridge_api.py`,
  `test_runelite_profiles.py`.

## Rules from the user

- Fighter test runs are **5 minutes**, not 30.
- Never resize the RuneLite client. Commit and merge only when asked; no
  attribution lines. From PowerShell, commit with `git commit -F <file>`.
- RuneLite must run in developer mode (`plugin/run-dev.ps1`) for the side-loaded
  plug-in to load. After a plug-in change: rebuild, copy the jar to
  `~/.runelite/sideloaded-plugins/`, restart the client.
