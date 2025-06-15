from types import ModuleType
from typing import Dict, List, Literal, Tuple, Union

import cv2
import numpy as np

if __name__ == "__main__":
    import os
    import sys

    # Go up a level to facilitate importing from `utilities`.
    sys.path[0] = os.path.dirname(sys.path[0])

ColorTuple = Union[
    Tuple[Tuple[int, int, int], Tuple[int, int, int]], Tuple[int, int, int]
]


class Color:
    def __init__(
        self,
        tup: ColorTuple,
        name: str = None,
        fmt: Literal["rgb", "hsv", "bgr"] = "hsv",
    ) -> None:
        """Initialize a color or a color range in RGB, OpenCV-style HSV, or BGR format.

        HSV is favored in OpenCV for color-based segmentation as it separates color
        from brightness, enhancing robustness to lighting changes. Conversely, BGR is
        preferred for OCR tasks due to its direct provision of grayscale information,
        aiding thresholding and filtering reliability.

        Note importantly that OpenCV's HSV format ranges from 0 to 179 for hue and 0 to
        255 for saturation and value, while BGR has all channel intensities ranging
        from 0 to 255.

        For online color pickers, hue often ranges from 0 to 359 degrees. If confirming
        an HSV color tuple in such a picker, adjust hue from a 0 to 179 scale to a 0
        to 359 scale by multiplying by 2. Additionally, normalize saturation and value
        by dividing by 255 and multiplying by 100%.

        Useful websites:
            - https://colorpicker.me (HSV color codes confirmation)
            - https://www.rapidtables.com/web/color/RGB_Color.html (named colors)

        Args:
            tup (ColorTuple): Lower and upper bounds of the OpenCV-style color range.
                Upper bound not required if defining an exact color.
            name (str, optional): Name of the color. Defaults to None, resulting in a
                generic label with `fmt` prefixed.
            fmt (Literal["rgb", "hsv", "bgr"], optional): Color format of the provided
                tuple. Defaults to "hsv".
        """
        self.fmt = fmt
        if len(tup) == 3:  # This represents a single color tuple: Tuple[int, int, int]
            self.lo = np.array(tup)
            self.hi = self.lo
        if len(tup) == 2:  # Now we have a tuple of tuples, so the length is 2.
            self.lo = np.array(tup[0])
            self.hi = np.array(tup[1])
        self.name = name if name else f"{fmt}({self.lo}, {self.hi})"

    def convert_RGB2BGR(self) -> "Color":
        """Convert the given `Color` from RGB format to BGR format.

        This method inverts the order of the color channels RGB to BGR. It only applies
        if the current color format is RGB. Once converted, the color is stored in BGR
        format.

        Note that the `Color` return type is quoted as a string to indicate that it's a
        forward reference to the class being defined.

        Returns:
            Color: The modified `Color` object, with the format changed to BGR.
        """
        if self.fmt == "rgb":
            self.lo = self.lo[::-1]
            self.hi = self.hi[::-1]
            self.fmt = "bgr"
        return self

    def convert_BGR2RGB(self) -> "Color":
        """Convert the given `Color` from BGR format to RGB format.

        This method inverts the order of the color channels BGR to RGB. It only applies
        if the current color format is BGR. Once converted, the color is stored in RGB
        format.

        Returns:
            Color: The modified `Color` object, with the format changed to RGB.
        """
        if self.fmt == "bgr":
            self.lo = self.lo[::-1]
            self.hi = self.hi[::-1]
            self.fmt = "rgb"
        return self


class ColorFile:
    """A class that loads a file containing color definitions into an organized palette.

    The class reads a module-like file object containing color names and tuples
    representing color values. It then creates an instance of `Color` for each color
    and sets each listed color (or color range) within the file as an attribute of the
    class with the color's name.

    Attributes:
        fmt (str): The format of the color tuples (e.g., "hsv", "rgb", "bgr").
        colors (dict): A dictionary of color names as keys and `Color` objects as
            values.

    Args:
        file (ModuleType): A module-like object containing color definitions (e.g. a
            Python file like `colors_hsv.py`).
        fmt (str): What color format the color tuples follow: "hsv", "rgb", or "bgr".
    """

    def __init__(self, file: ModuleType, fmt: str) -> None:
        """Initialize a `ColorFile` instance by loading the colors from the given file.

        This method reads color data from the `file`, processes it, and sets each color
        as an attribute of the instance, using the color's name for the attribute name.

        Args:
            file (ModuleType): The file containing color definitions, where each color
                is represented as a tuple (or a tuple of tuples for color ranges).
            fmt (str): The format of the color tuples: "hsv", "rgb", or "bgr".
        """
        self.fmt = fmt
        self.colors = self.load_colors(file)
        for name, tup in self.colors.items():
            setattr(self, name, tup)

    def load_colors(self, file: ModuleType) -> Dict[str, Color]:
        """Load colors from a provided file and return a dictionary of `Color` objects.

        This method extracts color names and tuples from the given file, filters out
        special methods (i.e. those starting with `__`), and converts each tuple into a
        `Color` object. The result is a dictionary where the keys are color names and
        the values are `Color` objects.

        Args:
            file (ModuleType): The file containing color definitions, where each color
                is represented as a tuple (or tuple of tuples for color ranges).

        Returns:
            Dict[str, Color]: A dictionary with color names as keys and `Color` objects
                as values.
        """
        colors_raw = {
            name: tup for name, tup in vars(file).items() if not name.startswith("__")
        }
        return {name: Color(tup, name, self.fmt) for name, tup in colors_raw.items()}


