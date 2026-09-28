"""The Power Miner's rules and its mine and drop steps, tested without a client."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import model.osrs.power_miner_rules as rules  # noqa: E402
from model.osrs.power_miner import OSRSPowerMiner  # noqa: E402
from utilities import runelite_profiles  # noqa: E402

TIN = rules.TIN_ORE
PICKAXE = 1265
SAPPHIRE = 1623
EMPTY = [-1] * 28


class RulesTest(unittest.TestCase):
    def test_finds_only_tin_ore(self):
        inventory = [PICKAXE, TIN, 436, TIN] + [-1] * 24
        self.assertEqual(rules.ore_slots(inventory), [1, 3])

    def test_unknown_inventory_has_no_ore_and_is_not_full(self):
        self.assertEqual(rules.ore_slots(None), [])
        self.assertFalse(rules.is_full(None))

    def test_full_only_without_empty_slots(self):
        self.assertTrue(rules.is_full([TIN] * 28))
        self.assertFalse(rules.is_full([TIN] * 27 + [-1]))

    def test_drop_slots_cover_tin_and_every_gem(self):
        inventory = [PICKAXE, TIN, 1623, 1621, 1619, 1617, 23442] + [-1] * 21
        self.assertEqual(rules.drop_slots(inventory), [1, 2, 3, 4, 5])

    def test_drop_order_follows_the_traversal(self):
        self.assertEqual(rules.drop_order([1, 4, 5], [5, 0, 1, 2, 4]), [5, 1, 4])


class FakeBridge:
    def __init__(self, inventory, idle_for=0.0):
        self.inventory = list(inventory)
        self.idle_for = idle_for


class FakeMouse:
    def __init__(self, on_click):
        self.on_click = on_click
        self.clicks = 0

    def move_to(self, point, **kwargs):
        pass

    def click(self):
        self.clicks += 1
        self.on_click()


class FakeMiner:
    mine = OSRSPowerMiner.mine
    drop_ore = OSRSPowerMiner.drop_ore
    _ore_count = OSRSPowerMiner._ore_count
    _wait_until = OSRSPowerMiner._wait_until
    game_tick = 0.003

    def __init__(self, bridge, rocks=1, says_tin=True, on_click=lambda: None):
        self.bridge = bridge
        self.mouse = FakeMouse(on_click)
        self.says_tin = says_tin
        self.rocks = rocks
        self.mark_color = None
        self.win = SimpleNamespace(game_view=None)
        self.ores_mined = 0
        self.ores_dropped = 0
        self.gems_dropped = 0
        self.dropped_slots = []

    def find_colors(self, rect, colors):
        point = SimpleNamespace(x=0, y=0)
        rock = SimpleNamespace(
            random_point=lambda: point,
            center=point,
            rect=SimpleNamespace(center=point),
        )
        return [rock] * self.rocks

    def get_mouseover_text(self, contains=None, colors=None):
        return self.says_tin

    def get_inv_drop_traversal_path(self):
        return list(range(28))

    def drop_items(self, slots, verbose=True):
        self.dropped_slots = list(slots)
        for slot in slots:
            self.bridge.inventory[slot] = -1

    def log_msg(self, msg, overwrite=False):
        pass


class MineTest(unittest.TestCase):
    def test_counts_the_ore_a_rock_gives(self):
        bridge = FakeBridge(EMPTY)

        def ore_arrives():
            bridge.inventory[0] = TIN

        bot = FakeMiner(bridge, on_click=ore_arrives)
        self.assertTrue(bot.mine())
        self.assertEqual(bot.ores_mined, 1)

    def test_counts_the_first_ore_into_an_empty_inventory(self):
        # The game never sends an empty inventory, so the plug-in has none to report.
        bridge = FakeBridge(EMPTY)
        bridge.inventory = None

        def ore_arrives():
            bridge.inventory = [TIN] + [-1] * 27

        bot = FakeMiner(bridge, on_click=ore_arrives)
        self.assertTrue(bot.mine())
        self.assertEqual(bot.ores_mined, 1)

    def test_no_marked_rock_means_no_click(self):
        bot = FakeMiner(FakeBridge(EMPTY), rocks=0)
        self.assertFalse(bot.mine())
        self.assertEqual(bot.mouse.clicks, 0)

    def test_does_not_click_a_rock_that_is_not_tin(self):
        bot = FakeMiner(FakeBridge(EMPTY), says_tin=False)
        self.assertFalse(bot.mine())
        self.assertEqual(bot.mouse.clicks, 0)


class DropTest(unittest.TestCase):
    def test_drops_only_tin_ore(self):
        inventory = [PICKAXE] + [TIN] * 26 + [995]
        bot = FakeMiner(FakeBridge(inventory))
        self.assertTrue(bot.drop_ore())
        self.assertEqual(bot.dropped_slots, list(range(1, 27)))
        self.assertEqual(bot.bridge.inventory[0], PICKAXE)
        self.assertEqual(bot.bridge.inventory[27], 995)
        self.assertEqual(bot.ores_dropped, 26)

    def test_drops_gems_with_the_ore(self):
        inventory = [PICKAXE, TIN, SAPPHIRE, 23442, TIN] + [-1] * 23
        bot = FakeMiner(FakeBridge(inventory))
        self.assertTrue(bot.drop_ore())
        self.assertEqual(bot.dropped_slots, [1, 2, 4])
        self.assertEqual(bot.bridge.inventory[3], 23442)
        self.assertEqual((bot.ores_dropped, bot.gems_dropped), (2, 1))

    def test_a_gem_alone_is_still_dropped(self):
        bot = FakeMiner(FakeBridge([PICKAXE] * 27 + [SAPPHIRE]))
        self.assertTrue(bot.drop_ore())
        self.assertEqual(bot.gems_dropped, 1)

    def test_nothing_to_drop_reports_failure(self):
        bot = FakeMiner(FakeBridge([PICKAXE] * 28))
        self.assertFalse(bot.drop_ore())
        self.assertEqual(bot.dropped_slots, [])


class ProfileTest(unittest.TestCase):
    def test_the_miner_has_a_profile_without_stray_cyan_markers(self):
        path = runelite_profiles.profile_path(OSRSPowerMiner.runelite_profile)
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertIn("runelite.objectindicatorsplugin=true", lines)
        self.assertIn("npcindicators.npcToHighlight=", lines)
        markers = [
            line for line in lines if line.startswith("objectindicators.region_")
        ]
        self.assertEqual(len(markers), 1)
        self.assertTrue(markers[0].startswith("objectindicators.region_12849="))
        self.assertEqual(markers[0].count('"Tin rocks"'), 3)


if __name__ == "__main__":
    unittest.main()
