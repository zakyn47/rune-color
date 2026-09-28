"""Checks every committed RuneLite profile against the rules loading depends on."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from model.osrs.power_chopper import OSRSPowerChopper  # noqa: E402
from utilities import runelite_profiles  # noqa: E402

GEOMETRY_KEYS = ("runelite.clientBounds=", "runelite.clientMaximized=")


def profile_files():
    return sorted(runelite_profiles.PROFILES_DIR.glob("*.properties"))


class RuneLiteProfilesTest(unittest.TestCase):
    def test_the_power_chopper_has_a_profile(self):
        path = runelite_profiles.profile_path(OSRSPowerChopper.runelite_profile)
        self.assertTrue(path.is_file(), path)

    def test_the_cow_profile_tags_cows_and_shows_their_loot(self):
        path = runelite_profiles.profile_path("cow_fighter")
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertIn("npcindicators.npcToHighlight=Cow", lines)
        self.assertIn("npcindicators.highlightColor=-16711681", lines)
        hidden = next(line for line in lines if line.startswith("grounditems.hidden"))
        self.assertNotIn("Coins", hidden)
        self.assertNotIn("Bones", hidden)

    def test_names_profiles_after_the_script(self):
        self.assertEqual(
            runelite_profiles.profile_name("Power Chopper & Firemaking"),
            "RuneColor - Power Chopper & Firemaking",
        )

    def test_no_profile_resizes_the_client(self):
        for path in profile_files():
            lines = path.read_text(encoding="utf-8").splitlines()
            for key in GEOMETRY_KEYS:
                self.assertFalse(
                    any(line.startswith(key) for line in lines), f"{path.name}: {key}"
                )

    def test_every_profile_keeps_the_bridge_enabled(self):
        # Switching profiles also switches plug-ins, so a profile without the bridge
        # would turn off the very plug-in that asked for the switch.
        for path in profile_files():
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertIn("runelite.runecolorbridgeplugin=true", lines, path.name)


if __name__ == "__main__":
    unittest.main()
