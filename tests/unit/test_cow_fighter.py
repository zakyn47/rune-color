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
import model.osrs.cow_fighter_rules as rules  # noqa: E402
from utilities.api.bridge_api import (  # noqa: E402
    GroundItem,
    Menu,
    MenuEntry,
    Npc,
    Target,
)
from utilities.geometry import Rectangle  # noqa: E402

EMPTY = [-1] * 28


class FakeBridge:
    def __init__(self, targets=(None,), ground_items=(), inventory=EMPTY, npcs=()):
        self._targets = list(targets)
        self.ground_items = list(ground_items)
        self.inventory = None if inventory is None else list(inventory)
        self.npcs = list(npcs)
        self.inventory_slots = None
        self.game_state = "LOGGED_IN"
        self.world_point = (3256, 3272, 0)
        self._hitpoints = [(15, 15)]
        self.menu = hover("Take Bones")
        self.objects = []
        self.requested = None

    def request_objects(self, ids):
        self.requested = set(ids)

    def clear_objects(self):
        self.requested = None

    @property
    def hitpoints(self):
        if len(self._hitpoints) > 1:
            return self._hitpoints.pop(0)
        return self._hitpoints[0]

    @hitpoints.setter
    def hitpoints(self, value):
        self._hitpoints = [value]

    @property
    def target(self):
        return self._targets.pop(0) if len(self._targets) > 1 else self._targets[0]


class FakeMouse:
    def __init__(self, on_click):
        self.on_click = on_click
        self.clicks = 0
        self.right_clicks = 0
        self.on_right_click = lambda: None
        self.moves = []

    def move_to(self, point, **kwargs):
        self.moves.append(point)

    def click(self):
        self.clicks += 1
        self.on_click()

    def right_click(self, force_delay=False):
        self.right_clicks += 1
        self.on_right_click()


class FakeFighter:
    wait_for_kill = OSRSCowFighter.wait_for_kill
    loot = OSRSCowFighter.loot
    take = OSRSCowFighter.take
    bury = OSRSCowFighter.bury
    bury_when_full = OSRSCowFighter.bury_when_full
    drop_cowhides = OSRSCowFighter.drop_cowhides
    _wait_until = OSRSCowFighter._wait_until
    _slot_item = OSRSCowFighter._slot_item
    attack = OSRSCowFighter.attack
    aim_at = OSRSCowFighter.aim_at
    bridge_is_heard = OSRSCowFighter.bridge_is_heard
    stay_home = OSRSCowFighter.stay_home
    open_gate = OSRSCowFighter.open_gate
    _aim_at_item = OSRSCowFighter._aim_at_item
    _aim_at_gate = OSRSCowFighter._aim_at_gate
    _here = OSRSCowFighter._here
    _take_bones_from_menu = OSRSCowFighter._take_bones_from_menu
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
        self.bones_taken = 0
        self.messages = []
        self.hover_words = []
        self.home = (3256, 3272, 0)
        self.walked_home = 0
        self.dropped = []
        self.slept = 0

    def is_in_game_view(self, point):
        return True

    def visible_objects(self):
        return self.bridge.objects

    def move_to_scene_object(self, obj):
        self.mouse.moves.append(obj)

    def drop_items(self, slots, verbose=True, rects=None):
        self.dropped.extend(slots)
        for slot in slots:
            self.bridge.inventory[slot] = -1

    def walk_home(self):
        self.walked_home += 1

    def sleep(self, lo=None, hi=None):
        self.slept += 1

    def wait_for_hover_text(self, contains, timeout=1.5):
        self.hover_words.append(contains)
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

    def test_a_kill_that_is_not_a_cow_is_not_counted(self):
        bridge = FakeBridge(targets=[Target("Man", 0, 30, (10, 10, 0)), None])
        bot = FakeFighter(bridge)
        bot.wait_for_kill(timeout=1)
        self.assertEqual(bot.kills, 0)
        self.assertIsNone(bot.death_tile)

    def test_a_fight_that_ends_without_a_kill_counts_nothing(self):
        bridge = FakeBridge(targets=[Target("Cow", 20, 30, (10, 10, 0)), None])
        bot = FakeFighter(bridge)
        bot.wait_for_kill(timeout=1)
        self.assertEqual(bot.kills, 0)


