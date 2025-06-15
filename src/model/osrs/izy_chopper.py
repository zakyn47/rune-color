import re
import time
from typing import List

import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from utilities.geometry import RuneLiteObject
from utilities.img_search import BOT_IMAGES


class IzyChopper(OSRSBot):
    def __init__(self):
        bot_title = "izy chopper"
        description = (
        """click nearest cyan-tagged object, then wait for time specified in click_interval, then click it again.
        \n\n
        Bot designed for early game skilling, such as woodcutting, fishing, mining or combat @ goblins"""
        )
        super().__init__(bot_title=bot_title, description=description)
        self.run_time = 60 * 10  # Measured in minutes
        self.take_breaks = False
        self.break_max = 15  # Measured in seconds.
        self.click_interval = 5  # Measured in seconds.
        self.skip_first_row = False  # If True, we skip the first row when dropping logs.
        self.options_set = True  # If True, we use the above defaults.
        self.relog_time = rd.biased_trunc_norm_samp(
            18000, 21000
        )  # Secs before relogging.

        self.mark_color = self.cp.hsv.CYAN_MARK  # Color of the marked objects
        self.logs_dropped = 0  # Number of logs dropped.
        self.failed_searches = 0  # Number of times we failed to find another tree.
        self.num_considerations = 0  # Num of times we considered switching targets.

    def create_options(self) -> None:
        """Add bot options. See `utilities.options_builder` for more."""
        self.options_builder.add_slider_option(
            "run_time", "How long to run (minutes)?", 1, 600
        )
        self.options_builder.add_checkbox_option(
            "take_breaks", "Take breaks?", [" "]
        )
        self.options_builder.add_slider_option("click_interval", "Click interval (secs)?", 1, 20)
        self.options_builder.add_checkbox_option("skip_first_row", "Skip dropping first inventory row?", [" "])

    def save_options(self, options: dict) -> None:
        """Load options into the bot object.

        Adjust this definition to mirror the options in `create_options`. These two
        functions are called during the setup of the bot controller.

        Args:
            options (dict): A dictionary of options (`customtkinter` widgets) as values
                and their corresponding option names as keys.
        """
        for option in options:
            if option == "run_time":
                self.run_time = int(options[option])
            elif option == "take_breaks":
                self.take_breaks = options[option] != []
            elif option == "click_interval":
                self.click_interval = int(options[option])
                if self.click_interval < 1:
                    self.log_msg("Click interval must be at least 1 second.", overwrite=True)
                    self.options_set = False
                    return
            elif option == "skip_first_row":
                self.skip_first_row = options[option] != []
            else:
                self.log_msg(f"Unknown option: {option}")
                self.options_set = False
                return

        self.log_msg(f"[RUN TIME] {self.run_time} MIN", overwrite=True)
        break_time_str = f"(MAX {self.break_max}s)" if self.take_breaks else ""
        self.log_msg(f"  [BREAKS] {str(self.take_breaks).upper()} {break_time_str}")
        self.log_msg(f"[CLICK INTERVAL] {self.click_interval} SECONDS")
        self.log_msg(f"[SKIP FIRST ROW] {str(self.skip_first_row).upper()}")
        self.options_set = True
        self.log_msg("Options set successfully.")

    def main_loop(self):
        """click nearest cyan-tagged object, then wait for time specified in
        click_interval, then click it again.
        """
        run_time_str = f"{self.run_time // 60}h {self.run_time % 60}m"
        self.log_msg(f"[START] ({run_time_str})", overwrite=True)
        start_time = time.time()
        end_time = int(self.run_time) * 60  # Measured in seconds.
        while time.time() - start_time < end_time:
            if self.take_breaks:
                self.potentially_take_a_break()
                self.potentially_relog_with_delayed_login(prob=0.001, wait_time=rd.biased_trunc_norm_samp(100, 5000))
            if self.is_inv_full():
                if self.skip_first_row:
                    self.drop_all_items(skip_slots=[0, 1, 2, 3])
                else:
                    self.drop_all_items()
            self.mouse_to_nearby_object(second_closest=False)
            self.mouse.click()
            if self.is_active:
                countdown = int(self.click_interval)
                while countdown > 0:
                    self.log_msg(f"Waiting: {countdown} seconds...", overwrite=True)
                    time.sleep(1)
                    countdown -= 1
                    if countdown == 0:
                        self.log_msg("clicking nearby object", overwrite=True)
                        continue
            self.update_progress((time.time() - start_time) / end_time)
            self.logout_if_greater_than(dt=self.relog_time, start=start_time)
        self.update_progress(1)
        self.logout_and_stop_script("[END]")

    @property
    def is_active(self) -> bool:
        """Whether our character is actively chopping wood.

        Returns:
            bool: True if our character is doing something, False otherwise.
        """
        is_idle = self.check_idle_notifier_status("is_idle")
        stopped_moving = self.check_idle_notifier_status("stopped_moving")
        non_active_statuses = [is_idle, stopped_moving]
        return all(not status for status in non_active_statuses)

    def mouse_to_nearby_object(self, second_closest: bool = False) -> bool:
        """Move the cursor to the nearest tree (or second-nearest).

        Note that if `second_closest` is True and a second-closest tree does not exist,
        this method will return False.

        Args:
            second_closest (bool, optional): If True, will move the cursor to the object
                second-nearest to our character's location (if such exists),
                False otherwise.

        Returns:
            bool: True if the mouse moved to a nearby object, False otherwise.
        """
        if objects := self.find_colors(self.win.game_view, self.mark_color):
            if second_closest and len(objects) < 1:
                return False
            objects = sorted(objects, key=RuneLiteObject.dist_from_rect_center)
            chosen_object = objects[1] if second_closest else objects[0]
            self.mouse.move_to(chosen_object.random_point(),mouse_speed="fastest")
            order = "second-closest" if second_closest else "closest"
            self.log_msg(f"Moused to {order} object.")
            return True
        self.log_msg("Could not detect new objects.")
        return False