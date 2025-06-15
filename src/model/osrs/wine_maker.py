import random
import time
from typing import Tuple

import pyautogui as pag

from model.osrs.osrs_bot import OSRSBot
from utilities import ocr
from utilities import random_util as rd
from utilities.mappings import item_ids as iid


class OSRSWineMaker(OSRSBot):
    def __init__(self):
        bot_title = "not ready"
        description = (
            "Withdraw grapes and jugs of water from a marked bank, make jugs of wine,"
            " deposit the products back at the bank, and then repeat."
        )
        super().__init__(bot_title=bot_title, description=description)
        self.run_time = 60 * 10  # Measured in minutes (default 10 hours).
        self.take_breaks = False
        self.bank_tab = 1
        self.options_set = True  # If True, we use the above defaults.

        self.relog_time = rd.biased_trunc_norm_samp(
            18000, 21000
        )  # Secs before relogging.
        self.break_max = 60 * 5  # Measured in seconds (default 5 minutes).
        self.wines_bankd = 0  # Number of jugs of wine deposited.
        self.invs_bankd = 0  # Number of inventories deposited.

        # Define initial states for state-based methods.
        self.first_bank = True  # Whether it is our first time banking.
        # Note that `first_bank` is a flag for whether our character is banking for the
        # first time (and thus whether we should spend extra time to configure the bank
        # interface for wine-making).
        self.hovering_bank = None  # Whether the cursor is hovering over a bank.
        self.deposit_all_btn = None

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
            elif option == "take_breaks":
                self.take_breaks = options[option] != []
            elif option == "bank_tab":
                self.bank_tab = int(options[option])
            else:
                self.log_msg(f"Unknown option: {option}")
                self.options_set = False
                return

        self.log_msg(f"[RUN TIME] {self.run_time} MIN", overwrite=True)
        break_time_str = f"(MAX {self.break_max}s)" if self.take_breaks else ""
        self.log_msg(f"  [BREAKS] {str(self.take_breaks).upper()} {break_time_str}")
        self.log_msg(f"[BANK TAB] {self.bank_tab}")
        self.options_set = True
        self.log_msg("Options set successfully.")

    def main_loop(self):
        """Make jugs of wine, bank, then withdraw grapes and jugs of water and repeat.

        Run the main game loop.
            1. Withdraw grapes and jugs of water from a chosen bank tab.
            2. Make 14 jugs of wine.
            3. Deposit the jugs of wine.

        For this to work as intended:
            1. Our character must begin next to a color-marked bank booth.
            2. All input materials should be in a separate bank tab and labeled with a
                distinctly unrelated item (e.g. a full beer). This bank tab should be
                cleared of any other items to ensure OpenCV reliably detects item
                sprites.
            3. The PIN for our bank must not get in the way of the bot. Disabling
                the PIN is recommended.
            4. Screen dimmers like F.lux or Night Light on Windows should be disabled
                since our bot is highly sensitive to colors.
        """
        run_time_str = f"{self.run_time // 60}h {self.run_time % 60}m"
        self.log_msg(f"[START] ({run_time_str})", overwrite=True)
        self.close_active_chat_cursor()
        if not self.is_chat_tab_open("game"):
            self.open_chat_tab("game")
        if not self.is_control_panel_tab_open("inventory"):
            self.open_control_panel_tab("inventory")
        start_time = time.time()
        end_time = int(self.run_time) * 60
        while time.time() - start_time < end_time:
            if self.take_breaks:
                self.potentially_take_a_break()
            if not self.has_req_mats and not self.is_bank_window_open():
                if not self.hovering_bank:
                    self.hovering_bank = self.find_and_mouse_to_bank()
                # As we wait for the bank to open (or because we are presumably
                # traveling toward it), preemptively move to the Deposit All button
                # if we have already configured the bank interface for wine-making.
                if self.open_bank(preemptive_loc=self.deposit_all_btn):
                    self.log_msg("Bank window opened.", overwrite=True)
                    if self.take_breaks:
                        # Taking a break with an open menu is humanizing.
                        self.potentially_take_a_break()
                    if self.first_bank:
                        self.set_withdraw_qty(qty=14, exit_direction="up")
                        self.open_bank_tab(tab_num=self.bank_tab)
                        if not self.deposit_all_btn:  # Locate Deposit All button.
                            self.deposit_all_btn = self.find_sprite(
                                win=self.win.game_view,
                                png="deposit-all.png",
                                folder="bank",
                                confidence=0.10,
                            )
                    if self.is_inv_nonempty():
                        if self.first_bank:
                            self.bank_left_click_deposit_all()
                            self.first_bank = False
                        # If we preemptively moved the mouse to the Deposit All
                        # button (because this isn't our first bank), save time by
                        # simply left-clicking instead of calling
                        # `bank_left_click_deposit_all`.
                        elif self.deposit_all_btn:
                            self.mouse.click()
                        self.invs_bankd += 1
                        self.wines_bankd += self.num_jugs_wine
                        self.report_status()
                    self.get_14_grapes_14_jugs_h2o()
                    # Closing the bank can take a few attempts, so we save time by
                    # preemptively mousing to a grapes sprite in our inventory.
                    inv_coord = self.mouse_to_grapes()
                    self.close_bank()
            if self.has_req_mats:
                # If we begin with an inventory that includes enough required
                # materials, we need to mouse to a grapes sprite in our inventory
                # (without worrying about closing the bank window) to then combine it
                # with a jug of water.
                if "inv_coord" not in locals():
                    inv_coord = self.mouse_to_grapes()
                self.log_msg("Preparing to make wine...")
                self.combine_grapes_and_h2o(inv_coord)  # Pre-positioned over grapes.
                self.make_wine()
            self.update_progress((time.time() - start_time) / end_time)
            self.logout_if_greater_than(dt=self.relog_time, start=start_time)
        self.update_progress(1)
        self.logout_and_stop_script("[END]")

    @property
    def has_req_mats(self) -> bool:
        """Check if there is at least 1 (grape, jug of water) pair in the inventory.

        Returns:
            bool: True if materials for at least one jug of wine are available,
                otherwise False.
        """
        has_grapes = self.is_item_in_inv(
            png="grapes.png", folder="wine_maker", confidence=0.12
        )
        has_jugs_h2o = self.is_item_in_inv(
            png="jug-of-water.png", folder="wine_maker", confidence=0.06
        )
        return bool(has_grapes and has_jugs_h2o)

    @property
    def wine_menu_open(self) -> bool:
        """Determine whether the wine making menu is showing in the chat box area.

        For improved performance, that this check uses OCR rather than template
        matching a button or menu frame.

        Returns:
            bool: True if the wine making menu is showing, False otherwise.
        """
        textboxes = ocr.find_textbox(
            text=["How many", "do you wish", "to make?"],
            rect=self.win.chat,
            font=ocr.BOLD_12,
            colors=self.cp.bgr.OFF_BROWN_TEXT,
        )
        return bool(textboxes)

    @property
    def num_jugs_wine(self) -> int:
        return self.get_num_item_in_inv(
            png="jug-of-wine.png",
            folder="wine_maker",
            confidence=0.06,
        )

    def get_14_grapes_14_jugs_h2o(self) -> bool:
        """Withdraw 14 grapes and 14 jugs of water from the bank.

        Returns:
            bool: True if the items were successfully withdrawn, False otherwise.
        """
        self.log_msg("Searching for wine-making materials...")
        grapes = self.find_sprite(
            win=self.win.game_view,
            png="grapes-bank.png",
            folder="wine_maker",
            confidence=0.12,
        )
        jugs_h2o = self.find_sprite(
            win=self.win.game_view,
            png="jug-of-water-bank.png",
            folder="wine_maker",
            confidence=0.06,
        )
        if not (grapes and jugs_h2o) and not self.has_req_mats:
            self.log_msg("Out of required materials. Logging out.")
            self.close_bank()
            self.logout_and_stop_script("[END]")
        msg = "Required materials found. Withdrawing grapes and jugs of water..."
        self.log_msg(msg, overwrite=True)
        req_mats = {"grapes": grapes, "jugs of water": jugs_h2o}
        for i, (name, material) in enumerate(req_mats.items()):
            mouse_speed = "fast" if i == 0 else "fastest"  # Speed optimization.
            self.mouse.move_to(material.random_point(), mouseSpeed=mouse_speed)
            self.mouse.click()
            self.log_msg(f"Withdrew 14 {name}.")
        return self.is_inv_full()

    def mouse_to_grapes(self) -> Tuple[int]:
        """Inventory open, mouse to a grapes sprite that borders a jug of water.

        Note that this method assumes grapes and jugs of water are guaranteed present
        in our inventory.

        Returns:
            Tuple[int]: The inventory slots indices for the associated grapes and jug
                of water respectively. Defaults to (12, 13) if sprites could not be
                found.
        """
        timeout = 20  # There is latency when withdrawing items, hence the retry logic.
        grapes_inds = None
        attempts = 0
        start = time.time()
        while not grapes_inds and (time.time() - start) < timeout:
            grapes_inds = self.get_inv_item_slots(png="grapes.png", folder="wine_maker")
            attempts += 1
        _s = "s" if attempts else ""
        self.log_msg(f"Sprite found: grapes ({attempts} attempt{_s})")
        # Match water jugs with a low `confidence` to avoid confusion with wine jugs.
        jug_h2o_inds = None
        attempts = 0
        start = time.time()
        while not jug_h2o_inds and (time.time() - start) < timeout:
            jug_h2o_inds = self.get_inv_item_slots(
                png="jug-of-water.png", folder="wine_maker", confidence=0.06
            )
            attempts += 1
        _s = "s" if attempts else ""
        self.log_msg(f"Sprite found: jug of h2o ({attempts} attempt{_s})")
        pref_pairs = [(12, 16), (9, 14), (10, 14), (13, 14), (13, 17)]
        random.shuffle(pref_pairs)
        try:
            chosen_grapes_ind, chosen_jug_h2o_ind = grapes_inds[0], jug_h2o_inds[0]
        except IndexError:
            msg = (
                "Failed to identify grapes-jug-of-h2o pair. Using (12, 13) and"
                " hoping for the best."
            )
            self.log_msg(msg)
            return (12, 13)
        for pair in pref_pairs:
            grapes_ind, jug_h2o_ind = pair
            if grapes_ind in grapes_inds and jug_h2o_ind in jug_h2o_inds:
                chosen_grapes_ind, chosen_jug_h2o_ind = grapes_ind, jug_h2o_ind
        self.mouse.move_to(self.win.inventory_slots[chosen_grapes_ind].random_point())
        self.log_msg("Moused to grapes.")
        # Having moused into our inventory, we are now guaranteed not hovering a bank.
        self.hovering_bank = False
        return (grapes_ind, chosen_jug_h2o_ind)

    def combine_grapes_and_h2o(self, inv_coord: Tuple[int]) -> None:
        """Combine grapes and a jug of water in our inventory to prompt wine making.

        In other words, combine ingredients and cause a wine-making crafting menu to
        appear in the chat area.

        We assume the mouse is pre-positioned over the grapes sprite from a previous
        call of `mouse_to_grapes`, but we move the mouse again if we fail to open the
        wine-making menu.

        Args:
            inv_coord (Tuple[int]): The indices corresponding to the inventory slots to
                click to prompt wine-making. The first is the slot for the grapes; the
                second for the jug of water.
        """
        grapes_ind, jug_h2o_ind = inv_coord
        attempt_num = 0
        self.log_msg("Combining grapes with jug of water...")
        while not self.wine_menu_open:
            if attempt_num > 0:  # Move the mouse if the first attempt failed.
                self.mouse.move_to(
                    self.win.inventory_slots[grapes_ind].random_point(),
                    mouseSpeed="fastest",
                )
            self.mouse.click()
            self.mouse.move_to(
                self.win.inventory_slots[jug_h2o_ind].random_point(),
                mouseSpeed="fastest",
            )
            self.log_msg("Moused to jug of h2o.")
            self.mouse.click()
            attempt_num += 1
            time.sleep(2 * self.game_tick)
        _s = "s" if attempt_num > 1 else ""
        msg = f"Grapes combined with jug of water ({attempt_num} attempt{_s})."
        self.log_msg(msg, overwrite=True)
        self.sleep()

    def make_wine(self) -> None:
        """With the wine-making prompt open, press space to begin making wine."""
        while self.wine_menu_open:  # Built-in redundancy for reliability.
            pag.press("space", presses=2, interval=rd.biased_trunc_norm_samp(0.1, 0.3))
            self.sleep()
        self.log_msg("Making wine...")
        msg = "Mousing to bank while making wine to save time..."
        self.log_msg(msg, overwrite=True)
        self.sleep(0.5, 0.7)
        self.hovering_bank = self.find_and_mouse_to_bank()
        # The instant we no longer have the required materials, stop making wines.
        timeout = 20  # It shouldn't take longer than 20s to make 14 jugs of wine.
        start = time.time()
        while self.has_req_mats and (time.time() - start < timeout):
            time.sleep(self.game_tick)
        # If we became idle while we still have materials to keep wine-making, maybe we
        # leveled up, so we'll have to restart our wine-making.
        if self.num_jugs_wine != 14:
            self.log_msg("Wine making unexpectedly interrupted. Resuming...")
            if self.has_req_mats:
                inv_coord = self.mouse_to_grapes()
                self.combine_grapes_and_h2o(inv_coord)
                self.make_wine()
        self.log_msg("Wines made.", overwrite=True)

    def report_status(self) -> None:
        """Update the log with a running tally of profit and item volume."""
        profit_per_item = self.get_price(iid.JUG_OF_WINE) or 3
        gp_amt = self.wines_bankd * profit_per_item
        gp_shorthand = self.get_shorthand_gp_value(gp_amt)
        _s = "" if self.invs_bankd == 1 else "s"
        msg = (
            f"Jugs of wine deposited: {self.wines_bankd} over"
            f" {self.invs_bankd} trip{_s} ({gp_shorthand} gp profit)"
        )
        self.log_msg(msg)