class ColorFileHSV(ColorFile):
    """A subclass of `ColorFile` that loads colors in OpenCV-style HSV format.

    This class automatically initializes the `ColorFile` parent class with OpenCV-style
    HSV color format (H ranging from 0 to 179, S and V from 0 to 255).

    Args:
        file (ModuleType): A module-like object containing HSV color definitions.
    """

    def __init__(self, file: ModuleType) -> None:
        """Initialize the `ColorFileHSV` class by loading colors in the HSV format."""
        super().__init__(file, "hsv")


class ColorFileRGB(ColorFile):
    """A subclass of `ColorFile` that loads colors in RGB format.

    This class automatically initializes the `ColorFile` parent class with RGB color
    format (ranging from 0 to 255).

    Args:
        file (ModuleType): A module-like object containing RGB color definitions.
    """

    def __init__(self, file: ModuleType) -> None:
        """Initialize the `ColorFileRGB` class by loading colors in the RGB format."""
        super().__init__(file, "rgb")


class ColorFileBGR(ColorFileRGB):
    """A subclass of `ColorFileRGB` that converts RGB colors to the BGR format.

    This class loads RGB colors using the `ColorFileRGB` class and swaps their
    channels, converting them to the BGR format (ranging from 0 to 255).

    Args:
        file (ModuleType): A module-like object containing RGB color definitions.
    """

    def __init__(self, file: ModuleType) -> None:
        """Initialize the `ColorFileBGR` class by loading in RGB and converting to BGR.

        This method uses the `ColorFileRGB` class to load RGB colors, converts them to
        BGR using the `convert_RGB2BGR` method of the `Color` class, and stores them as
        attributes of the instance.
        """
        self.fmt = "bgr"
        self.rgb = ColorFileRGB(file)
        self.colors = {}
        for name, rgb_color in self.rgb.colors.items():
            bgr_color = rgb_color.convert_RGB2BGR()
            setattr(self, name, bgr_color)
            self.colors[name] = bgr_color


class ColorPalette:
    """A class that provides access to color palettes in HSV, RGB, and BGR formats.

    This class initializes three `ColorFile` objects, one for each color format (HSV,
    RGB, and BGR), by loading predefined color modules under `utilities.mappings`.
    These color palettes can be accessed via the `hsv`, `rgb`, and `bgr` attributes.

    Attributes:
        hsv (ColorFileHSV): The color palette in the HSV format.
        rgb (ColorFileRGB): The color palette in the RGB format.
        bgr (ColorFileBGR): The color palette in the BGR format.
    """

    def __init__(self) -> None:
        """Initialize a palette by loading each color in HSV, RGB, and BGR format."""
        from utilities.mappings import colors_hsv, colors_rgb

        self.hsv = ColorFileHSV(colors_hsv)
        self.rgb = ColorFileRGB(colors_rgb)
        self.bgr = ColorFileBGR(colors_rgb)


