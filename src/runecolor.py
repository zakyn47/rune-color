import importlib
import tkinter
import sys
from pathlib import Path
from typing import List

import customtkinter as ctk
import pynput.keyboard as keyboard
from PIL import Image, ImageTk

sys.path.append(str(Path(__file__).parents[1]))
from runecolor_version import __version__

import utilities.settings as settings
from controller.bot_controller import BotController, MockBotController
from model import Bot, RuneLiteBot
from views import BotView, HomeView, TitleView
from views.fonts import fonts as fnt

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

PATH_SRC = Path(__file__).parents[0]
PATH_IMG = PATH_SRC / "img"
PATH_UI = PATH_IMG / "ui"

COLOR_HOVER = "#144870"  # Slate blue.
DEFAULT_GRAY = ("gray50", "gray30")  # 50% white (50% black) and 30% white (70% black).
PADX = 0
PADY = 0
IMG_SIZE = 24
IMG_SIZE_SMALL = 15


class ScrollableButtonFrame(ctk.CTkScrollableFrame):
    """A scrollable frame that dynamically loads and displays buttons for each bot.

    The displayed bot buttons belong to the selected game title. This class imports the
    appropriate module, finds all bot classes, and creates buttons for them.

    Attributes:
        buttons (List[ctk.CTkButton]): A list that stores the buttons corresponding to
            the bots loaded from a given game title's associated module in `src.model`.

    Args:
        master (ctk.CTkFrame): The parent frame where this scrollable frame is placed.
        width (int): The width of the scrollable frame in pixels.
        parent (App): The parent application (`App`), passed to maintain state across
            the UI.
        game_title (str): The title of the game, used to dynamically load the bots.
    """

    def __init__(
        self, master: ctk.CTkFrame, width: int, parent: "App", game_title: str
    ) -> None:
        """Initialize the scrollable button frame for a specific game title.

        This method dynamically loads bot classes for the selected game, creates
        buttons for each bot, and configures the scrollable frame.

        Args:
            master (ctk.CTkFrame): The parent frame within which to to embed the frame.
            width (int): The width of the scrollable frame in pixels.
            parent (App): The main application instance to manage UI state.
            game_title (str): The title of the game used to load its bot classes.
        """
        super().__init__(master, width=width)
        self.buttons: List = []
        self.grid_columnconfigure(0, weight=0)
        game_title = game_title.replace("-", "_").lower()  # Sanitize for import.
        # Dynamically import the module corresponding to the game title.
        module = importlib.import_module(f"model.{game_title}")
        names = dir(module)  # List of all imports (names) in the module.
        exclude = [] if parent.DEV_MODE else ["Screenshotter"]
        i = 2  # Start creating buttons from row 2 (skip heading and dropdown).
        for name in names:
            obj = getattr(module, name)  # Get the actual object (e.g. class).
            if (
                obj is not Bot
                and obj is not RuneLiteBot
                # The line below checks if `obj` is a class (rather than a normal
                # object or instance of a class).
                and isinstance(obj, type)
                and issubclass(obj, Bot)  # Check if it is a subclass of `Bot`.
                and obj.__name__ not in exclude
            ):
                instance = obj()  # Create an instance of the class.
                bot_key = obj.__name__  # Class of the object (e.g. "OSRSJeweler").
                name = instance.bot_title  # Name of the object (e.g. "Jeweler").
                btn = self._create_button_scrollable(name, bot_key, parent, i)
                self.buttons.append(btn)
                i += 1

    def _create_button_scrollable(
        self, name: str, bot_key: str, parent: "App", row_index: int
    ) -> ctk.CTkButton:
        """Helper function to create and place a button in the grid.

        Args:
            name (str): The display name of the bot (e.g. "Jeweler").
            bot_key (str): The class name of the bot (e.g. "OSRSJeweler").
            parent (App): The parent application (`App`), passed to maintain state.
            row_index (int): The current row index where the button will be placed.

        Returns:
            ctk.CTkButton: The configured button instance associated with the bot,
            ready to be displayed in the UI.
        """
        self.color_logo = ImageTk.PhotoImage(
            Image.open(PATH_UI / "color.png").resize((IMG_SIZE_SMALL, IMG_SIZE_SMALL)),
            Image.Resampling.LANCZOS,
        )
        img = self.color_logo if bot_key.lower() == "screenshotter" else None
        btn = ctk.CTkButton(
            master=self,
            text=name,
            fg_color=DEFAULT_GRAY,
            hover_color=COLOR_HOVER,
            hover=True,
            image=img,  # Put images next to script names if needed.
            command=lambda: self._toggle_bot_by_key(bot_key, btn, parent),
            corner_radius=0,
            state="normal",
            anchor="center",
            width=120 - 5,
        )
        btn.grid(row=row_index + 1, column=0, padx=0, pady=(0, 0), sticky="w")
        return btn

    def _toggle_bot_by_key(
        self, bot_key: str, btn_clicked: ctk.CTkButton, parent: "App"
    ) -> None:
        """Handle the event of the user selecting a bot from the dropdown menu.

        This method manages the state of the buttons in the left frame and the content
        displayed on the right side by reassigning the model to the controller.

        Args:
            bot_key (str): The key representing the selected bot in the `models` dict.
            btn_clicked (ctk.CTkButton): The button representing the selected bot.
            parent (App): The parent application (`App`), used to update the state and
                UI elements.
        """
        # Reset all buttons' `fg_color` to `DEFAULT_GRAY` except the clicked one.
        for btn in self.buttons:
            if btn != btn_clicked:
                btn.configure(fg_color=DEFAULT_GRAY)

        btn_clicked.configure(fg_color=COLOR_HOVER)
        parent.current_btn = btn_clicked

        bot_title = parent.models[bot_key].bot_title  # Bot name (e.g. "Jeweler").
        parent.current_btn = [
            btn for btn in parent.current_btn_list if btn._text == bot_title
        ][0]
        if parent.models[bot_key] is None:  # If no model exists, return early.
            return
        # If the selected bot's frame is already visible, hide it.
        if parent.controller.model == parent.models[bot_key]:
            parent.controller.model.progress = 0
            parent.controller.update_progress()
            parent.controller.change_model(None)
            parent.views["Script"].pack_forget()
            parent.current_title_view.pack(
                in_=parent.frame_right,
                side=tkinter.TOP,
                fill=tkinter.BOTH,
                expand=True,
                padx=PADX,
                pady=PADY,
            )
            # When hiding the home view, make sure to reset the clicked button's color.
            for btn in self.buttons:
                if btn == btn_clicked:
                    btn_clicked.configure(fg_color=DEFAULT_GRAY)
        # If we are starting from scratch, display the selected bot.
        elif parent.controller.model is None:
            parent.current_title_view.pack_forget()
            parent.controller.change_model(parent.models[bot_key])
            parent.views["Script"].pack(
                in_=parent.frame_right,
                side=tkinter.TOP,
                fill=tkinter.BOTH,
                expand=True,
                padx=PADX,
                pady=PADY,
            )
        # If switching from one bot to another, display the selected bot.
        else:
            parent.controller.model.progress = 0
            parent.controller.update_progress()
            parent.controller.change_model(parent.models[bot_key])


