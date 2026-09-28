"""Getting a client to the front and into the game, tested without a client."""

import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import pywintypes

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.runelite_bot import RuneLiteBot  # noqa: E402
from model.window import Window  # noqa: E402


class FakeClient:
    def __init__(self, activates: bool, raises: bool = False):
        self.activates = activates
        self.raises = raises
        self.isActive = False
        self.calls = []

    def activate(self):
        self.calls.append("activate")
        if self.raises:
            raise pywintypes.error(0, "SetForegroundWindow", "No error message")
        self.isActive = self.activates

    def minimize(self):
        self.calls.append("minimize")

    def restore(self):
        self.calls.append("restore")
        self.isActive = True


class FakeWindow:
    focus = Window.focus

    def __init__(self, client):
        self.window = client


class FocusTest(unittest.TestCase):
    def test_activates_without_the_fallback_when_windows_allows_it(self):
        client = FakeClient(activates=True)
        FakeWindow(client).focus()
        self.assertEqual(client.calls, ["activate"])

    def test_restores_the_window_when_windows_blocks_the_activation(self):
        client = FakeClient(activates=False)
        FakeWindow(client).focus()
        self.assertEqual(client.calls, ["activate", "minimize", "restore"])

    def test_restores_the_window_when_the_activation_raises(self):
        client = FakeClient(activates=False, raises=True)
        FakeWindow(client).focus()
        self.assertEqual(client.calls, ["activate", "minimize", "restore"])


class FakeBot:
    enter_game = RuneLiteBot.enter_game

    def __init__(self, game_state, welcome_screen=False):
        self.bridge = (
            None if game_state is None else SimpleNamespace(game_state=game_state)
        )
        self.welcome_screen = welcome_screen
        self.logins = 0
        self.welcome_clicks = 0
        self.messages = []

    def login(self):
        self.logins += 1

    def click_through_welcome_screen(self):
        if not self.welcome_screen:
            return False
        self.welcome_clicks += 1
        return True

    def log_msg(self, msg, overwrite=False):
        self.messages.append(msg)


class EnterGameTest(unittest.TestCase):
    def setUp(self):
        self.sleep = time.sleep
        time.sleep = lambda _: None

    def tearDown(self):
        time.sleep = self.sleep

    def test_logs_in_from_the_login_screen(self):
        bot = FakeBot("LOGIN_SCREEN")
        self.assertIs(bot.enter_game(), True)
        self.assertEqual(bot.logins, 1)

    def test_does_not_log_in_when_already_in_game(self):
        bot = FakeBot("LOGGED_IN")
        self.assertIs(bot.enter_game(), False)
        self.assertEqual(bot.logins, 0)

    def test_clicks_through_the_welcome_screen_without_logging_in(self):
        bot = FakeBot("LOGGED_IN", welcome_screen=True)
        self.assertIs(bot.enter_game(), True)
        self.assertEqual((bot.welcome_clicks, bot.logins), (1, 0))

    def test_logs_in_when_the_bridge_cannot_tell(self):
        bot = FakeBot(None)
        self.assertIs(bot.enter_game(), True)
        self.assertEqual(bot.logins, 1)


if __name__ == "__main__":
    unittest.main()
