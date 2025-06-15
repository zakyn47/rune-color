import time

import pyautogui as pag

import utilities.mappings.item_ids as iid
import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot


class OSRSJeweler(OSRSBot):
    def __init__(self) -> None:
        bot_title = "not ready"
        description = (
            "Withdraw metal bars and a choice of gem from the Edgeville bank, walk to"
            " the nearby furnace, craft jewlery, deposit the products back at the"
            " bank, and then repeat. Choose which jewelry to craft from a variety of"
            " options."
        )
        super().__init__(bot_title=bot_title, description=description)
        self.run_time = 60 * 10  # Measured in minutes (default 10 hours).
        self.take_breaks = False
        self.break_max = 60  # Measured in seconds.
        self.bank_tab = 2
        self.relog_time = rd.biased_trunc_norm_samp(
            18000, 21000
        )  # Secs before relogging.

        self.gem = "emerald"
        self.mould = "bracelet"
        self.gem_formatted_name = self.gem.replace("_", " ").capitalize()
        self.options_set = False  # If True, we use the above defaults.

        self.just_starting = True  # Whether we are on our very first round of crafting.
        self.jewelry_bankd = 0  # Number of pieces of jewelry deposited.
        self.invs_bankd = 0  # Number of inventories deposited.
        self.total_profit = 0
        # Since iid is used in an `eval`, defining here it avoids any import warnings.
        self.iid = iid

    def create_options(self) -> None:
        """Add bot options. See `utilities.options_builder` for more."""
        self.options_builder.add_slider_option(
            "run_time", "How long to run (minutes)?", 1, 600
        )
        self.options_builder.add_dropdown_option(
            "bank_tab",
            'Bank tab (1 is "Tab 1"):',
            ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        )
        self.options_builder.add_dropdown_option(
            "gem", "Gem:", ["Emerald", "Sapphire", "Red topaz"]
        )
        self.options_builder.add_dropdown_option(
            "mould", "Mould:", ["Amulet", "Ring", "Bracelet"]
        )
        self.options_builder.add_checkbox_option("take_breaks", "Take breaks?", [" "])

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
            elif option == "bank_tab":
                self.bank_tab = int(options[option])
            elif option == "gem":
                self.gem = options[option].replace(" ", "_").lower()
            elif option == "mould":
                self.mould = options[option].lower()
            elif option == "take_breaks":
                self.take_breaks = options[option] != []
            else:
                self.log_msg(f"unknown option: {option}")
                self.options_set = False
                return

        self.log_msg(f"[RUN TIME] {self.run_time} MIN", overwrite=True)
        break_time_str = f"(MAX {self.break_max}s)" if self.take_breaks else ""
        self.log_msg(f"  [BREAKS] {str(self.take_breaks).upper()} {break_time_str}")
        self.gem_formatted_name = self.gem.replace("_", " ").capitalize()
        self.log_msg(f"[CRAFTING] {self.gem_formatted_name} {self.mould}s")
        self.options_set = True
        self.log_msg("Options set successfully.")

    def main_loop(self) -> None:
        """Craft jewlery at the Edgeville furnace, bank, then repeat.

        Run the main game loop of
            1. Deposit jewlery and withdraw metal bars and gems from the Edgeville bank.
            2. Travel to the furnace east of the Edgeville bank.
            3. Craft 13 jewlery pieces.
            4. Travel back to the bank to deposit the jewlery.

        For this to work as intended:
            1. Our character must begin between the Edgeville bank and furnace and have
                a single mould type in their inventory.
            2. The furnace must be marked with a specific color
                (e.g. `cp.hsv.CYAN_MARK`).
            3. The Edgeville bank booth must be marked with a different color
                (e.g. `cp.hsv.PURPLE_MARK`).
            4. Make sure to store all input materials in a separate bank tab and label
                it with an item distinctly different from any of the input materials
                (e.g. a beer). This bank tab should be cleared of any other items to
                ensure OpenCV reliably detects the sprites.
            5. Craft one of the desired items beforehand so that it is pre-highlighted
                in the furnace.
            6. The PIN for our bank must not get in the way of the bot. Disabling
                the PIN is recommended.
            7. Screen dimmers like F.lux or Night Light on Windows should be disabled
                since our bot is highly sensitive to colors.
        """
        run_time_str = f"{self.run_time // 60}h {self.run_time % 60}m"
        self.log_msg(f"   [START] ({run_time_str})", overwrite=True)
        self.log_msg(f"[CRAFTING] {self.gem_formatted_name} {self.mould}s")
        start_time = time.time()
        end_time = int(self.run_time) * 60
        while time.time() - start_time < end_time:
            if self.take_breaks:
                self.potentially_take_a_break()
            if self.has_req_mats and self.find_and_mouse_to_furnace():
                self.craft_jewelry()
            if not self.has_req_mats:
                # After the first round, `craft_jewelry` takes care of mousing to the
                # bank because it's more efficient to reposition the mouse during
                # crafting rather than after crafting completes.
                if self.just_starting:
                    self.find_and_mouse_to_bank()
                self.bank_at_edgeville()
                self.set_compass_direction("east")
                if self.find_and_mouse_to_furnace():
                    self.craft_jewelry()
            self.update_progress((time.time() - start_time) / end_time)
            self.logout_if_greater_than(dt=self.relog_time, start=start_time)
        self.update_progress(1)
        self.logout_and_stop_script("[END]")

    @property
    def has_req_mats(self) -> bool:
        """Check if there is at least 1 relevant (bar, gem) pair in the inventory.

        Returns:
            bool: True if materials for at least one piece of jewelry are available,
                otherwise False.
        """
        folder = "jeweler"
        if self.gem in ["emerald", "sapphire"]:
            metal = "gold"
        elif self.gem == "red_topaz":
            metal = "silver"
        has_bars = self.is_item_in_inv(png=f"{metal}-bar.png", folder=folder)
        if self.gem == "red_topaz":
            gem = "red-topaz"
        if self.gem in ["emerald", "sapphire"]:
            gem = self.gem
        has_gems = self.is_item_in_inv(png=f"{gem}.png", folder=folder)
        return has_bars and has_gems

    @property
    def is_hovering_furnace(self) -> bool:
        """Whether the cursor is actively hovering over a furnace.

        Returns:
            bool: True if the mouse cursor is hovering over a furnace, False otherwise.
        """
        return self.get_mouseover_text(contains=["Smelt", "Furnace"])

    def bank_at_edgeville(self) -> None:
        """Given the mouse is in position, travel to, use, and close the Edgeville bank.

        Args:
            min_energy (int, optional): The threshold at which our character must
                walk to conserve energy. Defaults to 500 (5 in game).
        """
        if self.gem == "red_topaz":
            jewel_sprite = f"topaz-{self.mould}"
        if self.gem in ["emerald", "sapphire"]:
            jewel_sprite = f"{self.gem}-{self.mould}"
        jewel_inds = self.get_inv_item_slots(
            png=f"{jewel_sprite}.png", folder="jeweler"
        )
        jewel_slot = None
        if jewel_inds:
            jewel_slot = self.win.inventory_slots[jewel_inds[0]]
        preemptive_loc = None
        if not self.just_starting:
            preemptive_loc = jewel_slot
        if self.open_bank(ctrl_click=self.is_run_off(), preemptive_loc=preemptive_loc):
            if self.take_breaks:  # Take breaks during menuing for more humanization.
                self.potentially_take_a_break()
            self.log_msg("Traveled to bank and opened window.", overwrite=True)
            if self.just_starting:
                self.set_withdraw_qty(13, exit_direction="up")
                self.open_bank_tab(self.bank_tab)
                if jewel_slot:
                    self.mouse.move_to(jewel_slot.random_point())
                self.just_starting = False
            self.mouse.click()
            self.invs_bankd += 1
            self.jewelry_bankd += len(jewel_inds)
            item_name = jewel_sprite.upper().replace("-", "_")
            eval_str = f"iid.{item_name}"
            item_id = eval(eval_str)
            profit_this_trip = self.get_price(item_id) * len(jewel_inds)
            self.total_profit += profit_this_trip
            gp_shorthand = self.get_shorthand_gp_value(gp_amt=self.total_profit)
            s_ = "" if self.invs_bankd == 1 else "s"
            msg = (
                f"{self.gem_formatted_name} {self.mould}s deposited:"
                f" {self.jewelry_bankd} over {self.invs_bankd} trip{s_}"
                f" ({gp_shorthand} gp profit)"
            )
            self.log_msg(msg)
            self.withdraw_13_metal_bars_and_13_gems()
        self.close_bank()

    def withdraw_13_metal_bars_and_13_gems(self) -> None:
        """Withdraw 13 metal bars and 13 gems from the bank."""
        if self.gem == "red_topaz":
            gem = "red-topaz"
            metal = "silver"
        if self.gem in ["emerald", "sapphire"]:
            gem = self.gem
            metal = "gold"
        bars = self.find_sprite(
            win=self.win.game_view, png=f"{metal}-bar-bank.png", folder="jeweler"
        )
        gems = self.find_sprite(
            win=self.win.game_view, png=f"{gem}-bank.png", folder="jeweler"
        )
        if not (bars and gems) and not self.has_req_mats:
            self.log_msg("Out of required materials. Logging out.")
            self.close_bank()
            self.logout_and_stop_script("[END]")
        self.log_msg("Required materials found. Withdrawing gems and bars...")
        req_mats = {"bars": bars, "gems": gems}
        for i, (name, material) in enumerate(req_mats.items()):
            mouse_speed = "fast" if i == 0 else "fastest"  # Speed optimization.
            self.mouse.move_to(material.random_point(), mouseSpeed=mouse_speed)
            self.mouse.click()
            self.log_msg(f"Withdrew 13 {name}.")

    def craft_jewelry(self) -> bool:
        """Craft jewelry at the Edgeville furnace.

        At the start of this method call, it is assumed the cursor is hovering above a
        the Edgeville furnace.

        Returns:
            bool: True if we were able to craft successfully, False otherwise.
        """
        hold_key = "ctrl" if self.is_run_on() else None
        self.mouse.click(hold_key=hold_key)
        # As we are moving to the furnace, change our perspective to get a good view of
        # the bank (which is now behind us).
        self.set_compass_direction("west")
        # Moving the mouse toward center after clicking the furnace adds a human touch.
        center = self.win.game_view.center
        self.mouse.move_to(rd.random_point_around(center, xpad=50, ypad=50))
        timeout = 30  # It shouldn't take more than 30 seconds to get to the furnace.
        start = time.time()
        attempt = 0
        while not self.is_furnace_window_open():
            attempt += 1
            self.log_msg(f"Traveling to furnace...({attempt})", overwrite=True)
            self.sleep()
            if time.time() - start > timeout:
                self.log_msg(f"Timed out ({timeout}s). Failed to travel to furnace.")
        if self.is_furnace_window_open():
            self.log_msg("Traveled to furnace. Opened window.", overwrite=True)
            if self.take_breaks:  # Take breaks during menuing for more humanization.
                self.potentially_take_a_break()
            pag.press("space", presses=2, interval=rd.biased_trunc_norm_samp(0.1, 0.2))
            self.log_msg("Crafting jewelry...")
            self.sleep(0.5, 0.7)
            self.find_and_mouse_to_bank()  # Time efficiency optimization.
            # The instant we no longer have the required materials, stop crafting.
            while self.has_req_mats:
                self.sleep()
            self.log_msg("Jewelry crafted.")
            return True
        # If we became idle while we still have materials to craft, start again. This
        # usually happens when our character levels up.
        self.sleep(2, 3)  # If we've failed up to this point, let things settle down.
        if self.check_idle_notifier_status("is_idle") and self.has_req_mats:
            self.log_msg("Unexpectedly idle. Resuming jewelry crafting...")
            # Esc is pressed here in the off chance that a window is open.
            pag.press("esc", presses=2, interval=rd.biased_trunc_norm_samp(0.1, 0.2))
            self.find_and_mouse_to_furnace()
            self.craft_jewelry()
        self.log_msg("Failed to open furnace window.")
        self.log_msg("Failed to craft jewelry.")
        return False

    def is_furnace_window_open(self) -> bool:
        """Return whether the furnace window is open.

        Returns:
            bool: True if the furnace window is open, False if it isn't.
        """
        if self.find_sprite(
            win=self.win.game_view, png="furnace-window-open.png", folder="jeweler"
        ):
            return True
        return False

    def find_and_mouse_to_furnace(self, num_retries: int = 10) -> bool:
        """After traveling within range, mouse to the color-tagged furnace.

        Note that this is a simple wrapper for `find_and_mouse_to_marked_object`.

        Args:
            num_retries (int, optional): The number of times to retry searching if the
                first search failed. Defaults to 10.

        Returns:
            bool: True if we found the furnace and moused to it, or False otherwise.
        """
        return self.find_and_mouse_to_marked_object(
            color=self.cp.hsv.CYAN_MARK,
            req_txt_colors=[self.cp.bgr.OFF_WHITE_TEXT, self.cp.bgr.OFF_CYAN_TEXT],
            req_txt=["Smelt", "Furnace"],
            num_retries=num_retries,
        )
