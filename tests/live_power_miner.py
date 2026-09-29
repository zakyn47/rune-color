"""Run the Power Miner against a live client and report what it did.

This is a live test, not a unit test. It needs RuneLite running in developer mode
with the RuneColor Bridge plug-in, and it moves the real mouse. Start next to
the marked rocks of the chosen ore with shift-click dropping turned on.

The pass criterion is checked against the game: every item the bot must not drop
(anything but the chosen ore and uncut gems) that was in the inventory at the start, as
the plug-in reports it, must still be there at the end.

Usage:
    python tests/live_power_miner.py [--minutes M] [--ore {Tin,Iron}]
"""

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import model.osrs.power_miner_rules as rules  # noqa: E402
from controller.bot_controller import MockBotController  # noqa: E402
from model.bot import BotStatus  # noqa: E402
from model.osrs.power_miner import OSRSPowerMiner  # noqa: E402
from utilities import runelite_profiles  # noqa: E402


def switch_profile(bot: OSRSPowerMiner, timeout: float = 20) -> bool:
    """Ask the plug-in for the script's profile and wait for it to be active."""
    name = runelite_profiles.profile_name(bot.bot_title)
    path = runelite_profiles.profile_path(bot.runelite_profile)
    bot.bridge.request_profile(name, str(path))
    end = time.time() + timeout
    while time.time() < end:
        if bot.bridge.active_profile == name:
            return True
        time.sleep(0.5)
    return False


def kept_items(inventory, ore: rules.Ore) -> Counter:
    """Count everything the bot must never drop."""
    return Counter(
        i for i in inventory or [] if i not in ore.dropped and i != rules.EMPTY
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=5)
    parser.add_argument("--ore", choices=list(rules.ORES), default="Tin")
    args = parser.parse_args()

    bot = OSRSPowerMiner()
    bot.set_controller(MockBotController(bot))
    bot.options_set = True
    bot.run_time = args.minutes
    bot.ore = rules.ORES[args.ore]
    bot.take_breaks = False
    bot.attach_bridge()
    time.sleep(2)
    print(f">>> profile switched: {switch_profile(bot)}", flush=True)
    print(f">>> world point: {bot.bridge.world_point}", flush=True)

    bot.set_status(BotStatus.RUNNING)
    if not bot._Bot__initialize_window():
        bot.enter_game()
        if not bot._Bot__initialize_window():
            raise RuntimeError("could not orient in the client after logging in")
    bot.set_status(BotStatus.STOPPED)

    before = bot.bridge.inventory
    snapshots = []
    logout = bot.logout_and_stop_script

    def snapshot_then_logout(msg: str) -> None:
        # Logged out, the plug-in has no inventory to report.
        snapshots.append(bot.bridge.inventory)
        logout(msg)

    bot.logout_and_stop_script = snapshot_then_logout
    bot.play()
    if bot.thread is None:
        raise RuntimeError(f"the bot did not start (status={bot.status})")
    bot.thread.join()
    after = snapshots[0] if snapshots else bot.bridge.inventory

    print("\n" + "=" * 60 + "\nSUMMARY\n" + "=" * 60, flush=True)
    print(f"  ore             : {bot.ore.name}", flush=True)
    print(f"  ore mined       : {bot.ores_mined}", flush=True)
    print(f"  ore dropped     : {bot.ores_dropped}", flush=True)
    print(f"  gems dropped    : {bot.gems_dropped}", flush=True)
    print(f"  inventory before: {before}", flush=True)
    print(f"  inventory after : {after}", flush=True)
    if after is None:
        print("  other items kept: unknown (logged out, no inventory)", flush=True)
        return
    # Mining can add items along the way (a clue geode, say), so only what was
    # there at the start has to still be there.
    lost = kept_items(before, bot.ore) - kept_items(after, bot.ore)
    gained = kept_items(after, bot.ore) - kept_items(before, bot.ore)
    print(f"  new other items : {dict(gained) or 'none'}", flush=True)
    print(f"  other items kept: {'FAIL ' + str(dict(lost)) if lost else 'PASS'}")


if __name__ == "__main__":
    main()
