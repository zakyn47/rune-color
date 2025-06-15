from typing import List

import cv2
import numpy as np

from utilities.geometry import RuneLiteObject


def extract_contours(image: cv2.Mat) -> List[RuneLiteObject]:
    """Extract the white from an image as a list of `RuneLiteObject` elements.

    This function finds external contours (i.e. boundaries) of detected white objects
    within `image`. Note that the provided `image` should be a binary mask, and the any
    extracted contour is stored as a NumPy array of (x, y) coordinates.

    There are two types of contours, external and internal. External contours represent
    the boundaries of objects or regions, while internal contours delineate internal
    features or holes within objects. For example, given an image with multiple
    objects, the external contours will trace the outlines of those objects, forming
    the outer boundary of each object.

    On a finer note regarding `cv2.findContours`, the `RETR_EXTERNAL` retrieval method
    is a contour detection algorithm that only identifies external contours.
    Additionally, the `CHAIN_APPROX_NONE` method stores all the points along the
    contour boundary. This mode provides the maximum accuracy, but can be
    memory-intensive.

    Contrast this with the `CHAIN_APPROX_SIMPLE` method is a contour approximation
    algorithm that compresses horizontal, vertical, and diagonal line segments and
    leaves only their end points. For example, given a straight line, only the two
    endpoints of that line are kept, and the intermediate points are discarded.

    Args:
        image (cv2.Mat): The image to process, represented as a matrix with properties
            very similar to a NumPy array.
    Returns:
        List[RuneLiteObject]: A list of `RuneLiteObject` elements if white objects were
            found in the image, or an empty list if no objects were found.
    """
    contours, _ = cv2.findContours(
        image=image, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_NONE
    )

    objs: List[RuneLiteObject] = []

    for contour in contours:
        # Create a mask from the contour and find all points within the contour area.
        # Note that mask is made up of (y, x) coordinates because it feels more natural
        # to reference pixels in a rectangle via a row-column lookup style.
        mask = cv2.drawContours(
            np.zeros_like(image), [contour], -1, 255, thickness=cv2.FILLED
        )
        # Find all points within the contour area (including the boundary).
        domain = np.column_stack(np.where(mask == 255))  # These are (y, x) coordinates!
        x, y, width, height = cv2.boundingRect(contour)  # Bounding rectangle coords.
        area = width * height

        # If the area of the bounding rectangle is less that 125 x 125 pixels, consider
        # the entire object as its own `RuneLiteObject`.
        if area <= 125 * 125:
            objs.append(
                RuneLiteObject(
                    xmin=x,
                    xmax=x + width,
                    ymin=y,
                    ymax=y + height,
                    width=width,
                    height=height,
                    domain=domain,
                )
            )
        # If the area is large, divide it into 50 x 50 chunks to analyze separately.
        elif area > 125 * 125:
            chunk_width, chunk_height = 50, 50
            for i in range(0, height, chunk_height):
                for j in range(0, width, chunk_width):
                    sub_image = image[
                        y + i : y + i + chunk_height, x + j : x + j + chunk_width
                    ]
                    if cv2.countNonZero(sub_image) > 0:  # Check for white pixels.
                        x_offset, y_offset = x + j, y + i
                        sub_width, sub_height = (
                            min(chunk_width, width - j),
                            min(chunk_height, height - i),
                        )
                        objs.append(
                            RuneLiteObject(
                                xmin=x_offset,
                                xmax=x_offset + sub_width,
                                ymin=y_offset,
                                ymax=y_offset + sub_height,
                                width=sub_width,
                                height=sub_height,
                                domain=domain,  # Domain remains unchanged!
                            )
                        )
    return objs
