"""Which slots the Power Miner drops and when it counts as full, kept free of I/O."""

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional

# Uncut sapphire, emerald, ruby and diamond: the gems mining can give.
GEMS = frozenset({1623, 1621, 1619, 1617})
EMPTY = -1


@dataclass(frozen=True)
class Ore:
    """An ore the Power Miner can mine, and how to recognise its rock."""

    name: str
    item_id: int
    # The rock's mouseover reads "Mine <rock_word> rocks".
    rock_word: str

    def __post_init__(self) -> None:
        if not self.name or not self.rock_word or self.item_id < 0:
            raise ValueError(f"Incomplete ore: {self!r}")

    @property
    def dropped(self) -> FrozenSet[int]:
        """The item IDs dropped on a full inventory: this ore and every gem."""
        return GEMS | {self.item_id}


TIN = Ore("Tin", 438, "Tin")
IRON = Ore("Iron", 440, "Iron")
ORES: Dict[str, Ore] = {ore.name: ore for ore in (TIN, IRON)}


def ore_slots(inventory: Optional[List[int]], ore: Ore) -> List[int]:
    """Return the inventory slots holding the ore, lowest first.

    Args:
        inventory (Optional[List[int]]): Item IDs per slot, or None if unknown.
        ore (Ore): The ore to look for.

    Returns:
        List[int]: The slot indices.
    """
    return [slot for slot, item in enumerate(inventory or []) if item == ore.item_id]


def drop_slots(inventory: Optional[List[int]], ore: Ore) -> List[int]:
    """Return the inventory slots holding the ore or a gem, lowest first."""
    dropped = ore.dropped
    return [slot for slot, item in enumerate(inventory or []) if item in dropped]


def is_full(inventory: Optional[List[int]]) -> bool:
    """Whether every slot holds something. Unknown reads as not full."""
    return bool(inventory) and EMPTY not in inventory


def drop_order(slots: List[int], traversal: List[int]) -> List[int]:
    """Return the slots to drop, in the order the traversal path visits them."""
    wanted = set(slots)
    return [slot for slot in traversal if slot in wanted]
