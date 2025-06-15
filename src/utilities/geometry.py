import math
from typing import List, NamedTuple

import cv2
import mss
import numpy as np

import utilities.random_util as rd

Point = NamedTuple("Point", x=int, y=int)

# TO DO: Remove this global variable. This is a temporary fix for a bug in mss.
sct = mss.mss()


class Rectangle:
    """Define a rectangular area on screen.

    (0, 0) ---- Main Monitor Screen Area ------ + ---------------- +
       |                                        |                  |
       |                                        |                  |
       |                                        | top              |
       |                                        |                  |
       |                                        |                  |
       |-----left-- + ----- Rectangle --------- +                  |
       |            |                           |                  |
       |            |                           |                  |
       |            |                           |                  |
       |            |                           | height           |
       |            |                           |                  |
       |            |                           |                  |
       |            |                           |                  |
       |            + --------- width --------- +                  |
       |                                                           |
       |                                                           |
       + --------------------------------------------------------- +

    Note that this coordinate system is defined with the origin in the upper left
    corner. This is because right-handed click-and-drag operations usually occur
    from a click in the upper-left corner of the screen that then drags down to the
    lower-right corner.
    """

    subtract_list: List[dict[str, int]] = []
    # In some instances, we may want to exclude areas within a `Rectangle` (e.g.
    # resizable game view). This should contain a list of dicts that represent
    # rectangles of form {left: int, top: int, width: int, height: int} that will be
    # subtracted from this `Rectangle` during screenshotting.
    reference_rect = None

    def __init__(self, left: int, top: int, width: int, height: int):
        """Initialize a newly-created `Rectangle`.

        Args:
            left (int): The leftmost x-coordinate.
            top (int): The topmost y-coordinate.
            width (int): The width of the rectangle.
            height (int): The height of the rectangle.
        """
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    @classmethod
    def from_points(cls, start_point: Point, end_point: Point):
        """Create a `Rectangle` from two `Point` objects.

        This method is an alternative constructor to create a `Rectangle` object from
        two `Point` objects. Instantiating a `Rectangle` using this constructor would
        look something like `Rectangle.from_points(start_point, end_point)`.

        Args:
            start_point (Point): The first point.
            end_point (Point): The second point.

        Returns:
            Rectangle: A `Rectangle` object using the `from_points` alternative class
                constructor.
        """
        return cls(
            start_point.x,
            start_point.y,
            end_point.x - start_point.x,
            end_point.y - start_point.y,
        )

    def set_rectangle_reference(self, rect):
        """Set the reference `Rectangle` of the object.

        Args:
            rect (Rectangle): A reference to the the `Rectangle` that this
                `Rectangle` belongs in (e.g. `Bot.win.control_panel`).
        """
        self.reference_rect = rect

    def screenshot(self) -> cv2.Mat:
        """Screenshot of the area on screen contained in this `Rectangle`.

        The `grab` method stores pixel data as BGRA; after conversion to a NumPy array,
        we discard the alpha channel to retain only BGR.

        Returns:
            cv2.Mat: NumPy array of BGR color tuples representing the captured image.
        """
        # `mss.mss()` is the primary interface for interacting with the library,
        # allowing us to capture screenshots. The created mss instance holds
        # information about available monitors and provides the tools to grab images.
        with mss.mss() as sct:
            monitor = self.to_dict()
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            img_bgr = img[:, :, :3]  # Truncate the alpha channel.

        if self.subtract_list:
            for area in self.subtract_list:
                img_bgr[
                    area["top"] : area["top"] + area["height"],
                    area["left"] : area["left"] + area["width"],
                ] = 0
        return img_bgr

    def random_point(self) -> Point:
        """Generate a random point within this `Rectangle`.

        Returns:
            Point: A random `Point` (i.e. xy-coordinate pair) within this `Rectangle`.
        """
        x, y = rd.random_point_in(self.left, self.top, self.width, self.height)
        return Point(x, y)

    @property
    def center(self) -> Point:
        """Get the center point of the rectangle.

        Returns:
            A Point representing the center of the rectangle.
        """
        return Point(self.left + self.width // 2, self.top + self.height // 2)

    def distance_from_center(self) -> Point:
        """Get the distance between the object and it's `Rectangle` parent center.

        This method is useful for sorting lists of `Rectangle` objects meaningfully.

        [TO DEV] Consider changing to this to accept a Point to check against, e.g.
            `distance_from(point: Point)`.

        Returns:
            The distance from the point to the center of the object.
        """
        if self.reference_rect is None:
            raise ReferenceError(
                "A `Rectangle` being sorted is missing a reference to the `Rectangle`"
                " it's contained in and therefore cannot be sorted."
            )
        center: Point = self.center
        rect_center: Point = self.reference_rect.center
        return math.dist([center.x, center.y], [rect_center.x, rect_center.y])

    @property
    def top_left(self) -> Point:
        """Get the top-left xy-coordinate of this `Rectangle`.

        Returns:
            A Point representing the top left of this `Rectangle`.
        """
        return Point(self.left, self.top)

    @property
    def top_right(self) -> Point:
        """Get the top-right xy-coordinate of this `Rectangle`.

        Returns:
            A Point representing the top right of this `Rectangle`.
        """
        return Point(self.left + self.width, self.top)

    @property
    def bottom_left(self) -> Point:
        """Get the bottom-left xy-coordinate of this `Rectangle`.

        Returns:
            A Point representing the bottom left of this `Rectangle`.
        """
        return Point(self.left, self.top + self.height)

    @property
    def bottom_right(self) -> Point:
        """Get the bottom-right xy-coordinate of this `Rectangle`.

        Returns:
            A Point representing the bottom right of this `Rectangle`.
        """
        return Point(self.left + self.width, self.top + self.height)

    def to_dict(self) -> dict:
        """Return a dict with the minimal data required to define this `Rectangle`.

        Returns:
            dict: A minimally-defined dict describing this `Rectangle` instance.
        """
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }

    def __str__(self) -> str:
        """Return a string representation of the object.

        Note that this method provides output equivalent to when a standard `print` is
        called on this `Rectangle`.

        Returns:
            str: The result of using the `str` or `print` function on this `Rectangle`.
        """
        return f"Rectangle(x={self.left}, y={self.top},w={self.width}, h={self.height})"

    def __repr__(self) -> str:
        """Return an unambiguous string representation of this `Rectangle`.

        Returns:
            str: The standard string representation of `Rectangle` objects.
        """
        return self.__str__()