def isolate_colors(image: cv2.Mat, colors: Union[Color, List[Color]]) -> cv2.Mat:
    """Adjust an image to isolate color ranges to prep for OCR, then save the result.

    Recall that a mask is a binary image, where each pixel has a value of either 0
    (black) or 255 (white). This function performs a bitwise OR operation between the
    corresponding pixels of successive pairs of binary masks.

    BGR is preferred over HSV for OCR tasks due to its direct provision of grayscale
    information, aiding thresholding and filtering reliability, BGR images and colors
    should be provided as inputs.

    Note importantly that `cv2.inRange` is used to perform color thresholding here, and
    it expects the `lowerb` (lower bound) parameter to be less than or equal to the
    `upperb` (upper bound) parameter for each corresponding channel. If `color.lo` is
    not less than or equal to `color.hi` for a channel, `cv2.inRange` returns a black
    image because it cannot find any pixels that meet the thresholding criteria. This
    is avoided by ensuring the lower bound is always less than or equal to the upper
    bound for any given channel. For example:
        >>> color.lo
        array([200,  51, 255])
        >>> color.hi
        array([100, 250, 255])
        >>> np.minimum(color.lo, color.hi)
        array([100,  51, 255])
        >>> np.maximum(color.lo, color.hi)
        array([200, 250, 255])

    Args:
        image (cv2.Mat): The OpenCV-style BGR image matrix to process.
        colors (Union[Color, List[Color]]): A `Color` or list of `Color` objects to
            isolate. These colors should be in OpenCV-style BGR format.
    Returns:
        cv2.Mat: The image matrix with isolated color pixels as white and all others as
            black (i.e. the thresholded image or masked image). Note that this image
            matrix has no color format because it is black-and-white.
    """
    if not isinstance(colors, list):
        colors = [colors]
    # Generate a binary mask (i.e. black-and-white, not grayscale) for each provided
    # color.

    masks = []
    for color in colors:
        lo = np.minimum(color.lo, color.hi)
        hi = np.maximum(color.lo, color.hi)
        masks.append(cv2.inRange(image, lo, hi))
    nrows, ncols = image.shape[:2]  # Matrix dimensions are (nrows, cols, channels).
    # Create an all-black, single-channel image to start as the bask mask.
    mask = np.zeros([nrows, ncols, 1], dtype=np.uint8)
    # Apply each color mask to the base mask, incrementally changing pixels to white.
    for mask_ in masks:
        mask = cv2.bitwise_or(mask, mask_)
    return mask


def isolate_contours(image: cv2.Mat, color: Union[Color, List[Color]]) -> np.array:
    """Threshold a BGR image to isolate HSV-colored regions as filled-in contours.

    HSV color space is often preferred over BGR for finding contours in an image
    because of its better separation of color information from brightness. This
    separation makes it more robust to changes in lighting conditions, which can affect
    the appearance of objects in an image.

    Args:
        image (cv2.Mat):  BGR matrix image to threshold to `color`.
        color (Union[Color, List[Color]]): One or several HSV `Color` objects to
            isolate.

    Returns:
        np.array: The thresholded image with external contours (defining found
            `color`-colored objects) completely filled-in with white, and black
            everywhere else. Remember that a thresholded image has no color format.
    """
    # Convert from BGR to HSV color space.
    image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Create a mask with pixels within range as white and all others as black.
    mask = cv2.inRange(image, color.lo, color.hi)
    # Apply the `mask` to keep only colored pixels in `image` that correspond to white
    # pixels in `mask` (i.e. get the masked region, but with colored pixels).
    result = cv2.bitwise_and(image, image, mask=mask)
    result = cv2.cvtColor(result, cv2.COLOR_HSV2BGR)
    result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)  # Convert result to grayscale.
    # Threshold the result: pixel strength < 50 to black (0), >= 50 to white (255).
    _, result = cv2.threshold(result, 50, 255, cv2.THRESH_BINARY)
    # Find external contours, which are outlines or curves that represent the
    # boundaries of objects or regions within our (binary) thresholded image.
    contours, _ = cv2.findContours(result, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    black_image = np.zeros(result.shape, dtype="uint8")  # Create a black base image.
    for c in contours:  # Fill external contours white pixels if they are large enough.
        color_fill_bgr = (255, 255, 255) if cv2.contourArea(c) >= 25 else (0, 0, 0)
        cv2.drawContours(
            image=black_image,
            contours=[c],
            contourIdx=0,
            color=color_fill_bgr,
            thickness=-1,  # -1 means contours are filled rather than drawn as lines.
        )
    _, black_image = cv2.threshold(black_image, 0, 255, cv2.THRESH_BINARY)
    # Use the following line for troubleshooting:
    # cv2.imwrite("test.png", black_image)
    return black_image


if __name__ == "__main__":
    CP = ColorPalette()
    msg = (
        f"{CP.hsv.CYAN.fmt}: {CP.hsv.CYAN.name}, {CP.hsv.CYAN.lo}, {CP.hsv.CYAN.hi}\n"
        f"{CP.rgb.CYAN.fmt}: {CP.rgb.CYAN.name}, {CP.rgb.CYAN.lo}, {CP.rgb.CYAN.hi}\n"
        f"{CP.bgr.CYAN.fmt}: {CP.bgr.CYAN.name}, {CP.bgr.CYAN.lo}, {CP.bgr.CYAN.hi}"
    )
    print(msg)
