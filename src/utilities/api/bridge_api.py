"""Receive exact game state pushed by the RuneColor Bridge RuneLite plug-in.

The bot reads its own vitals off the screen: `get_hp` and `get_prayer` OCR the orb
text, and `get_world_point` OCRs the World Location overlay, which is unreliable
enough to need a retry wrapper. Every one of those values is an integer inside the
client, and the RuneColor Bridge plug-in pushes them here every game tick.

Note that this object listens for POST requests emitted by the plug-in at:
    http://127.0.0.1:8099/api/snapshot/
Port 8099 avoids 8081 (`events_api.py`) and 9420 (`gi_tracker.py`), so all three can
run at once.

Nothing here knows about OCR or about bots. It stores the most recent snapshot and
answers whether that snapshot is still fresh; deciding what to do about a stale one
belongs to the caller.
"""

import logging
import socket
import threading
import time
from typing import Dict, Optional, Tuple

from flask import Flask, request
from werkzeug.serving import make_server

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

# Two game ticks. A snapshot older than this is treated as no snapshot at all.
DEFAULT_MAX_AGE = 1.2

DEFAULT_PORT = 8099

_shared_lock = threading.Lock()
_shared_instance = None


class BridgeAPI:
    """Interface between Python and the RuneColor Bridge RuneLite plug-in.

    Freshness is measured from the moment a snapshot arrives here, never from the
    `sent_at` the plug-in stamped on it. That sidesteps clock skew between the two
    processes, and it measures the thing that actually matters: how long it has been
    since anything was heard at all.

    Every accessor returns its sentinel unless a fresh snapshot is available, so a
    stale feed retires all fields together. A caller must never pair a fresh HP
    reading with a stale position and act on an inconsistent picture of the world.
    """

    SCHEMA_VERSION = SCHEMA_VERSION

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        max_age: float = DEFAULT_MAX_AGE,
        verbose: bool = False,
        start: bool = True,
    ) -> None:
        """Instantiate a `BridgeAPI` and begin receiving snapshots.

        Args:
            port (int, optional): The local port to listen on. Defaults to 8099.
            max_age (float, optional): How many seconds a snapshot stays usable.
                Defaults to 1.2, which is two game ticks.
            verbose (bool, optional): Whether to print the request log from the
                underlying server. Defaults to False so as not to clutter the
                console, since the plug-in posts every 600 ms.
            start (bool, optional): Whether to bind the port and serve. Defaults to
                True. Pass False to build the app without a socket, which is what
                the unit tests do.

        Raises:
            OSError: If the port is already in use. The bind happens on the calling
                thread precisely so that this surfaces here instead of dying quietly
                inside a daemon thread.
        """
        self.port = port
        self.max_age = max_age
        self.app = Flask(__name__)
        self.fallback_count = 0

        self._snapshot: Dict = {}
        self._arrived_at: Optional[float] = None
        self._disabled = False
        self._lock = threading.Lock()
        self._server = None
        self._server_thread = None
        self._stopped = False

        werkzeug_log = logging.getLogger("werkzeug")
        werkzeug_log.disabled = not verbose

        @self.app.route("/api/snapshot/", methods=["POST"])
        def handle_snapshot() -> Tuple[str, int]:
            """Store the pushed snapshot and stamp its arrival time.

            Returns:
                Tuple[str, int]: Informational message and HTTP status code.
            """
            if self._disabled:
                return "Bridge disabled by a schema mismatch.", 409

            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return "Malformed snapshot.", 400

            schema = data.get("schema")
            if schema != SCHEMA_VERSION:
                self._disable_on_schema_mismatch(schema)
                return f"Expected schema {SCHEMA_VERSION}, got {schema!r}.", 409

            with self._lock:
                self._snapshot = data
                self._arrived_at = time.time()
            return "Snapshot received.", 200

        if start:
            self._serve()

    def _serve(self) -> None:
        """Bind the port on this thread, then serve from a daemon thread.

        Binding here rather than inside the thread is deliberate. `app.run` in a
        daemon thread swallows a port collision: the thread dies and the caller
        carries on believing it is listening. Doing the bind first means a busy port
        raises `OSError` where someone can see it.

        Raises:
            OSError: If the port is already in use.
        """
        self._assert_port_is_free(self.port)
        self._server = make_server("127.0.0.1", self.port, self.app, threaded=True)
        self.port = self._server.server_port  # Resolves port 0 to what was granted.
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name=f"runecolor-bridge-{self.port}",
            daemon=True,
        )
        self._server_thread.start()

    @staticmethod
    def _assert_port_is_free(port: int) -> None:
        """Raise if something is already listening on the port.

        Werkzeug binds with `SO_REUSEADDR`, and on Windows that flag lets a second
        process bind a port another process is actively listening on. Both servers
        then appear healthy while requests land on whichever one Windows picks, which
        is the quiet kind of wrong that costs an evening. Probing first with
        `SO_EXCLUSIVEADDRUSE` (Windows) or a plain bind (elsewhere) turns that into an
        error at startup.

        Args:
            port (int): The port to probe. Port 0 means "any free port", so there is
                nothing to check.

        Raises:
            OSError: If the port is already in use.
        """
        if port == 0:
            return
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind(("127.0.0.1", port))
        finally:
            probe.close()

    def _disable_on_schema_mismatch(self, schema) -> None:
        """Reject this and every later payload, loudly, exactly once.

        A jar built from an older commit keeps running long after `git pull`, because
        the built artifact lives in `~/.runelite/sideloaded-plugins/` and does not
        rebuild. Reading fields that have moved is worse than reading none, so the
        bridge shuts itself off for the session and the bot reverts to OCR.

        Args:
            schema (Any): The schema version the plug-in claimed.
        """
        if not self._disabled:
            self._disabled = True
            log.error(
                "RuneColor Bridge schema mismatch: expected %s, got %r. Disabling the"
                " bridge for this session and falling back to OCR. Rebuild the"
                " plug-in jar and copy it to ~/.runelite/sideloaded-plugins/.",
                SCHEMA_VERSION,
                schema,
            )

    @classmethod
    def shared(
        cls, port: int = DEFAULT_PORT, max_age: float = DEFAULT_MAX_AGE
    ) -> "BridgeAPI":
        """Return the process-wide `BridgeAPI`, starting it on first use.

        Several bots can run in one process, and only one of them may hold the port.

        Args:
            port (int, optional): The local port to listen on. Defaults to 8099.
            max_age (float, optional): How many seconds a snapshot stays usable.
                Defaults to 1.2.

        Returns:
            BridgeAPI: The shared instance.
        """
        global _shared_instance
        with _shared_lock:
            if _shared_instance is None:
                _shared_instance = cls(port=port, max_age=max_age)
            return _shared_instance

    def age(self) -> float:
        """Return the seconds since the last snapshot arrived.

        Returns:
            float: The age of the newest snapshot, or `float("inf")` if none has
                arrived.
        """
        with self._lock:
            if self._arrived_at is None:
                return float("inf")
            return time.time() - self._arrived_at

    def is_fresh(self) -> bool:
        """Report whether the newest snapshot is recent enough to act on.

        Returns:
            bool: True if a snapshot arrived within `max_age` seconds and the bridge
                has not been disabled by a schema mismatch.
        """
        return not self._disabled and self.age() <= self.max_age

    def note_fallback(self) -> None:
        """Record that a caller had to read the screen instead.

        A bridge that is dead 40% of the time still looks like it works from the
        bot's side while buying nothing, so the count is worth reporting.
        """
        self.fallback_count += 1

    def _field(self, name: str, sentinel):
        """Return a field of the freshest snapshot, or a sentinel.

        Args:
            name (str): The JSON key to read.
            sentinel: What to return when there is no fresh value.

        Returns:
            The field's value, or the sentinel.
        """
        if not self.is_fresh():
            return sentinel
        with self._lock:
            value = self._snapshot.get(name)
        return sentinel if value is None else value

    def _stat(self, name: str) -> Tuple[int, int]:
        """Return a current and maximum pair, as the orbs show them.

        Args:
            name (str): Either "hitpoints" or "prayer".

        Returns:
            Tuple[int, int]: The current and maximum values, or (-1, -1).
        """
        stat = self._field(name, None)
        if not isinstance(stat, dict):
            return -1, -1
        return int(stat.get("current", -1)), int(stat.get("max", -1))

    @property
    def hitpoints(self) -> Tuple[int, int]:
        """Tuple[int, int]: Current and maximum hitpoints, or (-1, -1)."""
        return self._stat("hitpoints")

    @property
    def prayer(self) -> Tuple[int, int]:
        """Tuple[int, int]: Current and maximum Prayer points, or (-1, -1)."""
        return self._stat("prayer")

    @property
    def run_energy(self) -> int:
        """int: Run energy from 0 to 100, or -1.

        The plug-in normalizes this. RuneLite reports run energy in hundredths of a
        percent, and converting it there keeps the scale question out of Python.
        """
        return int(self._field("run_energy", -1))

    @property
    def world_point(self) -> Tuple[int, int, int]:
        """Tuple[int, int, int]: Our tile as (x, y, plane), or (-1, -1, -1).

        Note that inside an instance the plug-in reports instance-local coordinates,
        not true world coordinates.
        """
        point = self._field("world_point", None)
        if not isinstance(point, dict):
            return -1, -1, -1
        return (
            int(point.get("x", -1)),
            int(point.get("y", -1)),
            int(point.get("plane", -1)),
        )

    @property
    def game_state(self) -> str:
        """str: The client's game state (e.g. "LOGGED_IN"), or an empty string.

        The plug-in keeps pushing while logged out, so an empty string here means the
        bridge is not being heard from, which is a different problem from being
        logged out.
        """
        return str(self._field("game_state", ""))

    @property
    def tick(self) -> int:
        """int: The client's game tick counter, or -1.

        Kept for diagnostics. If arrival gaps grow while tick deltas stay at 1, the
        network path is at fault rather than the game.
        """
        return int(self._field("tick", -1))

    def stop(self) -> None:
        """Shut the server down. Safe to call more than once."""
        if self._stopped or self._server is None:
            self._stopped = True
            return
        self._stopped = True
        self._server.shutdown()
        self._server.server_close()
        if self._server_thread is not None:
            self._server_thread.join(timeout=5)
