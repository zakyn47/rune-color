import time
from typing import Callable, Optional

import model.osrs.cow_fighter_rules as rules
import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from utilities.api.bridge_api import GroundItem, Tile
from utilities.geometry import Point

BRIDGE_TIMEOUT = 5  # Seconds to wait for the plug-in's first inventory.
ATTACK_TRIES = 3  # Cows to try before looking elsewhere.
AIM_PASSES = 2  # Aim, then correct for where the cow walked meanwhile.
ATTACK_TIMEOUT = 5  # Seconds for a clicked cow to become our target.
KILL_TIMEOUT = 60
LOOT_APPEAR_TIMEOUT = 3  # Drops appear a tick or two after the death.
TAKE_TIMEOUT = 5  # Includes walking to the item.
BURY_TIMEOUT = 3
MAX_TAKES = 5  # Bounds the loot loop if an item can never be taken.


class OSRSCowFighter(OSRSBot):
    runelite_profile = "cow_fighter"

    def __init__(self) -> None:
        bot_title = "Cow Fighter"
        description = (
            "Kill cyan-tagged cows, take the bones (and any coins) they drop, bury the"
            " bones, and repeat. Hitpoints are not watched.\n\n"
            "Setup:\n"
            "- Stand in the cow field east of the River Lum, north of Lumbridge castle.\n"
            "- Empty inventory; wield a weapon if you have one.\n"
            "- The script's RuneLite profile tags cows cyan and shows their"
            " bones and coins; the bot aims with the plug-in's live positions.\n"
            "- Requires the RuneColor Bridge plug-in (plugin/README.md).\n"
            "- Stretched Mode off, Resizable - Classic layout."
        )
        super().__init__(bot_title=bot_title, description=description)
        self.run_time = 60  # Measured in minutes.
        self.take_breaks = False
        self.relog_time = rd.biased_trunc_norm_samp(18000, 21000)
        self.death_tile: Optional[Tile] = None
        self.kills = 0
        self.bones_buried = 0
        self.coins_looted = 0

    def create_options(self) -> None:
        """Add bot options. See `utilities.options_builder` for more."""
        self.options_builder.add_slider_option(
            "run_time", "How long to run (minutes)?", 1, 600
        )
        self.options_builder.add_checkbox_option(
            "take_breaks", "Take short breaks?", [" "]
        )

    def save_options(self, options: dict) -> None:
        """Load options into the bot object.

        Args:
            options (dict): A dictionary of options (`customtkinter` widgets) as values
                and their corresponding option names as keys.
        """
        for option in options:
            if option == "run_time":
                self.run_time = int(options[option])
            elif option == "take_breaks":
                self.take_breaks = options[option] != []
            else:
                self.log_msg(f"Unexpected option: {option}")
        self.log_msg(f"Running time: {self.run_time} minutes.")
        self.log_msg("Options set successfully.")
        self.options_set = True

    def main_loop(self) -> None:
        """Fight, loot and bury until the run time is up."""
        if not self._wait_until(
            lambda: self.bridge is not None and self.bridge.inventory is not None,
            BRIDGE_TIMEOUT,
        ):
            self.log_msg(
                "The Cow Fighter needs the RuneColor Bridge plug-in. Turn it on"
                " in RuneLite and try again."
            )
            self.stop()
            return
        self.log_msg(f"[START] ({self.run_time // 60}h {self.run_time % 60}m)")
        self.prepare_standard_initial_state()
        start_time = time.time()
        end_time = int(self.run_time) * 60
        while time.time() - start_time < end_time:
            if self.take_breaks:
                self.potentially_take_a_break()
            self.loot()
            self.bury()
            self.fight()
            self.update_progress((time.time() - start_time) / end_time)
            self.logout_if_greater_than(dt=self.relog_time, start=start_time)
        self.update_progress(1)
        self.log_msg(
            f"Killed {self.kills} cows, buried {self.bones_buried} bones, looted"
            f" {self.coins_looted} coins."
        )
        self.logout_and_stop_script("[END]")

    def fight(self) -> None:
        """Attack a cow unless one is already our target, then see it die."""
        if self.bridge.target is None and not self.attack():
            return
        self.wait_for_kill()

    def attack(self) -> bool:
        """Click the nearest cow that nobody else is fighting.

        Cows wander, so a colour scan of the screen is out of date by the time the
        cursor arrives. The plug-in reports where each one is every tick, and the
        cursor follows the chosen cow by its index until the mouseover confirms.

        Returns:
            bool: True once the cow is our target.
        """
        for _ in range(ATTACK_TRIES):
            candidates = rules.attack_candidates(self.bridge.npcs)
            if not candidates:
                self.log_msg("No free cow in sight. Moving a little...")
                self.walk_to_random_point_nearby(verbose=False)
                return False
            if not self.aim_at(candidates[0].index):
                continue
            if not self.get_mouseover_text(contains="Attack"):
                continue
            self.mouse.click()
            if self._wait_until(lambda: self.bridge.target is not None, ATTACK_TIMEOUT):
                return True
        return False

    def aim_at(self, index: int) -> bool:
        """Move the cursor onto an NPC, following it if it walks.

        Args:
            index (int): The NPC's index, as the plug-in reports it.

        Returns:
            bool: True if the cursor ended on it, False if it went off screen.
        """
        for _ in range(AIM_PASSES):
            npc = rules.find_npc(self.bridge.npcs, index)
            if npc is None:
                return False
            self.mouse.move_to(Point(*npc.point), mouseSpeed="fastest")
        return True

    def wait_for_kill(self, timeout: float = KILL_TIMEOUT) -> None:
        """Wait for the fight to end, counting a kill and where it died.

        Args:
            timeout (float, optional): Seconds to wait at most.
        """
        last_tile: Optional[Tile] = None
        end_time = time.time() + timeout
        while time.time() < end_time:
            target = self.bridge.target
            if target is not None and target.tile is not None:
                last_tile = target.tile
            if rules.is_finished(target):
                # Only a health bar seen at zero is a kill: a target that simply
                # disappears walked off or was taken by someone else.
                if target is not None:
                    self.kills += 1
                    self.death_tile = last_tile
                    self.log_msg(f"Killed a {target.name} ({self.kills} so far).")
                return
            time.sleep(self.game_tick / 3)

    def loot(self) -> None:
        """Take the bones and coins our last kill dropped."""
        if self.death_tile is None:
            return
        self._wait_until(
            lambda: rules.loot_to_take(self.bridge.ground_items, self.death_tile),
            LOOT_APPEAR_TIMEOUT,
        )
        # Read the ground again after every take: walking to an item moves the
        # camera, so the other items' screen points go stale.
        for _ in range(MAX_TAKES):
            items = rules.loot_to_take(self.bridge.ground_items, self.death_tile)
            if not items or not self.take(items[0]):
                break
        self.death_tile = None

    def take(self, item: GroundItem) -> bool:
        """Pick one item up off the ground.

        Args:
            item (GroundItem): The item to take.

        Returns:
            bool: True once it reached the inventory.
        """
        before = self.bridge.inventory
        self.mouse.move_to(Point(*item.point))
        if not self.get_mouseover_text(contains="Take"):
            self.log_msg(f"Aimed at the {item.name}, but the cursor doesn't read Take.")
            return False
        self.mouse.click()
        if not self._wait_until(lambda: self.bridge.inventory != before, TAKE_TIMEOUT):
            return False
        if item.id == rules.COINS:
            self.coins_looted += item.quantity
        return True

    def bury(self) -> None:
        """Bury every bone in the inventory."""
        for slot in rules.bone_slots(self.bridge.inventory):
            self.mouse.move_to(self.win.inventory_slots[slot].random_point())
            self.mouse.click()
            if self._wait_until(
                lambda: self._slot_item(slot) != rules.BONES, BURY_TIMEOUT
            ):
                self.bones_buried += 1

    def _slot_item(self, slot: int) -> int:
        inventory = self.bridge.inventory
        # Unknown reads as still there, so a stale feed doesn't count a burial.
        return inventory[slot] if inventory else rules.BONES

    def _wait_until(self, condition: Callable[[], object], timeout: float) -> bool:
        end_time = time.time() + timeout
        while time.time() < end_time:
            if condition():
                return True
            time.sleep(self.game_tick / 3)
        return False
