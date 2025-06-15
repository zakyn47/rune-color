import tkinter
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk
from PIL import Image, ImageTk
from pynput import keyboard

import utilities.settings as settings
from views.fonts import fonts as fnt

if TYPE_CHECKING:
    from controller.bot_controller import BotController
    from views.bot_view import BotView


PATH_SRC = Path(__file__).parents[1]
PATH_IMG = PATH_SRC / "img"
PATH_UI = PATH_IMG / "ui"
DEFAULT_GRAY = ("gray50", "gray30")  # 50% white (50% black) and 30% white (70% black).
COLOR_HOVER = "#203a4f"  # Dark, muted blue.


class InfoFrame(ctk.CTkFrame):
    listener = None
    pressed = False
    current_keys = set()
    combination_keys = settings.get("keybind") or [
        keyboard.Key.shift_l,
        keyboard.Key.enter,
    ]
    status = "stopped"

    def __init__(self, parent: "BotView", title: str, info: str) -> None:
        """Initialize an `InfoFrame` as a 5x2 frame of widgets.

        The following widgets are created:
            - script title (label)
            - script description (label)
            - script progress bar (progressbar)
            - right-side controls title (label)
            - right-side control buttons (buttons)

        Args:
            parent (BotView): The view representing the UI for a given `Bot`.
            title (str): The title of the bot.
            info (str): Information about the bot.
        """
        super().__init__(parent)
        self.title = title
        self.info = info
        self.controller = None  # The controller and script options are set later.
        self.options_class = None
        self._setup_grid()
        self._create_script_title_text()
        self._create_description_text()
        self._create_percentage_progress_text()
        self._create_script_progressbar()
        self._load_control_buttons()
        self._create_play_button()
        self._create_stop_button()
        self._create_options_button()
        self._create_status_text()

    def _setup_grid(self) -> None:
        """Set up the base grid layout."""
        self.rowconfigure((0, 2, 4, 5), weight=0)  # `weight=0` means static.
        self.rowconfigure((1, 3), weight=0)  # `weight=1` indicates resizable.
        self.columnconfigure(0, weight=1, minsize=200)
        self.columnconfigure(1, weight=0)

    def _create_script_title_text(self) -> None:
        """Create a label for the script title."""
        self.lbl_script_title = ctk.CTkLabel(
            master=self,
            text=self.title,
            font=fnt.title_font(),
            justify=tkinter.LEFT,
        )
        self.lbl_script_title.grid(column=0, row=0, sticky="wns", padx=20, pady=(15, 0))

    def _create_description_text(self) -> None:
        """Create a label for the associated bot description."""
        self.lbl_script_desc = ctk.CTkLabel(
            master=self,
            text=self.info,
            font=fnt.body_med_font(),
            justify="left",
            height=150,
        )
        self.lbl_script_desc.grid(column=0, row=2, sticky="nwe", padx=5)
        self.lbl_script_desc.bind(
            "<Configure>",
            lambda e: self.lbl_script_desc.configure(
                wraplength=self.lbl_script_desc.winfo_width() - 10
            ),
        )

    def _create_percentage_progress_text(self) -> None:
        """Create a label for script progress as a percentage."""
        self.lbl_progress = ctk.CTkLabel(
            master=self,
            text="Progress: 0%",
            font=fnt.small_font(),
            justify=tkinter.CENTER,
        )
        self.lbl_progress.grid(row=4, column=0, pady=(15, 0), sticky="ew")

    def _create_script_progressbar(self) -> None:
        """Create a progress bar object to visualize percentage completion."""
        self.progressbar = ctk.CTkProgressBar(master=self)
        self.progressbar.grid(row=5, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.progressbar.set(0)

    def _load_control_buttons(self) -> None:
        """Create the right-side control buttons on above the console log."""
        img_size = 18
        self.img_play = ImageTk.PhotoImage(
            Image.open(str(PATH_UI / "play.png")).resize((img_size, img_size)),
            Image.LANCZOS,
        )
        self.img_stop = ImageTk.PhotoImage(
            Image.open(str(PATH_UI / "stop.png")).resize((img_size, img_size)),
            Image.LANCZOS,
        )
        self.img_options = ImageTk.PhotoImage(
            Image.open(str(PATH_UI / "options.png")).resize((img_size, img_size)),
            Image.LANCZOS,
        )

        # Create a frame to contain the Play/Stop and Options buttons.
        self.btn_frame = ctk.CTkFrame(master=self, fg_color="#333333")
        self.btn_frame.rowconfigure((1, 2, 3), weight=0)  # Fixed size.
        self.btn_frame.rowconfigure((0, 4), weight=1)  # Resizable.
        self.btn_frame.grid(row=0, rowspan=4, column=1, padx=0, sticky="n")

    def _create_play_button(self) -> None:
        """Create and configure the Play button."""
        self.btn_play = ctk.CTkButton(
            master=self.btn_frame,
            text="Play",
            font=fnt.body_large_font(),
            text_color="white",
            height=64,
            image=self.img_play,
            command=self.__on_play_btn_clicked,
            corner_radius=0,
        )
        self.btn_play.bind(
            "<Enter>",
            lambda event: self.btn_play.configure(
                text=f"{settings.keybind_to_text(self.combination_keys)}"
            ),
        )
        self.btn_play.bind(
            "<Leave>", lambda event: self.btn_play.configure(text="Play")
        )
        self.btn_play.grid(row=1, column=0, pady=(0, 0), sticky="nsew")

    def _create_stop_button(self) -> None:
        """Create and configure the Stop button."""
        self.btn_stop = ctk.CTkButton(
            master=self.btn_frame,
            text="Stop",
            font=fnt.button_med_font(),
            text_color="white",
            fg_color="#910101",
            height=64,
            hover_color="#690101",
            image=self.img_stop,
            command=self.__on_stop_btn_clicked,
            corner_radius=0,
        )
        self.btn_stop.bind(
            "<Enter>",
            lambda event: self.btn_stop.configure(
                text=f"{settings.keybind_to_text(self.combination_keys)}"
            ),
        )
        self.btn_stop.bind(
            "<Leave>", lambda event: self.btn_stop.configure(text="Stop")
        )

    def _create_options_button(self) -> None:
        """Create and configure the Options button."""
        self.btn_options = ctk.CTkButton(
            master=self.btn_frame,
            text="Options",
            font=fnt.body_large_font(),
            text_color="white",
            height=64,
            fg_color=DEFAULT_GRAY,
            hover_color=COLOR_HOVER,
            image=self.img_options,
            command=self.__on_options_btn_clicked,
            corner_radius=0,
        )
        self.btn_options.grid(row=2, column=0, pady=0, sticky="nsew")

    def _create_status_text(self) -> None:
        """Create and configure the status label for the current Script view.

        Note that the possible bot statuses are Idle, Running, Stopped, Configuring, or
        Configured.
        """
        self.lbl_status = ctk.CTkLabel(
            master=self,
            text="Status: Idle",
            font=fnt.small_font(),
            justify=tkinter.CENTER,
        )
        self.lbl_status.grid(row=5, column=1, pady=(0, 15), sticky="we")

    # --- Setup ---
    def set_controller(self, controller: "BotController") -> None:
        """Set the the associated controller for the `InfoFrame` for this `Bot`.

        Args:
            controller (BotController): The associated controller.
        """
        self.controller = controller

    def setup(self, title: str, description: str) -> None:
        """Setup a default start configuration for an `InfoFrame` for this `Bot`."""
        self.lbl_script_title.configure(text=title)
        self.lbl_script_desc.configure(text=description)
        self.lbl_status.configure(text="Status: Idle")

    # --- Button Handlers ---
    def __on_play_btn_clicked(self) -> None:
        """Press play on the `BotController`."""
        self.controller.play()

    def __on_stop_btn_clicked(self) -> None:
        """Press stop on the `BotController`."""
        self.controller.stop()

    def __on_options_btn_clicked(self) -> None:
        """Press options on the `BotController`.

        This creates a new `CtkTopLevel` view to display bot options.
        """
        window = ctk.CTkToplevel(master=self)
        window.title("Options")
        window.protocol(
            "WM_DELETE_WINDOW", lambda arg=window: self.__on_options_closing(arg)
        )

        view = self.controller.get_options_view(parent=window)
        view.pack(side="top", fill="both", expand=True, padx=20, pady=20)
        window.after(
            100, window.lift
        )  # The 100ms wait is a workaround for the main window focusing first.

    def __on_options_closing(self, window) -> None:
        """Perform cleanup operations when the options window is closed."""
        self.controller.abort_options()
        window.destroy()

    # --- Keyboard Interrupt Handlers ---
    def start_keyboard_listener(self) -> None:
        """Start a `keyboard.Listener` to monitor key press and release events.

        This method initializes a keyboard listener that triggers corresponding actions
        based on specific key combinations. The listener runs in the background.
        """
        self.listener = keyboard.Listener(
            on_press=self.__on_key_press,
            on_release=self.__on_key_release,
        )
        self.listener.start()

    def stop_keyboard_listener(self) -> None:
        """Stop a `keyboard.Listener`.

        This method terminates an active keyboard listener that was started with the
        `start_keyboard_listener` method.
        """
        self.listener.stop()

    def __on_key_press(self, key: keyboard.Key) -> None:
        """Handle key press events.

        This method is called when a key is pressed. It adds the pressed key to the set
        of currently pressed keys and checks if a predefined combination of keys is
        active. Depending on the current status of the application, it may stop or
        start the controller.

        Args:
            key (keyboard.Key): The key that was pressed.
        """
        self.current_keys.add(key)

        if (
            all(k in self.current_keys for k in self.combination_keys)
            and not self.pressed
        ):
            self.pressed = True
            if self.status == "running":
                self.controller.stop()
            elif self.status == "stopped":
                self.controller.play()
                self.pressed = False
                self.current_keys.clear()

    def __on_key_release(self, key: keyboard.Key) -> None:
        """Handle key release events.

        This method is called when a key is released. It removes the released key from
        the set of currently pressed keys. If none of the combination keys are active,
        it resets the pressed state.

        Args:
            key (keyboard.Key): The key that was released.
        """
        self.current_keys.discard(key)
        if all(k not in self.current_keys for k in self.combination_keys):
            self.pressed = False

    # --- `BotView` Status Handlers ---
    def update_status_running(self) -> None:
        """Update the `BotView` to show that the `Bot` is running."""
        self.__toggle_buttons(True)
        self.btn_options.configure(state=tkinter.DISABLED)
        self.btn_play.grid_forget()
        self.btn_stop.grid(row=1, column=0, pady=(0, 0), sticky="nsew")
        self.lbl_status.configure(text="Status: Running")
        self.status = "running"

    def update_status_stopped(self) -> None:
        """Update the `BotView` to show that the `Bot` is stopped."""
        self.__toggle_buttons(True)
        self.btn_stop.grid_forget()
        self.btn_play.grid(row=1, column=0, pady=(0, 0), sticky="nsew")
        self.lbl_status.configure(text="Status: Stopped")
        self.status = "stopped"

    def update_status_configuring(self) -> None:
        """Update the `BotView` to show that the `Bot` is configuring."""
        self.__toggle_buttons(False)
        self.lbl_status.configure(text="Status: Configuring")

    def update_status_configured(self) -> None:
        """Update the `BotView` to show that the `Bot` is configured."""
        self.__toggle_buttons(True)
        self.lbl_status.configure(text="Status: Configured")

    def __toggle_buttons(self, enabled: bool) -> None:
        """Enable or disable the play/stop and options buttons.

        Args:
            enabled (bool): If True, the buttons will be enabled (i.e. a normal
                clickable state). If False, the buttons will be disabled (greyed out
                and unclickable).
        """
        if enabled:
            self.btn_play.configure(state=tkinter.NORMAL)
            self.btn_stop.configure(state=tkinter.NORMAL)
            self.btn_options.configure(state=tkinter.NORMAL)
        else:
            self.btn_play.configure(state=tkinter.DISABLED)
            self.btn_stop.configure(state=tkinter.DISABLED)
            self.btn_options.configure(state=tkinter.DISABLED)

    # --- Progress Bar Handlers ---
    def update_progress(self, progress: float) -> None:
        """Update the progress bar and completion percentage label on the `BotView`.

        The controller tells the view to update the progress bar and percentage label.

        Args:
            progress (float):  The script's progress, ranging from 0 (no progress) to 1
                (fully complete).
        """
        self.progressbar.set(progress)
        self.lbl_progress.configure(text=f"Progress: {progress*100:.0f}%")