class LootTest(unittest.TestCase):
    def bones(self, point=(300, 200)):
        return GroundItem(rules.BONES, "Bones", 1, (10, 10, 0), point)

    def test_takes_bones_near_the_kill_and_counts_them(self):
        bridge = FakeBridge(ground_items=[self.bones()])

        def picked_up():
            bridge.ground_items = []
            bridge.inventory = [rules.BONES] + [-1] * 27

        bot = FakeFighter(bridge, on_click=picked_up)
        bot.death_tile = (10, 10, 0)
        bot.loot()
        self.assertEqual(bot.bones_taken, 1)
        self.assertIsNone(bot.death_tile)
        self.assertEqual(bot.hover_words, ["Take"])

    def test_leaves_cowhides_and_coins_on_the_ground(self):
        items = [
            GroundItem(1739, "Cowhide", 1, (10, 10, 0), (300, 200)),
            GroundItem(995, "Coins", 25, (10, 10, 0), (300, 200)),
        ]
        bot = FakeFighter(FakeBridge(ground_items=items))
        bot.death_tile = (10, 10, 0)
        bot.loot()
        self.assertEqual(bot.mouse.moves, [])

    def test_aims_again_where_the_item_now_is_before_giving_up(self):
        bridge = FakeBridge(ground_items=[self.bones()])
        bot = FakeFighter(bridge, says_take=False)
        answers = iter([False, True])
        bot.wait_for_hover_text = lambda contains, timeout=1.5: next(answers)

        def moved_on_screen():
            bridge.ground_items = []
            bridge.inventory = [rules.BONES] + [-1] * 27

        bot.mouse.on_click = moved_on_screen
        bridge.ground_items = [self.bones(point=(310, 210))]
        bot.death_tile = (10, 10, 0)
        bot.loot()
        self.assertEqual(bot.mouse.moves, [(310, 210), (310, 210)])
        self.assertEqual(bot.bones_taken, 1)

    def test_does_not_click_when_the_cursor_does_not_read_take(self):
        bot = FakeFighter(FakeBridge(ground_items=[self.bones()]), says_take=False)
        bot.death_tile = (10, 10, 0)
        bot.loot()
        self.assertEqual(bot.mouse.clicks, 0)
        self.assertEqual(bot.bones_taken, 0)


def hover(text):
    option, _, target = text.partition(" ")
    return Menu(False, MenuEntry(option, target, None), [])


def row(option, target, top):
    return MenuEntry(option, target, Rectangle(300, top, 120, 15))


class PileTest(unittest.TestCase):
    """Cows drop bones, cowhide and beef on one tile; a left-click takes the top one."""

    def bones(self):
        return GroundItem(rules.BONES, "Bones", 1, (10, 10, 0), (300, 200))

    def fighter(self, bridge):
        def picked_up():
            bridge.ground_items = []
            bridge.inventory = [rules.BONES] + [-1] * 27

        bot = FakeFighter(bridge, on_click=picked_up)
        bot.death_tile = (10, 10, 0)
        return bot

    def test_left_clicks_when_bones_are_on_top(self):
        bridge = FakeBridge(ground_items=[self.bones()])
        bridge.menu = hover("Take Bones")
        bot = self.fighter(bridge)
        bot.loot()
        self.assertEqual((bot.mouse.clicks, bot.mouse.right_clicks), (1, 0))
        self.assertEqual(bot.bones_taken, 1)

    def test_picks_bones_from_the_menu_when_a_cowhide_is_on_top(self):
        bridge = FakeBridge(ground_items=[self.bones()])
        bridge.menu = hover("Take Cowhide")
        bot = self.fighter(bridge)
        bones_row = row("Take", "Bones", 129)

        def menu_opened():
            bridge.menu = Menu(
                True,
                MenuEntry("Take", "Cowhide", None),
                [row("Take", "Cowhide", 114), bones_row, row("Cancel", "", 144)],
            )

        bot.mouse.on_right_click = menu_opened
        bot.loot()
        self.assertEqual(bot.mouse.right_clicks, 1)
        self.assertEqual(bot.mouse.clicks, 1)
        clicked = bot.mouse.moves[-1]
        self.assertTrue(129 <= clicked.y < 144)
        self.assertEqual(bot.bones_taken, 1)

    def test_cancels_the_menu_when_it_holds_no_bones(self):
        bridge = FakeBridge(ground_items=[self.bones()])
        bridge.menu = hover("Take Cowhide")
        bot = FakeFighter(bridge)
        bot.death_tile = (10, 10, 0)

        def menu_opened():
            bridge.menu = Menu(
                True,
                MenuEntry("Take", "Cowhide", None),
                [row("Take", "Cowhide", 114), row("Cancel", "", 129)],
            )

        bot.mouse.on_right_click = menu_opened
        bot.loot()
        self.assertEqual(bot.mouse.clicks, 1)
        self.assertTrue(129 <= bot.mouse.moves[-1].y < 144)
        self.assertEqual(bot.bones_taken, 0)


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
        self.assertEqual(bot.hover_words, ["Attack"])

    def test_waits_for_a_free_cow_instead_of_wandering(self):
        bot = FakeFighter(FakeBridge(npcs=[self.cow(1, (5, 5), busy=True)]))
        self.assertIs(bot.attack(), False)
        self.assertFalse(hasattr(bot, "walked"))
        self.assertEqual(bot.walked_home, 0)
        self.assertEqual(bot.mouse.clicks, 0)

    def test_walks_home_when_it_has_drifted_away(self):
        bridge = FakeBridge()
        bridge.world_point = (3240, 3250, 0)
        bot = FakeFighter(bridge)
        self.assertIs(bot.attack(), False)
        self.assertEqual(bot.walked_home, 1)

    def test_ignores_a_cow_outside_the_game_view(self):
        bot = FakeFighter(FakeBridge(npcs=[self.cow(2, (9, 9))]))
        bot.is_in_game_view = lambda point: False
        self.assertIs(bot.attack(), False)
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

    def test_clicks_the_slots_the_bridge_reports(self):
        bridge = FakeBridge(inventory=[-1, 526] + [-1] * 26)
        bridge.inventory_slots = [
            SimpleNamespace(random_point=lambda i=i: ("bridge", i)) for i in range(28)
        ]

        def buried():
            bridge.inventory[1] = -1

        bot = FakeFighter(bridge, on_click=buried)
        bot.bury()
        self.assertEqual(bot.mouse.moves, [("bridge", 1)])


