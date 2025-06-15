from typing import TYPE_CHECKING

import customtkinter as ctk

from views.info_frame import InfoFrame
from views.output_log_frame import OutputLogFrame

if TYPE_CHECKING:
    from controller.bot_controller import BotController


class BotView(ctk.CTkFrame):
    """A custom frame that displays the main interface for a given `Bot`.

    This view consists of two primary sub-frames:
    - Top Half: Displays bot information (i.e., script title and description) and
        control buttons (`frame_info`).
    - Bottom Half: Shows a log for bot-related output and messages (`frame_output_log`).
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        """Initialize a new `BotView` frame with default UI components.

        The `BotView` frame includes an `InfoFrame` for displaying bot-related info and
        an `OutputLogFrame` for displaying log messages. After initialization, the view
        needs to be further configured by calling `set_controller` to link the
        appropriate controller and bot data.

        Args:
            parent (ctk.CTkFrame): The parent widget or frame that holds this `BotView`.
        """
        super().__init__(parent)

        # Configure a 3 row x 1 column grid layout.
        self.rowconfigure(
            0, weight=0, uniform="row_uniform"
        )  # The info row is not resizable.
        self.rowconfigure(2, weight=1)  # The row for the output log is resizable.
        self.columnconfigure(0, weight=1)

        # Configure the top half (script info and control buttons).
        self.frame_info = InfoFrame(parent=self, title="Title", info="Description")
        self.frame_info.configure(fg_color="#333333")
        self.frame_info.grid(row=0, column=0, pady=0, padx=0, sticky="nsew")

        # Configure the bottom half (bot output log).
        self.frame_output_log = OutputLogFrame(parent=self)
        self.frame_output_log.grid(row=2, column=0, pady=(0, 0), padx=0, sticky="nsew")
        self.frame_output_log.configure(fg_color="#333333")

        self.controller = None

    def set_controller(self, controller: "BotController") -> None:
        """Assign the provided `BotController` to the `BotView` and its child frames.

        This method connects the view to the bot's controller, allowing the `BotView`
        and its sub-frames (`InfoFrame` and `OutputLogFrame`) to update dynamically
        based on bot interactions.

        Args:
            controller (BotController): The controller managing the bot's state and
                behavior.
        """
        self.controller = controller
        self.frame_info.set_controller(controller=controller)
        self.frame_output_log.set_controller(controller=controller)
