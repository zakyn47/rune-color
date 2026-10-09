import time
from typing import Callable, Optional

import model.osrs.cow_fighter_rules as rules
import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from utilities.api.bridge_api import GroundItem, SceneObject, Tile
from utilities.geometry import Point
from utilities.walker import Walker

BRIDGE_TIMEOUT = 5  # Seconds to wait for the plug-in to be heard from.
ATTACK_TRIES = 3  # Cows to try before looking elsewhere.
AIM_PASSES = 2  # Aim, then correct for where the cow walked meanwhile.
ATTACK_TIMEOUT = 5  # Seconds for a clicked cow to become our target.
KILL_TIMEOUT = 60
LOOT_APPEAR_TIMEOUT = 3  # Drops appear a tick or two after the death.
TAKE_TIMEOUT = 5  # Includes walking to the item.
BURY_TIMEOUT = 3
OPEN_TIMEOUT = 5  # Seconds for a clicked gate to swing open.
GATE_AIM_TRIES = 4
WALK_TIMEOUT = 60  # A walk this long is stuck, most likely at the closed gate.
HOME_SQUARE = 4  # Tiles; arriving anywhere in this square around home will do.
MAX_TAKES = 5  # Bounds the loot loop if an item can never be taken.


class OSRSCowFighter(OSRSBot):
    runelite_profile = "cow_fighter"

    def __init__(self) -> None:
        bot_title = "Cow Fighter"
        description = (
            "Kill cows, take the bones they drop, bury them once the inventory is"
            " full, and repeat. Stays near where it starts, walking back (and opening the field's"
            " west gate) if it drifts away. Hitpoints are not watched.\n\n"
            "Setup:\n"
            "- Stand in the cow field east of the River Lum, north of Lumbridge castle.\n"
            "- Empty inventory; wield a weapon if you have one.\n"
            "- The bot aims with the plug-in's live positions.\n"
            "- Requires the RuneColor Bridge plug-in (plugin/README.md).\n"
            "- Stretched Mode off, Resizable - Classic layout."
        )
        super().__init__(bot_title=bot_title, description=description)
        self.run_time = 60  # Measured in minutes.
        self.take_breaks = False
        self.relog_time = rd.biased_trunc_norm_samp(18000, 21000)
        self.death_tile: Optional[Tile] = None
        self.home: Optional[Tile] = None
        self.kills = 0
        self.bones_buried = 0
        self.bones_taken = 0

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
        # Not the inventory: the game never sends an empty one.
        if not self._wait_until(self.bridge_is_heard, BRIDGE_TIMEOUT):
            self.log_msg(
                "The Cow Fighter needs the RuneColor Bridge plug-in. Turn it on"
                " in RuneLite and try again."
            )
            self.stop()
            return
        self.log_msg(f"[START] ({self.run_time // 60}h {self.run_time % 60}m)")
        self.prepare_standard_initial_state()
        self.home = self.home or self.bridge.world_point
        if rules.far_from(self._here(), self.home):
            self.walk_home()
        start_time = time.time()
        end_time = int(self.run_time) * 60
        while time.time() - start_time < end_time:
            if self.take_breaks:
                self.potentially_take_a_break()
            self.loot()
            self.bury_when_full()
            self.fight()
            self.update_progress((time.time() - start_time) / end_time)
            self.logout_if_greater_than(dt=self.relog_time, start=start_time)
        self.update_progress(1)
        self.log_msg(
            f"Killed {self.kills} cows, took {self.bones_taken} bones and buried"
            f" {self.bones_buried}."
        )
        self.logout_and_stop_script("[END]")

    def bridge_is_heard(self) -> bool:
        return self.bridge is not None and bool(self.bridge.game_state)

    def fight(self) -> None:
        """Attack a cow unless one is already our target, then see it die."""
        if self.bridge.target is None and not self.attack():
            return
        self.wait_for_kill()

    def attack(self) -> bool:
        """Click the nearest cow that nobody else is fighting.

        Cows wander, so a colour scan of the screen is out of date by the time the
        cursor arrives. The plug-in reports where each one is every tick, and the
        cursor follows the chosen cow by its index until the hover text confirms.

        Returns:
            bool: True once the cow is our target.
        """
        for _ in range(ATTACK_TRIES):
            candidates = [
                npc
                for npc in rules.attack_candidates(self.bridge.npcs)
                if self.is_in_game_view(Point(*npc.point))
            ]
            if not candidates:
                self.stay_home()
                return False
            if not self.aim_at(candidates[0].index):
                continue
            if not self.wait_for_hover_text("Attack"):
                continue
            self.mouse.click()
            if self._wait_until(lambda: self.bridge.target is not None, ATTACK_TIMEOUT):
                return True
        return False

    def stay_home(self) -> None:
        """With no free cow in view, go back if we drifted away, or wait for one.

        Clicking somewhere at random to find cows walked the bot out of the field and,
        once, into a fight with a Man in the farmhouse.
        """
        if rules.far_from(self._here(), self.home):
            self.log_msg("Drifted away from the cows. Walking back...")
            self.walk_home()
            return
        self.sleep(1, 2)

    def walk_home(self) -> None:
        """Walk back to the home tile, opening the field gate if it blocks the way."""
        walker = Walker(self, dest_square_side_length=HOME_SQUARE)
        home = Point(self.home[0], self.home[1])
        if walker.walk_to(home, host="dax", timeout=WALK_TIMEOUT):
            return
        if self.open_gate():
            walker.walk_to(home, host="dax", timeout=WALK_TIMEOUT)

    def open_gate(self) -> bool:
        """Open the field gate if it is closed within reach.

        Returns:
            bool: True once it swung open.
        """
        self.bridge.request_objects(rules.GATE_CLOSED)
        try:
            self._wait_until(self.visible_objects, self.game_tick * 3)
            gates = [
                g for g in self.visible_objects() if g.distance <= rules.GATE_REACH
            ]
            if not gates:
                return False
            if not self._aim_at_gate(gates[0]):
                return False
            self.mouse.click()
            return self._wait_until(lambda: not self.visible_objects(), OPEN_TIMEOUT)
        finally:
            self.bridge.clear_objects()

    def _aim_at_gate(self, gate: SceneObject) -> bool:
        """Point at the gate until the hover text reads Open.

        Its outline is the convex hull of thin planks, so a random point inside it
        can land on the gap between them; another point usually hits.
        """
        for _ in range(GATE_AIM_TRIES):
            self.move_to_scene_object(gate)
            if self.wait_for_hover_text("Open"):
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
                # disappears walked off or was taken by someone else. And only a cow:
                # anything else was clicked by mistake.
                if target is not None and target.name == rules.TARGET_NAME:
                    self.kills += 1
                    self.death_tile = last_tile
                    self.log_msg(f"Killed a {target.name} ({self.kills} so far).")
                return
            time.sleep(self.game_tick / 3)

    def loot(self) -> None:
        """Take the bones our last kill dropped."""
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
        if not self._aim_at_item(item):
            menu = self.bridge.menu
            seen = menu.top_text if menu is not None else "nothing"
            self.log_msg(f"Aimed at the {item.name}, but the cursor reads {seen!r}.")
            return False
        self.mouse.click()
        if not self._wait_until(lambda: self.bridge.inventory != before, TAKE_TIMEOUT):
            return False
        self.bones_taken += 1
        return True

    def _aim_at_item(self, item: GroundItem) -> bool:
        """Point at an item until the hover text reads Take, aiming twice at most.

        The item's screen point comes from a snapshot, and the camera follows us, so
        if we were still moving the item has since slid across the screen.
        """
        for _ in range(AIM_PASSES):
            self.mouse.move_to(Point(*item.point))
            if self.wait_for_hover_text("Take"):
                return True
            item = next(
                (
                    i
                    for i in self.bridge.ground_items
                    if i.id == item.id and i.tile == item.tile
                ),
                None,
            )
            if item is None:
                return False
        return False

    def bury_when_full(self) -> None:
        """Bury the bones we carry, but only once the inventory has no room left."""
        if rules.is_full(self.bridge.inventory):
            self.bury()

    def bury(self) -> None:
        """Bury every bone in the inventory."""
        rects = self.bridge.inventory_slots or self.win.inventory_slots
        for slot in rules.bone_slots(self.bridge.inventory):
            self.mouse.move_to(rects[slot].random_point())
            self.mouse.click()
            if self._wait_until(
                lambda: self._slot_item(slot) != rules.BONES, BURY_TIMEOUT
            ):
                self.bones_buried += 1

    def _here(self) -> Optional[Tile]:
        here = self.bridge.world_point
        return None if here[0] < 0 else here

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
