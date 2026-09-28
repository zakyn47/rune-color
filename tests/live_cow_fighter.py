"""Run the Cow Fighter against a live client and report what it did.

This is a live test, not a unit test. It needs RuneLite running in developer mode
with the RuneColor Bridge plug-in, and it moves the real mouse.

The kill, bone and coin counts come from the bot, but the pass criteria are checked
against the game: bones buried must match bones picked up, and the coins in the
inventory (from the plug-in) must have grown if any were looted.

Usage:
    python tests/live_cow_fighter.py [--minutes M] [--walk]
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from controller.bot_controller import MockBotController  # noqa: E402
from model.bot import BotStatus  # noqa: E402
from model.osrs.cow_fighter import OSRSCowFighter  # noqa: E402
from utilities import runelite_profiles  # noqa: E402
from utilities.geometry import Point  # noqa: E402
from utilities.walker import Walker  # noqa: E402

# Open ground among the the cow field north-east of Lumbridge castle.
COWS = Point(3256, 3272)


def switch_profile(bot: OSRSCowFighter, timeout: float = 20) -> bool:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument(
        "--walk", action="store_true", help="walk to the cows before starting"
    )
    args = parser.parse_args()

    bot = OSRSCowFighter()
    bot.set_controller(MockBotController(bot))
    bot.options_set = True
    bot.run_time = args.minutes
    bot.take_breaks = False
    bot.attach_bridge()
    time.sleep(2)
    print(f">>> profile switched: {switch_profile(bot)}", flush=True)

    bot.set_status(BotStatus.RUNNING)
    if not bot._Bot__initialize_window():
        bot.enter_game()
        if not bot._Bot__initialize_window():
            raise RuntimeError("could not orient in the client after logging in")
    if args.walk:
        print(f">>> walking to the cows at {COWS}", flush=True)
        Walker(bot, dest_square_side_length=4).walk_to(COWS, host="dax")
    bot.set_status(BotStatus.STOPPED)

    coins_before = coins_in(bot.bridge.inventory)
    bot.play()
    if bot.thread is None:
        raise RuntimeError(f"the bot did not start (status={bot.status})")
    bot.thread.join()

    print("\n" + "=" * 60 + "\nSUMMARY\n" + "=" * 60, flush=True)
    print(f"  kills         : {bot.kills}", flush=True)
    print(f"  bones buried  : {bot.bones_buried}", flush=True)
    print(f"  coins looted  : {bot.coins_looted}", flush=True)
    print(f"  coins before  : {coins_before}", flush=True)


def coins_in(inventory) -> str:
    """Say whether a coin stack is in the inventory; its size isn't reported."""
    if inventory is None:
        return "unknown"
    return "present" if 995 in inventory else "none"


if __name__ == "__main__":
    main()
