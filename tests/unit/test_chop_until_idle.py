"""Waiting out a chop on the plug-in's idle flag, tested without a client.

The borrowed method is the shipped `OSRSPowerChopper.chop_until_idle`, run on a minimal
host with a scripted bridge, so no window, mouse or screen is involved.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import model.osrs.power_chopper as power_chopper  # noqa: E402
from model.osrs.power_chopper import OSRSPowerChopper  # noqa: E402


class ScriptedBridge:
    """Answers `idle_for` from a script, repeating the last answer once it runs out."""

    def __init__(self, *answers):
        self.answers = list(answers)

    @property
    def idle_for(self):
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


class FakeChopper:
    chop_until_idle = OSRSPowerChopper.chop_until_idle
    game_tick = 0.003

    def __init__(self, bridge):
        self.bridge = bridge
        self.messages = []
        self.cursor_moves = 0

    def log_msg(self, message: str) -> None:
        self.messages.append(message)

    def potentially_mouse_to_second_closest_tree(self, probability: float) -> None:
        self.cursor_moves += 1

    def sleep(self, lo: float = 0.1, hi: float = 0.3) -> None:
        pass


@mock.patch.object(power_chopper, "START_TIMEOUT", 0.05)
class ChopUntilIdleTest(unittest.TestCase):
    def test_defers_to_the_screen_without_a_bridge(self):
        self.assertIsNone(FakeChopper(None).chop_until_idle())

    def test_defers_to_the_screen_when_the_plugin_predates_idle(self):
        self.assertIsNone(FakeChopper(ScriptedBridge(None)).chop_until_idle())

    def test_reports_a_click_that_never_set_us_moving(self):
        bot = FakeChopper(ScriptedBridge(5.0))
        self.assertIs(bot.chop_until_idle(), False)

    def test_returns_once_idle_long_enough_after_chopping(self):
        # Idle from before the click, then busy, a one-tick gap between swings that
        # must not end the chop, busy again, and finally idle for good.
        bridge = ScriptedBridge(0.4, 0.0, 0.0, 0.6, 0.0, 0.0, 2.0)
        bot = FakeChopper(bridge)
        self.assertIs(bot.chop_until_idle(), True)
        self.assertEqual(bridge.answers, [2.0])
        self.assertIn("Idle", bot.messages[-1])

    def test_gives_control_back_when_the_feed_is_lost_mid_chop(self):
        bot = FakeChopper(ScriptedBridge(0.0, 0.0, None))
        self.assertIs(bot.chop_until_idle(), True)

    def test_times_out_a_chop_that_never_stops(self):
        bot = FakeChopper(ScriptedBridge(0.0))
        self.assertIs(bot.chop_until_idle(timeout=0.05), True)
        self.assertIn("timeout", bot.messages[-1])


if __name__ == "__main__":
    unittest.main()
