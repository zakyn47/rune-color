# Cow Fighter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A "Cow Fighter" script that kills cyan-tagged cows at Lumbridge, loots Bones and Coins from its own kills, and buries the bones, with its own RuneLite profile.

**Architecture:** The RuneColor Bridge snapshot gains `target`, `ground_items` and `inventory`. Python exposes them as typed accessors. The script's decisions (which loot, which slots, whether the target is dead) are pure functions in a rules module. The script finds cows by their cyan NPC Indicators hull, like the chopper finds trees.

**Tech Stack:** Python 3.10 (unittest, Flask bridge), Java 11 plug-in on RuneLite 1.12.38 (JUnit 4, Mockito 4, Gson).

**Spec:** `docs/superpowers/specs/2026-09-28-cow-fighter-design.md`

## Global Constraints

- Branch `feature/cow-fighter` from `main`.
- Snapshot schema stays 1. New fields are optional and omitted when null.
- Item IDs: Bones 526, Coins 995. Loot names: "Bones", "Coins". Loot radius 2 tiles (Chebyshev) from the death tile. Ground item scan radius 5 tiles, at most 10 items.
- Profile key `cow_fighter`; RuneLite name "RuneColor - Cow Fighter".
- HP is ignored. No food logic.
- Never resize the client.
- Checks: `venv/Scripts/python.exe -m unittest discover -s tests/unit -t .`, flake8 and black on changed Python files, `cd plugin && JAVA_HOME="$HOME/tools/jdk-11" ./gradlew test shadowJar --no-daemon -q`.
- Commits: ask the user first; no attribution lines; use `git commit -F <file>` from PowerShell.

---

### Task 1: Snapshot fields in the plug-in (Java)

**Files:**
- Modify: `plugin/src/main/java/com/runecolor/bridge/Snapshot.java`
- Modify: `plugin/src/main/java/com/runecolor/bridge/SnapshotBuilder.java`
- Modify: `plugin/src/test/java/com/runecolor/bridge/SnapshotBuilderTest.java`, `SnapshotFixtureTest.java`, `SnapshotPublisherTest.java`, `LoopbackMain.java`
- Modify: `tests/fixtures/snapshot_v1.json`

**Interfaces:**
- Produces JSON: `target` `{name, health_ratio, health_scale, tile:{x,y,plane}}`; `ground_items` `[{id, name, quantity, tile:{x,y,plane}, x, y}]`; `inventory` `[28 ints]`.
- Java: `Snapshot.Target(String name, int healthRatio, int healthScale, Point tile)`, `Snapshot.GroundItem(int id, String name, int quantity, Point tile, int x, int y)`; the `Snapshot` constructor gains `Target target, List<GroundItem> groundItems, List<Integer> inventory` after `profile`. `SnapshotBuilder.target(Player)`, `SnapshotBuilder.groundItems(Client, Player)`, `SnapshotBuilder.inventory(Client)`.

- [ ] **Step 1: Failing tests.** In `SnapshotBuilderTest`, add tests with Mockito mocks:
  - `reportsTheNpcBeingFought`: player's `getInteracting()` returns a mocked `NPC` named "Cow" with health 0/30 at WorldPoint(3250, 3230, 0); `SnapshotBuilder.target(player)` has name "Cow", ratio 0, scale 30, tile (3250, 3230, 0).
  - `reportsNoTargetWhenNotFighting`: `getInteracting()` null → null.
  - `listsTheInventoryWithEmptySlots`: `client.getItemContainer(InventoryID.INV)` returns a container whose items are `[Item(526,1), Item(-1,0)]`; result has 28 entries, `[526, -1, -1, ...]`.
  - `reportsNoInventoryWhenItIsNotLoaded`: container null → null.
  - `listsNearbyGroundItemsNearestFirst`: build the scene the way the fire tests do; one tile 2 west with a `TileItem` 995 qty 25 and one on the player's tile with 526; `getItemLayer().getCanvasLocation()` returns (100, 50); canvas on screen at (10, 20); `client.getItemDefinition(id).getName()` gives "Coins"/"Bones". Expect Bones first, then Coins, with x=110, y=70 and the tiles' world points.
  - Fixture: add to `tests/fixtures/snapshot_v1.json` `"target": {"name": "Cow", "health_ratio": 12, "health_scale": 30, "tile": {"x": 3250, "y": 3230, "plane": 0}}`, `"ground_items": [{"id": 526, "name": "Bones", "quantity": 1, "tile": {"x": 3250, "y": 3230, "plane": 0}, "x": 600, "y": 410}]`, and `"inventory"` = 28 entries, the first `995`, the rest `-1`; `SnapshotFixtureTest` builds the same.
