"""Which slots the Power Miner drops and when it counts as full, kept free of I/O."""

from typing import List, Optional

TIN_ORE = 438
# Uncut sapphire, emerald, ruby and diamond: the gems mining can give.
GEMS = frozenset({1623, 1621, 1619, 1617})
DROPPED = GEMS | {TIN_ORE}
EMPTY = -1


def ore_slots(inventory: Optional[List[int]], ore: int = TIN_ORE) -> List[int]:
    """Return the inventory slots holding the ore, lowest first.

    Args:
        inventory (Optional[List[int]]): Item IDs per slot, or None if unknown.
        ore (int, optional): The item ID to look for. Defaults to tin ore.

    Returns:
        List[int]: The slot indices.
    """
    return [slot for slot, item in enumerate(inventory or []) if item == ore]


def drop_slots(inventory: Optional[List[int]]) -> List[int]:
    """Return the inventory slots holding tin ore or a gem, lowest first."""
    return [slot for slot, item in enumerate(inventory or []) if item in DROPPED]


def is_full(inventory: Optional[List[int]]) -> bool:
    """Whether every slot holds something. Unknown reads as not full."""
    return bool(inventory) and EMPTY not in inventory


def drop_order(slots: List[int], traversal: List[int]) -> List[int]:
    """Return the slots to drop, in the order the traversal path visits them."""
    wanted = set(slots)
    return [slot for slot in traversal if slot in wanted]
