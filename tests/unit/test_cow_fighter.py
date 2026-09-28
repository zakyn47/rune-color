"""The Cow Fighter's fight, loot and bury steps, tested without a client.

The borrowed methods are the shipped ones, run on a minimal host whose bridge is
changed by each click the way the game would change it.
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.osrs.cow_fighter import OSRSCowFighter  # noqa: E402
from utilities.api.bridge_api import GroundItem, Npc, Target  # noqa: E402

EMPTY = [-1] * 28


class FakeBridge:
    def __init__(self, targets=(None,), ground_items=(), inventory=EMPTY, npcs=()):
        self._targets = list(targets)
        self.ground_items = list(ground_items)
        self.inventory = list(inventory)
        self.npcs = list(npcs)

    @property
    def target(self):
        return self._targets.pop(0) if len(self._targets) > 1 else self._targets[0]


class FakeMouse:
    def __init__(self, on_click):
        self.on_click = on_click
        self.clicks = 0
        self.moves = []

    def move_to(self, point, **kwargs):
        self.moves.append(point)

    def click(self):
        self.clicks += 1
        self.on_click()


class FakeFighter:
    wait_for_kill = OSRSCowFighter.wait_for_kill
    loot = OSRSCowFighter.loot
    take = OSRSCowFighter.take
    bury = OSRSCowFighter.bury
    _wait_until = OSRSCowFighter._wait_until
    _slot_item = OSRSCowFighter._slot_item
    attack = OSRSCowFighter.attack
    aim_at = OSRSCowFighter.aim_at
    game_tick = 0.003

    def __init__(self, bridge, on_click=lambda: None, says_take=True):
        self.bridge = bridge
        self.mouse = FakeMouse(on_click)
        self.says_take = says_take
        slot = SimpleNamespace(random_point=lambda: None)
        self.win = SimpleNamespace(inventory_slots=[slot] * 28)
        self.death_tile = None
        self.kills = 0
        self.bones_buried = 0
        self.coins_looted = 0
        self.messages = []

    def get_mouseover_text(self, contains=None, colors=None):
        return self.says_take

    def walk_to_random_point_nearby(self, verbose=True):
        self.walked = True

    def log_msg(self, msg, overwrite=False):
        self.messages.append(msg)


class WaitForKillTest(unittest.TestCase):
    def test_counts_a_kill_and_remembers_where_it_died(self):
        bridge = FakeBridge(
            targets=[
                Target("Cow", 20, 30, (10, 10, 0)),
                Target("Cow", 0, 30, (11, 10, 0)),
                None,
            ]
        )
        bot = FakeFighter(bridge)
        bot.wait_for_kill(timeout=1)
        self.assertEqual(bot.kills, 1)
        self.assertEqual(bot.death_tile, (11, 10, 0))

    def test_a_fight_that_ends_without_a_kill_counts_nothing(self):
        bridge = FakeBridge(targets=[Target("Cow", 20, 30, (10, 10, 0)), None])
        bot = FakeFighter(bridge)
        bot.wait_for_kill(timeout=1)
        self.assertEqual(bot.kills, 0)


class LootTest(unittest.TestCase):
    def coins(self):
        return GroundItem(995, "Coins", 25, (10, 10, 0), (300, 200))

    def test_takes_coins_near_the_kill_and_counts_them(self):
        bridge = FakeBridge(ground_items=[self.coins()])

        def picked_up():
            bridge.ground_items = []
            bridge.inventory = [995] + [-1] * 27

        bot = FakeFighter(bridge, on_click=picked_up)
        bot.death_tile = (10, 10, 0)
        bot.loot()
        self.assertEqual(bot.coins_looted, 25)
        self.assertIsNone(bot.death_tile)

    def test_does_not_click_when_the_cursor_does_not_read_take(self):
        bot = FakeFighter(FakeBridge(ground_items=[self.coins()]), says_take=False)
        bot.death_tile = (10, 10, 0)
        bot.loot()
        self.assertEqual(bot.mouse.clicks, 0)
        self.assertEqual(bot.coins_looted, 0)


class AttackTest(unittest.TestCase):
    def cow(self, index, point, busy=False):
        return Npc(index, "Cow", 2, (0, 0, 0), point, busy)

    def test_follows_the_nearest_free_cow_and_attacks_it(self):
        bridge = FakeBridge(npcs=[self.cow(1, (5, 5), busy=True), self.cow(2, (9, 9))])

        def engaged():
            bridge._targets = [Target("Cow", 30, 30, (0, 0, 0))]

        bot = FakeFighter(bridge, on_click=engaged)
        self.assertIs(bot.attack(), True)
        self.assertEqual(bot.mouse.moves, [(9, 9), (9, 9)])
        self.assertEqual(bot.mouse.clicks, 1)

    def test_moves_on_when_no_cow_is_free(self):
        bot = FakeFighter(FakeBridge(npcs=[self.cow(1, (5, 5), busy=True)]))
        self.assertIs(bot.attack(), False)
        self.assertTrue(bot.walked)
        self.assertEqual(bot.mouse.clicks, 0)


class BuryTest(unittest.TestCase):
    def test_buries_every_bone_in_the_inventory(self):
        bridge = FakeBridge(inventory=[526, -1, 526] + [-1] * 25)

        def buried():
            bridge.inventory[bridge.inventory.index(526)] = -1

        bot = FakeFighter(bridge, on_click=buried)
        bot.bury()
        self.assertEqual(bot.bones_buried, 2)
        self.assertEqual(bot.mouse.clicks, 2)


if __name__ == "__main__":
    unittest.main()
