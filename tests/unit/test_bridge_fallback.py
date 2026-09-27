"""The bridge-versus-OCR decision, tested without a client or a window.

`RuneLiteBot` is abstract and drags in the whole window stack, so these tests borrow
the real `_from_bridge` onto a minimal host. The function under test is the shipped
one, not a copy of it.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import model.runelite_bot as runelite_bot  # noqa: E402
from model.runelite_bot import RuneLiteBot  # noqa: E402


class FakeBridge:
    def __init__(self, fresh: bool):
        self._fresh = fresh
        self.fallbacks = 0

    def is_fresh(self) -> bool:
        return self._fresh

    def note_fallback(self) -> None:
        self.fallbacks += 1


class FakeBot:
    """The smallest host `_from_bridge` needs: a bridge and a log."""

    _from_bridge = RuneLiteBot._from_bridge

    def __init__(self, bridge):
        self.bridge = bridge
        self.messages = []

    def log_msg(self, message: str) -> None:
        self.messages.append(message)


class BridgeFallbackTest(unittest.TestCase):
    def test_uses_the_bridge_when_fresh(self):
        bot = FakeBot(FakeBridge(fresh=True))
        self.assertEqual(bot._from_bridge(lambda: 42, lambda: 42, "hp", -1), 42)

    def test_falls_back_to_ocr_when_stale(self):
        bridge = FakeBridge(fresh=False)
        bot = FakeBot(bridge)
        self.assertEqual(bot._from_bridge(lambda: 42, lambda: 41, "hp", -1), 41)
        self.assertEqual(bridge.fallbacks, 1)

    def test_falls_back_to_ocr_when_no_bridge_attached(self):
        bot = FakeBot(None)
        self.assertEqual(bot._from_bridge(lambda: 42, lambda: 41, "hp", -1), 41)

    @mock.patch.object(runelite_bot, "COMPARE_BRIDGE_WITH_OCR", True)
    def test_warns_when_the_two_disagree(self):
        bot = FakeBot(FakeBridge(fresh=True))
        bot._from_bridge(lambda: 42, lambda: 41, "hp", -1)
        self.assertTrue(
            any("hp" in message for message in bot.messages),
            f"expected a disagreement warning, got {bot.messages!r}",
        )

    @mock.patch.object(runelite_bot, "COMPARE_BRIDGE_WITH_OCR", True)
    def test_does_not_warn_when_ocr_simply_failed(self):
        # A failed OCR read is the sentinel, not a disagreement worth reporting.
        bot = FakeBot(FakeBridge(fresh=True))
        bot._from_bridge(lambda: 42, lambda: -1, "hp", -1)
        self.assertEqual(bot.messages, [])

    @mock.patch.object(runelite_bot, "COMPARE_BRIDGE_WITH_OCR", True)
    def test_does_not_warn_when_the_two_agree(self):
        bot = FakeBot(FakeBridge(fresh=True))
        bot._from_bridge(lambda: 42, lambda: 42, "hp", -1)
        self.assertEqual(bot.messages, [])

    @mock.patch.object(runelite_bot, "COMPARE_BRIDGE_WITH_OCR", True)
    def test_survives_an_ocr_comparison_that_raises(self):
        bot = FakeBot(FakeBridge(fresh=True))

        def explode():
            raise RuntimeError("no window")

        # The comparison is diagnostics; it must never break the read it audits.
        self.assertEqual(bot._from_bridge(lambda: 42, explode, "hp", -1), 42)

    @mock.patch.object(runelite_bot, "COMPARE_BRIDGE_WITH_OCR", False)
    def test_skips_the_screen_entirely_once_comparison_is_off(self):
        # With the comparison off, a fresh bridge read must not pay for an OCR read.
        bot = FakeBot(FakeBridge(fresh=True))

        def must_not_run():
            raise AssertionError("OCR read while the bridge was fresh")

        self.assertEqual(bot._from_bridge(lambda: 42, must_not_run, "hp", -1), 42)
        self.assertEqual(bot.messages, [])

    def test_propagates_an_ocr_failure_when_the_bridge_is_absent(self):
        # With no bridge there is nothing to fall back from, so an OCR exception is
        # the caller's problem, exactly as it was before the bridge existed.
        bot = FakeBot(None)

        def explode():
            raise RuntimeError("no window")

        with self.assertRaises(RuntimeError):
            bot._from_bridge(lambda: 42, explode, "hp", -1)


if __name__ == "__main__":
    unittest.main()
