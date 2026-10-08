"""The bot helpers that act on the bridge's scene targets, tested without a client."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.runelite_bot import RuneLiteBot  # noqa: E402
from utilities.api.bridge_api import Menu, MenuEntry  # noqa: E402


class FakeBridge:
    def __init__(self, menus):
        self._menus = list(menus)

    @property
    def menu(self):
        return self._menus.pop(0) if len(self._menus) > 1 else self._menus[0]


def hover(target):
    return Menu(False, MenuEntry("Mine", target, None), [])


class FakeBot:
    wait_for_hover_text = RuneLiteBot.wait_for_hover_text
    game_tick = 0.003

    def __init__(self, menus):
        self.bridge = FakeBridge(menus)


class WaitForHoverTextTest(unittest.TestCase):
    def test_waits_for_the_snapshot_to_catch_up_with_the_mouse(self):
        bot = FakeBot([None, hover("Rocks"), hover("Tin rocks")])
        self.assertTrue(bot.wait_for_hover_text("Tin", timeout=0.2))

    def test_gives_up_on_the_wrong_object(self):
        bot = FakeBot([hover("Iron rocks")])
        self.assertFalse(bot.wait_for_hover_text("Tin", timeout=0.05))


if __name__ == "__main__":
    unittest.main()
