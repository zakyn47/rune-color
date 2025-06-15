import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import cv2

from model.runelite_window import RuneLiteWindow
from utilities import settings

PATH_SRC = Path(__file__).parents[1]
PATH_IMG = PATH_SRC / "img"
PATH_TEMP = PATH_IMG / "temp"


def current_time():
    """Get the current time as a formatted HH:MM:SS timestamp.

    Returns:
        str: The current time in HH:MM:SS format.
    """
    return datetime.now().strftime("%H:%M:%S")


def get_test_window() -> RuneLiteWindow:
    """Get an active (i.e. focused) `Window` object representing RuneLite.

    The `Window` is only returned if the RuneLite window is open, otherwise a
    `RuntimeError` is raised.

    Returns:
        RuneLiteWindow: A `RuneLiteWindow` object.

    Raises:
        RuntimeError: If the RuneLite window is not found.
    """
    win = RuneLiteWindow(f"RuneLite - {settings.get('username')}")
    win.focus()  # Focus the window, meaning select it to be the active one.
    time.sleep(0.5)
    if not win.initialize():  # Initialize the `RuneLiteWindow`.
        raise RuntimeError("RuneLite window not found.")
    return win


def save_image(filename: str, im: cv2.Mat) -> bool:
    """Save an image to the temporary image directory "./src/img/temp".

    Args:
        filename (str): The filename to save the image as (which must include a .png
            file extension).
        im (cv2.Mat): The image to save, converting from a matrix to a PNG file.

    Returns:
        bool: True if the image was saved successfully, False otherwise.
    """
    filepath = PATH_TEMP / filename
    cv2.imwrite(str(filepath), im)


def timer(func: Callable) -> Callable:
    """Print the time taken to execute a function.

    Note that this function is a decorator that may be inserted as @timer above a
    function definition to log the decorated function's execution time.

    Args:
        func (Callable): The function to time.

    Returns:
        Callable: The decorated function.
    """

    def wrapper(*args, **kwargs):
        start = time.time_ns() // 1_000_000
        result = func(*args, **kwargs)
        end = time.time_ns() // 1_000_000
        print(f"`{func.__name__}` took {round(end - start, 2)} ms.")
        return result

    return wrapper
