import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from utilities.api.pathfinder import Pathfinder  # noqa: E402
from utilities.geometry import Point  # noqa: E402


class TestDaxMembership(unittest.TestCase):
    def sent_members(self, **kwargs) -> bool:
        with mock.patch.object(
            Pathfinder, "make_api_call", return_value={"path": []}
        ) as call:
            Pathfinder.get_path_dax(Point(1, 2), Point(3, 4), **kwargs)
        return call.call_args.args[2]["player"]["members"]

    def test_defaults_to_free_to_play(self):
        self.assertFalse(self.sent_members())

    def test_members_can_be_requested(self):
        self.assertTrue(self.sent_members(members=True))


if __name__ == "__main__":
    unittest.main()
