from pathlib import Path
from typing import Union

import cv2

from utilities.geometry import Point, Rectangle

PATH_SRC = Path(__file__).parents[1]
PATH_IMG = PATH_SRC / "img"
BOT_IMAGES = PATH_IMG / "bot"


def _search_img_in_img(template: cv2.Mat, im: cv2.Mat, confidence: float) -> Rectangle:
    """Locate a template image within a larger containing image.

    Note that the input images supplied to this function should be in BGR format for
    the base image and BGRA format for the template (i.e. sprite). This is because `cv2.
    matchTemplate` typically operates on BGRA images for matching so as not to lose
    alpha channel (i.e. transparency) information by switching to HSV.

    Args:
        template (cv2.Mat): The image (i.e. sprite, subsection, region) to search for
            as a BGRA image matrix array.
        im (cv2.Mat): The image to search within as a BGR image matrix array.
        confidence (float, optional): The acceptable confidence level of reporting a
            match (i.e. p-value), ranging from 0 to 1, where 0 is a perfect match.
            Defaults to 0.15.
    Returns:
        Rectangle: A Rectangle outlining the found template inside the image.
    """
    # If the image doesn't have an alpha channel, convert it from BGR to BGRA because
    # template matching can be affected by transparency.
    if len(template.shape) < 3 or template.shape[2] != 4:
        template = cv2.cvtColor(template, cv2.COLOR_BGR2BGRA)
    hh, ww = template.shape[:2]  # Get template dimensions.
    base = template[:, :, 0:3]  # Extract base image and alpha channel separately.
    alpha = template[:, :, 3]
    alpha = cv2.merge([alpha, alpha, alpha])
    correlation = cv2.matchTemplate(im, base, cv2.TM_SQDIFF_NORMED, mask=alpha)
    # Find the minimum value (best match) and its location in the correlation map.
    min_val, _, min_loc, _ = cv2.minMaxLoc(correlation)
    if min_val < confidence:
        # Proceed to create a `Rectangle` outlining the found template inside `im`.
        # Notice we're using a non-default, alternative constructor for this instance.
        return Rectangle.from_points(
            Point(min_loc[0], min_loc[1]), Point(min_loc[0] + ww, min_loc[1] + hh)
        )


def search_img_in_rect(
    img: Union[cv2.Mat, str, Path],
    rect: Union[Rectangle, cv2.Mat],
    confidence: float = 0.15,
    num_retries: int = 1,
) -> Union[Rectangle, None]:
    """Search for a smaller rectangular section within a larger rectangular image.

    Note that this function improves template matching with images (a.k.a. templates,
    or sprites) containing transparency. See: https://tinyurl.com/yckesp5k. Using
    `cv2.IMREAD_UNCHANGED` is critical for this method because many templates include
    an alpha channel (e.g. src/img/bot/ui_templates/minimap-fixed-classic.png).

    On a finer note, if a BGR-formatted image matrix (i.e `cv2.Mat`, which is very
    similar to a NumPy array) is supplied for the `rect` argument instead of a
    `Rectangle` and the `template` is found within it, the returned `Rectangle` will be
    relative to the top-left corner of the matrix and NOT the screen.

    In other words, the returned `Rectangle` will NOT be suitable for use with mouse
    movement/clicks, as it will be inappropriately positioned relative to its
    containing window. This does, however, still allow us to confirm whether or not the
    template was found. This is useful in cases when taking screenshots and
    subsequently verifying if a series of images is present or not.

    Args:
        img (Union[cv2.Mat, str, Path]): The image subsection (i.e. sprite) we're
            searching for. If provided as a string or a `Path`, the associated PNG
            image located at the given path will be dynamically loaded and converted
            into a BGR `cv2.Mat` array.
        rect (Union[Rectangle, cv2.Mat]): The larger image to search within.
        confidence (float, optional): The acceptable confidence level of reporting a
            match (i.e. p-value), ranging from 0 to 1, where 0 is a perfect match.
            Defaults to 0.15.
        num_retries (int, optional): The number of retries to perform. Defaults to 1.
            Note that with every retry, confidence is incremented by 0.01 to improve
            the probability of a match.

    Raises:
        ValueError: If the template image could not be read in correctly, raise a flag.

    Returns:
        Union[Rectangle, None]: A `Rectangle` outlining the found template image
            relative to the containing window, or None if the image was not found.

    Examples:
        deposit_all_btn = search_img_in_rect(
            BOT_IMAGES.joinpath("bank", "deposit.png"),
            self.win.game_view
        )
        if deposit_all_btn:
            self.mouse.move_to(deposit_all_btn.random_point())
            self.mouse.click()
    """
    img = str(img) if isinstance(img, Path) else img
    template = cv2.imread(img, cv2.IMREAD_UNCHANGED)
    if template is None:
        raise ValueError(f"Could not read in template: {img}")
    im = rect.screenshot() if isinstance(rect, Rectangle) else rect
    for _ in range(num_retries):
        if found_rect := _search_img_in_img(template, im, confidence):
            # Shift the found rectangle back into the live frame.
            if isinstance(rect, Rectangle):
                found_rect.left += rect.left
                found_rect.top += rect.top
            return found_rect
        confidence += 0.01
