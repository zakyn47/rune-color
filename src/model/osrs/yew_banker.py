import time

import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from model.osrs.power_chopper import OSRSPowerChopper
from utilities.geometry import Point
from utilities.mappings import item_ids as iid
from utilities.mappings import locations as loc
from utilities.walker import Walker, WalkPath


class OSRSYewBanker(OSRSPowerChopper, OSRSBot):
    def __init__(self) -> None:
        bot_title = "not ready"
        description = (
            "Chop the yew trees directly behind Varrock castle, gather a full inventory"
            " of logs, travel to the GE, bank the logs, then repeat."
        )
        # We are able to access all methods in `OSRSPowerChopper`, but not its
        # attributes because it was not instantiated directly. Instead, as usual, we
        # have access to the base attributes of OSRSBot.
        OSRSBot.__init__(self, bot_title=bot_title, description=description)
        self.run_time = 60 * 10  # Measured in minutes (default 10 hours).
        self.take_breaks = False
        self.break_max = 60  # Measured in seconds.
        self.options_set = True  # If True, use the above defaults.

        self.walker = Walker(self, dest_square_side_length=4)
        self.first_bank = True  # Whether it is our first time banking.
        self.logs_bankd = 0  # Number of logs put into the bank.
        self.invs_bankd = 0  # Number of inventories deposited.
        self.relog_time = rd.biased_trunc_norm_samp(
            18000, 21000
        )  # Secs before relogging.

        # These are the core attributes of OSRSPowerChopper that we need.
        self.mark_color = self.cp.hsv.CYAN_MARK  # Color of the marked trees.
        self.logs_dropped = 0  # Number of logs dropped.
        self.failed_searches = 0  # Number of times we failed to find another tree.
        self.num_considerations = 0  # Num of times we considered the next target tree.
        self.woodcut_keywords = ["Yew", "Yew tree", "Chop down", "Tree"]

    def create_options(self) -> None:
        """Add bot options.

        See `utilities.options_builder` or `osrs.template` for more.
        """
        self.options_builder.add_slider_option(
            "run_time", "How long to run (minutes)?", 1, 600
        )
        self.options_builder.add_checkbox_option(
            "take_breaks", "Take short breaks?", [" "]
        )

    def save_options(self, options: dict) -> None:
        """Load options into the bot object.

        Adjust this definition to mirror the options in `create_options`. These two
        functions are called during the setup of the bot controller.

        Args:
            options (dict): A dictionary of options, with the option names as keys.
        """
        for option in options:
            if option == "run_time":
                self.run_time = int(options[option])
            elif option == "take_breaks":
                self.take_breaks = options[option] != []
            else:
                self.log_msg(f"Unknown option: {option}")
                self.options_set = False
                return

        self.log_msg(f"[RUN TIME] {self.run_time} MIN")
        break_time_str = f"(MAX {self.break_max}s)" if self.take_breaks else ""
        self.log_msg(f"  [BREAKS] {str(self.take_breaks).upper()} {break_time_str}")
        self.options_set = True
        self.log_msg("Options set successfully.")

    def main_loop(self) -> None:
        """Farm yew trees behind Varrock Castle, bank them at the GE, then repeat.

        Run the main game loop of:
            1. Searching for yew trees and chopping them for yew logs.
            2. Traveling to the bank booth at the GE and banking the yew logs.
            3. Traveling back to the three yew trees behind Varrock castle.
            4. Resuming the task of chopping yew trees to gather yew logs.

        For this to work as intended:
            1. Our character must begin next to the yew trees behind Varrock castle.
            2. The yew trees must be marked as a specific color
                (e.g. `self.cp.hsv.CYAN_MARK`) as defined in `utilities.api.colors_hsv`.
                Objects are intended to be marked with the Object Markers RuneLite
                plug-in.
            3. The eastern GE bank booth(s) must be marked as a different color
                (e.g. `self.cp.hsv.PURPLE_MARK`).
            4. The PIN for our bank must not get in the way of the bot. Disabling
                the PIN is recommended.
            5. Screen dimmers like F.lux or Night Light on Windows should be disabled
                since our bot is highly sensitive to colors.
        """
        run_time_str = f"{self.run_time // 60}h {self.run_time % 60}m"  # e.g. 6h 0m
        self.log_msg(f"[START] ({run_time_str})", overwrite=True)
        self.prepare_standard_initial_state()
        start_time = time.time()
        end_time = int(self.run_time) * 60  # Measured in seconds.
        while time.time() - start_time < end_time:
            if self.take_breaks:
                self.potentially_take_a_break()
            self.toggle_run_on_if_enough_energy()
            if self.is_inv_full():
                self.log_msg("Inventory is full. Headed to GE.")
                self.pitch_down_and_align_camera("west")
                self.travel_to(
                    tile_coord=loc.GRAND_EXCHANGE_EAST,
                    walk_path=loc.GE_TO_BEHIND_VARROCK_PATH[::-1],
                    dest_name="GRAND_EXCHANGE_EAST",
                )
                if self.find_and_mouse_to_bank():
                    if self.bank_yew_logs_at_ge():
                        self.set_compass_direction("east")
                        self.travel_to(
                            tile_coord=loc.BEHIND_VARROCK_CASTLE,
                            walk_path=loc.GE_TO_BEHIND_VARROCK_PATH,
                            dest_name="BEHIND_VARROCK_CASTLE",
                        )
                    else:
                        self.log_msg("Something went wrong. Attempting to reset.")
                        self.drop_1_yew_log()
            if self.is_inv_not_full():
                northern_angles = list(range(355, 360)) + list(range(0, 5))
                if self.get_compass_angle() not in northern_angles:
                    self.pitch_down_and_align_camera("north")
                self.resume_chopping()
            self.update_progress((time.time() - start_time) / end_time)
            self.logout_if_greater_than(dt=self.relog_time, start=start_time)
        self.update_progress(1)
        self.logout_and_stop_script("[END]")

    def travel_to(self, tile_coord: Point, walk_path: WalkPath, dest_name: str):
        """Travel to a provided destination via a `Walker` object.

        Args:
            tile_coord (Point): Tile coordinate of the destination.
            walk_path (WalkPath): Manually-set list of waypoints to walk along if API
                path-finding services fail.
            dest_name (str): The name of the intended destination.
        """
        if self.walker.travel_to_dest_along_path(
            tile_coord,
            walk_path,
            dest_name,
        ):
            self.log_msg(f"Arrived: {dest_name}")
        else:
            self.log_msg(f"Failed to arrive at {dest_name}.")
        self.sleep_while_traveling()

    def bank_yew_logs_at_ge(self) -> bool:
        """Given the mouse is over a bank booth, open, use, and close the GE bank.

        Returns:
            bool: True if we banked our yew logs at the GE, False otherwise.
        """
        if self.open_bank():
            self.log_msg("Traveled to bank and opened window.")
            if self.first_bank:
                self.set_withdraw_qty(27, exit_direction="right")
                self.first_bank = False
            if slots := self.get_inv_item_slots(
                png="yew-logs.png", folder="yew_banker"
            ):
                chosen_slot = self.win.inventory_slots[slots[0]]
                self.mouse.move_to(chosen_slot.random_point())
                self.mouse.click()
                self.logs_bankd += len(slots)
                self.invs_bankd += 1
                self.sleep(0.4, 0.6)  # A pause here improves reliability.
                price_avg_api = self.get_price(iid.YEW_LOGS)
                profit_per_log = 220 if price_avg_api == 0 else price_avg_api
                gp_amt = self.logs_bankd * profit_per_log
                gp_shorthand = self.get_shorthand_gp_value(gp_amt)
                _s = "" if self.invs_bankd == 1 else "s"
                msg = (
                    f"Logs deposited: {self.logs_bankd} over {self.invs_bankd} trip{_s}"
                    f" ({gp_shorthand} gp profit)"
                )
                self.log_msg(msg)
                self.close_bank()
                return True
            else:
                self.log_msg("Failed to find any inventory slots with yew logs.")
        else:
            self.log_msg("Could not open bank window.")
            self.log_msg("Failed to bank yew logs.")
            return False

    def drop_1_yew_log(self) -> None:
        """Drop a log from our inventory.

        This can help reset the search algorithm if the bot gets stuck.
        """
        self.log_msg("Dropping 1 log...")
        log_slots = self.get_inv_item_slots(png="yew-logs.png", folder="yew_banker")
        if log_slots:
            self.drop_items(slots=[log_slots[0]], verbose=False)
            self.log_msg("Dropped 1 log.", overwrite=True)
            self.logs_dropped += 1
        else:
            self.log_msg("Failed to drop 1 log.")
