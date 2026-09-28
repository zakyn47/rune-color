# Cow Fighter (design)

Date: 2026-09-28. Status: approved in chat.

## Goal

A new script, "Cow Fighter", that kills cyan-tagged cows east of Lumbridge
castle, picks up the Bones and Coins they drop, and buries the bones. It ships its
own RuneLite profile. Hitpoints are ignored: no food, no low-HP exit.

## Decisions

- Cows are found by colour: NPC Indicators tags them cyan, as Object Markers
  tags the chopper's trees.
- The fight and the loot are read from the RuneColor Bridge, not the screen:
  sprite and text matching caused the chopper's phantom logs.
- Bones are buried right after they are picked up.
- Only loot within 2 tiles of where our own target died is taken, so other
  players' drops are left alone.

## Profile: `src/profiles/cow_fighter.properties`

Derived from `power_chopper.properties` with these keys changed:

- `npcindicators.npcToHighlight=Cow`
- `npcindicators.highlightColor=-16711681` (cyan, `#FF00FFFF`, as the chopper's
  `objectindicators.markerColor`)
- `grounditems.hiddenItems` without `Coins` and `Bones`

The bridge stays enabled, and there is no window geometry, as for every script
profile. `tests/unit/test_runelite_profiles.py` checks both rules; a new test pins
the three keys above.

## Bridge snapshot additions (schema stays 1)

All optional and omitted when null, so older jars and bots keep working.

- `target`: the NPC the player is interacting with, or null:
  `{name, health_ratio, health_scale, tile: {x, y, plane}}`. `health_ratio` is -1
  while no health bar is showing.
- `ground_items`: items within 5 tiles, nearest first, at most 10:
  `[{id, name, quantity, tile: {x, y, plane}, x, y}]`, where the top-level x and y are
  the screen point to click (the tile's centre, offset by the canvas's position, as
  `fire` is).
- `inventory`: 28 item IDs, -1 for an empty slot.

`BridgeAPI` gains `target -> Optional[Target]`, `ground_items -> List[GroundItem]`
and `inventory -> Optional[List[int]]`, with `Target` and `GroundItem` as frozen
dataclasses.

## Script loop

1. **Loot.** Take every Bones or Coins item within 2 tiles of the tile where the
   last target died. Hover the item's screen point, require the mouseover to read
   "Take", click, and wait up to 5 s for the inventory to change.
2. **Bury.** For each inventory slot holding Bones (item 526), click it, and wait
   up to 3 s for the slot to empty.
3. **Fight.** If there is no target, mouse to the nearest cyan cow, requiring
   the mouseover "Attack", and click. If no target appears within 5 s, try the next
   one. Then wait until the target's health is 0 or the target is gone, remembering
   its last tile as the death tile, for up to 60 s.
4. Repeat until the run time ends, with the usual breaks and relog.

The rules for which items to take, which slots to bury and when a target is dead
are pure functions in their own module, `model/osrs/cow_fighter_rules.py`, so
they are unit-tested without a client.

## Testing

- Java: unit tests for `target`, `ground_items` and `inventory` in
  `SnapshotBuilderTest`, and the shared fixture gains the three fields.
- Python: `BridgeAPI` accessors, the rules module, and the profile keys.
- Live: a 30-minute run from logged out, counting kills, bones buried and coins
  gained (from the bridge's inventory), with no errors.

## Out of scope

Food, safe-spotting, banking, other monsters, and walking to Lumbridge. The user
starts the script next to the cows.