- [ ] **Step 2: Run** `./gradlew test` and see it fail to compile.
- [ ] **Step 3: Implement.** Add the nested classes and fields to `Snapshot` (with `@SerializedName` for `health_ratio`, `health_scale`, `ground_items`). In `SnapshotBuilder`:
  - Extract the canvas-origin lookup from `nearestFire` into `static java.awt.Point canvasOrigin(Client client)` (null when the canvas is missing or not on screen) and use it in both places.
  - `target(Player)`: `player.getInteracting()`, only an `NPC`, name, `getHealthRatio()`, `getHealthScale()`, world tile.
  - `inventory(Client)`: `client.getItemContainer(InventoryID.INV)` (`net.runelite.api.gameval.InventoryID`), 28 IDs, an item with quantity ≤ 0 or id < 0 → -1.
  - `groundItems(Client, Player)`: scan scene tiles within `GROUND_ITEM_RADIUS = 5`, each `TileItem` on `tile.getGroundItems()` (null-safe), click point from `tile.getItemLayer().getCanvasLocation()` plus the canvas origin, name from `client.getItemDefinition(id).getName()`, sort by Chebyshev distance, keep `MAX_GROUND_ITEMS = 10`. Return null when the canvas isn't on screen.
  - `build(...)` passes the three into the constructor (null for the logged-out branch). Update the three test call sites and `LoopbackMain` with `, null, null, null`.
- [ ] **Step 4: Run** `./gradlew test shadowJar`: all pass.
- [ ] **Step 5: Commit** "Report the fight, nearby loot and the inventory in each snapshot".

---

### Task 2: Typed accessors in `BridgeAPI` (Python)

**Files:**
- Modify: `src/utilities/api/bridge_api.py`
- Test: `tests/unit/test_bridge_api.py`

**Interfaces:**
- Produces: `Target(name: str, health_ratio: int, health_scale: int, tile: Optional[Tuple[int,int,int]])` frozen dataclass; `GroundItem(id: int, name: str, quantity: int, tile: Tuple[int,int,int], point: Tuple[int,int])` frozen dataclass; `BridgeAPI.target -> Optional[Target]`, `BridgeAPI.ground_items -> List[GroundItem]` (empty when unknown), `BridgeAPI.inventory -> Optional[List[int]]`.

- [ ] **Step 1: Failing tests** in `BridgeAPITest`:

```python
    def test_exposes_the_target_from_the_fixture(self):
        self.post(payload())
        self.assertEqual(
            self.bridge.target, Target("Cow", 12, 30, (3250, 3230, 0))
        )

    def test_reports_no_target_when_not_fighting(self):
        self.post(dict(payload(), target=None))
        self.assertIsNone(self.bridge.target)

    def test_exposes_nearby_ground_items(self):
        self.post(payload())
        self.assertEqual(
            self.bridge.ground_items,
            [GroundItem(526, "Bones", 1, (3250, 3230, 0), (600, 410))],
        )

    def test_reports_no_ground_items_from_an_older_plugin(self):
        self.post({k: v for k, v in payload().items() if k != "ground_items"})
        self.assertEqual(self.bridge.ground_items, [])

    def test_exposes_the_inventory(self):
        self.post(payload())
        self.assertEqual(self.bridge.inventory, [995] + [-1] * 27)
```

(import `GroundItem`, `Target` from `utilities.api.bridge_api`).
- [ ] **Step 2: Run** and see them fail on the missing names.
- [ ] **Step 3: Implement** the two dataclasses at module level and three properties next to `fire`, each reading `self._field(...)` so a stale feed retires them together; convert the tile dicts with a small `_tile(d) -> Optional[Tuple[int,int,int]]` helper.
- [ ] **Step 4: Run** the suite, flake8, black.
- [ ] **Step 5: Commit** "Read the fight, nearby loot and the inventory from the bridge".

---

### Task 3: The rules (Python)

**Files:**
- Create: `src/model/osrs/cow_fighter_rules.py`
- Test: `tests/unit/test_cow_fighter_rules.py`

