"""The rules for which RuneLite profile a selected script asks for."""

import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from controller.profile_selector import ProfileSelector  # noqa: E402
from utilities import runelite_profiles  # noqa: E402


class FakeBridge:
    def __init__(self, active=None):
        self.wanted = "unset"
        self.active_profile = active

    def request_profile(self, name, path):
        self.wanted = (name, path)

    def clear_profile(self):
        self.wanted = None


def script(profile="power_chopper", title="Chopper"):
    return SimpleNamespace(runelite_profile=profile, bot_title=title)


class ProfileSelectorTest(unittest.TestCase):
    def setUp(self):
        self.settings = {}
        self.logged = []
        self.bridge = FakeBridge()

    def selector(self, timeout=0.05):
        return ProfileSelector(
            self.bridge,
            self.settings.get,
            self.settings.__setitem__,
            self.logged.append,
            confirm_timeout=timeout,
            poll=0.005,
        )

    def test_requests_the_scripts_profile(self):
        self.selector().select(script())
        name, path = self.bridge.wanted
        self.assertEqual(name, "RuneColor - Chopper")
        self.assertEqual(path, str(runelite_profiles.profile_path("power_chopper")))

    def test_clears_the_request_for_a_script_without_a_profile(self):
        self.selector().select(script(profile=None))
        self.assertIsNone(self.bridge.wanted)

    def test_clears_the_request_when_nothing_is_selected(self):
        self.selector().select(None)
        self.assertIsNone(self.bridge.wanted)

    def test_opting_out_clears_the_request_and_is_remembered(self):
        selector = self.selector()
        selector.select(script())
        selector.set_use_own(True)
        self.assertIsNone(self.bridge.wanted)
        self.assertIs(self.settings[runelite_profiles.USE_OWN_PROFILE_SETTING], True)
        self.assertTrue(self.selector().use_own)

    def test_opting_back_in_requests_the_selected_scripts_profile(self):
        self.settings[runelite_profiles.USE_OWN_PROFILE_SETTING] = True
        selector = self.selector()
        selector.select(script())
        self.assertIsNone(self.bridge.wanted)
        selector.set_use_own(False)
        self.assertEqual(self.bridge.wanted[0], "RuneColor - Chopper")

    def test_logs_once_the_client_has_switched(self):
        self.bridge.active_profile = "RuneColor - Chopper"
        self.selector().select(script())
        self.wait_for_log()
        self.assertEqual(
            self.logged, ["Switched RuneLite to profile RuneColor - Chopper."]
        )

    def test_warns_when_the_client_never_switches(self):
        self.selector().select(script())
        self.wait_for_log()
        self.assertIn("didn't switch", self.logged[0])

    def wait_for_log(self):
        deadline = time.time() + 2
        while not self.logged and time.time() < deadline:
            time.sleep(0.005)


if __name__ == "__main__":
    unittest.main()
