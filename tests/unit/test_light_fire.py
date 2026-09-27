"""A light that outlasts its timeout, tested without a client.

The borrowed methods are the shipped `OSRSPowerChopper.light_fire` and
`wait_until_idle`, run on a minimal host with a scripted slot and bridge.
"""

import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.osrs.power_chopper import OSRSPowerChopper  # noqa: E402


class ScriptedBridge:
    def __init__(self, *answers, fires=(None,)):
        self.answers = list(answers)
        self.fires = list(fires)

    @property
    def fire(self):
        return self.fires.pop(0) if len(self.fires) > 1 else self.fires[0]

    @property
    def idle_for(self):
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


class FakeChopper:
    light_fire = OSRSPowerChopper.light_fire
    wait_until_idle = OSRSPowerChopper.wait_until_idle
    wait_for_fire = OSRSPowerChopper.wait_for_fire
    tend_campfire = OSRSPowerChopper.tend_campfire
    click_fire = OSRSPowerChopper.click_fire
    game_tick = 0.003
    tinderbox_slot = 1

    def __init__(self, bridge, empties_after: float):
        self.bridge = bridge
        self.empties_at = time.time() + empties_after
        self.mouse = SimpleNamespace(move_to=lambda _: None, click=lambda: None)
        slot = SimpleNamespace(random_point=lambda: None)
        self.win = SimpleNamespace(inventory_slots=[slot] * 28)

    def is_inv_slot_empty(self, _slot: int) -> bool:
        return time.time() >= self.empties_at

    def sleep(self, lo: float = 0.1, hi: float = 0.3) -> None:
        pass

    def count_logs(self) -> int:
        return 3

    def find_fire(self):
        return None

    def get_mouseover_text(self, contains=None):
        return False


class LightFireTest(unittest.TestCase):
    def test_a_light_still_going_at_the_timeout_counts_once_it_lands(self):
        bot = FakeChopper(ScriptedBridge(0.0), 0.05)
        bot.bridge.answers = [0.0] * 200 + [1.0]
        self.assertIs(bot.light_fire(5, timeout=0.01), True)

    def test_a_light_that_never_lands_fails(self):
        bot = FakeChopper(ScriptedBridge(1.0), 60)
        self.assertIs(bot.light_fire(5, timeout=0.01), False)

    def test_without_a_bridge_the_timeout_is_final(self):
        bot = FakeChopper(None, 0.5)
        self.assertIs(bot.light_fire(5, timeout=0.01), False)


class WaitForFireTest(unittest.TestCase):
    def test_idle_before_the_fire_appears_is_not_enough(self):
        # Idle already, as between the log leaving its slot and the lighting
        # animation starting, then busy lighting, then idle beside the fire.
        fires = [None] * 5 + [(10, 20)]
        bridge = ScriptedBridge(1.0, 1.0, 1.0, 0.0, 0.0, 1.0, fires=fires)
        FakeChopper(bridge, 0).wait_for_fire()
        self.assertEqual(bridge.fires, [(10, 20)])

    def test_gives_up_on_a_fire_that_never_appears(self):
        bridge = ScriptedBridge(1.0)
        FakeChopper(bridge, 0).wait_for_fire(timeout=0.02)


class FireBurnsOutTest(unittest.TestCase):
    def test_tending_a_campfire_that_just_burnt_out_is_a_miss(self):
        bridge = ScriptedBridge(1.0, fires=[(10, 20), None])
        self.assertIs(FakeChopper(bridge, 0).tend_campfire(), False)

    def test_clicking_a_fire_that_just_burnt_out_is_a_miss(self):
        bridge = ScriptedBridge(1.0, fires=[(10, 20), None])
        self.assertIs(FakeChopper(bridge, 0).click_fire(), False)


if __name__ == "__main__":
    unittest.main()
