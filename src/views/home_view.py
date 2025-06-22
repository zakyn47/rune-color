from pathlib import Path

import customtkinter
from PIL import Image, ImageTk

from views.fonts import fonts as fnt

PATH_SRC = Path(__file__).parents[1]
PATH_IMG = PATH_SRC / "img"
PATH_UI = PATH_IMG / "ui"


class HomeView(customtkinter.CTkFrame):
    def __init__(self, parent, game_title: str) -> None:
        """Initialize a home screen for the selected script folder.

        Args:
            parent: The parent window.
            game_title (str): The title of the game (e.g. "OSRS").
        """
        super().__init__(parent)
        self.game_title = game_title
        self._setup_grid()
        self._create_title_text()
        self._create_welcome_text()
        self._create_home_logo()

    def _setup_grid(self) -> None:
        """Configure the grid layout for the UI components."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # - Title
        self.grid_rowconfigure(1, weight=0)  # - Note
        self.grid_rowconfigure(2, weight=1)  # - Logo

    def _create_title_text(self) -> None:
        """Create the title of the main home view"""
        self.label_title = customtkinter.CTkLabel(
            self, text=f"{self.game_title}", font=fnt.title_font()
        )
        self.label_title.grid(
            row=0, column=0, columnspan=3, sticky="nw", padx=15, pady=(15, 0)
        )

    def _create_welcome_text(self) -> None:
        """Create a label to display the main welcome and introduction."""
        self.txt_welcome = (
            "Welcome to Runecolor, a color botting framework for oldschool runescape.\n\nRunecolor is"
            " designed to develop gaming automation solutions that run while you sleep."
            " Each folder provides a range of script options, many of which include"
            " humanizing features such as:\n\n  - Randomized breaks for varying time"
            " intervals.\n  - Inefficient or randomized pathing.\n  - Curved-path"
            " cursor movement at variable speeds.\n  - Randomized mouse movements.\n  -"
            " Moderate zoom speeds at variable rates.\n  - Randomized inventory slot"
            " selection.\n\nThere's no guarantee any automation will go completely"
            " unnoticed. The best way to decide whether a bot seems human enough to fly"
            " under the radar is to watch it in action."
        )
        self.lbl_welcome = customtkinter.CTkLabel(
            master=self, text=self.txt_welcome, font=fnt.body_med_font(), justify="left"
        )
        self.lbl_welcome.bind(
            "<Configure>",
            lambda e: self.lbl_welcome.configure(
                wraplength=self.lbl_welcome.winfo_width() - 20
            ),
        )
        self.lbl_welcome.grid(row=1, column=0, sticky="nwe", padx=5, pady=(10, 10))

    def _create_home_logo(self) -> None:
        """Create and display the Home view splash art."""
        self.logo = ImageTk.PhotoImage(Image.open(str(PATH_UI / "logo.png")))
        self.label_logo = customtkinter.CTkLabel(self, image=self.logo, text="")
        self.label_logo.grid(
            row=2, column=0, columnspan=3, sticky="se", padx=15, pady=0
        )