class RuneLiteObject:
    """A `RuneLiteObject` represents object on the screen, bounded by a `Rectangle`.

    Note that the bounding `Rectangle` for a `RuneLiteObject` is contained within a
    larger reference `Rectangle` (i.e. the entire screen).


    (0, 0) ---- Main Monitor Screen Area ------- + ---------------- +
        |                                        |                  |
        |                                        |                  |
        |                                        | top              |
        |                                        |                  |
        |                                        |                  |
        |-----left-- + ----- Rectangle --------- +                  |
        |            |                           |                  |
        |            |                           |                  |
        |            |  + -- RuneLiteObject -- + |                  |
        |            |  |                      | | height           |
        |            |  |                      | |                  |
        |            |  |                      | |                  |
        |            |  + -------------------- + |                  |
        |            + --------- width --------- +                  |
        |                                                           |
        |                                                           |
        + --------------------------------------------------------- +

    Note that this coordinate system is defined with the origin in the upper left
    corner. This is because right-handed click-and-drag operations usually occur
    from a click in the upper-left corner of the screen that then drags down to the
    lower-right corner.
    """

    rect = None

    def __init__(
        self,
        xmin: int,
        xmax: int,
        ymin: int,
        ymax: int,
        width: int,
        height: int,
        domain: np.ndarray,
    ) -> None:
        """Initialize a newly-created `RuneLiteObject`.

        Args:
            xmin (int): The minimum x-coordinate of the object.
            xmax (int): The maximum x-coordinate of the object.
            ymin (int): The minimum y-coordinate of the object.
            ymax (int): The maximum y-coordinate of the object.
            width (int): The width of the object.
            height (int): The height of the object.
            domain (np.ndarray): A 2-column stacked array of points that exist inside
                the object outline, representing (y, x) coordinate pairs. Given an
                image with pixels located at (x, y) coordinates, it's more intuitive to
                think of (row, column) coordinates, i.e. (y, x). Note that `domain` is
                a NumPy array with shape (N, 2).

        Raises:
            ReferenceError: Raises a reference error if the `Rectangle` containing this
                `RuneLiteObject` is not defined.
        """
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.width = width
        self.height = height
        self.domain = domain

    def set_rectangle_reference(self, rect: Rectangle) -> None:
        """Set the reference (i.e. containing) `Rectangle` of this `RuneLiteObject`.

        Args:
            rect (Rectangle): The `Rectangle` that this `RuneLiteObject` belongs in
            (e.g. `Bot.win.game_view`).
        """
        self.rect = rect

    @property
    def center(self) -> Point:
        """Get the center of this object relative to its reference `Rectangle`.

        It's important not to confuse this method with `get_center`!

        Raises:
            ReferenceError: Raised if the reference `Rectangle` cannot be found.

        Returns:
            Point: The xy-coordinate corresponding to the center of this object, framed
                by its reference `Rectangle`.
        """
        if not self.rect:
            msg = (
                "Center `Point` of `RuneLiteObject` cannot be determined. Reference"
                " to containing `Rectangle` is missing."
            )
            raise ReferenceError(msg)
        x = round((self.xmin + self.xmax) / 2)
        y = round((self.ymin + self.ymax) / 2)
        return Point(self.rect.left + x, self.rect.top + y)

    def dist_from_rect_center(self) -> float:
        """Get the distance from an object's center to its parent's center.

        This method is designed for sorting a list of `RuneLiteObject` elements
        contained in the same `Rectangle`.

        Returns:
            float: The absolute distance from the given Point to its parent `Rectangle`
                center.
        """
        center: Point = self.center
        rect_center: Point = self.rect.center
        return math.dist([center.x, center.y], [rect_center.x, rect_center.y])

    def vert_dist_from_rect_center(self) -> float:
        """Get the vertical distance from an object's center to its parent's center.

        This method is designed for sorting a list of `RuneLiteObject` elements
        contained in the same `Rectangle`.

        Returns:
            float: The absolute distance from the given Point to its parent `Rectangle`
                center.
        """
        center: Point = self.center
        rect_center: Point = self.rect.center
        return abs(center.y - rect_center.y)

    def horz_dist_from_rect_center(self) -> float:
        """Get the horizontal distance from an object's center to its parent's center.

        This method is designed for sorting a list of `RuneLiteObject` elements
        contained in the same `Rectangle`.

        Returns:
            float: The absolute distance from the given Point to its parent `Rectangle`
                center.
        """
        center: Point = self.center
        rect_center: Point = self.rect.center
        return abs(center.x - rect_center.x)

    def random_point(self) -> Point:
        """Generate a random point within this `RuneLiteObject`.

        Note that unlike the `random_point` method defined in `Rectangle`, this method
        checks for existence since the points generated are from the reference
        `Rectangle` and not this object directly.

        Returns:
            Point: A random `Point` (i.e. xy-coordinate pair) within this
                `RuneLiteObject`.
        """
        kwargs = {
            "xmin": self.xmin,
            "ymin": self.ymin,
            "width": self.width,
            "height": self.height,
        }
        point = rd.random_point_in(**kwargs)
        attempt = 0
        while not self._point_exists(point):
            point = rd.random_point_in(**kwargs)
            attempt += 1
            if attempt > 100:
                return self.center
        return self._relative_point(point)

    def _relative_point(self, point: Point) -> Point:
        """Get a point relative to this object's container (i.e. the client window).

        Args:
            point (Point): The point to get relative to this object's container.

        Returns:
            Point: A `Point` object relative to the parent client window.
        """
        return Point(self.rect.left + point.x, self.rect.top + point.y)

    def _point_exists(self, point: Point, pad: int = 5) -> bool:
        """Check if a row-column coordinate exists within its parent `RuneLiteObject`.

        Note that the coordinates are represented as (y, x) in this context because it
        feels more natural to reference pixels on a rectangle by row then column (and
        also because it is the convention used by OpenCV).

        Args:
            point (List[Tuple[int, int]]): The yx-coordinate to check.
            pad (int): The distance (in pixels) by which we erode the domain on all of
                its borders. This effectively shrinks area where existence is defined.
                Defaults to 5.

        Returns:
            bool: True if the point exists within the (padded) domain, False otherwise.
        """
        x, y = point
        try:
            points_at_x = self.domain[self.domain[:, 1] == x]
            ymax_at_x = points_at_x[points_at_x[:, 0].argmax()][0]
            ymin_at_x = points_at_x[points_at_x[:, 0].argmin()][0]

            points_at_y = self.domain[self.domain[:, 0] == y]
            xmax_at_y = points_at_y[points_at_y[:, 1].argmax()][1]
            xmin_at_y = points_at_y[points_at_y[:, 1].argmin()][1]

            if (ymin_at_x + pad <= y <= ymax_at_x - pad) and (
                xmin_at_y + pad <= x <= xmax_at_y - pad
            ):
                return True
        except ValueError as exc:
            print(f"{point} does not exist in `RuneLiteObject`: {exc}")
            return False
        return False


def cosine_similarity(v1: tuple, v2: tuple) -> float:
    """Calculate the cosine similarity of two vectors.

    Note that a cosine similarity of:
        1 indicates the vectors are pointing in the same direction.
        -1 indicates the vectors are pointing in opposite directions.
        0 indicates the vectors are perpendicular to each other.

    Args:
        v1 (tuple): The first required vector input.
        v2 (tuple): The second required vector input.

    Returns:
        float: The cosine similarity, ranging from -1 to 1.
    """
    dot_product = np.dot(v1, v2)
    magnitude1 = np.linalg.norm(v1)
    magnitude2 = np.linalg.norm(v2)
    cosine_similarity = dot_product / (magnitude1 * magnitude2)
    return cosine_similarity
