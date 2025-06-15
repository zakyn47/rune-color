from typing import Optional

import pywinctl
import pywintypes

from utilities.geometry import Point, Rectangle


class WindowInitializationError(Exception):
    """Exception raised for errors in the `Window` class."""

    def __init__(self, message: str = None) -> None:
        if message is None:
            message = (
                "Failed to initialize `Window`. Ensure nothing on-screen is blocking"
                " the game client window, the entire window is visible, and the client"
                " is in the appropriate layout (e.g. NOT in 'Resizable - Modern layout'"
                " for OSRS)."
            )
        super().__init__(message)


class Window:
    """A class that provides utilities for interacting with the game client window.

    It includes methods to map out the window's features and perform basic operations.
    All `Bot` classes contain a `Window` object, meant to enable the identification of
    key on-screen regions as `Rectangle` regions regardless of the game client's
    position.

    This class is designed for easy extension to incorporate additional functionality.
    For an example, see `model.runelite_window.RuneliteWindow`.
    """

    def __init__(self, window_title: str, padding_top: int, padding_left: int) -> None:
        """Initialize a `Window` object to interact with the client window.

        Args:
            window_title (str): The title of the client window.
            padding_top (str): The height of the client window's header.
            padding_left (str): The width of the client window's left border.
        """
        self.window_title = window_title
        self.padding_top = padding_top
        self.padding_left = padding_left

    @property
    def window(self) -> Optional[pywintypes.HANDLE]:
        """Retrieve the handle of the game client window.

        Raises:
            WindowInitializationError: Raised if no client window is found with a title
                matching `self.window_title`.

        Returns:
            Optional[pywintypes.HANDLE]: The handle of the `pywinctl.Window` object
                representing the game client if found, otherwise None. Note that the
                `pywinctl.Window` object is an aliased version of `pywinctl.Win32Window`.
        """

        # Attempt to get an exact match for the window title.
        self._client = pywinctl.getWindowsWithTitle(self.window_title)
        if self._client:
            return self._client[0]
        msg = f"No client window found matching name:\n\t{self.window_title}"
        raise WindowInitializationError(msg)

    def focus(self) -> None:
        """Focus the client window.

        In other words, make the game client the active window.

        Raises:
            WindowInitializationError: If the game client window cannot be focused.
        """
        if client := self.window:
            try:
                client.activate()
            except pywintypes.error as exc:
                msg = f"Failed to focus the game client window: {exc}"
                raise WindowInitializationError(msg)

    def position(self) -> Optional[Point]:
        """Get the origin (i.e. left-top corner) of the client window.

        Returns:
            Optional[Point]: The coordinate pair representing the top-left corner of the
                game client `Window` object, measured in pixels. Returns None if the
                client window is not open.
        """
        if client := self.window:
            return Point(client.left, client.top)

    def rectangle(self) -> Optional[Rectangle]:
        """Get a `Rectangle` outlining the client window.

        Returns:
            Optional[Rectangle]: The bounding `Rectangle` containing the game client
            `Window` object, measured in pixels. Returns None if the client window is
            not open.
        """
        if client := self.window:
            return Rectangle(client.left, client.top, client.width, client.height)

    def resize(self, width: int, height: int) -> None:
        """Resize the client window, keeping the top-left corner fixed.

        Args:
            width (int): The new width of the window.
            height (int): The new height of the window.
        """
        if client := self.window:
            client.size = (width, height)
