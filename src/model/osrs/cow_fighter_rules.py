"""What the Cow Fighter takes, buries and counts as a kill, kept free of I/O."""

from typing import List, Optional

from utilities.api.bridge_api import GroundItem, Npc, Target, Tile

BONES = 526
EMPTY = -1
TARGET_NAME = "Cow"
LOOT_NAMES = ("Bones",)
# The cow field's west gate, both halves while closed. Open, they change ID.
GATE_CLOSED = frozenset({1558, 1560})
GATE_REACH = 3  # Tiles; a gate further away is not the one blocking our walk.
# Cows wander the whole field; further than this from home, we have left it.
LEASH = 8
# Drops land on the tile the cow died on; a little slack covers one that died
# mid-step, and anything further out is likelier to be someone else's.
LOOT_RADIUS = 2


def loot_to_take(
    items: List[GroundItem], death_tile: Optional[Tile]
) -> List[GroundItem]:
    """Return the Bones lying near where our last target died.

    Args:
        items (List[GroundItem]): The items the plug-in sees near the player.
        death_tile (Optional[Tile]): Where our last target died, or None.

    Returns:
        List[GroundItem]: The items to take, in the order given.
    """
    if death_tile is None:
        return []
    return [
        item
        for item in items
        if item.name in LOOT_NAMES and _near(item.tile, death_tile)
    ]


def is_full(inventory: Optional[List[int]]) -> bool:
    """Whether every slot holds something. Unknown reads as not full."""
    return bool(inventory) and EMPTY not in inventory


def bone_slots(inventory: Optional[List[int]]) -> List[int]:
    """Return the inventory slots holding Bones.

    Args:
        inventory (Optional[List[int]]): Item IDs per slot, or None if unknown.

    Returns:
        List[int]: The slot indices, lowest first.
    """
    return [slot for slot, item in enumerate(inventory or []) if item == BONES]


def is_finished(target: Optional[Target]) -> bool:
    """Whether the fight is over: no target, or one whose health bar is empty.

    Args:
        target (Optional[Target]): The NPC being fought, or None.

    Returns:
        bool: True if there is nothing left to fight.
    """
    return target is None or target.health_ratio == 0


def attack_candidates(npcs: List[Npc], name: str = TARGET_NAME) -> List[Npc]:
    """Return the NPCs of this name that nobody else is fighting, nearest first.

    Args:
        npcs (List[Npc]): The NPCs the plug-in sees, nearest first.
        name (str, optional): The NPC name to fight. Defaults to "Cow".

    Returns:
        List[Npc]: The free ones, in the order given.
    """
    return [npc for npc in npcs if npc.name == name and not npc.busy]


def far_from(here: Optional[Tile], home: Tile, leash: int = LEASH) -> bool:
    """Whether we are further than the leash from home, or on another plane.

    Args:
        here (Optional[Tile]): Our tile, or None if unknown.
        home (Tile): The tile to stay near.
        leash (int, optional): Tiles we may stray. Defaults to `LEASH`.

    Returns:
        bool: True if we should walk home. An unknown position never is, so a
            stale feed does not send us walking on a guess.
    """
    if here is None:
        return False
    return here[2] != home[2] or (
        max(abs(here[0] - home[0]), abs(here[1] - home[1])) > leash
    )


def find_npc(npcs: List[Npc], index: int) -> Optional[Npc]:
    """Return the NPC with this index, or None if it is gone or off screen."""
    return next((npc for npc in npcs if npc.index == index), None)


def _near(tile: Tile, other: Tile) -> bool:
    return (
        tile[2] == other[2]
        and max(abs(tile[0] - other[0]), abs(tile[1] - other[1])) <= LOOT_RADIUS
    )
