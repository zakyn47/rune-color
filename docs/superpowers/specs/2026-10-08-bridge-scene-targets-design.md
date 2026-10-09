# Bridge scene targets: objects, inventory slots, menu (design)

Date: 2026-10-08. Status: awaiting review.

## Goal

The RuneColor Bridge plug-in reports exact click targets so scripts stop
guessing with colour markers, template matching and mouseover OCR. Python
still decides what to do and still moves the real mouse with humanized paths.
The plug-in only reports; it never clicks or invokes menu actions.

The first consumer is the Power Miner, which proves all three targets at once.

## Decisions

- Automation level: the plug-in sends targets; Python clicks (no synthetic
  input inside the client, no `menuAction`). Keeps the detection profile of the
  current input path.
- Scope of v1: game objects by ID, inventory slot rectangles, menu entries.
- The bot names the object IDs it wants in its reply to each snapshot.
- Objects are sent as their clickbox outline (a screen polygon). Python picks a
  random point inside it, so all humanization stays in Python.
- The Power Miner drops its colour/OCR code entirely. It already refuses to run
  without the bridge, so there is no vision fallback. Other scripts are
  unchanged until migrated.

## Wire format (schema 1 → 2)

Both sides bump `SCHEMA_VERSION` to 2. A mismatch already disables the bridge,
so the jar and Python must be updated together.

### Bot → plug-in (reply)

```json
{"profile": {"name": "...", "path": "..."}, "objects": [11360, 11361]}
```

The plug-in keeps what the latest reply asked for. A missing, empty or malformed
`objects` means no objects are reported (the bot states its wish on every reply,
so the next good reply corrects it).

### Plug-in → bot (snapshot), new fields

```json
"objects": [
  {"id": 11360, "tile": {"x": 3229, "y": 3148, "plane": 0}, "distance": 2,
   "hull": [[812, 401], [840, 398], [851, 430]]}
],
"inventory_slots": [[x, y, w, h], "... 28 entries"],
"menu": {"open": false,
         "top": {"option": "Mine", "target": "Tin rocks"},
         "entries": [{"option": "Mine", "target": "Tin rocks", "rect": [x, y, w, h]}]}
```

- `inventory` (item IDs per slot) is unchanged. Slot rectangles are a separate
  field so the chopper and cow fighter keep working, and so slots are known even
  when the game sends no inventory (empty inventory).
- All coordinates are screen pixels with the canvas origin added, as for NPCs.
- `objects`: requested IDs only, `GameObject`s only, within 15 tiles, on the
  player's plane, nearest first (Chebyshev distance), at most 10. Objects with
  no clickbox (off screen) are skipped. `hull` has 3 to 20 points.
- `inventory_slots`: exactly 28 rectangles, or null when the inventory widget is
  hidden.
- `menu.entries` is top-first and empty when the menu is closed. `menu.top` is
  what a left-click would do (the hover text), or null when there is no entry.
  Option and target text have colour tags stripped.
- Each field is built independently. If building one throws, that field is null
  and the rest of the snapshot is still sent.

## Plug-in (Java, `com.runecolor.bridge`)

| Class | Responsibility |
|---|---|
| `BotReply` | Parses a reply body once into `profile` and `objects`. |
| `ProfileSwitcher` | Unchanged behaviour, but takes the parsed `BotReply` instead of parsing JSON itself. |
| `ObjectRequest` | Holds the latest requested ID set (`AtomicReference<Set<Integer>>`). Written on the publisher thread, read on the client thread. |
| `ObjectScanner` | Scans scene tiles within 15 tiles for `GameObject`s in the requested set and builds `Snapshot.SceneObject`s. Reuses `SnapshotBuilder`'s nearest-first helper; a multi-tile object is reported once. |
| `HullOutline` | Pure function: clickbox `Shape` + canvas origin → screen polygon of 3 to 20 points (flatten the path, convex hull, drop points evenly). |
| `InventorySlots` | Inventory container widget → 28 child bounds, or null when hidden. |
| `MenuReader` | Reads `isMenuOpen()`, `getMenuEntries()` (bottom-up in the client, reversed here), menu x/y/width. Entry rect = menu origin + 19 px header + 15 px per row. Top entry = last element of the client's array. |

