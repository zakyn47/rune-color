import random
import time
from typing import Literal

import mss
import numpy as np
import pyautogui as pag
from pyclick import HumanCurve
from pytweening import easeOutElastic, easeOutQuad

import utilities.img_search as imsearch
from utilities.geometry import Point, Rectangle
from utilities.random_util import trunc_norm_samp

SQRT3 = np.sqrt(3)
SQRT5 = np.sqrt(5)


class Mouse:
    # By default, `click_delay` is True to instruct `click` to include a small time
    # delay between the down-clicks and up-clicks it issues to provide humanization.
    click_delay = True

    def move_to(
        self,
        destination: tuple,
        style: Literal["bezier", "wind"] = "bezier",
        G_0: int = 60,
        W_0: int = 30,
        M_0: int = 30,
        D_0: int = 30,
        **kwargs,
    ) -> None:
        """Move the mouse cursor in a human-like way in an absolute frame.

        For Bezier style, first, we obtain an ordered set of xy-coordinates after
        instantiating a `HumanCurve` connecting our current mouse position and desired
        destination. Then, we move the cursor to each point in the set, tracing out a
        path. As a side note, the path that is generated is a type of continuous
        polynomial (i.e. smooth) curve called a Bezier curve, and is commonly used in
        animation.

        For WindMouse style, we obtain the next destination xy-coordinate based on the
        previous one's state, moving along the curve with each new point. The algorithm
        simulates a small mass traveling through windy conditions. For an in-depth
        walkthrough, see: https://tinyurl.com/mv8yaub5

        Args:
            destination (tuple): Cartesian coordinate of the destination point.
            style (["bezier", "wind"], optional): The style of movement. Defaults to
                "bezier".
            G_0 (int, optional): Magnitude of the gravitational force. Defaults to 60.
            W_0 (int, optional): Magnitude of the wind force variations. Defaults to 30.
            M_0 (int, optional): Max step size (velocity clip threshold). Default is 30.
            D_0 (int, optional): Distance where wind behavior changes from random to
                damped. Defaults to 30.
            **kwargs: Arbitrary keyword arguments used in the context of the pyclick
                module and the `HumanCurve` class.

        Notable Kwargs:
            knotsCount (int): Number of knots to use in the curve. The default amount
                is determined by the distance to the destination. Note that the lower
                the `knotsCount`, the more linear the movement, down to a minimum of 0.
            mouseSpeed: The speed of the mouse as it traverses the generated
                `HumanCurve`. Defaults to "fast". The possible choices are:
                - "slowest"
                - "slow"
                - "medium"
                - "fast"
                - "fastest"
            tween: The tweening function to use from pytweening. Defaults to
                `easeOutQuad`.
        """
        x0, y0 = pag.position()
        xf, yf = destination

        if style == "bezier":
            offsetBoundaryX = kwargs.get("offsetBoundaryX", 100)
            offsetBoundaryY = kwargs.get("offsetBoundaryY", 100)
            knotsCount = kwargs.get("knotsCount", self.__calculate_knots(destination))
            distortionMean = kwargs.get("distortionMean", 1)
            distortionStdev = kwargs.get("distortionStdev", 1)
            distortionFrequency = kwargs.get("distortionFrequency", 0.5)
            tween = kwargs.get("tweening", random.choice([easeOutElastic, easeOutQuad]))
            mouseSpeed = kwargs.get("mouseSpeed", "fast")
            mouseSpeed = self.__get_mouse_speed(mouseSpeed)

            for x, y in HumanCurve(
                (x0, y0),
                (xf, yf),
                offsetBoundaryX=offsetBoundaryX,
                offsetBoundaryY=offsetBoundaryY,
                knotsCount=knotsCount,
                distortionMean=distortionMean,
                distortionStdev=distortionStdev,
                distortionFrequency=distortionFrequency,
                tween=tween,
                targetPoints=mouseSpeed,
            ).points:  # For each tuple in the ordered set of xy-coordinate tuples...
                pag.moveTo((x0 := x, y0 := y))  # Move to the next position.

        if style == "wind":
            v_x = v_y = W_x = W_y = 0
            while (dist := np.hypot(xf - x0, yf - y0)) >= 1:
                W_mag = min(W_0, dist)
                if dist >= D_0:
                    W_x = W_x / SQRT3 + (2 * np.random.random() - 1) * W_mag / SQRT5
                    W_y = W_y / SQRT3 + (2 * np.random.random() - 1) * W_mag / SQRT5
                else:
                    W_x /= SQRT3
                    W_y /= SQRT3
                    if M_0 < 3:
                        M_0 = np.random.random() * 3 + 3
                    else:
                        M_0 /= SQRT5
                v_x += W_x + G_0 * (xf - x0) / dist
                v_y += W_y + G_0 * (yf - y0) / dist
                v_mag = np.hypot(v_x, v_y)
                if v_mag > M_0:
                    v_clip = M_0 / 2 + np.random.random() * M_0 / 2
                    v_x = (v_x / v_mag) * v_clip
                    v_y = (v_y / v_mag) * v_clip
                x0 += v_x
                y0 += v_y
                move_x = int(np.round(x0))
                move_y = int(np.round(y0))
                if x0 != move_x or y0 != move_y:
                    # This should wait for the mouse polling interval
                    pag.moveTo(x0 := move_x, y0 := move_y)

    def move_rel(self, x: int, y: int, dx: int = 0, dy: int = 0, **kwargs) -> None:
        """Move the mouse cursor in a human-like way in a relative frame.

        This function acts as a wrapper for `move_to`, allowing it to be used in a frame
        relative to something like a game window rather than the entire active screen.

        Note that if right-click menus are being cancelled due to erratic mouse
        movements, try reducing `dx` and `dy` as well as passing the `knotsCount` kwarg
        equal to 1 or 0 with this method call. Calling this method with `dx` and `dy`
        equal to 0 alongside a `knotsCount` equal to 0 will produce the most reliable
        results.

        Args:
            x (int): The horizontal distance to traverse relative to the current
                position of the mouse cursor.
            y (int): The relative vertical distance to traverse.
            dx (int): Used to define an interval of 2dx, centered on x, via which x may
                effectively be resampled. Defaults to 0.
            dy (int): Similarly defined as dx, but used for resampling y.
            **kwargs: Arbitrary keyword arguments used in the context of the pyclick
                module and the `HumanCurve` class.

        Notable Kwargs:
            knotsCount (int): Number of knots to use in the curve. The default amount
                is determined by the distance to the destination. Note that the lower
                the `knotsCount`, the more linear the movement, down to a minimum of 0.
            mouseSpeed: The speed of the mouse as it traverses the generated
                `HumanCurve`. Defaults to "fast". The possible choices are:
                - "slowest"
                - "slow"
                - "medium"
                - "fast"
                - "fastest"
            tween: The tweening function to use from pytweening. Defaults to
                `easeOutQuad`. To get a clarified visual understanding, see:
                https://derivative.ca/sites/default/files/field/image/Tweener_easing.gif
        """
        if dx:
            x += round(trunc_norm_samp(-dx, dx))
        if dy:
            y += round(trunc_norm_samp(-dy, dy))
        x0, y0 = pag.position()
        self.move_to((x0 + x, y0 + y), **kwargs)

    def click(
        self,
        button="left",
        hold_key: str = None,
        force_delay=True,
        check_red_click=False,
    ) -> None | bool:
        """Click on the current mouse cursor position.

        Args:
            button (str, optional): The mouse button to perform the click. Defaults to
                "left".
            hold_key (str, optional): If the name of a valid keyboard key is provided,
                the key will be held while the click is issued. Defaults to None.
            force_delay (bool, optional): Whether to force a delay between the
                down-click and up-click. By default, `force_delay` is True to instruct
                `click` to include a small time delay between the down-clicks and
                up-clicks it issues to provide humanization.
            check_red_click (bool, optional): Checks if the click produced a red X.
                This is useful in OSRS because the red X can indicate success or
                failure. Defaults to False.

        Returns:
            None | bool: None by default, or a boolean if checking for a red click
                (which returns True if the click was red, and False otherwise).
        """
        mouse_pos_before = pag.position()
        if hold_key:
            pag.keyDown(hold_key)
        pag.mouseDown(button=button)
        mouse_pos_after = pag.position()
        if force_delay:
            LOWER_BOUND_CLICK = 0.03  # Measured in milliseconds.
            UPPER_BOUND_CLICK = 0.2
            AVERAGE_CLICK = 0.06
            time.sleep(
                trunc_norm_samp(LOWER_BOUND_CLICK, UPPER_BOUND_CLICK, AVERAGE_CLICK)
            )
        pag.mouseUp(button=button)
        if hold_key:
            pag.keyUp(hold_key)
        if check_red_click:
            return self.__is_red_click(mouse_pos_before, mouse_pos_after)

    def right_click(self, force_delay=False):
        """Right-click on the current mouse position.

        Note that this is simply a wrapper for `click(button="right")`.

        Args:
            force_delay (bool, optional): Whether to force a delay in milliseconds
            between the right-click's associated down-click and up-click. Defaults to
            False.
        """
        self.click(button="right", force_delay=force_delay)

    def get_rect_around_point(self, mouse_pos: Point, pad: int) -> Rectangle:
        """Return a `Rectangle` around a `Point` with some padding.

        Args:
            mouse_pos (Point): The current position of the mouse cursor.
            pad (int): The amount to pad the `Rectangle` by, measured in pixels.

        Returns:
            Rectangle: The resultant `Rectangle` centered around the given `Point`.
        """
        max_x, max_y = pag.size()  # The full screen (i.e. monitor) dimensions.
        # As we create the `Rectangle`, using `max` and `min` ensures it's well-defined
        # within the boundaries of the screen.
        mouse_x, mouse_y = mouse_pos
        p1 = Point(max(mouse_x - pad, 0), max(mouse_y - pad, 0))
        p2 = Point(min(mouse_x + pad, max_x), min(mouse_y + pad, max_y))
        return Rectangle.from_points(p1, p2)

    def __is_red_click(self, mouse_pos_from: Point, mouse_pos_to: Point) -> bool:
        """Check if recent a click was red, indicating a successful action.

        Args:
            mouse_pos_from (Point): Mouse cursor position before the click.
            mouse_pos_to (Point): Mouse cursor position after the click.
        Returns:
            bool: True if the click was red, False otherwise (e.g. yellow).
        """
        CLICK_SPRITE_WIDTH_HALF = 7  # Measured in pixels.
        rect1 = self.get_rect_around_point(mouse_pos_from, CLICK_SPRITE_WIDTH_HALF)
        rect2 = self.get_rect_around_point(mouse_pos_to, CLICK_SPRITE_WIDTH_HALF)
        # Combine the two rectangles into a bigger rectangle.
        top_left_pos = Point(
            min(rect1.top_left.x, rect2.top_left.x),
            min(rect1.top_left.y, rect2.top_left.y),
        )
        bottom_right_pos = Point(
            max(rect1.bottom_right.x, rect2.bottom_right.x),
            max(rect1.bottom_right.y, rect2.bottom_right.y),
        )
        cursor_sct = Rectangle.from_points(top_left_pos, bottom_right_pos).screenshot()

        for click_sprite in ["red-1.png", "red-2.png", "red-3.png", "red-4.png"]:
            try:
                if imsearch.search_img_in_rect(
                    imsearch.BOT_IMAGES.joinpath("mouse_clicks", click_sprite),
                    cursor_sct,
                ):
                    return True
            except mss.ScreenShotError:
                print("Critical error. Failed to screenshot mouse cursor.")
                continue
        return False

    def __calculate_knots(self, destination: tuple) -> int:
        """Assign a number of knots for a Bezier curve based on destination distance.

        Note that the knot count is limited to 3 for any especially long distance.

        Args:
            destination (tuple): Cartesian coordinate of the destination.

        Returns:
            int: The number of knots to use in the generation of a Bezier curve to
                connect the current mouse cursor position to a desired destination
                coordinate. The number correspond to the `knotsCount` kwarg used in
                `move_to`.
        """
        distance = np.sqrt(
            (destination[0] - pag.position()[0]) ** 2
            + (destination[1] - pag.position()[1]) ** 2
        )
        return min(round(distance / 200), 3)

    def __get_mouse_speed(self, speed: str = "fast") -> int:
        """Get a speed in pixels/s for the traversal of a `targetPoints` list.

        Args:
            speed (str): The desired traversal speed in pixels per second. Choose from:
                - "slowest"
                - "slow"
                - "medium"
                - "fast"
                - "fastest"
                Defaults to "fast".

        Returns:
            int: A speed in pixels per second, randomly sampled from the appropriate
                range. Defaults to a speed sampled from the "fast" range if an invalid
                speed is provided.
        """
        speed_ranges = {
            "slowest": (85, 100),
            "slow": (65, 80),
            "medium": (45, 60),
            "fast": (20, 30),
            "fastest": (10, 15),
        }
        if speed in speed_ranges:
            min_speed, max_speed = speed_ranges[speed]
        return round(trunc_norm_samp(min_speed, max_speed))


if __name__ == "__main__":
    mouse = Mouse()
    points = [(1, 1), Point(765, 503), (1, 1), (300, 350), (400, 450), (234, 122)]
    speeds = ["slowest", "slow", "medium", "fast", "fastest", "invalid_speed"]
    traversal = dict(zip(points, speeds))
    for xy_tuple in traversal:
        mouse.move_to(xy_tuple)
        time.sleep(0.5)
    for _ in range(5):
        mouse.move_rel(x=50, y=50, dx=5, dy=5)
        time.sleep(0.5)
