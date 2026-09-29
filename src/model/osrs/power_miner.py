import time
from typing import Callable

import model.osrs.power_miner_rules as rules
import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from utilities.geometry import RuneLiteObject

BRIDGE_TIMEOUT = 5  # Seconds to wait for the plug-in to be heard from.
# How long a click on a rock has to set us walking or mining.
START_TIMEOUT = 5
# Three ticks idle means the rock is gone: someone else took it, or it never gave.
IDLE_SECONDS = 1.8
MINE_TIMEOUT = 30
DROP_TIMEOUT = 5
# Tin and iron respawn in a few seconds, so a mine with every rock depleted is normal.
# Only this long without a single marked rock means we are somewhere else.
SEARCH_TIMEOUT = 60
CAMERA_EVERY = 5  # Failed searches between camera turns.


class OSRSPowerMiner(OSRSBot):
    runelite_profile = "power_miner"

    def __init__(self) -> None:
        bot_title = "Power Miner"
        description = (
            "Mine cyan-marked tin or iron rocks until the inventory is full, drop"
            " that ore and uncut gems (and nothing else), and repeat.\n\n"
            "Setup:\n"
            "- Choose the ore in the options.\n"
            "- Tin: stand in the Lumbridge Swamp mine, whose tin rocks the script's"
            " profile marks. Iron: stand in an iron mine and mark its iron rocks cyan"
            " with RuneLite's Object Markers plug-in.\n"
            "- A pickaxe wielded or in the inventory.\n"
            "- Turn on shift-click dropping in the game's settings.\n"
            "- Requires the RuneColor Bridge plug-in (plugin/README.md).\n"
            "- Stretched Mode off, Resizable - Classic layout."
        )
        super().__init__(bot_title=bot_title, description=description)
        self.run_time = 60  # Measured in minutes.
        self.take_breaks = False
        self.relog_time = rd.biased_trunc_norm_samp(18000, 21000)
        self.mark_color = self.cp.hsv.CYAN_MARK
        self.ore = rules.TIN
        self.ores_mined = 0
        self.ores_dropped = 0
        self.gems_dropped = 0

    def create_options(self) -> None:
        """Add bot options. See `utilities.options_builder` for more."""
        self.options_builder.add_slider_option(
            "run_time", "How long to run (minutes)?", 1, 600
        )
        self.options_builder.add_checkbox_option(
            "take_breaks", "Take short breaks?", [" "]
        )
        self.options_builder.add_dropdown_option("ore", "Ore:", list(rules.ORES))

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
            elif option == "ore":
                self.ore = rules.ORES[options[option]]
            else:
                self.log_msg(f"Unexpected option: {option}")
        self.log_msg(f"Running time: {self.run_time} minutes.")
        self.log_msg(f"Ore: {self.ore.name}.")
        self.log_msg("Options set successfully.")
        self.options_set = True

    def main_loop(self) -> None:
        """Mine and drop until the run time is up."""
        # Not the inventory: the game never sends an empty one, so the plug-in
        # reports none until the first ore arrives.
        if not self._wait_until(
            lambda: self.bridge is not None and self.bridge.game_state,
            BRIDGE_TIMEOUT,
        ):
            self.log_msg(
                "The Power Miner needs the RuneColor Bridge plug-in. Turn it on"
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
            if rules.is_full(self.bridge.inventory) and not self.drop_ore():
                self.logout_and_stop_script(
                    f"The inventory is full and holds no {self.ore_label} or gems to drop."
                )
                return
            if not self.mine_until_found():
                self.logout_and_stop_script(
                    f"No marked {self.ore.name.lower()} rocks in sight."
                )
                return
            self.update_progress((time.time() - start_time) / end_time)
            self.logout_if_greater_than(dt=self.relog_time, start=start_time)
        self.update_progress(1)
        self.log_msg(
            f"Mined {self.ores_mined} {self.ore_label}, dropped {self.ores_dropped} ore and"
            f" {self.gems_dropped} gems."
        )
        self.logout_and_stop_script("[END]")

    def mine_until_found(self) -> bool:
        """Mine a rock, waiting out depleted ones.

        Returns:
            bool: False if no rock turned up within `SEARCH_TIMEOUT`.
        """
        end_time = time.time() + SEARCH_TIMEOUT
        misses = 0
        while time.time() < end_time:
            if self.mine():
                return True
            misses += 1
            if misses % CAMERA_EVERY == 0:
                self.search_with_camera(phi=-10)
            time.sleep(self.game_tick)
        return False

    def mine(self) -> bool:
        """Click the nearest marked rock of our ore and wait until it is mined out.

        Returns:
            bool: True if a rock was clicked and mining started.
        """
        rocks = self.find_colors(self.win.game_view, self.mark_color)
        if not rocks:
            return False
        rock = min(rocks, key=RuneLiteObject.dist_from_rect_center)
        self.mouse.move_to(rock.random_point())
        # Guards against another ore's rock marked by mistake: its ore would never
        # be dropped and would fill the inventory for good.
        if not self.get_mouseover_text(contains=self.ore.rock_word):
            return False
        ores_before = self._ore_count()
        self.mouse.click()
        if not self._wait_until(lambda: self.bridge.idle_for == 0, START_TIMEOUT):
            self.log_msg("Clicked the rock, but we never started mining.")
            return False
        self._wait_until(
            lambda: self._ore_count() > ores_before
            or (self.bridge.idle_for or 0) >= IDLE_SECONDS,
            MINE_TIMEOUT,
        )
        mined = max(self._ore_count() - ores_before, 0)
        self.ores_mined += mined
        if mined:
            self.log_msg(
                f"Mined {self.ores_mined} {self.ore_label} so far.", overwrite=True
            )
        return True

    def drop_ore(self) -> bool:
        """Shift-click drop every ore of our kind and gem, leaving everything else alone.

        Returns:
            bool: True if anything was dropped.
        """
        slots = rules.drop_order(
            rules.drop_slots(self.bridge.inventory, self.ore),
            self.get_inv_drop_traversal_path(),
        )
        if not slots:
            return False
        ores_before = self._ore_count()
        self.drop_items(slots, verbose=False)
        self._wait_until(
            lambda: self.bridge.inventory is not None
            and not rules.drop_slots(self.bridge.inventory, self.ore),
            DROP_TIMEOUT,
        )
        dropped = len(slots) - len(rules.drop_slots(self.bridge.inventory, self.ore))
        ores = ores_before - self._ore_count()
        self.ores_dropped += ores
        self.gems_dropped += dropped - ores
        self.log_msg(
            f"Dropped {ores} {self.ore_label} and {dropped - ores} gems"
            f" ({self.ores_dropped} ore, {self.gems_dropped} gems so far)."
        )
        return dropped > 0

    @property
    def ore_label(self) -> str:
        return f"{self.ore.name.lower()} ore"

    def _ore_count(self) -> int:
        return len(rules.ore_slots(self.bridge.inventory, self.ore))

    def _wait_until(self, condition: Callable[[], object], timeout: float) -> bool:
        end_time = time.time() + timeout
        while time.time() < end_time:
            if condition():
                return True
            time.sleep(self.game_tick / 3)
        return False
