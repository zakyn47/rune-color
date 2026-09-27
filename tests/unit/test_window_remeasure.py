"""Re-measuring the client window after it moves, tested without a real window.

Every region the bot reads or clicks is stored in absolute screen coordinates, measured
once when the bot starts. Moving or resizing the client afterwards leaves all of them
pointing at the wrong pixels, which a live run showed as nearly every OCR read failing
from the moment the window was resized. These tests pin the re-measure that fixes it.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.bot import Bot  # noqa: E402
from model.window import Window, WindowInitializationError  # noqa: E402
from utilities.geometry import Rectangle  # noqa: E402


class FakeWindow(Window):
    """A `Window` whose rectangle is set by the test and whose measuring is counted."""

    def __init__(self, rect: Rectangle, measures: bool = True):
        super().__init__("RuneLite - test", padding_top=0, padding_left=0)
        self.rect = rect
        self.measures = measures
        self.initialize_calls = 0

    def rectangle(self) -> Rectangle:
        return self.rect

    def initialize(self) -> bool:
        self.initialize_calls += 1
        if self.measures:
            self.mark_measured()
        return self.measures


class FakeBot:
    """The smallest host `remeasure_if_moved` needs: a window and a log."""

    remeasure_if_moved = Bot.remeasure_if_moved

    def __init__(self, win: Window):
        self.win = win
        self.messages = []

    def log_msg(self, message: str) -> None:
        self.messages.append(message)


class WindowMovedTest(unittest.TestCase):
    def test_unmeasured_window_counts_as_moved(self):
        self.assertTrue(FakeWindow(Rectangle(0, 0, 800, 600)).moved())

    def test_same_rectangle_is_not_moved(self):
        win = FakeWindow(Rectangle(0, 0, 800, 600))
        win.initialize()
        win.rect = Rectangle(0, 0, 800, 600)  # A new object with the same geometry.
        self.assertFalse(win.moved())

    def test_dragged_window_is_moved(self):
        win = FakeWindow(Rectangle(0, 0, 800, 600))
        win.initialize()
        win.rect = Rectangle(7, 0, 800, 600)
        self.assertTrue(win.moved())

    def test_resized_window_is_moved(self):
        win = FakeWindow(Rectangle(0, 0, 800, 600))
        win.initialize()
        win.rect = Rectangle(0, 0, 835, 564)
        self.assertTrue(win.moved())


class RemeasureIfMovedTest(unittest.TestCase):
    def test_does_nothing_while_the_window_stays_put(self):
        win = FakeWindow(Rectangle(0, 0, 800, 600))
        win.initialize()
        bot = FakeBot(win)
        self.assertTrue(bot.remeasure_if_moved())
        self.assertEqual(win.initialize_calls, 1)
        self.assertEqual(bot.messages, [])

    def test_remeasures_once_after_a_move(self):
        win = FakeWindow(Rectangle(0, 0, 800, 600))
        win.initialize()
        bot = FakeBot(win)
        win.rect = Rectangle(7, 0, 835, 564)
        self.assertTrue(bot.remeasure_if_moved())
        self.assertTrue(bot.remeasure_if_moved())
        self.assertEqual(win.initialize_calls, 2)
        self.assertEqual(len(bot.messages), 1)

    def test_keeps_retrying_while_measuring_fails(self):
        # Mid-drag, or with something covering the client, the templates will not
        # match. The next check has to try again instead of trusting stale regions.
        win = FakeWindow(Rectangle(0, 0, 800, 600))
        win.initialize()
        bot = FakeBot(win)
        win.rect = Rectangle(7, 0, 835, 564)
        win.measures = False
        self.assertFalse(bot.remeasure_if_moved())
        self.assertFalse(bot.remeasure_if_moved())
        self.assertEqual(win.initialize_calls, 3)
        win.measures = True
        self.assertTrue(bot.remeasure_if_moved())
        self.assertTrue(bot.remeasure_if_moved())
        self.assertEqual(win.initialize_calls, 4)

    def test_a_measuring_error_is_reported_not_raised(self):
        win = FakeWindow(Rectangle(0, 0, 800, 600))
        win.initialize()
        bot = FakeBot(win)
        win.rect = Rectangle(7, 0, 835, 564)

        def explode() -> bool:
            raise RuntimeError("template search failed")

        win.initialize = explode
        self.assertFalse(bot.remeasure_if_moved())
        self.assertIn("template search failed", bot.messages[-1])

    def test_a_closed_client_is_reported_not_raised(self):
        win = FakeWindow(Rectangle(0, 0, 800, 600))
        win.initialize()
        bot = FakeBot(win)

        def gone() -> Rectangle:
            raise WindowInitializationError("No client window found")

        win.rectangle = gone
        self.assertFalse(bot.remeasure_if_moved())
        self.assertIn("No client window found", bot.messages[-1])


if __name__ == "__main__":
    unittest.main()