class App(ctk.CTk):
    """`App` is the main overall class for the Runecolor application.

    This class serves as the main entry point for the Runecolor bot automation
    application. It extends the `CTk` class from the `customtkinter` library to create
    a graphical user interface (GUI) for managing and running bots.

    Key Features:
    - Builds the main window and user interface components like a sidebar, home screen,
        and bot views.
    - Loads bot scripts dynamically from the `model` package and presents them in a
        grid-based layout.
    - Provides handlers for managing user interactions such as selecting bots,
        switching views, and starting/stopping bots.
    - Supports testing bot behaviors without a GUI by simulating keyboard inputs.

    Attributes:
        WIDTH (int): The default width of the main application window.
        HEIGHT (int): The default height of the main application window.
        DEV_MODE (bool): Determines if Runecolor runs in development mode (shows all
            buttons) or production mode (hides Color Filter and Scraper).
        img_home (ImageTk.PhotoImage): Home icon for the home button in the sidebar.
        color_logo (ImageTk.PhotoImage): Color logo for the bot buttons (loaded only if
            `test=False`).
        corner_icon (ImageTk.PhotoImage): Icon displayed in the window corner.
        frame_left (ctk.CTkFrame): Sidebar for game selection and bot options.
        frame_right (ctk.CTkFrame): Main content area for displaying bot views and
            scripts.
        views (dict[str, ctk.CTkFrame]): Dictionary of game views keyed by game title.
        models (dict[str, Bot]): Dictionary of bot models, keyed by bot class name.
        btn_map (dict[str, List[ctk.CTkButton]]): Dictionary mapping game titles to a
            list of bot buttons. This is the core model-view-controller mapping.
        current_title_view (ctk.CTkFrame): The currently active view on the right side
            of the window.
        current_btn (ctk.CTkButton): The currently active bot button in the sidebar.
        current_btn_list (List[ctk.CTkButton]): List of buttons for the currently
            selected game.
        scrollable_button_frame (ScrollableButtonFrame): The frame containing
            dynamically loaded bot buttons.
        subscription_key (str): Cached subscription key for user authentication.
        username (str): Cached username for user authentication.
        keybind (List[keyboard.Key]): Cached start/stop keybind for controlling bots.

    Args:
        test (bool, optional): If True, the application runs in test mode without
            loading certain UI elements. Defaults to False.
    """

    WIDTH = 654  # Set the minimum dimensions of the Home Screen.
    HEIGHT = 520
    DEV_MODE = True

    def __init__(self, test: bool = False) -> None:
        """Initialize the Runecolor application.

        This method sets up Runecolor in an unauthorized state by default, loads cached
        settings, and initializes the UI (unless in test mode).

        If `test` is set to `True`, loading images and building the UI is skipped,
        allowing for a lightweight, testing-friendly initialization.

        Args:
            test (bool, optional): Determines whether to initialize the application in
                test mode (without loading images or building the UI). Defaults to
                False.
        """
        super().__init__()
        self.auth = False  # Initialize Runecolor as unauthorized.
        self.subscription_key = settings.get("subscription_key")
        self.username = settings.get("username")
        self.load_cached_settings()  # Load settings from `src/settings.pickle`.
        if not test:
            # self.corner_icon = ImageTk.PhotoImage(file=PATH_UI / "logo-corner.ico")
            self.build_ui()

    def build_ui(self) -> None:
        """Build Runecolor's graphic user interface."""
        self.title("Runecolor")
        self.views: dict[str, ctk.CTkFrame] = (
            {}
        )  # All views as CTkFrame objects, keyed by game title.
        self.models: dict[str, Bot] = {}  # All models (bots), keyed by bot title.
        self.geometry(f"{App.WIDTH}x{App.HEIGHT}")
        self.update()
        self.minsize(self.winfo_width(), self.winfo_height())
        # Delay 201ms to avoid a bug where CTkToplevel re-applies the default icon
        # 200ms after instantiation. See: https://tinyurl.com/mvw55pkd
        self.after(
            201,
            lambda: self.iconbitmap(PATH_UI / "logo-corner.ico"),
        )
        self.protocol(
            "WM_DELETE_WINDOW", self.__on_closing
        )  # Always perform the same cleanup when the app closes.

        self._setup_grid()
        self._create_frame_left()
        self._create_frame_right()
        self._create_title_view()
        self._initialize_script_view()
        self._create_btn_map()
        self._create_menu_game_selector()
        self._create_home_btn()

        # Define status variables to track the states of views and buttons.
        self.current_title_view: ctk.CTkFrame = self.views["Home"]
        self.current_btn: ctk.CTkButton = None
        self.current_btn_list: List[ctk.CTkButton] = []

    # --- Main UI Creation Steps ---
    def _setup_grid(self) -> None:
        """Configure the Main Menu as a 1 row x 2 column grid layout."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _create_title_view(self) -> None:
        """Create the default view to display when Runecolor is first launched."""
        self.title_view = TitleView(parent=self.frame_right, main=self)
        self.title_view.pack(
            in_=self.frame_right,
            side=tkinter.TOP,
            fill=tkinter.BOTH,
            expand=True,
            padx=PADX,
            pady=PADY,
        )
        self.views["Home"] = self.title_view

    def _initialize_script_view(self) -> None:
        """Initialize the Script view and set up the controller for dynamic UI updates.

        `self.views["Script"]` holds a reference to the dynamically updated `BotView`
        displayed on `frame_right`. The displayed content changes depending on the
        model assigned to the controller.

        This code block is a critical component of the dynamic UI update process.
        Modifying it could break the connection between the view and controller.
        """
        self.views["Script"] = BotView(parent=self.frame_right)
        self.controller = BotController(model=None, view=self.views["Script"])
        self.views["Script"].set_controller(self.controller)

    def _create_frame_left(self) -> None:
        """Create and configure the Left-hand Sidebar (`frame_left`)."""
        self.frame_left = ctk.CTkFrame(
            master=self,
            width=180,  # Static minimum width for the left-hand sidebar.
            corner_radius=0,
        )
        # Give `frame_left` a grid layout, and then configure the rows.
        self.frame_left.grid(row=0, column=0, sticky="nswe", padx=PADX, pady=PADY)
        self.frame_left.grid_rowconfigure(
            0, minsize=10
        )  # Top padding above title (i.e. "Library") (adjusted by minsize).
        self.frame_left.grid_rowconfigure(
            18, weight=1
        )  # Resizable spacing between the Home dropdown menu and Home button below.
        self.frame_left.grid_rowconfigure(
            19, minsize=20
        )  # Top padding above Home button.
        self.frame_left.grid_rowconfigure(
            21, minsize=0
        )  # Bottom padding below Home button.

        # Add version label above Library
        self.lbl_version = ctk.CTkLabel(
            master=self.frame_left,
            text=f"Version: {__version__}",
            font=fnt.micro_font(),
            anchor="n",
        )
        self.lbl_version.grid(row=0, column=0, pady=(4, 0), padx=PADX)

        # Create a title label for `frame_left` and insert it as the 2nd-from-top row.
        self.lbl_frame_left = ctk.CTkLabel(
            master=self.frame_left,
            text="Library",
            font=fnt.title_font(),
            anchor="n",
        )
        self.lbl_frame_left.grid(row=1, column=0, pady=(4, 10), padx=PADX)

    def _create_frame_right(self) -> None:
        """Create and configure the Right-hand Main Menu (`frame_right`)."""
        self.frame_right = ctk.CTkFrame(
            master=self,
            corner_radius=0,
        )
        self.frame_right.grid(row=0, column=1, sticky="nswe", padx=PADX, pady=PADY)

    def _create_btn_map(self) -> None:
        """Configure the UI button map by dynamically importing all bot classes.

        The `btn_map` consists of key-value pairs of game titles and their associated
        list of their bots. Once the game title is selected, its list of bots
        populates below it.

        Ensure all bots are referenced in their folder's `__init__.py` for proper
        loading (e.g. `src.model.osrs.__init__.py`).
        """
        self.btn_map: dict[str, List[ctk.CTkButton]] = {
            "Home": [],  # Note that Home has no bots, so it has no buttons.
        }
        module = importlib.import_module("model")
        names = dir(module)  # List of names of all imports in `module`.
        exclude = [] if self.DEV_MODE else ["Screenshotter"]
        for name in names:
            obj = getattr(module, name)  # Get the actual object (e.g. function, class).
            if (
                obj is not Bot
                and obj is not RuneLiteBot
                # The line below checks if `obj` is a class (rather than a normal
                # object or instance of a class).
                and isinstance(obj, type)
                and issubclass(obj, Bot)
                and obj.__name__ not in exclude
            ):  # If we are evaluating one of our custom bots (e.g. Jeweler)...
                instance = obj()
                # Make a home view if one doesn't exist.
                if (
                    isinstance(instance, RuneLiteBot)
                    and instance.game_title not in self.views
                ):
                    runelite_home_view = HomeView(
                        parent=self,
                        game_title=instance.game_title,
                    )
                    runelite_home_view.configure(fg_color="#333333")
                    self.views[instance.game_title] = runelite_home_view
                # Make a button section if one doesn't exist.
                if instance.game_title not in self.btn_map:
                    self.btn_map[instance.game_title] = []
                instance.set_controller(self.controller)
                self.models[name] = instance
                self.btn_map[instance.game_title].append(
                    self._create_button_placeholder(bot_key=name)
                )

    def _create_menu_game_selector(self) -> None:
        """Configure the dropdown menu for selecting a game title."""
        self.menu_game_selector = ctk.CTkOptionMenu(
            master=self.frame_left,
            values=list(self.btn_map.keys()),
            command=self.__on_game_selector_change,
            corner_radius=0,
            anchor="center",
            font=fnt.body_med_font(),
            state="disabled",
        )
        self.menu_game_selector.grid(row=2, column=0, sticky="we", padx=PADX, pady=PADY)

    def _create_home_btn(self) -> None:
        """Set up the Home button to return the user to the main screen."""
        self.img_home = ImageTk.PhotoImage(
            Image.open(PATH_UI / "home.png").resize((IMG_SIZE, IMG_SIZE)),
            Image.Resampling.LANCZOS,
        )
        self.btn_home = ctk.CTkButton(
            master=self.frame_left,
            image=self.img_home,
            corner_radius=0,
            height=64,
            compound="left",
            font=fnt.body_large_font(),
            text="Home",
            command=self.__on_home_clicked,
            state="disabled",
        )
        self.btn_home.grid(row=20, column=0, pady=(5, 0), padx=PADX)

    # --- UI Creation Helpers ---
    def _create_button_placeholder(self, bot_key: str) -> ctk.CTkButton:
        """Create a pre-configured button for a bot.

        Note that these buttons are never directly clicked, but are instead set up as
        dummies to configure `self.btn_map`, the central mapping that connects the
        model, view, and controller.

        Args:
            bot_key (str): The name of the bot as it exists in the `models` mapping.
        Returns:
            (ctk.CTkButton): Button for the associated bot name.
        """
        btn = ctk.CTkButton(
            master=self.frame_left,
            text=self.models[bot_key].bot_title,
            fg_color=DEFAULT_GRAY,
            corner_radius=0,
            state="disabled",
        )
        return btn

    # --- Load Cached Settings ---
    def load_cached_settings(self) -> None:
        """Initialize default application-wide settings.

        Right now this only initializes the default Start/Stop keybind, but can be
        expanded later.
        """
        self.subscription_key = settings.get("subscription_key")
        self.username = settings.get("username")
        self.keybind = settings.get("keybind")
        msg = (
            f"{'[CACHED SETTINGS]':>20}"
            f"\n{'Subscription Key:':>20} {self.subscription_key}"
            f"\n{'Username:':>20} {self.username}"
            f"\n{'Start/Stop Keybind:':>20} {settings.keybind_to_text(self.keybind)}"
        )
        print(msg)
        if self.keybind is None:  # Default to Right Shift + Enter.
            settings.set("keybind", [keyboard.Key.shift_r, keyboard.Key.enter])

    # --- Button Handlers ---
    def __on_home_clicked(self) -> None:
        """Return to the Home screen after the associated button is clicked."""
        # Un-highlight the current button.
        if self.current_btn is not None:
            self.current_btn.configure(fg_color=DEFAULT_GRAY)
            self.current_btn = None
        # Unpack the current buttons.
        if (
            hasattr(self, "scrollable_button_frame")
            and self.scrollable_button_frame is not None
        ):
            self.scrollable_button_frame.grid_forget()
        if self.current_btn_list is not None:
            for btn in self.current_btn_list:
                btn.grid_forget()
        # Unpack the current script view.
        if self.views["Script"].winfo_exists():
            self.views["Script"].pack_forget()
        # Unlink the model from the controller.
        self.controller.change_model(None)
        # Pack new buttons.
        self.current_btn_list = self.btn_map["Home"]
        # Start from 3 since Spacing, "Library", and the Dropdown take up Rows 1-3.
        for r, btn in enumerate(self.current_btn_list, 3):
            btn.grid(row=r, column=0, sticky="we", padx=PADX, pady=PADY)
        # Repack the new home view.
        self.current_title_view.pack_forget()
        self.menu_game_selector._text_label["text"] = "Home"
        self.current_title_view = self.views["Home"]
        self.current_title_view.pack(
            in_=self.frame_right,
            side=tkinter.TOP,
            fill=tkinter.BOTH,
            expand=True,
            padx=PADX,
            pady=PADY,
        )

    def __on_game_selector_change(self, choice: str) -> None:
        """Handle the event when the user selects a game title from the dropdown menu.

        Args:
            choice (str): The name of the game as it exists in the `views` mapping.
        """
        if choice not in list(self.btn_map.keys()):
            return
        # Unpack the current buttons.
        if self.current_btn_list is not None:
            for btn in self.current_btn_list:
                btn.grid_forget()
        # Remove any previous scrollable button frames.
        if (
            hasattr(self, "scrollable_button_frame")
            and self.scrollable_button_frame is not None
        ):
            self.scrollable_button_frame.grid_forget()
        # Unpack the current script view.
        if self.views["Script"].winfo_exists():
            self.views["Script"].pack_forget()
        # Unlink the model from the controller.
        self.controller.change_model(None)
        # Pack new buttons.
        self.current_btn_list = self.btn_map[choice]

        if choice == "Home":
            self.__on_home_clicked()
        if choice != "Home":
            # Create the scrollable button frame and populate with buttons.
            self.scrollable_button_frame = ScrollableButtonFrame(
                master=self.frame_left,
                parent=self,
                game_title=choice,
                width=120,
            )
            self.scrollable_button_frame.grid(
                row=3, column=0, sticky="we", padx=PADX, pady=PADY
            )

        # Repack the new home view.
        self.current_title_view.pack_forget()
        self.current_title_view = self.views[choice]
        self.current_title_view.pack(
            in_=self.frame_right,
            side=tkinter.TOP,
            fill=tkinter.BOTH,
            expand=True,
            padx=PADX,
            pady=PADY,
        )

    # --- Misc Handlers ---
    def __on_closing(self) -> None:
        """Handle the event where Runecolor is closed (e.g. Alt + F4 or clicking X.)"""
        self.destroy()

    def start(self) -> None:
        """Handle the event where Runecolor is executed, prompting the GUI to appear."""
        self.mainloop()

    # --- UI-less Test Functions ---
    def test(self, bot: Bot) -> None:
        """Test the behavior of a `Bot` instance without a UI.

        This method configures the provided `Bot` to use a mock controller. It
        simulates user input via a keyboard listener. The `Bot` is then started and can
        be controlled by pressing the left control key.

        Args:
            bot (Bot): The `Bot` instance to be tested.
        """
        bot.set_controller(MockBotController(bot))
        bot.options_set = True  # Mark bot options as set to avoid prompting for them.
        # Configure a `keyboard.Listener`` to detect key presses.
        self.listener = keyboard.Listener(
            on_press=lambda event: self.__on_press(event, bot),
            on_release=None,
        )
        self.listener.start()  # Start the listener.
        bot.play()  # Start the bot.
        self.listener.join()  # Wait for the listener to finish before continuing.

    def __on_press(self, key: keyboard.Key, bot: Bot) -> None:
        """Handle the press of a keyboard key during bot testing.

        This function listens for a left-control key press to stop the bot's thread.
        Once the key is pressed, the bot is stopped, and then the keyboard listener is
        terminated.

        Args:
            key (keyboard.Key): The key that was pressed on the keyboard.
            bot (Bot): The `Bot` instance being tested.
        """
        if key == keyboard.Key.ctrl_l:
            bot.thread.stop()
            self.listener.stop()


if __name__ == "__main__":
    # Follow this example to test without the GUI. Press Left-Ctrl to stop.
    run_without_gui = False
    if run_without_gui:
        from model.osrs.izy_chopper import IzyChopper

        app = App(test=True)
        app.test(IzyChopper())

    app = App()
    app.start()
