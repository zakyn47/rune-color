"""Polygon: the clickbox outline the bridge sends for a scene object."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from utilities.geometry import Point, Polygon  # noqa: E402

SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]
TRIANGLE = [(0, 0), (40, 0), (0, 40)]


class PolygonTest(unittest.TestCase):
    def test_needs_three_points(self):
        with self.assertRaises(ValueError):
            Polygon([(0, 0), (1, 1)])

    def test_contains_inside_points_only(self):
        square = Polygon(SQUARE)
        self.assertTrue(square.contains(Point(5, 5)))
        self.assertFalse(square.contains(Point(15, 5)))
        self.assertFalse(Polygon(TRIANGLE).contains(Point(35, 35)))

    def test_center_is_the_vertex_mean(self):
        self.assertEqual(Polygon(SQUARE).center, Point(5, 5))

    def test_random_points_stay_inside(self):
        triangle = Polygon(TRIANGLE)
        for _ in range(300):
            self.assertTrue(triangle.contains(triangle.random_point()))

    def test_bounds_cover_every_point(self):
        bounds = Polygon(TRIANGLE).bounds
        self.assertEqual((bounds.left, bounds.top), (0, 0))
        self.assertEqual((bounds.width, bounds.height), (41, 41))


if __name__ == "__main__":
    unittest.main()
