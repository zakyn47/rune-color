"""Run the Power Chopper against a live client and measure what it actually did.

This is a live test, not a unit test. It drives the real bot against a running
RuneLite client and checks the bot's own reporting against the game state, because
the failures worth catching here are the ones where the bot believes it succeeded.
Burning logs, for instance, once reported 25 logs burned while consuming 1.

Every measurement is taken from the game rather than from the bot's counters:

    - Burns compare the inventory before and after against the tally the bot adds
      to `logs_burned`, and flag any mismatch.
    - Every light verdict is checked against whether that slot really did empty.
    - Grove returns compare the distance from the burn's starting tile before and
      after walking back.

See `tests/README.md` for prerequisites and for how to read the output.

Usage:
    python tests/live_power_chopper.py [--runs N] [--minutes M] [--out PATH]

Note that a session needs long enough to fill an inventory before it will burn
anything. Chopping 26 logs takes roughly 20-25 minutes, so `--minutes` under about
30 will usually measure chopping only.
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import pyautogui as pag  # noqa: E402

from controller.bot_controller import MockBotController  # noqa: E402
from model.bot import BotStatus  # noqa: E402
from model.osrs.power_chopper import OSRSPowerChopper  # noqa: E402

WorldPoint = Tuple[int, int, int]


def tile_distance(p1: WorldPoint, p2: WorldPoint) -> Optional[float]:
    """Measure the distance in tiles between two world points.

    Args:
        p1 (WorldPoint): The first (x, y, plane) world point.
        p2 (WorldPoint): The second (x, y, plane) world point.

    Returns:
        Optional[float]: The distance in tiles, or None if either point is the
            (-1, -1, -1) sentinel `get_world_point` returns when it can't read the
            Grid Info overlay.
    """
    if p1[0] == -1 or p2[0] == -1:
        return None
    return round(((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5, 1)


def park_cursor() -> None:
    """Move the cursor away from the corners of the screen.

    PyAutoGUI's fail-safe raises if the cursor is sitting in a corner when any
    movement is requested, which kills a run outright. It checks the position it
    starts from, so a cursor left in a corner by a previous run is enough to do it.
    """
    pag.FAILSAFE = False
    pag.moveTo(700, 400, duration=0.2)
    pag.FAILSAFE = True


def build_bot(minutes: int) -> OSRSPowerChopper:
    """Create a Power Chopper wired to a UI-less controller and ready to play.

    Args:
        minutes (int): How long the bot should run for, in minutes.

    Returns:
        OSRSPowerChopper: The configured bot.

    Raises:
        RuntimeError: Raised if the game window can't be located even after
            logging in.
    """
    bot = OSRSPowerChopper()
    bot.set_controller(MockBotController(bot))
    bot.options_set = True
    bot.run_time = minutes
    bot.take_breaks = False

    # Window regions only resolve once the game is rendered, so a failed initialize
    # means the client is sitting on the login splash rather than in game.
    bot.set_status(BotStatus.RUNNING)
    if not bot._Bot__initialize_window():
        print(">>> client logged out, logging in...", flush=True)
        bot.login()
        time.sleep(3)
        if not bot._Bot__initialize_window():
            raise RuntimeError("could not locate the game window after logging in")
    bot.set_status(BotStatus.STOPPED)
    return bot


def instrument(bot: OSRSPowerChopper, stats: Dict) -> None:
    """Wrap the bot's burn, light, and walk-back calls to record ground truth.

    Note that this only wraps bound methods on the instance, so the bot's own code
    is untouched and behaves exactly as it does in a normal run.

    Args:
        bot (OSRSPowerChopper): The bot to instrument.
        stats (Dict): The dictionary to record results into.
    """
    original_burn = bot.burn_all_logs
    original_return = bot.return_to_grove
    original_light = bot.light_fire
    walk_back: Dict = {}
    lights = {"ok": 0, "fail": 0, "wrong_verdicts": 0, "times": []}

    def traced_return(world_point: WorldPoint) -> bool:
        before = bot.get_world_point()
        arrived = original_return(world_point)
        walk_back.update(
            {
                "grove": world_point,
                "drift_before": tile_distance(world_point, before),
                "drift_after": tile_distance(world_point, bot.get_world_point()),
                "arrived": arrived,
            }
        )
        return arrived

    def traced_light(log_slot: int, timeout: float = 4) -> bool:
        start = time.time()
        burned = original_light(log_slot, timeout)
        lights["times"].append(round(time.time() - start, 1))
        lights["ok" if burned else "fail"] += 1
        # The verdict is only trustworthy if it agrees with the slot it describes.
        if burned != bot.is_inv_slot_empty(log_slot):
            lights["wrong_verdicts"] += 1
        return burned

    def traced_burn() -> bool:
        walk_back.clear()
        logs_before = bot.count_logs()
        tally_before = bot.logs_burned
        start = time.time()
        burned_any = original_burn()
        time.sleep(2)  # Let the last fire settle before reading the inventory.
        logs_after = bot.count_logs()
        record = {
            "logs_before": logs_before,
            "logs_after": logs_after,
            "actual_burned": logs_before - logs_after,
            "claimed_burned": bot.logs_burned - tally_before,
            "returned": burned_any,
            "secs": round(time.time() - start, 1),
            "grove_return": dict(walk_back),
        }
        record["mismatch"] = record["actual_burned"] != record["claimed_burned"]
        stats["burns"].append(record)
        print(f"    [BURN] {record}", flush=True)
        return burned_any

    bot.return_to_grove = traced_return
    bot.light_fire = traced_light
    bot.burn_all_logs = traced_burn
    stats["_lights"] = lights


def run_session(run_no: int, total: int, minutes: int) -> Dict:
    """Run a single measured session and return what it observed.

    Args:
        run_no (int): The 1-based index of this session.
        total (int): How many sessions are being run in all.
        minutes (int): How long this session should run for, in minutes.

    Returns:
        Dict: The recorded statistics for the session.
    """
    banner = f"RUN {run_no}/{total} (run_time={minutes}m) {time.strftime('%H:%M:%S')}"
    print(f"\n{'=' * 70}\n{banner}\n{'=' * 70}", flush=True)
    stats: Dict = {
        "run": run_no,
        "burns": [],
        "errors": [],
        "start": time.strftime("%H:%M:%S"),
    }
    try:
        park_cursor()
        bot = build_bot(minutes)
        instrument(bot, stats)
        bot.play()
        if bot.thread is None:
            raise RuntimeError(f"the bot did not start (status={bot.status})")
        bot.thread.join()
        lights = stats.pop("_lights")
        times = lights.pop("times")
        lights["avg_s"] = round(sum(times) / len(times), 1) if times else None
        stats["lights"] = lights
        stats["logs_burned_total"] = bot.logs_burned
        stats["status"] = str(bot.status)
    except Exception as exc:
        # An exception raised inside the bot's own thread won't surface here, so a
        # clean `errors` list is not by itself proof that the run went well. Check
        # the log for a traceback too.
        stats.pop("_lights", None)
        stats["errors"].append(f"{type(exc).__name__}: {exc}")
        print("!!! RUN EXCEPTION:", traceback.format_exc(), flush=True)
    stats["end"] = time.strftime("%H:%M:%S")
    return stats


def summarize(results) -> None:
    """Print a short verdict over every session that ran.

    Args:
        results: The list of per-session statistics.
    """
    burned = sum(b["actual_burned"] for r in results for b in r["burns"])
    mismatches = sum(1 for r in results for b in r["burns"] if b["mismatch"])
    ok = sum(r.get("lights", {}).get("ok", 0) for r in results)
    failed = sum(r.get("lights", {}).get("fail", 0) for r in results)
    wrong = sum(r.get("lights", {}).get("wrong_verdicts", 0) for r in results)
    errors = sum(len(r["errors"]) for r in results)
    print(f"\n{'=' * 70}\nSUMMARY\n{'=' * 70}", flush=True)
    print(f"  logs burned      : {burned}", flush=True)
    print(f"  burn mismatches  : {mismatches}  (want 0)", flush=True)
    print(f"  lights ok/failed : {ok}/{failed}", flush=True)
    print(f"  wrong verdicts   : {wrong}  (want 0)", flush=True)
    print(f"  run errors       : {errors}  (want 0)", flush=True)


def main() -> None:
    """Run every requested session, then report and save the results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="sessions to run")
    parser.add_argument(
        "--minutes", type=int, default=35, help="minutes per session (30+ to burn)"
    )
    parser.add_argument("--out", type=Path, default=Path("live_power_chopper.json"))
    args = parser.parse_args()

    results = []
    for run_no in range(1, args.runs + 1):
        stats = run_session(run_no, args.runs, args.minutes)
        results.append(stats)
        print(f">>> RUN {run_no} SUMMARY: {json.dumps(stats)}", flush=True)
        args.out.write_text(json.dumps(results, indent=2))
        if run_no < args.runs:
            time.sleep(8)
    summarize(results)
    print(f"\nresults written to {args.out}", flush=True)


if __name__ == "__main__":
    main()
