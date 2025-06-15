"""
Note! The Status Socket plug-in has been banned by RuneLite. The code remains here for
legacy purposes.
"""

import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Dict, List, Union

import simplejson as JSON

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path[0] = str(Path(sys.path[0]).parents[1])
    from utilities.mappings import item_ids as iid


PLAYER_DATA = {}  # Global to store data returned from Status Socket RuneLite plug-in.


class RLSTATUS(BaseHTTPRequestHandler):
    """`RLSTATUS` is an HTTP request handler for getting data from the status socket."""

    data_bytes: bytes

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_POST(self):
        global PLAYER_DATA
        self._set_headers()
        self.data_bytes = self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(200)
        self.end_headers()
        PLAYER_DATA = JSON.loads(self.data_bytes)

    def log_message(self, format, *args):
        """Suppress logging."""
        return


class StatusSocket:
    """Establish a socket connection to the Status Socket server for HTTP communication.

    Note that although the OSRS game tick is reported as 0.6s, `gameTick` is set 3
    milliseconds higher to account for variations in server performance or network
    latency.

    Using these endpoints requires the Status Socket plugin in RuneLite. The Status
    Socket RuneLite plug-in exposes an HTTP API on http://localhost:5000 for receiving
    character data.
    """

    gameTick = 0.603  # Fundamental time unit (in seconds) equal to one server cycle.

    def __init__(self) -> None:
        t_server = Thread(target=self.__RSERVER)
        t_server.daemon = True
        t_server.start()
        print("Thread alive:", t_server.is_alive())

    def __RSERVER(self, port: int = 5000):
        try:
            httpd = HTTPServer(("127.0.0.1", port), RLSTATUS)
            httpd.serve_forever()
        except OSError:
            print("Status socket already running.")

    def get_player_data(self):
        """Get a JSON blob of player data."""
        return PLAYER_DATA

    def get_game_tick(self) -> int:
        """Get the game tick.

        The game tick serves as the fundamental time unit within OSRS servers,
        representing the duration of one server cycle. Analogous to a game's frame
        rate, it dictates the pace of in-game events and actions. Data is transmitted
        to the server in discrete chunks accumulated over the duration of a game tick.

        Returns:
            int: Integer representing the game tick.
        """
        return PLAYER_DATA.get("tick")

    def get_real_level(self, skill_name: str) -> int:
        """Get our character's real skill level for a specified skill.

        Args:
            skill_name (str): The UPPERCASE name of the skill to check.

        Returns:
            int: The real skill level, ranging from 0 to 99.

        Example:
            >>> print(api_status.get_real_level("ATTACK"))
            98
        """
        return next(
            (
                skill["realLevel"]
                for skill in PLAYER_DATA.get("skills")
                if skill["skillName"] == skill_name
            ),
            None,
        )

    def get_boosted_level(self, skill_name: str) -> int:
        """Get our character's boosted skill level for a specified skill.

        Args:
            skill_name (str): The UPPERCASE name of the skill to check.

        Returns:
            int: The boosted skill level, potentially exceeding 99.

        Example:
            >>> print(api_status.get_boosted_level("ATTACK"))
            101
        """
        return next(
            (
                skill["boostedLevel"]
                for skill in PLAYER_DATA.get("skills")
                if skill["skillName"] == skill_name
            ),
            None,
        )

    def is_boosted(self, skill_name: str) -> bool:
        """Check if a skill is boosted.

        Args:
            skill_name (str): The UPPERCASE name of the skill to check.

        Returns:
            bool: True if the skill is boosted, False otherwise.

        Example:
            >>> print(api_status.get_is_boosted("ATTACK"))
            True
        """
        real_level = self.get_real_level(skill_name)
        boosted_level = self.get_boosted_level(skill_name)
        if real_level is not None and boosted_level is not None:
            return boosted_level > real_level
        return False

    def get_run_energy(self) -> int:
        """Get our character's current run energy on a scale from 0 to 10000.

        Note that 10000 run energy from this endpoint equates to 100 run energy in game.

        Returns:
            int: The player's current run energy.
        """
        return int(PLAYER_DATA.get("runEnergy"))

    def is_inv_full(self) -> bool:
        """Check if our character's inventory is full.

        Returns:
            bool: True if our character's inventory is full, False otherwise.
        """
        return len(PLAYER_DATA.get("inventory")) >= 28

    def is_inv_empty(self) -> bool:
        """Check if our character's inventory is empty.

        Returns:
            bool: True if our character's inventory is empty, False otherwise.
        """
        return len(PLAYER_DATA.get("inventory")) == 0

    def get_inv(self) -> List[Dict[str, int]]:
        """Get a list of dictionaries representing our character's inventory.

        Returns:
            List[Dict[str, int]]: A list of dictionaries, each containing "index",
                "id", and "amount" keys, with one dictionary for each inventory slot.
        """
        return PLAYER_DATA.get("inventory")

    def get_num_empty_inv_slots(self) -> int:
        return 28 - len(self.get_inv())

    def get_num_full_inv_slots(self) -> int:
        return 28 - len(self.get_inv())

    def get_inv_item_indices(self, item_id: Union[List[int], int]) -> List[int]:
        """Get inventory slot indexes that contain any one of the specified item IDs.

        Args:
            Union[List[int], int] item_id: The item ID(s) to search for.

        Returns:
            List[int]: Inventory slot indexes containing any one of the given item IDs.
        """
        inv = self.get_inv()
        if isinstance(item_id, int):
            return [slot["index"] for slot in inv if slot["id"] == item_id]
        elif isinstance(item_id, list):
            return [slot["index"] for slot in inv if slot["id"] in item_id]

    def get_inv_item_stack_amount(self, item_id: Union[int, List[int]]) -> int:
        """Get the stack size of the first matching item in our character's inventory.

        This method is primarily intended for items that stack (e.g. coins or runes).

        Args:
            item_id (Union[int, List[int]]): The item ID to search for. If a list is
                passed, the first matching item will be used.
        Returns:
            int: The total number of items corresponding to the matched item ID.
        """
        inv = self.get_inv()
        if isinstance(item_id, int):
            item_id = [item_id]
        if result := next((item for item in inv if item["id"] in item_id), None):
            return int(result["amount"])
        return 0

    def is_player_idle(self) -> bool:
        """Check if our character is idle*.

        *Note! This method does not check whether our character is moving, but only
        whether they are performing an action animation (e.g. skilling or combat). If
        you have the option, use `MorgHTTPSocket.get_is_player_idle` instead because
        Morg HTTP Client considers movement animations while Status Socket does not.

        Returns:
            bool: True if our character is idle*, False otherwise.
        """
        start_time = time.time()
        while time.time() - start_time < 0.8:  # 1.33 game ticks.
            if PLAYER_DATA.get("attack").get("animationId") != -1:
                return False
        return True

    def is_player_praying(self) -> bool:
        """Check if our character is currently praying.

        Returns:
            bool: True if our character is praying, False otherwise.
        """
        return bool(PLAYER_DATA.get("prayers"))

    def get_player_equipment(self) -> List[Dict[str, Union[int, str]]]:
        """Get a list of item dictionaries corresponding to currently equipped items.

        Returns:
            List[Dict[str:Union[int, str]]]: A list of dictionaries, each containing
                "index", "id", "amount", and "name" keys, with one dictionary for each
                equipped item, or an empty list if no equipment info is found.
        """
        return PLAYER_DATA.get("equipment") or []

    def get_equipment_stats(self) -> Dict[str, int]:
        """Check current equipment stats.

        Stats returned are "aStab", "aSlash", "aCrush", "aMagic", "aRange",
        "dStab", "dSlash", "dCrush", "dMagic", "dRange", "str", "rStr", and "mDmg".

        Returns:
            Dict[str, int]: Our character's current active equipment stats.
        """
        return PLAYER_DATA.get("equipmentStats")

    def get_animation_data(self) -> Dict[str, Union[None, bool, str, int]]:
        """Get a dictionary of esoteric animation data.

        [TO DEV]: More work needs to be done to clarify what these response keys mean.

        An example response is:
            {'targetName': None, 'isAttacking': False, 'animationName': 'N/A',
             'animationId': -1, 'animationIsSpecial': False,
             'animationAttackStyle': None, 'animationBaseSpellDmg': 0}

        Returns:
            Dict[str: Union[None, bool, str, int]]: Esoteric animation data. An
                "animationId" of -1 indicates a state of idleness (where moving is
                included in the definition of being idle).
        """
        return PLAYER_DATA.get("attack")

    def get_animation_id(self) -> int:
        """Get the animation ID for our character's current animation.

        Returns:
            int: Animation ID for our character's current state. -1 if idle (where
                moving is still considered to be idle).
        """
        return PLAYER_DATA.get("attack").get("animationId")

    def get_world_point(self):
        return PLAYER_DATA.get("worldPoint")

    def get_local_point(self):
        return PLAYER_DATA.get("localPoint")

    def get_camera_position(self):
        return PLAYER_DATA.get("camera")

    def get_core_skills_data(self):
        return PLAYER_DATA.get("skills")


