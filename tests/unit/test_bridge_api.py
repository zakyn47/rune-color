"""Unit tests for the RuneColor Bridge receiver.

Run with:
    python -m unittest discover -s tests/unit -t . -v
"""

import json
import logging
import sys
import time
import unittest
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from utilities.api.bridge_api import BridgeAPI  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "snapshot_v1.json"


def payload() -> dict:
    """Return the shared wire-format fixture the Java suite also pins."""
    return json.loads(FIXTURE.read_text())


class BridgeAPITest(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = BridgeAPI(port=0, start=False)
        self.client = self.bridge.app.test_client()

    def post(self, body: dict):
        return self.client.post("/api/snapshot/", json=body)

    def test_reports_no_data_before_any_snapshot(self):
        self.assertFalse(self.bridge.is_fresh())
        self.assertEqual(self.bridge.hitpoints, (-1, -1))
        self.assertEqual(self.bridge.prayer, (-1, -1))
        self.assertEqual(self.bridge.run_energy, -1)
        self.assertEqual(self.bridge.world_point, (-1, -1, -1))
        self.assertEqual(self.bridge.game_state, "")
        self.assertEqual(self.bridge.tick, -1)

    def test_exposes_a_received_snapshot(self):
        self.assertEqual(self.post(payload()).status_code, 200)
        self.assertTrue(self.bridge.is_fresh())
        self.assertEqual(self.bridge.hitpoints, (42, 55))
        self.assertEqual(self.bridge.prayer, (12, 43))
        self.assertEqual(self.bridge.run_energy, 87)
        self.assertEqual(self.bridge.world_point, (3222, 3218, 0))
        self.assertEqual(self.bridge.game_state, "LOGGED_IN")
        self.assertEqual(self.bridge.tick, 123456)

    def test_goes_stale_after_max_age(self):
        self.bridge.max_age = 0.05
        self.post(payload())
        self.assertTrue(self.bridge.is_fresh())
        time.sleep(0.1)
        self.assertFalse(self.bridge.is_fresh())
        # Stale means every field falls back together, never a mixed picture.
        self.assertEqual(self.bridge.hitpoints, (-1, -1))
        self.assertEqual(self.bridge.world_point, (-1, -1, -1))
        self.assertEqual(self.bridge.run_energy, -1)

    def test_rejects_a_mismatched_schema_and_stays_disabled(self):
        body = payload()
        body["schema"] = 2
        self.assertEqual(self.post(body).status_code, 409)
        self.assertFalse(self.bridge.is_fresh())
        # A stale jar disables the bridge for the session rather than letting a
        # later good payload paper over the mismatch.
        self.assertEqual(self.post(payload()).status_code, 409)
        self.assertFalse(self.bridge.is_fresh())

    def test_ignores_a_malformed_payload(self):
        response = self.client.post(
            "/api/snapshot/", data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.bridge.is_fresh())

    def test_serves_partial_fields_when_logged_out(self):
        self.post(
            {
                "schema": 1,
                "tick": 7,
                "sent_at": 99,
                "game_state": "LOGIN_SCREEN",
                "hitpoints": None,
                "prayer": None,
                "run_energy": None,
                "world_point": None,
            }
        )
        self.assertTrue(self.bridge.is_fresh())
        self.assertEqual(self.bridge.game_state, "LOGIN_SCREEN")
        self.assertEqual(self.bridge.hitpoints, (-1, -1))
        self.assertEqual(self.bridge.world_point, (-1, -1, -1))
        self.assertEqual(self.bridge.run_energy, -1)

    def test_counts_fallbacks(self):
        self.assertEqual(self.bridge.fallback_count, 0)
        self.bridge.note_fallback()
        self.bridge.note_fallback()
        self.assertEqual(self.bridge.fallback_count, 2)

    def test_rejects_a_get(self):
        self.assertEqual(self.client.get("/api/snapshot/").status_code, 405)

    def test_logs_the_schema_mismatch_once(self):
        body = payload()
        body["schema"] = 99
        with self.assertLogs(level=logging.ERROR) as captured:
            self.post(body)
        self.assertTrue(any("schema" in line.lower() for line in captured.output))


class BridgeAPIServerTest(unittest.TestCase):
    """Proves the real server binds and answers, which the test client cannot."""

    def test_binds_a_port_and_receives_over_the_wire(self):
        bridge = BridgeAPI(port=8123)
        try:
            response = requests.post(
                "http://127.0.0.1:8123/api/snapshot/", json=payload(), timeout=5
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(bridge.hitpoints, (42, 55))
        finally:
            bridge.stop()

    def test_raises_when_the_port_is_taken(self):
        first = BridgeAPI(port=8124)
        try:
            with self.assertRaises(OSError):
                BridgeAPI(port=8124)
        finally:
            first.stop()

    def test_stop_is_idempotent(self):
        bridge = BridgeAPI(port=8125)
        bridge.stop()
        bridge.stop()


if __name__ == "__main__":
    unittest.main()
