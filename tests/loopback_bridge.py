"""Prove the Java plug-in and the Python receiver agree on the wire.

This needs no game and no account. It starts the real `BridgeAPI`, runs the real
`SnapshotPublisher` in a JVM, and checks that what arrives parses into the values the
publisher sent. It is the widest test that can run without a live client, and it is
the one that would catch a payload the two halves disagree about: a renamed key, a
changed nesting, a number serialized as a string.

The unit suites on either side cannot catch that. Each one tests its own half against
its own idea of the format, and both pass happily while the two ideas differ.

Usage:
    venv/Scripts/python.exe tests/loopback_bridge.py

Exits 0 when every field matches, 1 otherwise.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from utilities.api.bridge_api import BridgeAPI  # noqa: E402

PORT = 8131
JAVA_HOME = Path.home() / "tools" / "jdk-11"


def start_publisher(url: str) -> subprocess.Popen:
    """Start the real Java publisher against `url`.

    Args:
        url (str): Where the publisher should POST.

    Returns:
        subprocess.Popen: The running Gradle invocation.
    """
    return subprocess.Popen(
        [
            str(ROOT / "plugin" / "gradlew.bat"),
            "loopback",
            f"-Purl={url}",
            "--no-daemon",
            "-q",
        ],
        cwd=str(ROOT / "plugin"),
        env={**os.environ, "JAVA_HOME": str(JAVA_HOME)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def wait_for_a_fresh_snapshot(bridge: BridgeAPI, publisher: subprocess.Popen) -> bool:
    """Poll for a fresh snapshot while the publisher is still running.

    The freshness window is 1.2 seconds, and Gradle spends several seconds tearing
    itself down after the POST lands. Waiting for the process to exit before looking
    therefore always finds an expired snapshot, so the poll runs concurrently.

    Args:
        bridge (BridgeAPI): The receiver to watch.
        publisher (subprocess.Popen): The running Gradle invocation.

    Returns:
        bool: True if a fresh snapshot was seen.
    """
    deadline = time.time() + 900
    while time.time() < deadline:
        if bridge.is_fresh():
            return True
        if publisher.poll() is not None:
            # The publisher has exited. Give any in-flight request a moment, then
            # take one last look before giving up.
            time.sleep(0.5)
            return bridge.is_fresh()
        time.sleep(0.05)
    return False


def main() -> int:
    """Run the loopback check and report field by field.

    Returns:
        int: 0 if every field matched, 1 otherwise.
    """
    bridge = BridgeAPI(port=PORT)
    try:
        publisher = start_publisher(f"http://127.0.0.1:{PORT}/api/snapshot/")
        arrived = wait_for_a_fresh_snapshot(bridge, publisher)

        # Read every field before the 1.2 s window closes; the assertions come after.
        observed = {
            "is_fresh": arrived,
            "hitpoints": bridge.hitpoints,
            "prayer": bridge.prayer,
            "run_energy": bridge.run_energy,
            "world_point": bridge.world_point,
            "game_state": bridge.game_state,
            "tick": bridge.tick,
        }

        output = publisher.communicate(timeout=900)[0]
        if publisher.returncode != 0:
            print(output)
            print("FAIL: the publisher did not run")
            return 1
        if not arrived:
            # The publisher logs its own failures; showing them beats guessing.
            print(output)

        checks = {
            "is_fresh": (observed["is_fresh"], True),
            "hitpoints": (observed["hitpoints"], (42, 55)),
            "prayer": (observed["prayer"], (12, 43)),
            "run_energy": (observed["run_energy"], 87),
            "world_point": (observed["world_point"], (3222, 3218, 0)),
            "game_state": (observed["game_state"], "LOGGED_IN"),
            "tick": (observed["tick"], 123456),
        }
        failed = {k: v for k, v in checks.items() if v[0] != v[1]}
        for name, (actual, expected) in checks.items():
            mark = "FAIL" if name in failed else "ok"
            print(f"[{mark}] {name}: {actual!r} (expected {expected!r})")

        print("FAIL" if failed else "PASS")
        return 1 if failed else 0
    finally:
        bridge.stop()


if __name__ == "__main__":
    sys.exit(main())