**Interfaces:**
- Produces: `BONES = 526`, `COINS = 995`, `LOOT_NAMES = ("Bones", "Coins")`, `LOOT_RADIUS = 2`, `loot_to_take(items: List[GroundItem], death_tile: Optional[Tuple[int,int,int]]) -> List[GroundItem]`, `bone_slots(inventory: Optional[List[int]]) -> List[int]`, `is_finished(target: Optional[Target]) -> bool`, `coins_held(inventory, quantities)` is NOT needed (coins are counted from the ground item quantities taken).

- [ ] **Step 1: Failing tests**

```python
class LootTest(unittest.TestCase):
    def item(self, name, tile):
        return GroundItem(1, name, 1, tile, (0, 0))

    def test_takes_bones_and_coins_near_the_kill(self):
        items = [self.item("Bones", (10, 10, 0)), self.item("Coins", (12, 9, 0))]
        self.assertEqual(rules.loot_to_take(items, (10, 10, 0)), items)

    def test_leaves_other_items_and_distant_drops(self):
        items = [
            self.item("Cowhide", (10, 10, 0)),
            self.item("Bones", (13, 10, 0)),
            self.item("Bones", (10, 10, 1)),
        ]
        self.assertEqual(rules.loot_to_take(items, (10, 10, 0)), [])

    def test_takes_nothing_without_a_kill(self):
        self.assertEqual(rules.loot_to_take([self.item("Bones", (0, 0, 0))], None), [])


class BonesTest(unittest.TestCase):
    def test_finds_every_bones_slot(self):
        self.assertEqual(rules.bone_slots([526, -1, 995, 526] + [-1] * 24), [0, 3])

    def test_no_inventory_means_nothing_to_bury(self):
        self.assertEqual(rules.bone_slots(None), [])


class FinishedTest(unittest.TestCase):
    def test_a_target_at_zero_health_is_finished(self):
        self.assertTrue(rules.is_finished(Target("Cow", 0, 30, None)))

    def test_no_target_is_finished(self):
        self.assertTrue(rules.is_finished(None))

    def test_a_hurt_target_is_not(self):
        self.assertFalse(rules.is_finished(Target("Cow", 5, 30, None)))

    def test_a_target_without_a_health_bar_yet_is_not(self):
        self.assertFalse(rules.is_finished(Target("Cow", -1, -1, None)))
```

- [ ] **Step 2: Run** and see the import fail.
- [ ] **Step 3: Implement**

```python
"""What the Cow Fighter takes, buries and counts as a kill, kept free of I/O."""

from typing import List, Optional, Tuple

from utilities.api.bridge_api import GroundItem, Target

BONES = 526
COINS = 995
LOOT_NAMES = ("Bones", "Coins")
# Drops land on the tile the cow died on; a little slack covers a death while
# it was stepping, and anything further is likelier someone else's.
LOOT_RADIUS = 2

Tile = Tuple[int, int, int]


def loot_to_take(items: List[GroundItem], death_tile: Optional[Tile]) -> List[GroundItem]:
    """Return the Bones and Coins lying near where our target died."""
    if death_tile is None:
        return []
    return [
        item
        for item in items
        if item.name in LOOT_NAMES and _near(item.tile, death_tile)
    ]


def bone_slots(inventory: Optional[List[int]]) -> List[int]:
    """Return the inventory slots holding Bones."""
    return [slot for slot, item in enumerate(inventory or []) if item == BONES]


def is_finished(target: Optional[Target]) -> bool:
    """Whether the fight is over: no target, or one at zero health."""
    return target is None or target.health_ratio == 0


def _near(tile: Tile, other: Tile) -> bool:
    return (
        tile[2] == other[2]
        and max(abs(tile[0] - other[0]), abs(tile[1] - other[1])) <= LOOT_RADIUS
    )
```

- [ ] **Step 4: Run** the suite, flake8, black.
- [ ] **Step 5: Commit** "Decide what the Cow Fighter loots and buries".

---

### Task 4: The profile

**Files:**
- Create: `src/profiles/cow_fighter.properties`
- Test: `tests/unit/test_runelite_profiles.py`

- [ ] **Step 1: Failing test**

```python
    def test_the_cow_profile_tags_cows_and_shows_their_loot(self):
        path = runelite_profiles.profile_path("cow_fighter")
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertIn("npcindicators.npcToHighlight=Cow", lines)
        self.assertIn("npcindicators.highlightColor=-16711681", lines)
        hidden = next(line for line in lines if line.startswith("grounditems.hiddenItems="))
        self.assertNotIn("Coins", hidden)
        self.assertNotIn("Bones", hidden)
```

