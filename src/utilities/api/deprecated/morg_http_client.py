"""
Note! The Morg HTTP Client plug-in has been banned by RuneLite. The code remains here
for legacy purposes.
"""

import time
from typing import Any, Dict, List, Literal, Tuple, Union

import requests
from deprecated import deprecated
from requests.exceptions import ConnectionError

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path[0] = str(Path(sys.path[0]).parents[1])
    from utilities.mappings import item_ids as iid
    from utilities.mappings import skills as sn


class SocketError(Exception):
    def __init__(self, error_message: str, endpoint: str):
        self.__error_message = error_message
        self.__endpoint = endpoint
        super().__init__(self.get_error())

    def get_error(self):
        return f"{self.__error_message} endpoint: {self.__endpoint}"


class MorgHTTPClient:
    """Establish a socket connection to the Morg server to enable HTTP communication.

    The Morg HTTP Client RuneLite plug-in exposes an HTTP API on localhost:8080 for
    querying character data.
    """

    gameTick = 0.603  # Fundamental time unit (in seconds) equal to one server cycle.

    def __init__(self):
        """Instantiate a `MorgHTTPSocket`."""
        self.base_endpoint = "http://localhost:8081/"

        self.inv_endpoint = "inv"
        self.stats_endpoint = "stats"
        self.equip_endpoint = "equip"
        self.events_endpoint = "events"

        self.timeout = 1

    def __do_get(self, endpoint: Literal["inv", "stats", "equip", "events"]) -> dict:
        """Retrieve a JSON response from a Morg HTTP Client API endpoint.

        Args:
            endpoint (Literal["inv", "stats", "equip", "events"]): The desired API
                endpoint to hit.

        Raises:
            SocketError: If the endpoint is not valid or the server is not running.

        Returns:
            dict: All JSON data from the chosen endpoint.
        """
        try:
            response = requests.get(
                f"{self.base_endpoint}{endpoint}", timeout=self.timeout
            )
        except ConnectionError as e:
            raise SocketError("Unable to reach socket", endpoint) from e

        if response.status_code != 200:
            if response.status_code == 204:
                return {}
            else:
                raise SocketError(
                    f"Unable to reach socket. Status code: {response.status_code}",
                    endpoint,
                )
        return response.json()

    def test_endpoints(self) -> bool:
        """Ensure all endpoints are working correctly.

        Returns:
            bool: True if all tests passed, False otherwise.
        """
        for i in list(self.__dict__.values())[1:-1]:  # Look away
            try:
                self.__do_get(endpoint=i)
            except SocketError as e:
                print(e)
                print(f"Endpoint {i} is not working.")
                return False
        return True

    def get_events(self) -> Dict[str, Any]:
        """Return a dictionary of miscellaneous game-state information."""
        return self.__do_get("events")

    def get_game_tick(self) -> int:
        """Get the game tick number.

        Returns:
            int: The current game tick.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["game tick"]) if "game tick" in data else -1

    def get_hitpoints(self) -> Tuple[int, int]:
        """Get the current and maximum hitpoints of the player.

        Returns:
            Tuple[int, int]: Tuple(current_hitpoints, maximum_hitpoints). If there was
            an issue getting hitpoints data, the tuple defaults to (-1, -1).
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        if hitpoints_data := data.get("health"):
            cur_hp, max_hp = hitpoints_data.split("/")
            return int(cur_hp), int(max_hp)
        else:
            return -1, -1

    def get_run_energy(self) -> int:
        """Get the current run energy of our character.

        Note that maximum run energy is 10000 (corresponding to 100 in game).

        Returns:
            int: Our character's current run energy between 0 and 10000.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(run_energy) if (run_energy := data.get("run energy")) else -1

    def get_animation(self) -> int:
        """Get the animation our character is currently is performing.

        Returns:
            int: The animation ID (found in `api.animation_ids`) corresponding to the
                current animation.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["animation"]) if data.get("animation") else -1

    @deprecated(reason="Use `get_animation` instead as it matches `api.animation_ids`.")
    def get_animation_id(self) -> int:
        """Get the animation ID for our character's current state.

        The endpoint is great for checking if our character is performing a particular
        action.

        Returns:
            int: An alternative animation ID (not listed in `api.animation_ids`). Its
                current applications are yet to be researched.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["animation pose"]) if data.get("animation pose") else -1

    def is_player_idle(self, poll_seconds: int = 1) -> bool:
        """Check if our character is idling.

        Args:
            poll_seconds (int, optional): The number of seconds to poll for an idle animation. Defaults to 1.

        Returns:
            bool: True if our character is idle, False otherwise.
        """
        start_time = time.time()
        while time.time() - start_time < poll_seconds:
            data = self.__do_get(endpoint=self.events_endpoint)
            if data.get("animation") != -1 or data.get("animation pose") not in [
                808,
                813,
            ]:
                return False
        return True

    def get_skill_level(self, skill: str) -> int:
        """Return the level of given skill.

        Args:
            skill (str): The case-insensitive name of the skill.

        Returns:
            int: The level of the skill, or -1 if an error occurred.
        """
        data = self.__do_get(endpoint=self.stats_endpoint)
        try:
            level = next(int(i["level"]) for i in data[1:] if i["stat"] == skill)
        except StopIteration:
            print(
                f"Invalid stat name: {skill}. Consider using the `stat_names` utility."
            )
            return -1
        return level

    def get_skill_xp(self, skill: str) -> int:
        """Return the total XP of the given skill.

        Args:
            skill (str): The case-insensitive name of the skill.

        Returns:
            int: The total XP of the skill, or -1 if an error occurred.
        """
        data = self.__do_get(endpoint=self.stats_endpoint)
        try:
            total_xp = next(int(i["xp"]) for i in data[1:] if i["stat"] == skill)
        except StopIteration:
            print(
                f"Invalid stat name: {skill}. Consider using the `stat_names` utility."
            )
            return -1
        return total_xp

    def get_skill_xp_gained(self, skill: str) -> int:
        """Get the XP gained of a skill since the tracker began at 0 on client startup.

        Args:
            skill (str): The case-insensitive name of the skill.

        Returns:
            int: The XP gained of the skill this session, or -1 if an error occurred.
        """
        data = self.__do_get(endpoint=self.stats_endpoint)
        try:
            xp_gained = next(
                int(i["xp gained"]) for i in data[1:] if i["stat"] == skill
            )
        except StopIteration:
            print(
                f"Invalid stat name: {skill}. Consider using the `stat_names` utility."
            )
            return -1
        return xp_gained

    def get_xp_gained_over_time(self, skill: str, timeout: int = 10) -> int:
        """Return the XP our character gains of the given skill in the given time.

        Args:
            skill (str): The case-insensitive name of the skill.
            timeout (int, optional): The time to wait for XP gain in seconds.

        Returns:
            int: The XP gained, or -1 if no XP was gained or an error occurred during
                the timeout.
        """
        starting_xp = self.get_skill_xp(skill)
        if starting_xp == -1:
            print("Failed to get starting xp.")
            return -1

        stop_time = time.time() + timeout
        while time.time() < stop_time:
            data = self.__do_get(endpoint=self.stats_endpoint)
            final_xp = next(int(i["xp"]) for i in data[1:] if i["stat"] == skill)
            if final_xp > starting_xp:
                return final_xp
            time.sleep(0.2)
        return -1

    def get_latest_chat_message(self) -> str:
        """Get the most recent chat message in the public chat box.

        Returns:
            str: A string representing the latest chat message, no spaces.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return data["latest msg"] if "latest msg" in data else ""

    def get_world_point(self) -> Tuple[int, int, int]:
        """Get the world point of a player.

        Returns:
            Tuple[int, int, int]: A tuple of integers representing the player's world
                point (x, y, z), or (-1, -1, -1) if data is not present or invalid.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        if "worldPoint" not in data:
            return -1, -1, -1
        return (
            int(data["worldPoint"]["x"]),
            int(data["worldPoint"]["y"]),
            int(data["worldPoint"]["plane"]),
        )

    def get_region_point(self) -> Tuple[int, int, int]:
        """Get the region data of our character's current position.

        The OSRS map is split up into a labeled grid system of regions. A picture is
        worth 1000 words, so visit https://explv.github.io/ to learn more.

        Returns:
            Tuple[int, int, int]: Our character's current regional coordinates,
                (region_x, region_y, region_ID).
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        if "worldPoint" not in data:
            return -1, -1, -1
        return (
            int(data["worldPoint"]["regionX"]),
            int(data["worldPoint"]["regionY"]),
            int(data["worldPoint"]["regionID"]),
        )

    def get_camera_position(self) -> Union[Dict[str, int], None]:
        """Get the position of the camera.

        Returns:
            Union[Dict[str, int]: The camera position {yaw, pitch, x, y, z, x2, y2, z2},
                or None if data is not present or invalid.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return data["camera"] if "camera" in data else None

    def get_mouse_position(self) -> Tuple[int, int]:
        """Get the position of the mouse cursor relative to the game window.

        Returns:
            Tuple[int, int]: The cursor position relative to the active RuneLite window.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        if "mouse" not in data:
            return -1, -1
        return int(data["mouse"]["x"]), int(data["mouse"]["y"])

    def get_interaction_code(self) -> str:
        """Get the interacting code of the current interaction.

        Use case is currently unknown.

        Returns:
            str: A string code representing an interaction.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return data["interacting code"] if "interacting code" in data else None

    def is_in_combat(self) -> Union[bool, None]:
        """Determine whether the player is in combat.

        Returns:
            Union[bool, None]: True if the player is in combat, False if not. Returns
                None if an error occurred.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return None if "npc name" not in data else data["npc name"] != "null"

    @deprecated(reason="This method returns unreliable values for the NPC's HP.")
    def get_npc_hitpoints(self) -> Union[int, None]:
        """Get the HP of the currently targeted NPC.

        [TO DEV]: Result seems to be multiplied by 6...?

        Returns:
            Union[int, None]: The NPC's HP, or None if an error occurred. If no NPC was
                in combat, returns 0.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["npc health "])

    def get_inv(self) -> List[Dict]:
        """Get a list of dictionaries representing our character's inventory.

        [TO DEV] Double check the output of this method.

        Returns:
            List[Dict]: List of dictionaries, each containing index, ID, and quantity of an item.
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        inventory = []
        for index, item in enumerate(data):
            if item["quantity"] == 0:
                continue
            item_info = {"index": index, "id": item["id"], "quantity": item["quantity"]}
            inventory.append(item_info)
        return inventory

    def is_item_in_inv(self, item_id: Union[List[int], int]) -> bool:
        """Check if an item is in our character's inventory or not.

        Args:
            item_id (Union[List[int], int]): The id of the item to check for (an single
                ID, or list of IDs).

        Returns:
            bool: True if the item is in the inventory, False if not.
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        if isinstance(item_id, int):
            return any(inventory_slot["id"] == item_id for inventory_slot in data)
        elif isinstance(item_id, list):
            return any(inventory_slot["id"] in item_id for inventory_slot in data)

    def is_inv_full(self) -> bool:
        """Check whether the inventory is full.

        Returns:
            bool: True if the inventory is full, False otherwise.
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        return len([item["id"] for item in data if item["id"] != -1]) == 28

    def is_inv_empty(self) -> bool:
        """Check whether the inventory is empty.

        Returns:
            bool: True if the inventory is empty, False otherwise.
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        return not [item["id"] for item in data if item["id"] != -1]

    def get_inv_item_indices(self, item_id: Union[List[int], int]) -> List[int]:
        """Get the inventory indices containing any one of a given amount of items.

        For the given item IDs, get a list of corresponding inventory slot indexes
        containing the at least one item with a matching ID.

        Args:
            item_id (Union[List[int], int]): The item ID to search for (a single ID,
                or list of IDs).

        Returns:
            List[int]: A list of inventory slot indexes that the item(s) exists in.
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        if isinstance(item_id, int):
            return [
                i
                for i, inventory_slot in enumerate(data)
                if inventory_slot["id"] == item_id
            ]
        elif isinstance(item_id, list):
            return [
                i
                for i, inventory_slot in enumerate(data)
                if inventory_slot["id"] in item_id
            ]

    def get_first_occurrences(
        self, item_id: Union[List[int], int]
    ) -> Union[int, List[int]]:
        """Get the first filled inventory slot index for each of the given item IDs.

        e.g. [1, 1, 2, 3, 3, 3, 4, 4, 4, 4] -> [0, 2, 3, 6]

        Args:
            item_id: The item ID to search for (an single ID, or list of IDs).
        Returns:
            Union[int, List[int]]: The first inventory slot index that the item exists
                in for each unique item ID. If a single item ID is provided, returns an
                integer (or -1 on a failure). If a list of item IDs is provided,
                returns a list of integers (or empty list on a failure).
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        if isinstance(item_id, int):
            return next(
                (
                    i
                    for i, inventory_slot in enumerate(data)
                    if inventory_slot["id"] == item_id
                ),
                -1,
            )
        elif isinstance(item_id, list):
            first_occurrences = {}
            for i, inventory_slot in enumerate(data):
                item_id_in_slot = inventory_slot["id"]
                if (
                    item_id_in_slot not in first_occurrences
                    and item_id_in_slot in item_id
                ):
                    first_occurrences[item_id_in_slot] = i
            return list(first_occurrences.values())

    def get_inv_item_stack_amount(self, item_id: Union[int, List[int]]) -> int:
        """Get the stack size of the first matching item in our character's inventory.

        This method is primarily intended for items that stack (e.g. coins or runes).

        Args:
            item_id (Union[int, List[int]]): The item ID to search for. If a list is
                passed, the first matching item will be used.
        Returns:
            int: The total number of items corresponding to the matched item ID.
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        if isinstance(item_id, int):
            item_id = [item_id]
        if result := next((item for item in data if item["id"] in item_id), None):
            return int(result["quantity"])
        return 0

    def is_item_equipped(self, item_id: Union[int, List[int]]) -> bool:
        """Check if an item is equipped to our character.

        Given a list of IDs, returns True on first ID found.

        Args:
            item_id (Union[int, List[int]]): The item ID to check for (a single ID, or
                list of IDs).
        Returns:
            bool: True if an item is equipped, False if not.
        """
        data = self.__do_get(endpoint=self.equip_endpoint)
        equipped_ids = [item["id"] for item in data]
        if isinstance(item_id, int):
            return item_id in equipped_ids
        return any(item in item_id for item in equipped_ids)

    def get_equipped_item_quantity(self, item_id: int) -> int:
        """Get the quantity of an equipped item.

        [TO DEV]: Double check this endpoint. Is this useful for checking ammunition
            numbers?

        Args:
            item_id: The item ID of the item our character is wearing, which we are
                checking for quantity.
        Returns:
            int: The quantity of the item equipped, or 0 if not equipped.
        """
        data = self.__do_get(endpoint=self.equip_endpoint)
        return next(
            (
                int(equip_slot["quantity"])
                for equip_slot in data
                if equip_slot["id"] == item_id
            ),
            0,
        )