`SnapshotBuilder` coordinates these. Everything runs where snapshots are built
today, on the client thread from the plug-in's timer. No new threads.

### Plug-in tests (JUnit)

- `HullOutline`: point count is 3 to 20; every point lies within the shape's bounds
  plus origin; degenerate shapes give null.
- `BotReply`: `objects` missing, empty, malformed, valid.
- `MenuReader`: entry rect arithmetic and reversal; colour-tag stripping.
- `ObjectScanner`: mocked scene, in the style of `SnapshotBuilderTest`: filters
  by ID and plane, radius, nearest-first order, cap of 10, skips null clickboxes.

## Python

### `utilities/api/bridge_api.py`

- `SCHEMA_VERSION = 2`.
- `request_objects(ids: Iterable[int])` and `clear_objects()`, stored under the
  same lock as the wanted profile and sent in every reply.
- Read-only properties, following the existing pattern (stale or missing →
  empty list or None):
  - `objects -> List[SceneObject]`, a dataclass with `id`, `tile`, `distance` and
    `hull: Polygon`.
  - `inventory_slots -> Optional[List[Rectangle]]`.
  - `menu -> Optional[Menu]`, a dataclass with `open`, `top`, `entries` and a
    `top_text` property (`"Mine Tin rocks"`).

### `utilities/geometry.py`

New `Polygon` built from screen points. The constructor rejects fewer than
3 points. It has `random_point()` (rejection sampling inside the bounds, biased to
the centre like `Rectangle.random_point`), `contains(point)` and `center` (property).

### `RuneLiteBot`

- `move_to_scene_object(obj)`: moves the mouse to `obj.hull.random_point()`.
- `wait_for_hover_text(contains) -> bool`: waits up to 1.5 s for `bridge.menu.top_text`
  to contain the text, because a snapshot lags the mouse by up to a tick. No OCR.
- `drop_items` accepts an optional source of slot rectangles. The default stays
  the template-measured slots, so other scripts are unchanged.

### Python tests (unittest)

- `Polygon`: sampled points always inside; constructor validation.
- `bridge_api`: parsing of the three new fields and the `objects` request in the
  reply, through the shared fixture renamed to `snapshot_v2.json`.

## Power Miner

- `Ore` gains `rock_ids: FrozenSet[int]`, required non-empty in
  `__post_init__`. Tin {11360, 11361}, Iron {11364, 11365}: live (not depleted)
  IDs, to be confirmed against the client in the first live check.
- On start: `bridge.request_objects(ore.rock_ids)`. On stop: `clear_objects()`.
- `mine_until_found`: picks from `bridge.objects`, usually the nearest,
  sometimes the second nearest. With none in view, keeps today's camera-turn
  search and `SEARCH_TIMEOUT`.
- `mine`: `move_to_scene_object(rock)`, then `wait_for_hover_text(ore.rock_word)`,
  then click.
- `drop_ore`: drops using the bridge's slot rectangles.
- Removed: `mark_color` and the cyan marker search; object-marker entries in
  `src/profiles/power_miner.properties`; "mark rocks cyan" from the setup text.
- If the bridge goes stale mid-run, the script logs it and stops cleanly, as it
  does today.

## Verification

1. `gradlew test`, the unittest suite, flake8 and black pass.
2. Jar rebuilt and side-loaded; a throwaway probe prints objects, slots and menu
   while standing at the mine (also confirms the rock IDs).
3. `tests/live_power_miner.py --minutes 5`, then `--minutes 30`. Pass: "other
   items kept: PASS", ore mined and dropped, no colour or OCR calls in the log.

## Out of scope

- Migrating the Power Chopper and Cow Fighter.
- Wall, decorative and ground objects.
- Combat/target fields from the bridge backlog.
- Any in-client input or menu invocation.
