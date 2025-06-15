import tkinter
from typing import TYPE_CHECKING

import customtkinter as ctk

from views.fonts import fonts as fnt

if TYPE_CHECKING:
    from controller.bot_controller import BotController
    from views.bot_view import BotView


class OutputLogFrame(ctk.CTkFrame):
    """A 2 row x 1 column frame for console log output."""

    def __init__(self, parent: "BotView") -> None:
        """Initialize the `OutputLogFrame` with a grid layout and console log text box.

        This frame consists of a title label and a scrollable text box for displaying
        log messages, allowing users to view output from the script.

        Args:
            parent (BotView): The parent view that contains this frame.
        """
        super().__init__(parent)
        self.controller = None
        self._setup_grid()
        self._create_log_title_text()
        self._create_console_log_text_box()
        self._create_console_log_scrollbar()

    # --- Output Log UI Creation Steps ---
    def _setup_grid(self) -> None:
        """Set up the base 2x1 grid layout."""
        self.rowconfigure(0, weight=0)  # `weight=0` means fixed.
        self.rowconfigure(1, weight=1)  # Remember that `weight=1` means resizable.
        self.columnconfigure(0, weight=1)

    def _create_log_title_text(self) -> None:
        """Configure the title of the console log frame."""
        self.lbl_title = ctk.CTkLabel(
            master=self,
            text="Script Log",
            font=fnt.subheading_font(weight="normal"),
            justify=tkinter.LEFT,
        )
        self.lbl_title.grid(row=0, column=0, sticky="wns", padx=15, pady=15)

    def _create_console_log_text_box(self) -> None:
        """Create the text box to contain the console log output messages."""
        self.txt_log = tkinter.Text(
            master=self,
            wrap=tkinter.WORD,
            font=fnt.log_font(),
            bg="#343638",
            fg="#ffffff",
            padx=20,
            pady=5,
            spacing1=4,  # Spacing before a line.
            spacing3=4,  # Spacing after a line or after a wrapped line.
            cursor="arrow",
        )
        self.txt_log.grid(row=1, column=0, padx=(15, 0), pady=(0, 15), sticky="nsew")
        self.txt_log.configure(state=tkinter.DISABLED)

    def _create_console_log_scrollbar(self) -> None:
        """Configure the output log scrollbar."""
        self.scrollbar = ctk.CTkScrollbar(master=self, command=self.txt_log.yview)
        self.scrollbar.grid(row=1, column=1, padx=(0, 15), pady=(0, 15), sticky="ns")
        # Connect textbox scroll events to the scrollbar.
        self.txt_log.configure(yscrollcommand=self.scrollbar.set)

    # --- Output Log Main Methods ---
    def set_controller(self, controller: "BotController") -> None:
        """Set the the associated controller for the `OutputLogFrame`.

        Args:
            controller (BotController): The associated controller.
        """
        self.controller = controller

    def update_log(self, msg: str, overwrite: bool = False) -> None:
        """Update the console log with a new message.

        The controller tells the view to update the log, adding a new message to the
        console by either appending it or replacing the last line depending on the
        `overwrite` flag.

        Args:
            msg (str): The message to add to the console log.
            overwrite (bool, optional): If True, replaces the last log line with the
                new message. Defaults to False.
        """
        self.txt_log.configure(state=tkinter.NORMAL)
        if overwrite:
            self.txt_log.delete("end-1c linestart", "end")
        self.txt_log.insert(tkinter.END, "\n" + msg)
        self.txt_log.configure(state=tkinter.DISABLED)
        self.txt_log.see(tkinter.END)

    def clear_log(self) -> None:
        """Clear the log of all messages.

        The controller tells the view to clear the log.
        """
        self.txt_log.configure(state=tkinter.NORMAL)
        self.txt_log.delete(1.0, tkinter.END)
        self.txt_log.configure(state=tkinter.DISABLED)
        self.txt_log.see(tkinter.END)
