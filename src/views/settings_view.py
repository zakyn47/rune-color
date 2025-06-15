import contextlib
from pathlib import Path

import customtkinter as ctk
import pynput.keyboard as keyboard
from PIL import Image, ImageTk

import utilities.settings as settings
from views.fonts import fonts as fnt

PATH_SRC = Path(__file__).parents[1]
PATH_IMG = PATH_SRC / "img"
PATH_UI = PATH_IMG / "ui"

DEFAULT_GRAY = ("gray50", "gray30")  # 50% white (50% black) and 30% white (70% black).
COLOR_HOVER = "#203a4f"  # Dark, muted blue.
IMG_SIZE = 18


class SettingsView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkToplevel) -> None:
        """Initialize a `SettingsView` for changing the Start/Stop keybind.

        This class manages the GUI interface for setting and saving keybinds. It
        creates and arranges widgets for displaying current keybinds, taking new
        inputs, and saving the changes.

        Args:
            parent (ctk.CTkToplevel): The top-level customtkinter window.
        """
        super().__init__(parent)
        self.parent = parent
        self.parent.protocol("WM_DELETE_WINDOW", self.__on_closing)
        self.entry_username = settings.get("username")
        self.current_keybind = settings.get("keybind")  # List of keyboard.Key objects.
        self.parent.resizable(False, False)
        self._setup_grid()
        self._load_button_icons()
        self._create_keybind_title()
        self._create_keybind_frame()
        self._create_username_title()
        self._create_username_frame()
        self._create_restart_instructions()
        self._create_save_button()

    # --- Settings View UI Creation Steps ---
    def _setup_grid(self) -> None:
        """Set up the base 3x1 grid layout."""
        self.grid_rowconfigure(0, weight=0)  # Fixed Keybind Title
        self.grid_rowconfigure(1, weight=0)  # Fixed Keybind Frame Row
        self.grid_rowconfigure(2, weight=0)  # Fixed Username Title
        self.grid_rowconfigure(3, weight=0)  # Fixed Username Frame Row
        self.grid_rowconfigure(4, weight=0)  # Fixed Restart Instructions
        self.grid_rowconfigure(5, weight=0)  # Fixed Save Button
        self.grid_columnconfigure(0, weight=1)

    def _create_keybind_title(self) -> None:
        """Create title text for the keybind entry."""
        self.lbl_keybind_title = ctk.CTkLabel(
            master=self,
            width=564,
            text="\n  Start/Stop Keybind",
            font=fnt.heading_font(),
            anchor="w",
            justify="left",
            fg_color="#333333",
        )
        self.lbl_keybind_title.grid(row=0, column=0, columnspan=1, sticky="nsw")

    def _create_keybind_frame(self) -> None:
        """Create the main keybind frame at the top of the Settings view."""
        self.frame_keybind = ctk.CTkFrame(master=self, width=564, height=120)

        # Split the Keybind Frame into a 1x3 array of cells.
        self.frame_keybind.rowconfigure(0, weight=0)
        self.frame_keybind.columnconfigure(0, weight=0)  # General instructions.
        self.frame_keybind.columnconfigure(1, weight=0)  # Symbolic entry text.
        self.frame_keybind.columnconfigure(2, weight=0)  # Edit/Set button.
        self.frame_keybind.grid_propagate(False)  # Prevent cell resizing.
        note = (
            "To adjust the Start/Stop Keybind:"
            "\n    1. Click 'Edit' to enable key input."
            "\n    2. Press 'Esc' to clear input."
            "\n    3. Enter the new keybind."
            "\n    4. Click 'Set' to set it."
        )
        self.lbl_keybind = ctk.CTkLabel(
            master=self.frame_keybind,
            text=note,
            justify="left",
            font=fnt.body_med_font(),
            anchor="w",
            width=269,  # This width pushes the Entry and Button snugly to the right.
        )
        txt_keybind = (
            settings.keybind_to_text(self.current_keybind)
            if self.current_keybind
            else "None"
        )
        self.entry_keybind = ctk.CTkLabel(
            master=self.frame_keybind,
            text=txt_keybind,
            fg_color="#2b2b2b",
            font=fnt.heading_font(),
            height=64,
            width=133,
            anchor="center",
            wraplength=120,
        )
        self.btn_keybinds = ctk.CTkButton(
            master=self.frame_keybind,
            image=self.img_edit,
            compound="left",
            text="Edit",
            font=fnt.body_large_font(),
            height=64,
            width=133,
            corner_radius=0,
            command=self.__on_modify_keybind,
        )
        self.lbl_keybind.grid(
            row=0, column=0, padx=(15, 15), pady=(15, 15), sticky="nw"
        )
        self.entry_keybind.grid(row=0, column=1, padx=(0, 0), pady=0, sticky="we")
        self.btn_keybinds.grid(row=0, column=2, padx=0, pady=0, sticky="we")
        self.frame_keybind.grid(row=1, column=0, columnspan=1, sticky="n")

    def _create_username_title(self) -> None:
        """Create title text for the username entry."""
        self.lbl_username_title = ctk.CTkLabel(
            master=self,
            width=564,
            text="  Username",
            font=fnt.heading_font(),
            anchor="w",
            justify="left",
            fg_color="#333333",
        )
        self.lbl_username_title.grid(row=2, column=0, columnspan=1, sticky="nw")

    def _create_restart_instructions(self) -> None:
        """Create instructional text about restarting RuneDark to apply changes."""
        self.lbl_restart = ctk.CTkLabel(
            master=self,
            width=564,
            text="  Restart RuneDark after saving to apply changes.\n",
            font=fnt.heading_font(),
            anchor="center",
            justify="left",
            fg_color="#333333",
        )
        self.lbl_restart.grid(row=4, column=0, columnspan=1, sticky="nw")

    def _create_username_frame(self) -> None:
        """Create the main keybind frame at the top of the Settings view."""
        self.frame_username = ctk.CTkFrame(
            master=self, width=564, height=64
        )  # This width matches the width of the parent window.

        # Split the Keybind Frame into a 1x2 array of cells.
        self.frame_username.columnconfigure(0, weight=0)  # General instructions.
        self.frame_username.columnconfigure(1, weight=1)  # Entry text.
        self.frame_username.grid_propagate(False)  # Prevent cell resizing.
        note = "To edit your Username:"
        self.lbl_username = ctk.CTkLabel(
            master=self.frame_username,
            text=note,
            justify="left",
            font=fnt.body_med_font(),
        )
        self.entry_username = ctk.CTkEntry(
            master=self.frame_username,
            placeholder_text=" Enter your username.",
            font=fnt.body_large_font(),
            corner_radius=0,
        )
        self.lbl_username.grid(row=0, column=0, padx=(15, 15), pady=5, sticky="w")
        self.entry_username.grid(row=0, column=1, padx=(0, 15), pady=0, sticky="we")
        self.frame_username.grid(row=3, column=0, columnspan=1)

    def _load_button_icons(self) -> None:
        """Load relevant icons and standardize their sizes."""
        self.img_edit = ImageTk.PhotoImage(
            Image.open(PATH_UI / "edit.png").resize(
                (IMG_SIZE, IMG_SIZE), Image.Resampling.LANCZOS
            )
        )
        self.img_check = ImageTk.PhotoImage(
            Image.open(PATH_UI / "check.png").resize(
                (IMG_SIZE, IMG_SIZE), Image.Resampling.LANCZOS
            )
        )
        self.img_save = ImageTk.PhotoImage(
            Image.open(PATH_UI / "save.png").resize(
                (IMG_SIZE, IMG_SIZE), Image.Resampling.LANCZOS
            )
        )

    def _create_save_button(self) -> None:
        """Create a Save button that closes the Settings window upon click."""
        self.btn_save = ctk.CTkButton(
            master=self,
            text="Save",
            image=self.img_save,
            compound="left",
            corner_radius=0,
            height=64,
            font=fnt.body_large_font(),
            command=lambda: self.save(window=self.parent),
        )
        self.btn_save.grid(row=5, column=0, columnspan=2, pady=0, padx=0, sticky="swe")

    # --- Keyboard Interrupt Handlers ---
    def start_keyboard_listener(self) -> None:
        """Start listening for key presses to capture new keybind input."""
        self.listener = keyboard.Listener(
            on_press=self.__on_press,
            on_release=self.__on_release,
        )
        self.listener.start()

    def stop_keyboard_listener(self) -> None:
        """Stop the keyboard listener, preventing further key input."""
        with contextlib.suppress(AttributeError):
            self.listener.stop()

    def __on_press(self, key: keyboard.Key) -> None:
        """Handle key presses and update the keybind label.

        Args:
            key: The key that was pressed.
        """
        if key == keyboard.Key.esc:
            self.entry_keybind.configure(text="")
            self.current_keybind.clear()
            return
        self.current_keybind.append(key)
        self.entry_keybind.configure(
            text=f"{settings.keybind_to_text(self.current_keybind)}",
            width=133,
            height=64,
        )

    def __on_release(self, key: keyboard.Key) -> None:
        """Handle key release events. Currently an unused placeholder."""
        pass

    # --- General Handlers ---
    def __on_modify_keybind(self) -> None:
        """Enable keybind editing and switch button text to 'Set'."""
        print("Modify keybind")
        self.btn_keybinds.configure(image=self.img_check, text="Set", width=133)
        self.btn_keybinds.configure(command=self.__on_set_keybind)
        self.start_keyboard_listener()

    def __on_set_keybind(self) -> None:
        """Finalize and save the new keybind, then disable further editing."""
        print("Set keybind")
        self.btn_keybinds.configure(image=self.img_edit, text="Edit", width=133)
        self.btn_keybinds.configure(command=self.__on_modify_keybind)
        self.stop_keyboard_listener()

    def __on_closing(self) -> None:
        """Clean up and close the Settings window."""
        self.stop_keyboard_listener()
        self.parent.destroy()

    def save(self, window: ctk.CTkToplevel) -> None:
        """Save the current keybind setting and close the settings window.

        If no keybind is set, it will default to 'Shift + Enter'. If no username is
        provided, it checks for a cached one.

        Args:
            window (CTkToplevel): The top-level customtkinter window.
        """
        txt_entry_username = self.entry_username.get()

        # Handle keybind saving.
        if not self.current_keybind:
            print("No keybind set, using default 'Shift + Enter'.")
            self.current_keybind = [keyboard.Key.shift_r, keyboard.Key.enter]
        settings.set("keybind", self.current_keybind)
        print(f"Keybind set to: {settings.keybind_to_text(self.current_keybind)}")

        # Handle username saving.
        if not txt_entry_username:
            print("No username provided.")
            window.destroy()
        else:
            settings.set("username", txt_entry_username)
            print(f"Username set to: {txt_entry_username}")

        # Inform user that a restart is required.
        if txt_entry_username or self.current_keybind:
            print("Restart required for changes to take effect.")

        # Close the settings window
        window.destroy()
