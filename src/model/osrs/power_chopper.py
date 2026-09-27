import re
import time
from typing import List, Tuple

import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from utilities.geometry import Point, RuneLiteObject
from utilities.img_search import BOT_IMAGES
from utilities.walker import Walker


class OSRSPowerChopper(OSRSBot):
    def __init__(self):
        bot_title = "Power Chopper"
        description = (
            "Chop trees, get a full inventory of logs, burn them in a fire, then"
            " repeat."
        )
        super().__init__(bot_title=bot_title, description=description)
        self.run_time = 60 * 10  # Measured in minutes (default 10 hours).
        self.take_breaks = False
        self.break_max = 15  # Measured in seconds.
        self.options_set = True  # If True, we use the above defaults.
        self.relog_time = rd.biased_trunc_norm_samp(
            18000, 21000
        )  # Secs before relogging.

        self.mark_color = self.cp.hsv.CYAN_MARK  # Color of the marked trees.
        # Inventory slot index of the tinderbox. Assumed fixed since tinderboxes
        # aren't consumed and nothing earlier in the inventory gets added/removed.
        self.tinderbox_slot = 1
        # Lighting a fire steps our character back a tile, so a run of failed lights
        # usually means we've backed into a wall and have nowhere left to burn.
        self.max_failed_lights = 3
        self.walker = Walker(self, dest_square_side_length=4)
        self.logs_dropped = 0  # Number of logs dropped.
        self.logs_burned = 0  # Number of logs burned.
        self.failed_searches = 0  # Number of times we failed to find another tree.
        self.num_considerations = 0  # Num of times we considered switching targets.
        self.woodcut_keywords = ["tree", "Chop", "Tree", "Chop down"]

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
            else:
                self.log_msg(f"Unknown option: {option}")
                self.options_set = False
                return

        self.log_msg(f"[RUN TIME] {self.run_time} MIN", overwrite=True)
        break_time_str = f"(MAX {self.break_max}s)" if self.take_breaks else ""
        self.log_msg(f"  [BREAKS] {str(self.take_breaks).upper()} {break_time_str}")
        self.options_set = True
        self.log_msg("Options set successfully.")

    def main_loop(self):
        """Chop marked trees, gather logs, burn them upon full inventory, and repeat.

        Run the main game loop.
            1. Travel to a marked tree and chop it.
            2. Continue the chop the tree, gathering logs, until it disappears.
            3. Repeat steps 1 and 2 until our inventory is full.
            4. Light a fire with the tinderbox and burn all logs in our inventory.

        For this to work as intended:
            1. Our character must begin next to a grove of color-marked trees. The
                trees must be marked as a specific color (e.g. `self.cp.hsv.CYAN_MARK`)
                as defined in `utilities.api.colors_hsv`. Objects are intended to be
                marked with the Object Markers RuneLite plug-in.
            2. Our inventory should be relatively empty.
            3. Screen dimmers like F.lux or Night Light on Windows should be disabled
                since our bot is highly sensitive to colors.
        """
        run_time_str = f"{self.run_time // 60}h {self.run_time % 60}m"
        self.log_msg(f"[START] ({run_time_str})", overwrite=True)
        self.prepare_standard_initial_state()
        start_time = time.time()
        end_time = int(self.run_time) * 60  # Measured in seconds.
        while time.time() - start_time < end_time:
            if self.take_breaks:
                self.potentially_take_a_break()
            if self.is_inv_full():
                self.burn_all_logs()
            self.resume_chopping()
            self.update_progress((time.time() - start_time) / end_time)
            self.logout_if_greater_than(dt=self.relog_time, start=start_time)
        self.update_progress(1)
        self.logout_and_stop_script("[END]")

    @property
    def is_hovering_tree(self) -> bool:
        """Whether the cursor is actively hovering over a tree.

        Returns:
            bool: True if the mouse cursor is hovering over a tree, False otherwise.
        """
        return self.get_mouseover_text(contains=self.woodcut_keywords)

    @property
    def is_active(self) -> bool:
        """Whether our character is actively chopping wood.

        Returns:
            bool: True if our character is presumed chopping wood, False otherwise.
        """
        is_idle = self.check_idle_notifier_status("is_idle")
        stopped_moving = self.check_idle_notifier_status("stopped_moving")
        non_active_statuses = [is_idle, stopped_moving]
        return all(not status for status in non_active_statuses)

    @property
    def is_harvesting(self) -> bool:
        """Whether we are chopping, gathering, or sitting with a full inventory.

        Returns:
            bool: True if we are chopping, gathering, or have a full inventory, False
                otherwise.
        """
        texts_to_match = {
            # You swing your axe at the tree.
            "start_chop": r"^You\w*swing\w*tree$",
            # You get some <tree_type> logs.
            "gather_logs": r"^Yougetsome\w*logs$",
            # Your inventory is too full to hold any more <tree_type> logs.
            "inv_full": r"^You\w*inventory\w*full\w*logs$",
        }
        chat_history = self.get_chat_history()
        first_line = chat_history[0]
        for label, pattern in texts_to_match.items():
            if re.search(pattern, first_line):
                msg = "Resumed harvesting."
                if label == "start_chop":
                    self.log_msg(f"{msg} Axe confirmed swinging.", overwrite=True)
                elif label == "gather_logs":
                    self.log_msg(f"{msg} Confirmed gathering logs.", overwrite=True)
                elif label == "inv_full":
                    self.log_msg(f"{msg} Inventory is confirmed full.", overwrite=True)
                return True
        return False

    def mouse_to_nearby_tree(self, second_closest: bool = False) -> bool:
        """Move the cursor to the nearest tree (or second-nearest).

        Note that if `second_closest` is True and a second-closest tree does not exist,
        this method will return False.

        Args:
            second_closest (bool, optional): If True, will move the cursor to the tree
                second-nearest to our character's location (if such a tree exists),
                False otherwise.

        Returns:
            bool: True if the mouse moved to a nearby tree, False otherwise.
        """
        if trees := self.find_colors(self.win.game_view, self.mark_color):
            if second_closest and len(trees) < 2:
                return False
            trees = sorted(trees, key=RuneLiteObject.dist_from_rect_center)
            chosen_tree = trees[1] if second_closest else trees[0]
            self.mouse.move_to(chosen_tree.random_point())
            if self.is_hovering_tree:
                order = "second-closest" if second_closest else "closest"
                self.log_msg(f"Moused to {order} tree.", overwrite=True)
                return True
        self.log_msg("Could not detect new trees.", overwrite=True)
        return False

    def potentially_mouse_to_second_closest_tree(self, prob_move_cursor: float) -> bool:
        """Potentially move the mouse to the second-closest tree next to us.

        Args:
            prob_move_cursor (float): The probability of moving the tree second-closest
                to our current location.

        Returns:
            bool: True if we moused to the second-closest tree, False otherwise.
        """
        if rd.random_chance(prob_move_cursor):
            prob_second_closest = rd.trunc_norm_samp(0.50, 0.60)
            if rd.random_chance(prob_second_closest):
                return self.mouse_to_nearby_tree(second_closest=True)
        return False

    def get_log_slots(self) -> List[int]:
        """Get inventory slots filled with logs of any type.

        Returns:
            List[int]: A list of inventory slots (0 to 27) filled with logs of any type.
        """
        sprite_folder = BOT_IMAGES / "power_chopper"
        logs_sprites = [
            sprite.name
            for sprite in sprite_folder.iterdir()
            if sprite.is_file() and sprite.name.lower().endswith("logs.png")
        ]
        log_slots = []
        for sprite in logs_sprites:
            log_slots += self.get_inv_item_slots(png=sprite, folder=sprite_folder)
        return log_slots

    def drop_all_logs(self) -> bool:
        """Drop all logs from our character's inventory.

        This function relies on the shift-click drop ingame setting being enabled.

        Returns:
            bool: True if the logs were successfully dropped, False otherwise.
        """
        log_slots = self.get_log_slots()
        traversal = self.get_inv_drop_traversal_path()
        log_slots = [slot for slot in traversal if slot in log_slots]
        _s = "s" if len(log_slots) > 1 else ""
        self.log_msg(f"Dropping {len(log_slots)} log{_s}...")
        if log_slots:
            self.drop_items(slots=log_slots)
            self.logs_dropped += len(log_slots)
            self.log_msg(f"Dropped {self.logs_dropped} log{_s} so far.", overwrite=True)
            return True
        self.log_msg("Failed to drop logs.")
        return False

    def count_logs(self) -> int:
        """Count the logs of any type in our character's inventory.

        Returns:
            int: The number of inventory slots filled with logs.
        """
        return len(set(self.get_log_slots()))

    def light_fire(self, log_slot: int, timeout: float = 4) -> bool:
        """Use the tinderbox on the given log slot to burn it on a fresh fire.

        Note that the two clicks must land in quick succession - the "use" selection
        on the tinderbox expires quickly, and if a second or more passes before the
        log is clicked, the combination silently fails to register.

        Success is measured by the log's own slot emptying rather than by spotting a
        fire on screen. Detecting a fire by its color is unreliable, as stray orange
        pixels scattered around the scene read as a fire even when nothing at all is
        lit. Watching the single slot rather than recounting every log also keeps this
        cheap enough to poll quickly, since counting the whole inventory means
        matching every log sprite against all 28 slots each time round.

        Args:
            log_slot (int): The inventory slot index of the log to burn.
            timeout (float, optional): Seconds to wait for the log to be consumed
                before giving up. Defaults to 4, which is generous next to the half
                second a successful light actually takes. A light either works almost
                at once or not at all, so waiting longer only slows down the retry.

        Returns:
            bool: True if the log was consumed, False otherwise.
        """
        if self.is_inv_slot_empty(log_slot):
            return False  # Nothing in that slot to burn.
        self.mouse.move_to(self.win.inventory_slots[self.tinderbox_slot].random_point())
        self.mouse.click()
        self.mouse.move_to(self.win.inventory_slots[log_slot].random_point())
        self.mouse.click()
        end_time = time.time() + timeout
        while time.time() < end_time:
            # Look before sleeping. A log leaves its slot about half a second after
            # the clicks land, so waiting first would sit through a burn that has
            # already happened.
            #
            # Confirm on a second look before trusting it. A slot can read as empty
            # for a frame while it redraws, and one such read is not a burn.
            if self.is_inv_slot_empty(log_slot) and self.is_inv_slot_empty(log_slot):
                return True
            self.sleep(0.15, 0.3)
        return False

    def return_to_grove(self, world_point: Tuple[int, int, int]) -> bool:
        """Walk back to the world point our character started burning from.

        Lighting a fire steps our character back a tile, so burning a full inventory
        walks it a good distance from the trees it was chopping. Left alone it ends up
        with no marked trees in the game view at all and nothing left to harvest.

        Args:
            world_point (Tuple[int, int, int]): The (x, y, plane) world point to walk
                back to, as returned by `get_world_point`.

        Returns:
            bool: True if we made it back, False otherwise.
        """
        x, y, _ = world_point
        if x == -1:  # `get_world_point` couldn't read the tile overlay.
            return False
        if self.get_world_point()[:2] == (x, y):
            return True
        self.log_msg("Returning to the trees...")
        try:
            return self.walker.walk_to(Point(x, y))
        except Exception as exc:
            # Pathfinding is a network call, and `walk` indexes an empty path when the
            # API gives nothing back. Losing our way back isn't worth crashing over.
            self.log_msg(f"Could not walk back to the trees: {exc}")
            return False

    def burn_all_logs(self) -> bool:
        """Burn every log in our character's inventory, one fire per log.

        Note that logs cannot be added to a fire that is already burning. Using a log
        on a lit fire does nothing at all, so each log gets its own fresh fire.

        Returns:
            bool: True if at least one log was burned, False otherwise.
        """
        log_slots = sorted(set(self.get_log_slots()))
        if not log_slots:
            self.log_msg("No logs to burn.")
            return False
        _s = "s" if len(log_slots) > 1 else ""
        self.log_msg(f"Burning {len(log_slots)} log{_s}...")
        # Where the trees are, to come back to. Read this properly: one bad
        # read here means never walking back at all.
        grove = self.get_world_point_reliably()
        failed_lights = 0
        for slot in log_slots:
            if self.light_fire(slot):
                failed_lights = 0
                continue
            # Stepping back a tile per fire walks our character into its own fires
            # and whatever else is behind it, and it can't light one where it stands.
            # Move somewhere clear and give the same log another try before counting
            # it against us.
            self.walk_to_random_point_nearby(verbose=False)
            if self.light_fire(slot):
                failed_lights = 0
                continue
            failed_lights += 1
            if failed_lights >= self.max_failed_lights:
                self.log_msg(
                    f"Failed to light {failed_lights} fires in a row. Stopping burn."
                )
                break
        # Count what actually left the inventory rather than how many lights we
        # believe succeeded, so the tally can't drift above the truth.
        burned = len(log_slots) - self.count_logs()
        self.logs_burned += burned
        self.return_to_grove(grove)
        if not burned:
            self.log_msg("Failed to burn any logs.")
            return False
        self.log_msg(f"Burned {self.logs_burned} logs so far.", overwrite=True)
        return True

    def resume_chopping(self) -> bool:
        """Mouse to a nearby tree and resume harvesting.

        Returns:
            bool: True if a nearby tree was found and chopping was resumed, False if a
                tree could not be found (and thus chopping could not resume).
        """
        start = time.time()
        timeout = 120
        phi = -10
        self.log_msg("Searching for new trees...")
        while not self.mouse_to_nearby_tree():
            if self.failed_searches % 2 == 0:
                self.search_with_camera(phi=phi)
            elif self.failed_searches % 100 == 0:
                self.walk_to_random_point_nearby(verbose=True)
            elif self.failed_searches % 250 == 0:
                self.zoom(out=True, verbose=False)
                self.reset_minimap_zoom()
            self.failed_searches += 1
            if (time.time() - start) >= timeout:
                msg = "Unable to continue harvesting. Logging out."
                self.logout_and_stop_script(msg)
                return False
            if self.failed_searches % 9 == 0:
                phi *= -1
            msg = f"Searching for new trees... ({self.failed_searches})"
            self.log_msg(msg, overwrite=True)
            time.sleep(self.game_tick)
        self.failed_searches = 0
        if self.is_hovering_tree:
            self.log_msg("Attempting to resume harvesting...")
            self.mouse.click()
            self.sleep()
            self.mouse.click()
            while self.is_traveling():
                self.sleep(4, 5)
            if self.is_harvesting:
                self.num_considerations = 1
                # `is_harvesting` reads the top chat line, which never expires on its
                # own (nothing overwrites it once the tree despawns and we go idle).
                # Without a cap this loop can never exit on a stale positive, so it
                # never returns control to `main_loop` to check the inventory or
                # search for a new tree. 90s is comfortably longer than a single
                # regular tree takes to deplete at low Woodcutting levels.
                harvest_start = time.time()
                harvest_timeout = 90
                while self.is_harvesting:
                    if time.time() - harvest_start >= harvest_timeout:
                        self.log_msg("Harvesting timeout reached. Reassessing.")
                        break
                    prob_move_cursor = 0.10 / (2 * self.num_considerations)
                    self.potentially_mouse_to_second_closest_tree(prob_move_cursor)
                    self.num_considerations += 1
                    self.sleep(0.6, 1.2)  # Pace to roughly a game tick or two.
                return True
        return False
