"""Measure the RuneColor Bridge plug-in against the screen on a live client.

This is a live test, not a unit test. It drives a real bot against a running RuneLite
client and compares what the plug-in pushes against what the bot reads off the screen,
because the failure worth catching here is the quiet one: a payload that parses
cleanly, looks plausible, and reports the wrong number.

Every sample reads each value twice, once from the plug-in and once by OCR, and
records both. Nothing is taken on trust:

    - Hitpoints, Prayer and run energy are compared against their orbs.
    - The world point is compared against the Grid Info overlay.
    - Samples where OCR itself failed are excluded from the agreement counts, because
      those measure the screen reader rather than the plug-in.

Exit criteria, from the design doc, for moving the bot off OCR:

    - Zero unexplained disagreements across a full session.
    - Bridge availability above 99% of samples.

The script exits non-zero unless both hold, so it can gate that decision.

See `tests/README.md` for prerequisites and for how to read the output.

Usage:
    venv/Scripts/python.exe tests/live_bridge.py [--minutes M] [--out PATH]

Note that the World Location plug-in must stay enabled for this test. The overlay is
the thing the bridge is being measured against, so it is required now and only becomes
optional once this test passes.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import pygetwindow as gw  # noqa: E402

from controller.bot_controller import MockBotController  # noqa: E402
from model.bot import BotStatus  # noqa: E402
from model.osrs.power_chopper import OSRSPowerChopper  # noqa: E402
from utilities.api.bridge_api import BridgeAPI  # noqa: E402

WorldPoint = Tuple[int, int, int]

# What each field's OCR read returns when it fails, so failed reads can be told apart
# from genuine disagreements.
SENTINELS = {
    "hitpoints": -1,
    "prayer": -1,
    "run_energy": -1,
    "world_point": (-1, -1, -1),
}

AVAILABILITY_FLOOR = 0.99

# How long to wait for the snapshot after a screen read: two game ticks.
NEXT_SNAPSHOT_TIMEOUT = 1.2


def require_client() -> None:
    """Exit with a plain message if no RuneLite window is open.

    Without this the harness walks into its login path and blocks there looking for a
    splash screen that will never appear, which reads as a hang rather than as the
    missing client it is.

    Raises:
        SystemExit: If no RuneLite window can be found.
    """
    if not gw.getWindowsWithTitle("RuneLite"):
        print(
            "No RuneLite window found. Start the client, log in, and enable the"
            " RuneColor Bridge plug-in before running this test.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def build_bot() -> OSRSPowerChopper:
    """Create a bot wired to a UI-less controller, logging in if needed.

    Any concrete `RuneLiteBot` would do; the Power Chopper is used because the other
    live test already does, so one client setup serves both.

    Returns:
        OSRSPowerChopper: The configured bot.

    Raises:
        RuntimeError: If the game window can't be located even after logging in.
    """
    bot = OSRSPowerChopper()
    bot.set_controller(MockBotController(bot))
    bot.options_set = True
    bot.take_breaks = False

    # Window regions only resolve once the game is rendered. Unlike the Power Chopper
    # harness this one does not log itself in: it only measures, so a client that is
    # not ready is a setup problem to report, not something to fix by logging in and
    # sampling a loading screen.
    bot.set_status(BotStatus.RUNNING)
    if not bot._Bot__initialize_window():
        bot.set_status(BotStatus.STOPPED)
        raise RuntimeError(
            "Could not read the game window. The client has to be logged in, visible,"
            " and unobscured -- every reading here is a screenshot of that window."
            " A locked screen, a Task View left open, or a notification toast is"
            " enough. See tests/README.md for how to find what owns those pixels."
        )
    bot.set_status(BotStatus.STOPPED)
    return bot


def read_from_screen(bot: OSRSPowerChopper) -> Dict:
    """Read every measured field by OCR, with the bridge detached.

    Detaching matters. The readers prefer the plug-in when one is attached, so leaving
    it attached would compare the plug-in against itself and agree every time.

    Args:
        bot (OSRSPowerChopper): The bot to read through.

    Returns:
        Dict: The four values as OCR sees them.
    """
    attached = bot.bridge
    bot.detach_bridge()
    try:
        return {
            "hitpoints": bot.get_hp(),
            "prayer": bot.get_prayer(),
            "run_energy": bot.get_run_energy(),
            "world_point": bot.get_world_point(),
        }
    finally:
        bot.bridge = attached


def read_from_bridge(bridge: BridgeAPI) -> Optional[Dict]:
    """Read every measured field from the plug-in.

    Args:
        bridge (BridgeAPI): The attached bridge.

    Returns:
        Optional[Dict]: The four values and the tick they came from, or None if
            the feed was not fresh.
    """
    if not bridge.is_fresh():
        return None
    return {
        "tick": bridge.tick,
        "hitpoints": bridge.hitpoints[0],
        "prayer": bridge.prayer[0],
        "run_energy": bridge.run_energy,
        "world_point": bridge.world_point,
    }


def read_next_from_bridge(bridge: BridgeAPI, after_tick: int) -> Optional[Dict]:
    """Wait for the first snapshot from a later tick than `after_tick`, and read it.

    Args:
        bridge (BridgeAPI): The attached bridge.
        after_tick (int): The tick the snapshot must come after.

    Returns:
        Optional[Dict]: As `read_from_bridge`, or None if no later snapshot arrived
            within two ticks.
    """
    deadline = time.time() + NEXT_SNAPSHOT_TIMEOUT
    while time.time() < deadline:
        if (reading := read_from_bridge(bridge)) and reading["tick"] > after_tick:
            return reading
        time.sleep(0.05)
    return None


def between(seen, first, second) -> bool:
    """Say whether a screen value lies between two snapshots, inclusive.

    World points must also share a plane: a changed plane is a jump, not a step
    anyone could be caught halfway through.

    Args:
        seen: The value read off the screen.
        first: The value in the snapshot before the screen read.
        second: The value in the first snapshot after it.

    Returns:
        bool: True if `seen` is `first`, `second`, or on the way between them.
    """
    if isinstance(seen, tuple):
        if not (seen[2] == first[2] == second[2]):
            return False
        return all(
            min(a, b) <= s <= max(a, b) for s, a, b in zip(seen[:2], first, second)
        )
    return min(first, second) <= seen <= max(first, second)


def sample(bot: OSRSPowerChopper, bridge: BridgeAPI, stats: Dict) -> None:
    """Take one paired reading and fold it into the running totals.

    The plug-in samples once per tick, but the screen is redrawn every frame and a
    screenshot takes a few hundred milliseconds. While a value is changing, the
    screen can therefore show something no snapshot ever held: a live run caught
    the Grid Info tile two squares ahead of an unchanged snapshot while running. So
    each screen read is bracketed by the snapshot before it and the first snapshot
    of a later tick, and it agrees if it lies between the two, inclusive. Standing
    still, that is an exact match. A wrong value -- another plane, swapped axes, a
    tile off the path -- still falls outside. Matches that needed the later
    snapshot are counted separately so the report shows how often the bracket
    mattered.

    The window is re-measured first if it moved, so dragging or resizing the client
    mid-run does not turn every later read into an OCR failure.

    Availability is judged on the first read alone. Reading the screen takes long
    enough that a snapshot fresh at the start of a sample can be stale by the end of
    it, which would look like unavailability rather than the measurement delay it is.

    Args:
        bot (OSRSPowerChopper): The bot to read through.
        bridge (BridgeAPI): The attached bridge.
        stats (Dict): The accumulating results, mutated in place.
    """
    bot.remeasure_if_moved()
    stats["samples"] += 1
    before = read_from_bridge(bridge)
    if before is None:
        stats["bridge_unavailable"] += 1
        return
    stats["bridge_available"] += 1

    from_screen = read_from_screen(bot)
    after = read_next_from_bridge(bridge, before["tick"]) or before
    for field, sentinel in SENTINELS.items():
        counts = stats["fields"][field]
        seen = from_screen[field]
        if seen == sentinel:
            counts["ocr_failed"] += 1
        elif seen == before[field]:
            counts["agreements"] += 1
        elif between(seen, before[field], after[field]):
            counts["agreements"] += 1
            counts["matched_later_tick"] += 1
        else:
            counts["disagreements"].append(
                {
                    "at": time.strftime("%H:%M:%S"),
                    "bridge": before[field],
                    "bridge_after": after[field],
                    "screen": seen,
                }
            )


def new_stats() -> Dict:
    """Return an empty results structure.

    Returns:
        Dict: Zeroed counters for every measured field.
    """
    return {
        "samples": 0,
        "bridge_available": 0,
        "bridge_unavailable": 0,
        "fields": {
            field: {
                "agreements": 0,
                "matched_later_tick": 0,
                "ocr_failed": 0,
                "disagreements": [],
            }
            for field in SENTINELS
        },
    }


def summarize(stats: Dict) -> bool:
    """Print the agreement table and say whether the run passed.

    Args:
        stats (Dict): The accumulated results.

    Returns:
        bool: True if there were no disagreements and availability held.
    """
    samples = stats["samples"] or 1
    availability = stats["bridge_available"] / samples
    stats["availability"] = round(availability, 4)

    print()
    print(f"samples: {stats['samples']}  availability: {availability:.2%}")
    print(
        f"{'field':<14}{'agree':>8}{'(later)':>9}{'disagree':>10}"
        f"{'ocr failed':>12}{'rate':>9}"
    )

    total_disagreements = 0
    for field, counts in stats["fields"].items():
        agree = counts["agreements"]
        disagree = len(counts["disagreements"])
        total_disagreements += disagree
        compared = agree + disagree
        rate = f"{agree / compared:.2%}" if compared else "n/a"
        print(
            f"{field:<14}{agree:>8}{counts['matched_later_tick']:>9}{disagree:>10}"
            f"{counts['ocr_failed']:>12}{rate:>9}"
        )

    for field, counts in stats["fields"].items():
        for entry in counts["disagreements"][:5]:
            print(
                f"  [{field} @ {entry['at']}] bridge={entry['bridge']!r}"
                f" then {entry['bridge_after']!r} screen={entry['screen']!r}"
            )

    passed = total_disagreements == 0 and availability >= AVAILABILITY_FLOOR
    if total_disagreements:
        print(f"\nFAIL: {total_disagreements} disagreement(s).")
    if availability < AVAILABILITY_FLOOR:
        print(
            f"\nFAIL: availability {availability:.2%} is below"
            f" {AVAILABILITY_FLOOR:.0%}. Is the plug-in enabled and on the right port?"
        )
    if passed:
        print("\nPASS: the plug-in agrees with the screen and stayed available.")
    return passed


def main() -> int:
    """Run the comparison and report.

    Returns:
        int: 0 if the run passed the exit criteria, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--minutes", type=float, default=10, help="How long to sample for."
    )
    parser.add_argument(
        "--out", default="live_bridge.json", help="Where to write the results."
    )
    args = parser.parse_args()

    require_client()
    try:
        bot = build_bot()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    bot.attach_bridge()
    stats = new_stats()

    print(
        f">>> sampling for {args.minutes} minutes. If availability stays at 0%, the"
        " plug-in is not running: check that it is enabled in the RuneLite sidebar"
        " and that its port matches 8099.",
        flush=True,
    )

    deadline = time.time() + args.minutes * 60
    try:
        while time.time() < deadline:
            sample(bot, bot.bridge, stats)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n>>> interrupted, reporting what was collected so far.", flush=True)

    passed = summarize(stats)
    Path(args.out).write_text(json.dumps(stats, indent=2))
    print(f"\nresults written to {args.out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
