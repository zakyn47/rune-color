import threading
import tkinter
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk

from utilities.sprite_scraper import SpriteScraper
from views.fonts import fonts as fnt

SCRAPER = SpriteScraper()

PATH_SRC = Path(__file__).parents[1]
PATH_IMG = PATH_SRC / "img"
PATH_UI = PATH_IMG / "ui"

DEFAULT_GRAY = ("gray50", "gray30")  # 50% white (50% black) and 30% white (70% black).
COLOR_HOVER = "#203a4f"  # Dark, muted blue.
IMG_SIZE = 24


class SpriteScraperView(ctk.CTkFrame):
    """A UI for the sprite scraper utility which scrapes online PNG item sprites."""

    def __init__(self, parent: ctk.CTkToplevel) -> None:
        """Initialize a view for the Sprite Scraper utility.

        Args:
            parent (ctk.CTkToplevel):  The top-level customtkinter window.
        """
        super().__init__(parent)
        self.parent = parent
        self.parent.protocol("WM_DELETE_WINDOW", self.__on_closing)
        self.parent.resizable(False, False)

        self._setup_grid()
        self._create_title_text()
        self._create_search_info_text()
        self._create_radio_group()
        self._create_radio_buttons()
        self._create_radio_button_labels()
        self._create_search_entry_field()
        self._create_submit_button()
        self._create_output_log()

    # --- Sprite Scraper UI Creation Steps ---
    def _setup_grid(self) -> None:
        """Configure the grid layout for the UI components.

        Set the weight for the grid columns and rows to manage their resizing behavior.
        Specifically, this method configures:
            - Column 0 to expand with the window.
            - Rows for the title, search info, radio group, search entry, and submit
                button to have fixed heights.
            - Row 5 (logs) to expand with the window.
        """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # - Title
        self.grid_rowconfigure(1, weight=0)  # - Search Info
        self.grid_rowconfigure(2, weight=0)  # - Radio Group
        self.grid_rowconfigure(3, weight=0)  # - Search Entry
        self.grid_rowconfigure(4, weight=0)  # - Submit
        self.grid_rowconfigure(5, weight=1)  # - Logs

    def _create_title_text(self) -> None:
        """Create the main title text on the Sprite Scraper view."""
        self.search_label = ctk.CTkLabel(
            self, text="Scrape Item Sprites", font=fnt.title_font(weight="normal")
        )
        self.search_label.grid(
            row=0, column=0, columnspan=2, sticky="nsew", padx=0, pady=10
        )

    def _create_search_info_text(self) -> None:
        """Create the instructional text for the Sprite Scraper utility."""
        self.search_info = ctk.CTkLabel(
            self,
            text=(
                "Submit item names, separated by commas, to find and download matching"
                " image sprites from the OSRS Wiki. Choose to scrape normal sprites,"
                " bank-adjusted, or both."
            ),
            font=fnt.body_large_font(),
            justify="left",
            # height=50,
            wraplength=390,
        )
        self.search_info.grid(
            row=1, column=0, columnspan=2, sticky="nswe", padx=0, pady=10
        )

    def _create_radio_group(self) -> None:
        """Configure the main options as a group of radio buttons."""
        self.radio_group = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.radio_group.grid_columnconfigure(0, weight=1)
        self.radio_group.grid_columnconfigure(1, weight=1)
        self.radio_group.grid_rowconfigure(0, weight=1)
        self.radio_group.grid_rowconfigure(1, weight=1)
        self.radio_group.grid_rowconfigure(2, weight=1)
        self.radio_group.grid_rowconfigure(3, weight=1)
        self.radio_group.grid(columnspan=2)

    def _create_radio_buttons(self) -> None:
        """Create the radio buttons for sprite scraping options."""
        self.radio_var = tkinter.IntVar(self)
        self.radio_normal = ctk.CTkRadioButton(
            master=self.radio_group, text="", variable=self.radio_var, value=0
        )
        self.radio_bank = ctk.CTkRadioButton(
            master=self.radio_group, text="", variable=self.radio_var, value=1
        )
        self.radio_both = ctk.CTkRadioButton(
            master=self.radio_group, text="", variable=self.radio_var, value=2
        )
        self.radio_normal.grid(row=1, column=0, sticky="e", padx=0, pady=(20, 10))
        self.radio_bank.grid(row=2, column=0, sticky="e", padx=0, pady=10)
        self.radio_both.grid(row=3, column=0, sticky="e", padx=0, pady=(10, 20))

    def _create_radio_button_labels(self) -> None:
        """Label the main radio buttons appropriately."""
        self.lbl_radio_normal = ctk.CTkLabel(
            master=self.radio_group, text="Normal", font=fnt.body_large_font()
        )
        self.lbl_radio_bank = ctk.CTkLabel(
            master=self.radio_group, text="Bank", font=fnt.body_large_font()
        )
        self.lbl_radio_both = ctk.CTkLabel(
            master=self.radio_group, text="Normal + Bank", font=fnt.body_large_font()
        )
        self.lbl_radio_normal.grid(row=1, column=1, sticky="w", padx=10, pady=(20, 10))
        self.lbl_radio_bank.grid(row=2, column=1, sticky="w", padx=10, pady=10)
        self.lbl_radio_both.grid(row=3, column=1, sticky="w", padx=10, pady=(10, 20))

        self.radio_group.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 30))

    def _create_search_entry_field(self) -> None:
        """Create the user entry text field for item sprite names."""
        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text=" Enter item name(s) (e.g. abyssal whip, fire cape).",
            font=fnt.body_large_font(),
            corner_radius=0,
        )
        self.search_entry.grid(
            row=3, column=0, columnspan=2, sticky="esw", padx=0, pady=0
        )

    def _create_submit_button(self) -> None:
        """Create the submit button with which to submit search queries."""
        self.img_submit = ImageTk.PhotoImage(
            Image.open(PATH_UI / "submit.png").resize((IMG_SIZE, IMG_SIZE)),
            Image.LANCZOS,
        )
        self.search_submit_button = ctk.CTkButton(
            self,
            text="Submit",
            image=self.img_submit,
            command=self.__on_submit,
            font=fnt.body_large_font(),
            height=64,
            corner_radius=0,
        )
        self.search_submit_button.grid(
            row=4, column=0, columnspan=2, sticky="nsew", padx=0, pady=(0, 0)
        )

    def _create_output_log(self) -> None:
        """Create the output log to track the status of the Sprite Scraper."""
        self.log_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=0)
        self.log_frame.grid_rowconfigure(1, weight=1)

        self.txt_logs = tkinter.Text(
            master=self.log_frame,
            font=fnt.log_font(),
            bg="#343638",
            fg="#ffffff",
        )
        self.txt_logs.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.txt_logs.configure(state=tkinter.DISABLED)
        self.log_frame.grid(row=5, column=0, sticky="nsew", padx=13, pady=13)

        self.scrollbar = ctk.CTkScrollbar(master=self, command=self.txt_logs.yview)
        self.scrollbar.grid(row=5, column=1, padx=(0, 15), pady=15, sticky="ns")
        # Connect textbox scroll events to the scrollbar.
        self.txt_logs.configure(yscrollcommand=self.scrollbar.set)

    # --- Handlers ---
    def __on_closing(self) -> None:
        """Handle the event where the Sprite Scraper is closed (e.g. clicking X)."""
        self.parent.destroy()

    def __on_submit(self) -> None:
        """Handle the event where a search query is submitted."""
        search_string = self.search_entry.get()
        thread = threading.Thread(
            target=SCRAPER.search_and_download,
            kwargs={
                "search_string": search_string,
                "image_type": self.radio_var.get(),
                "notify_callback": self.__update_log,
            },
            daemon=True,
        )
        self.search_entry.delete(0, "end")
        self.txt_logs.configure(state=tkinter.NORMAL)
        # The following line would delete the previous log before adding new info.
        # self.txt_logs.delete("1.0", "end")
        self.txt_logs.configure(state=tkinter.DISABLED)
        thread.start()

    def __update_log(self, text: str) -> None:
        """Update the Sprite Scraper log with the given text.

        Args:
            text (str): The text with which to update the log.
        """
        self.txt_logs.configure(state=tkinter.NORMAL)
        self.txt_logs.insert("end", "\n" + text)
        self.txt_logs.configure(state=tkinter.DISABLED)
        self.txt_logs.see(tkinter.END)
