import math
import time
from typing import TYPE_CHECKING, List, Literal, Tuple, Union

if TYPE_CHECKING:
    from model import RuneLiteBot

from utilities import random_util as rd
from utilities.api.pathfinder import Pathfinder
from utilities.geometry import Point
from utilities.mappings import locations as loc

WalkPath = Union[List[Point], List[Tuple[int]]]
NamedDest = Union[str, Tuple[int, int]]


class Walker:
    PIXELS_PER_TILE: int = 4  # There are 4 pixels per tile on a default-scale minimap.

    def __init__(
        self,
        rune_lite_bot: "RuneLiteBot",
        dest_square_side_length: int = 1,
        max_waypoint_dist: int = 10,
        max_horizon: int = 12,
        reset_zoom_each_embark: bool = True,
    ) -> None:
        """Initialize a `RuneLiteBot` so we may equip it to walk.

        Args:
            rune_lite_bot (RuneLiteBot): The `RuneLiteBot` to walk with.
            dest_square_side_length (int, optional): The side length of the square
                destination zone. Defaults to 1 (i.e. the exact tile).
            max_waypoint_dist (int, optional): Maximum number of tiles between
                waypoints. Defaults to 10 tiles.
            max_horizon (int, optional): Click up to a certain number of tiles ahead
                when walking between waypoints. Defaults to 12 tiles.
            reset_zoom_each_embark: (bool, optional). Whether to reset the minimap zoom
                each time before setting out to travel a given path. Defaults to True.
        """
        self.DEST_SQUARE_SIDE_LENGTH = dest_square_side_length
        self.MAX_WAYPOINT_DIST = max_waypoint_dist
        self.MAX_HORIZON = max_horizon
        self.bot = rune_lite_bot
        self.reset_zoom_each_embark = reset_zoom_each_embark
        self.camera_angle = None
        self.position = None

    def _format_walk_path(self, walk_path_raw: List[Tuple[int]]) -> WalkPath:
        """Convert a list of world point tuples into a list of `Point` objects.

        Args:
            walk_path_raw (List[Tuple[int]]): A list of tuples representing an (x, y,
                plane) world point.

        Returns:
            WalkPath: The same list of waypoints, but with `Point` objects rather than
                tuples.
        """
        return [Point(world_point[0], world_point[1]) for world_point in walk_path_raw]

    def update_position(self) -> None:
        """Update the `position`, `x`, and `y` attributes.

        Note that the returned position is measured in game tiles (rather than pixels).
        """
        while True:
            if posn := self.bot.get_world_point():
                break
            time.sleep(0.3)
        self.position = posn
        self.x, self.y, _ = self.position  # Ignore the z-coordinate (i.e. plane).
        self.loc = Point(self.x, self.y)

    def update_camera_angle(self) -> None:
        """Update the `camera_angle` (measured as degrees clockwise from north)."""
        self.camera_angle = self.bot.get_compass_angle()

    def get_pixel_distance(self, dest: Point) -> Point:
        """Find the distance from minimap center to a destination point in pixels.

        The `Walker` seems to perform best with the minimap brought to its default zoom
        level via right-clicking, but it still works at different zoom levels. It need
        not be aligned in any direction, however.

        Args:
            Point: Destination xy-coordinate, measured in minimap pixel space.

        Returns:
            Point: A `Point` representing a pixel coordinate relative to the center of
                the minimap, accounting for any rotation.
        """
        self.update_position()
        self.update_camera_angle()
        theta = math.radians(self.camera_angle)  # Convert degrees clockwise to radians.

        # Convert the tile-space difference between our current location and desired
        # destination to a pixel-space difference on the minimap in a North-aligned
        # coordinate frame.
        x_reg = (dest.x - self.x) * self.PIXELS_PER_TILE
        y_reg = (self.y - dest.y) * self.PIXELS_PER_TILE

        # Now get the same pixel coordinate in the potentially-rotated minimap frame.
        x_mini = round(x_reg * math.cos(theta) - y_reg * math.sin(theta))
        y_mini = round(x_reg * math.sin(theta) + y_reg * math.cos(theta))

        return Point(x_mini, y_mini)

    def change_position(self, dest: Point) -> None:
        """Click a point on the minimap and thus command our character to walk there.

        Args:
            dest (Point): The destination xy-coordinate in potentially-rotated minimap
                pixel space.
        """
        self.update_position()
        if dist_mini := self.get_pixel_distance(dest):
            minimap_center = self.bot.win.minimap.center
            x_new = round(minimap_center.x + dist_mini.x)
            y_new = round(minimap_center.y + dist_mini.y)
            self.bot.mouse.move_to(Point(x_new, y_new))
            self.bot.mouse.click()
            self.bot.sleep()

    def get_target_posn(self, walk_path: WalkPath) -> Point:
        """Get the furthest-away coordinate to the destination within a boundary.

        Get the furthest-away `Point` within `self.MAX_HORIZON` tiles by searching from
        the destination `Point` backward to our current position.

        Args:
            walk_path (WalkPath): A list of `Point` tuples describing our character's
                travel path.

        Returns:
            Point: The next target point to walk to, measured in tile space.
        """
        self.update_position()
        # Using a generator for back-to-front search improves performance.
        try:
            ind = next(
                i
                for i in range(len(walk_path) - 1, -1, -1)
                if (
                    abs(walk_path[i].x - self.x) <= self.MAX_HORIZON
                    and abs(walk_path[i].y - self.y) <= self.MAX_HORIZON
                )
            )
            self.bot.log_msg(
                f"Walking progress: {ind}/{len(walk_path)}", overwrite=True
            )
            return walk_path[ind]
        except StopIteration:
            msg = "Travel halted. An obstacle (e.g. a gate) may be blocking the path."
            self.bot.log_msg(msg)

    def has_arrived(self, dest: Point, pad: int = None) -> bool:
        """Return True if our position in tile-space is within a bounding area.

        Args:
            dest (Point): The destination `Point` to define an arrival area around,
                measured in tiles.
            pad (int, optional): How much padding to add around the destination point
                which defines the midpoint of a square destination zone. Defaults to a
                `self.DEST_SQUARE_SIDE_LENGTH // 2` number of tiles. For example,
                `pad=1` corresponds to a 2x2 square destination zone. Graphically,
                    .-----.-----p2
                    |     |     |
                    |-----.-pad-.
                    |     |     |
                   p1-----.-----`
                Note that `pad=0` corresponds to the exact destination tile.

        Returns:
            bool: True if we have arrived within the destination area, False otherwise.
        """
        pad = pad or self.DEST_SQUARE_SIDE_LENGTH // 2
        self.update_position()
        if pad == 0:
            return self.x == dest.x and self.y == dest.y
        p1 = Point(dest.x - pad, dest.y - pad)
        p2 = Point(dest.x + pad, dest.y + pad)
        within_x_range = p1.x <= self.x <= p2.x
        within_y_range = p1.y <= self.y <= p2.y
        return within_x_range and within_y_range

    def walk(self, walk_path: WalkPath, dest: Point = None) -> bool:
        """Walk along a `WalkPath` to a destination area.

        Note that each `Point` defining the `walk_path` and also `dest` are measured in
        tile space. Unlike `walk_to`, `walk` requires a previously-generated `WalkPath`
        instead of just a starting `Point` and a destination `Point`.

        Args:
            walk_path (WalkPath): The list of `Point` objects to walk along.
            dest (Point, optional): The destination `Point` to define an arrival area
                around. Defaults to None, meaning the `walk_path` is simply walked until
                the last `Point` is reached.

        Returns:
            bool: True if the specified destination was reached, False otherwise.
        """
        walk_path = (
            walk_path
            if isinstance(walk_path[-1], Point)
            else self._format_walk_path(walk_path)
        )
        dest = dest or walk_path[-1]

        try:
            embarking = True
            self.bot.log_msg("Embarking...")
            while not self.has_arrived(dest):
                new_pos = self.get_target_posn(walk_path)
                if self.reset_zoom_each_embark and embarking:
                    minimap_center = self.bot.win.minimap.center
                    self.bot.mouse.move_to(
                        rd.random_point_around(minimap_center, xpad=10, ypad=10)
                    )
                    self.bot.mouse.right_click()
                    embarking = False
                if self.has_arrived(dest):  # Double-checking helps us stop gracefully.
                    break
                self.change_position(new_pos)
            return True
        except Exception as exc:
            msg = (
                "Did not arrive at intended destination. Something went wrong"
                f" unexpectedly: {exc}"
            )
            self.bot.log_msg(msg)
            return False

    def walk_to(
        self, dest: Union[NamedDest, Point], host: Literal["dax", "osrspf"] = "dax"
    ) -> bool:
        """Use an API-generated `WalkPath` to travel to a destination.

        Note that DAX is more reliable than OSRSpathfinder. OSRSpathfinder periodically
        fails in certain locations. Why this occurs isn't immediately obvious.

        The pathfinding API hosted by either OSRSpathfinder or explv-map (i.e. DAX)
        calculates the shortest path between our character's current position in the
        center of the game view and a desired location on the map (measured in tiles)
        via the A* (pronounced "A-star") pathfinding algorithm.

        Args:
            dest Union[NamedDest, Point]: Any `Point`, or perhaps instead a string name
                (i.e."VARROCK_SQUARE") associated with a destination listed in
                `utilities.locations`.
            host ("dax" or "osrspf"): Whether to use the DAX or OSRSpathfinder
                pathfinding API. Defaults to the more reliable "dax".

        Returns:
            bool: True if the specified destination was reached, False otherwise.
        """
        self.update_position()
        dest = (  # `dest` is a `Point` measured in tile space.
            getattr(loc, dest)  # If named, look up in `utilities.mappings.locations`.
            if isinstance(dest, str)
            else dest
        )
        dest = Point(dest[0], dest[1])
        path = self.get_api_walk_path(p1=self.loc, p2=dest, host=host)
        return self.walk(path, dest)

    def get_api_walk_path(
        self, p1: Point, p2: Point, host: Literal["dax", "osrspf"]
    ) -> WalkPath:
        """Retrieve a `WalkPath` from either the DAX or OSRSpathfinder API endpoints.

        This method returns the results of the A* (pronounced "A-star") pathfinding
        algorithm. A* is a popular and efficient algorithm used to find the shortest
        path between two points in a graph or grid. It's commonly applied in video
        games, robotics, and other fields where pathfinding is essential.

        Args:
            p1 (Point): The start of the path to be calculated.
            p2 (Point): The destination point of the path to be calculated.
            host ("dax" or "osrspf"): Whether to use the DAX or OSRSpathfinder
                pathfinding API to obtain the desired path. Note that the DAX API is
                significantly more reliable than OSRSpathfinder equivalent.

        Returns:
            WalkPath: The shortest valid path between the two provided points.
        """
        api = Pathfinder.get_path_dax if host == "dax" else Pathfinder.get_path_osrspf
        if path_raw := api(p1, p2):
            return self.add_waypoints(path_raw)
        host_name = "DAX" if host == "dax" else "OSRSPathfinder"
        msg = f"{host_name} API request for shortest path failed ({p1} -> {p2})."
        self.bot.log_msg(msg)
        return []

    def distance(self, p1: Point, p2: Point) -> float:
        """Return the Euclidean distance between two points.

        Args:
            p1 (Point): The reference point to use in the distance calculation.
            p2 (Point): Another point we'd like to measure distance to relative to the
                reference point.

        Returns:
            float: The absolute distance between the two provided `Point` objects.
        """
        return math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)

    def add_waypoints(self, walk_path: WalkPath) -> WalkPath:
        """Smooth a `WalkPath` by computing intermediary `Point` objects between steps.

        Args:
            walk_path (WalkPath): The list of `Point` objects representing the
                traversal path we would like to smooth out.

        Returns:
            WalkPath: The original `WalkPath` provided, but with additional
                intermediary `Point` objects interspersed throughout. Note that the
                relative ordering of the points provided in `walk_path` is maintained.
        """
        walk_path_w_waypoints = [walk_path[0]]  # Start with the first coordinate.
        for step in range(len(walk_path) - 1):  # Note that we stop before the last one.
            p1 = walk_path[step]
            p2 = walk_path[step + 1]
            dist = self.distance(p1, p2)
            # If the next point is far, add intermediary waypoints in between.
            if dist > self.MAX_WAYPOINT_DIST:  # Measured in tile space.
                num_waypoints = math.ceil(dist / 10)
                dx = (p2.x - p1.x) / num_waypoints
                dy = (p2.y - p1.y) / num_waypoints
                for i in range(1, num_waypoints):
                    walk_path_w_waypoints.append(
                        Point(round(p1.x + i * dx), round(p1.y + i * dy))
                    )
            # Cap off the intermediary waypoints with the original point that was
            # further than 10 tiles away.
            walk_path_w_waypoints.append(p2)
        return walk_path_w_waypoints

    def travel_to_dest_along_path(
        self, tile_coord: Tuple[int], walk_path: WalkPath, dest_name: str
    ) -> bool:
        """Travel to a destination point along a path.

        This method uses three ways to attempt to walk to a destination:
            1. Call the DAX API to get a dynamically-generated A* path.
            2. Call the OSRSPathfinder API to get a dynamically-generated A* path.
            3. Use a hard-coded path.

        Args:
            tile_coord (Tuple[int]): The xy tile coordinate of the destination.
            walk_path (WalkPath): A hardcoded list of xy-coordinates from the start of
                the path to the destination to be used as a backup in case `tile_coord`
                is insufficient.
            dest_name (str): The name of the destination.

        Returns:
            bool: True if the destination was reached, False otherwise.
        """
        try:
            if self.walk_to(tile_coord, host="dax"):
                return True
        except Exception:
            try:
                if self.walk_to(tile_coord, host="osrspf"):
                    return True
            except Exception:
                try:
                    print("Walking along manually-set path...")
                    if self.walk(walk_path):
                        return True
                except Exception as exc:
                    print(f"Failed to travel to {dest_name}: {exc}")
                    return False