- [ ] **Step 2: Run** and see it fail (no file).
- [ ] **Step 3: Derive the profile** from the chopper's with a short Python snippet: read `power_chopper.properties`, replace the `npcindicators.npcToHighlight` line, add or replace `npcindicators.highlightColor`, and drop `Coins` and `Bones` from the comma-separated `grounditems.hiddenItems` value; write `cow_fighter.properties`.
- [ ] **Step 4: Run** the profile tests (the existing rules test the new file too).
- [ ] **Step 5: Commit** "Give the Cow Fighter its RuneLite profile".

---

### Task 5: The script

**Files:**
- Create: `src/model/osrs/cow_fighter.py`
- Modify: `src/model/osrs/__init__.py` (register it)
- Test: `tests/unit/test_cow_fighter.py`

**Interfaces:**
- Consumes: Task 2 accessors, Task 3 rules, `RuneLiteBot.find_and_mouse_to_marked_object`, `get_mouseover_text`, `prepare_standard_initial_state`, `logout_and_stop_script`.
- Produces: `OSRSCowFighter` with `runelite_profile = "cow_fighter"`, counters `kills`, `bones_buried`, `coins_looted`, methods `loot() -> None`, `bury() -> None`, `fight() -> None`, `wait_for_kill(timeout: float = 60) -> None`.

- [ ] **Step 1: Failing tests** on a fake host (borrowed methods, scripted bridge, recorded clicks), as `test_chop_until_idle.py` does:
  - `wait_for_kill` returns once the target's health reads 0, counts a kill, and keeps the target's last tile as `death_tile`.
  - `bury` clicks each Bones slot and counts buried bones once the slot empties.
  - `loot` hovers each item, clicks only when the mouseover has "Take", and adds a Coins item's quantity to `coins_looted` once the inventory changes.
- [ ] **Step 2: Run** and see them fail.
- [ ] **Step 3: Implement** `OSRSCowFighter(OSRSBot)`:
  - Title "Cow Fighter"; description with the setup: the cow field north-east of Lumbridge castle, empty inventory, weapon equipped, NPC Indicators tagging Cow cyan (the script's profile does this), the RuneColor Bridge plug-in required.
  - Options like the chopper's (run time, breaks).
  - `main_loop`: stop with a clear message if `self.bridge` is None or `self.bridge.inventory` is None after 5 s ("needs the RuneColor Bridge plug-in"); `prepare_standard_initial_state()`; loop `loot()`, `bury()`, `fight()`, progress, breaks, `logout_if_greater_than`; end with `logout_and_stop_script("[END]")` and a summary log line of the counters.
  - `fight`: if a target already exists, go straight to `wait_for_kill`; otherwise `find_and_mouse_to_marked_object(self.cp.hsv.CYAN_MARK, "Attack", self.cp.bgr.OFF_WHITE_TEXT, num_retries=3)`, click, wait up to 5 s for `bridge.target`; if none, return (the next pass picks another cow).
  - `wait_for_kill`: poll every tick; track the last non-None target tile; stop when `rules.is_finished(target)`; if it was seen at 0 health, `kills += 1` and set `death_tile`; give up after the timeout.
  - `loot`: for each item from `rules.loot_to_take(self.bridge.ground_items, self.death_tile)`: move to `item.point`, `get_mouseover_text(contains="Take")`, click, wait up to 5 s for `bridge.inventory` to change; on success add `item.quantity` to `coins_looted` for Coins. Clear `death_tile` when nothing is left to take.
  - `bury`: for each slot in `rules.bone_slots(self.bridge.inventory)`: click the inventory slot, wait up to 3 s for that slot to read -1, count it.
- [ ] **Step 4: Run** the suite, flake8, black.
- [ ] **Step 5: Commit** "Add the Cow Fighter script".

---

### Task 6: Live run

- [ ] Rebuild and install the jar; restart RuneLite with `plugin/run-dev.ps1` if it isn't running the new jar (the log line "RuneColor Bridge started" after the copy).
- [ ] Walk the character to the the cow field north-east of Lumbridge castle (ask the user if the bot can't path there).
- [ ] Write `tests/live_cow_fighter.py` modelled on `live_power_chopper.py`: build the bot with the bridge, log in if needed, run `--minutes`, and print kills, bones buried and coins looted, plus the coin count from the bridge inventory... (coins stack in one slot, so read the Coins ground-item quantities taken as the tally, and check the slot holds 995).
- [ ] Run 30 minutes. Pass: kills > 0, bones buried equals bones picked up, no tracebacks.
- [ ] Commit, then ask the user about push and merge.
