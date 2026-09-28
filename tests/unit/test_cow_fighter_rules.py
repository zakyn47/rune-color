"""What the Cow Fighter loots, buries and counts as a kill."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import model.osrs.cow_fighter_rules as rules  # noqa: E402
from utilities.api.bridge_api import GroundItem, Npc, Target  # noqa: E402


def item(name, tile):
    return GroundItem(1, name, 1, tile, (0, 0))


class LootTest(unittest.TestCase):
    def test_takes_bones_and_coins_near_the_kill(self):
        items = [item("Bones", (10, 10, 0)), item("Coins", (12, 9, 0))]
        self.assertEqual(rules.loot_to_take(items, (10, 10, 0)), items)

    def test_leaves_other_items_and_distant_drops(self):
        items = [
            item("Cowhide", (10, 10, 0)),
            item("Bones", (13, 10, 0)),
            item("Bones", (10, 10, 1)),
        ]
        self.assertEqual(rules.loot_to_take(items, (10, 10, 0)), [])

    def test_takes_nothing_without_a_kill(self):
        self.assertEqual(rules.loot_to_take([item("Bones", (0, 0, 0))], None), [])


def npc(index, name="Cow", busy=False):
    return Npc(index, name, 2, (0, 0, 0), (index, index), busy)


class AttackCandidatesTest(unittest.TestCase):
    def test_keeps_free_cows_in_order(self):
        npcs = [npc(1), npc(2, busy=True), npc(3, name="Man"), npc(4)]
        self.assertEqual(rules.attack_candidates(npcs), [npc(1), npc(4)])

    def test_finds_a_cow_again_by_its_index(self):
        self.assertEqual(rules.find_npc([npc(1), npc(4)], 4), npc(4))
        self.assertIsNone(rules.find_npc([npc(1)], 4))


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


if __name__ == "__main__":
    unittest.main()