if __name__ == "__main__":
    api_m = MorgHTTPClient()
    if not api_m:
        print("No character found. Is the RuneLite client logged in and active?")
    test_skill = sn.WOODCUTTING
    test_equip = iid.CHEFS_HAT
    test_stack = iid.FEATHER
    test_item = iid.YEW_LOGS
    timeout = 60
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(api_m.gameTick)
        msg = (
            f"\nTEST ENDPOINTS: {api_m.test_endpoints()}"
            f"\nGAME TICK: {api_m.get_game_tick()}"
            f"\nHITPOINTS: {api_m.get_hitpoints()}"
            f"\nRUN ENERGY: {api_m.get_run_energy()}"
            f"\nANIMATION: {api_m.get_animation()}"
            f"\nANIMATION ID: {api_m.get_animation_id()}"
            f"\nIS PLAYER IDLE: {api_m.is_player_idle()}"
            f"\nSKILL LEVEL: {api_m.get_skill_level(test_skill)}"
            f"\nSKILL XP: {api_m.get_skill_xp(test_skill)}"
            f"\nSKILL XP GAINED: {api_m.get_skill_xp_gained(test_skill)}"
            f"\nSKILL XP GAINED OVER TIME: {api_m.get_xp_gained_over_time(test_skill)}"
            f"\nLATEST CHAT MSG: {api_m.get_latest_chat_message()}"
            f"\nCURRENT POSITION: {api_m.get_world_point()}"
            f"\nREGION DATA: {api_m.get_region_point()}"
            f"\nCAMERA POSITION: {api_m.get_camera_position()}"
            f"\nMOUSE POSITION: {api_m.get_mouse_position()}"
            f"\nINTERACTION CODE: {api_m.get_interaction_code()}"
            f"\nIS IN COMBAT: {api_m.is_in_combat()}"
            f"\nINV: {api_m.get_inv()}"
            f"\nYEW LOGS IN INV: {api_m.is_item_in_inv(test_item)}"
            f"\nIS INV FULL: {api_m.is_inv_full()}"
            f"\nIS INV EMPTY: {api_m.is_inv_empty()}"
            f"\nYEW LOG INV INDICES: {api_m.get_inv_item_indices(test_item)}"
            f"\nYEW LOG FIRST OCCURRENCE: {api_m.get_first_occurrences(test_item)}"
            f"\nGOLD STACK AMT: {api_m.get_inv_item_stack_amount(test_stack)}"
            f"\nIS CHEF HAT EQUIPPED: {api_m.is_item_equipped(test_equip)}"
            f"\nNUM EQUIPPED CHEF HATS: {api_m.get_equipped_item_quantity(test_equip)}"
            "\n-----------------------------"
        )
        # msg = (
        #     f"\nANIMATION: {api_m.get_animation()}"
        #     f"\nANIMATION ID: {api_m.get_animation_id()}"
        #     f"\nIS PLAYER IDLE: {api_m.get_is_player_idle()}"
        #     f"\nCAMERA POSITION: {api_m.get_camera_position()}"
        #     f"\nIS COOKING: {api_m.get_animation() == 897}"
        # )
        # msg = f"{api_m.get_events()}"
        print(msg)
