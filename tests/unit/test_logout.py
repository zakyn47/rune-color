"""Logging out, checked against the game state the bridge reports."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.runelite_bot import RuneLiteBot  # noqa: E402


class FakeMouse:
    def __init__(self, on_click):
        self.on_click = on_click
        self.clicks = 0

    def move_to(self, point, **kwargs):
        pass

    def move_rel(self, **kwargs):
        pass

    def click(self):
        self.clicks += 1
        self.on_click(self.clicks)


class FakeBot:
    logout = RuneLiteBot.logout
    _logged_out = RuneLiteBot._logged_out
    game_tick = 0.003
    LOGOUT_RETRY_SECONDS = 0.01
    LOGOUT_TIMEOUT = 1

    def __init__(self, bridge, on_click):
        self.bridge = bridge
        self.mouse = FakeMouse(on_click)
        tab = SimpleNamespace(random_point=lambda: None)
        self.win = SimpleNamespace(cp_tabs=[tab] * 14)
        self.messages = []

    def sleep(self, lo=None, hi=None):
        pass

    def log_msg(self, msg, overwrite=False):
        self.messages.append(msg)


class LogoutTest(unittest.TestCase):
    def test_tries_again_until_the_game_lets_us_out(self):
        # Clicks: tab, button (refused, still in combat), button again (accepted).
        bridge = SimpleNamespace(game_state="LOGGED_IN")

        def clicked(n):
            if n == 3:
                bridge.game_state = "LOGIN_SCREEN"

        bot = FakeBot(bridge, clicked)
        bot.logout()
        self.assertEqual(bot.mouse.clicks, 3)
        self.assertEqual(bot.messages[-1], "Logged out.")

    def test_reports_a_logout_that_never_happened(self):
        bot = FakeBot(SimpleNamespace(game_state="LOGGED_IN"), lambda n: None)
        bot.logout()
        self.assertIn("Could not log out", bot.messages[-1])

    def test_without_a_bridge_clicks_once_and_trusts_it(self):
        bot = FakeBot(None, lambda n: None)
        bot.logout()
        self.assertEqual(bot.mouse.clicks, 2)
        self.assertEqual(bot.messages[-1], "Logged out.")


if __name__ == "__main__":
    unittest.main()