class BuryWhenFullTest(unittest.TestCase):
    def test_keeps_bones_while_there_is_room(self):
        bot = FakeFighter(FakeBridge(inventory=[526, 526] + [-1] * 26))
        bot.bury_when_full()
        self.assertEqual(bot.mouse.clicks, 0)

    def test_buries_every_bone_once_the_inventory_is_full(self):
        bridge = FakeBridge(inventory=[1351] + [526] * 27)

        def buried():
            bridge.inventory[bridge.inventory.index(526)] = -1

        bot = FakeFighter(bridge, on_click=buried)
        bot.bury_when_full()
        self.assertEqual(bot.bones_buried, 27)

    def test_drops_every_cowhide_once_the_inventory_is_full(self):
        cowhide = rules.COWHIDE
        bot = FakeFighter(
            FakeBridge(inventory=[1351, cowhide, 526, cowhide] + [995] * 24)
        )
        bot.bury_when_full()
        self.assertEqual(bot.dropped, [1, 3])

    def test_keeps_cowhides_while_there_is_room(self):
        bot = FakeFighter(FakeBridge(inventory=[rules.COWHIDE] + [-1] * 27))
        bot.bury_when_full()
        self.assertEqual(bot.dropped, [])


class StartTest(unittest.TestCase):
    def test_an_empty_inventory_does_not_block_the_start(self):
        bot = FakeFighter(FakeBridge(inventory=None))
        self.assertTrue(bot.bridge_is_heard())

    def test_a_silent_bridge_blocks_the_start(self):
        bridge = FakeBridge()
        bridge.game_state = ""
        self.assertFalse(FakeFighter(bridge).bridge_is_heard())


class GateTest(unittest.TestCase):
    def gate(self, distance):
        return SimpleNamespace(id=1558, distance=distance)

    def test_opens_a_closed_gate_next_to_us(self):
        bridge = FakeBridge()
        bridge.objects = [self.gate(1)]

        def opened():
            bridge.objects = []

        bot = FakeFighter(bridge, on_click=opened)
        bot.wait_for_hover_text = lambda contains, timeout=1.5: contains == "Open"
        self.assertIs(bot.open_gate(), True)
        self.assertEqual(bridge.requested, None)
        self.assertEqual(bot.mouse.clicks, 1)

    def test_tries_another_point_on_the_gate_before_giving_up(self):
        bridge = FakeBridge()
        bridge.objects = [self.gate(1)]

        def opened():
            bridge.objects = []

        bot = FakeFighter(bridge, on_click=opened)
        answers = iter([False, True])
        bot.wait_for_hover_text = lambda contains, timeout=1.5: next(answers)
        self.assertIs(bot.open_gate(), True)
        self.assertEqual(len(bot.mouse.moves), 2)
        self.assertEqual(bot.mouse.clicks, 1)

    def test_leaves_a_gate_that_does_not_read_open(self):
        bridge = FakeBridge()
        bridge.objects = [self.gate(1)]
        bot = FakeFighter(bridge)
        bot.wait_for_hover_text = lambda contains, timeout=1.5: False
        self.assertIs(bot.open_gate(), False)
        self.assertEqual(bot.mouse.clicks, 0)

    def test_no_gate_in_reach_means_nothing_to_open(self):
        bridge = FakeBridge()
        bridge.objects = [self.gate(rules.GATE_REACH + 1)]
        bot = FakeFighter(bridge)
        self.assertIs(bot.open_gate(), False)
        self.assertEqual(bot.mouse.clicks, 0)


class RulesTest(unittest.TestCase):
    def test_home_is_left_beyond_the_leash(self):
        home = (3256, 3272, 0)
        self.assertFalse(rules.far_from((3256 + rules.LEASH, 3272, 0), home))
        self.assertTrue(rules.far_from((3256 + rules.LEASH + 1, 3272, 0), home))
        self.assertTrue(rules.far_from((3256, 3272, 1), home))
        self.assertFalse(rules.far_from(None, home))

    def test_the_field_gate_ids_are_the_closed_halves(self):
        self.assertEqual(rules.GATE_CLOSED, frozenset({1558, 1560}))


if __name__ == "__main__":
    unittest.main()