if __name__ == "__main__":
    api_s = StatusSocket()
    if not api_s:
        print("No character found. Is the RuneLite client logged in and active?")
    test_item = iid.DRAGON_AXE
    timeout = 60 * 5
    start = time.time()
    while time.time() - start < timeout:
        api_s.get_player_data()
        time.sleep(api_s.gameTick)
        msg = (
            f"\nGAME TICK: {api_s.get_game_tick()}"
            # f"\nREAL LEVEL: {api_s.get_real_level('STRENGTH')}"
            # f"\nBOOSTED LEVEL: {api_s.get_boosted_level('STRENGTH')}"
            # f"\nIS BOOSTED: {api_s.is_boosted('STRENGTH')}"
            # f"\nRUN ENERGY: {api_s.get_run_energy()}"
            # f"\nIS INV FULL: {api_s.is_inv_full()}"
            # f"\nIS INV EMPTY: {api_s.is_inv_empty()}"
            # f"\nINV: {api_s.get_inv()}"
            # f"\nINV ITEM INDICES ({test_item}): {api_s.get_inv_item_indices(test_item)}"
            # f"\nINV ITEM STACK AMT: {api_s.get_inv_item_stack_amount(test_item)}"
            # f"\nIS IDLE: {api_s.is_player_idle()}"
            # f"\nIS PRAYING: {api_s.is_player_praying()}"
            # f"\nEQUIPMENT: {api_s.get_player_equipment()}"
            # f"\nEQUIPMENT STATS: {api_s.get_equipment_stats()}"
            # f"\nANIMATION DATA: {api_s.get_animation_data()}"
            # f"\nANIMATION ID: {api_s.get_animation_id()}"
            # f"\nWORLD POINT: {api_s.get_world_point()}"
            f"\nCAMERA: {api_s.get_camera_position()}"
            "\n-----------------------------"
        )
        print(msg)
        time.sleep(3)
