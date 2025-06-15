import threading
import tkinter
import tkinter as tk
from pathlib import Path
from typing import Callable

import customtkinter as ctk
from PIL import Image, ImageTk

from utilities import settings
from utilities.sprite_scraper import SpriteScraper
from views.fonts import fonts as fnt

SCRAPER = SpriteScraper()

PATH_SRC = Path(__file__).parents[1]
PATH_IMG = PATH_SRC / "img"
PATH_UI = PATH_IMG / "ui"

DEFAULT_GRAY = ("gray50", "gray30")  # 50% white (50% black) and 30% white (70% black).
COLOR_HOVER = "#203a4f"  # Dark, muted blue.
IMG_SIZE = 24


class AuthView(ctk.CTkFrame):
    """A UI for the sprite scraper utility which scrapes online PNG item sprites."""

    def __init__(self, parent: ctk.CTkToplevel, on_success_callback: Callable) -> None:
        """Initialize a view for the Sprite Scraper utility.

        Args:
            parent (ctk.CTkToplevel):  The top-level customtkinter window.
        """
        super().__init__(parent)
        self.parent = parent
        self.on_success_callback = on_success_callback
        self.parent.protocol("WM_DELETE_WINDOW", self.__on_closing)
        self.parent.resizable(False, False)

        self._setup_grid()
        self._create_title_text()
        self._create_auth_info_text()
        self._create_subscription_key_entry_field()
        self._create_submit_button()
        self._create_output_log()

    # --- Sprite Scraper UI Creation Steps ---
    def _setup_grid(self) -> None:
        """Configure the grid layout for the UI components."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # - Title
        self.grid_rowconfigure(1, weight=0)  # - Auth Info Text
        self.grid_rowconfigure(2, weight=0)  # - Subscription Key Entry
        self.grid_rowconfigure(3, weight=0)  # - Submit
        self.grid_rowconfigure(4, weight=1)  # - Output Log

    def _create_title_text(self) -> None:
        """Create the main title text on the Auth view."""
        self.search_label = ctk.CTkLabel(
            self, text="Authentication", font=fnt.title_font(weight="normal")
        )
        self.search_label.grid(row=0, column=0, sticky="nsew", padx=0, pady=10)

    def _create_auth_info_text(self) -> None:
        """Create the instructional text for the Auth utility."""
        self.lbl_key = ctk.CTkLabel(
            master=self,
            text=("Submit your Runecolor subscription key to authenticate your client."),
            font=fnt.body_med_font(),
            anchor="w",
        )
        self.lbl_key.grid(row=1, column=0, sticky="ew", padx=0, pady=10)

    def _create_subscription_key_entry_field(self) -> None:
        """Create the subscription key text field."""
        self.entry_sub_key = ctk.CTkEntry(
            self,
            placeholder_text=" Enter your subscription key.",
            font=fnt.body_large_font(),
            corner_radius=0,
        )
        self.entry_sub_key.grid(row=2, column=0, sticky="esw", padx=0, pady=0)

    def _create_submit_button(self) -> None:
        """Create a button to submit subscription keys for authentication."""
        self.img_submit = ImageTk.PhotoImage(
            Image.open(PATH_UI / "submit.png").resize((IMG_SIZE, IMG_SIZE)),
            Image.LANCZOS,
        )
        self.btn_submit = ctk.CTkButton(
            self,
            text="Submit",
            image=self.img_submit,
            command=self.__on_submit,
            font=fnt.body_large_font(),
            height=64,
            corner_radius=0,
        )
        self.btn_submit.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, 0))

    def _create_output_log(self) -> None:
        """Create the output log to track the status of authentication.

        [TO DEV] Consider using an `output_log_frame` here to include a scrollbar.
        """
        self.log_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=0)
        self.log_frame.grid_rowconfigure(1, weight=1)

        self.txt_log = tkinter.Text(
            master=self.log_frame,
            font=fnt.log_font(),
            bg="#343638",
            fg="#ffffff",
        )
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.txt_log.configure(state=tkinter.DISABLED)
        self.log_frame.grid(row=4, column=0, sticky="nsew", padx=13, pady=13)

    # --- Handlers ---
    def __on_closing(self) -> None:
        """Handle the event where the auth window is closed (e.g. clicking X)."""
        self.parent.destroy()

    def _start_countdown(self, count: int) -> None:
        """Start a countdown for closing the auth window, updating the log each second.

        Args:
            countdown (int): The number of seconds remaining in the countdown.
        """
        if count > 0:
            msg = (
                "Subscription key cached. Your subscription key will be pre-loaded the "
                " next time Runecolor starts. Restart Runecolor to apply this change."
                f"\nWindow will close automatically in {count} seconds."
            )
            self.__update_log(msg, overwrite=True)
            # Schedule the next countdown update after 1 second
            self.after(1000, lambda: self._start_countdown(count - 1))
        else:
            # When countdown reaches 0, close the window and trigger the callback
            self.__update_log("Closing now...", overwrite=True)
            self.parent.after(500, self.parent.destroy)

    def __on_submit(self) -> None:
        """Handle the event where a subscription key is submitted."""
        subscription_key = self.entry_sub_key.get()
        thread = threading.Thread(
            target=self._submit_and_authenticate,
            kwargs={
                "subscription_key": subscription_key,
                "notify_callback": self.__update_log,
            },
            daemon=True,
        )

        def __on_auth_result(self, success: bool) -> None:
            """Callback to handle the result of the authentication.

            Args:
                success (bool): A boolean indicating whether the authentication was
                    successful. True if authenticated, False otherwise.
            """
            if success and self.on_success_callback:
                settings.set("subscription_key", subscription_key)
                self._start_countdown(3)
                self.on_success_callback()  # Trigger the callback in TitleView.
                self.parent.after(3000, self.parent.destroy)

        def __threaded_auth() -> None:
            """Run the authentication process in a separate thread.

            This method executes the auth process without blocking the UI and passes
            the result to `__on_auth_result` on the main thread using
            `self.parent.after`. The threaded process keeps the UI responsive if
            authentication takes a few seconds.
            """
            result = self._submit_and_authenticate(
                subscription_key=subscription_key,
                notify_callback=self.__update_log,
            )
            # Call the callback on the main thread. Delay 500ms for user reading time.
            self.parent.after(500, lambda: __on_auth_result(self, result))

        # Start the authentication in a new thread.
        thread = threading.Thread(target=__threaded_auth, daemon=True)
        self.__set_default_placeholder_text()
        self.entry_sub_key.bind("<FocusIn>", self.__clear_placeholder_text)
        self.entry_sub_key.bind("<FocusOut>", self.__add_placeholder_text)
        self.parent.focus()
        self.txt_log.configure(state=tkinter.NORMAL)
        # tkinter and customtkinter use 0-indexing for chars but 1-indexing for lines.
        # self.txt_log.delete("1.0", "end")  # Delete the previous line on update.
        self.txt_log.configure(state=tkinter.DISABLED)
        thread.start()

    def _submit_and_authenticate(self, subscription_key: str, **kwargs) -> bool:
        """Submit a Runecolor subscription key for authentication.

        Notable Kwargs:
            notify_callback (Callable): Callback function to notify the user. Defaults
                to `print`.

        Args:
            subscription_key (str): Runecolor subscription key.

        Returns:
            bool: True if successfully authenticated, False otherwise.
        """
        notify_callback = kwargs.get("notify_callback", print)
        if subscription_key != "osbc":
            notify_callback("Authentication failed.")
            return False
        notify_callback("Authentication successful.\n\n")  # Prevent overwrite.
        return True

    def __set_default_placeholder_text(self) -> None:
        """Set the default placeholder text for the subscription key entry field.

        Note that "end" is a special constant referring to the last char in the entry
        field. The line below deletes text in the entry field from char 0 to the end.
        """
        self.entry_sub_key.delete(0, "end")
        self.entry_sub_key.insert(0, " Enter your subscription key.")
        self.entry_sub_key.configure(text_color="grey")

    def __clear_placeholder_text(self, event: tk.Event) -> None:
        """Clear the placeholder text when the entry field gains focus.

        This method is triggered when the entry field is clicked or focused. It checks
        if the current content is the default placeholder text. If so, it clears the
        entry field to allow user input.

        Args:
            event (tk.Event): The event triggered when the entry field gains focus.
                While it is not used directly in this function, it is required by
                the binding.
        """
        if self.entry_sub_key.get() == " Enter your subscription key.":
            self.entry_sub_key.delete(0, "end")
            self.entry_sub_key.configure(text_color="white")

    def __add_placeholder_text(self, event: tk.Event) -> None:
        """Restore the placeholder text if the entry field is left empty.

        This method is triggered when the entry field loses focus. If the user leaves
        the field empty (i.e. no text is entered), the placeholder text is restored to
        guide the user.

        Args:
            event (tk.Event): The event triggered when the entry field loses focus.
                Although it is not directly used, it is required by the binding.
        """
        if self.entry_sub_key.get() == "":
            self.__set_default_placeholder_text()

    def __update_log(self, text: str, overwrite: bool = False) -> None:
        """Update the console log with the given text.

        Note that `tkinter` and `customtkinter` use 0-indexing for chars but 1-indexing
        for lines.

        Args:
            text (str): The desired text to append to the log.
            overwrite (bool): Whether to overwrite the previous line with the new one.
                Defaults to False.
        """
        self.txt_log.configure(state=tkinter.NORMAL)
        if overwrite:
            self.txt_log.delete("end-2l", "end")
        self.txt_log.insert("end", "\n" + text)
        self.txt_log.configure(state=tkinter.DISABLED)
        self.txt_log.see(tkinter.END)
