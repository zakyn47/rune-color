from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Union

import customtkinter as ctk
from PIL import Image, ImageTk

from views.fonts import fonts as fnt

if TYPE_CHECKING:
    from controller.bot_controller import BotController

PATH_SRC = Path(__file__).parents[1]
PATH_IMG = PATH_SRC / "img"
PATH_UI = PATH_IMG / "ui"


# Construct templates for a variety of basic option input styles.
class OptionWidgetInfo:
    """A class representing the core informational attributes of an option widget.

    Args:
        title (str): The title of the option widget.
    """

    def __init__(self, title: str) -> None:
        self.title = title


class SliderMenuInfo(OptionWidgetInfo):
    """A class representing the core informational attributes of a slider menu."""

    def __init__(
        self, title: str, min: Union[int, float], max: Union[int, float]
    ) -> None:
        """Initialize a selectable slider menu that ranges between two values.

        Args:
            title (str): The title of the slider menu.
            min (Union[int, float]): The minimum value for the associated option.
            max (Union[int, float]): The maximum value for the associated option.
        """
        super().__init__(title)
        self.min = min
        self.max = max


class DropdownMenuInfo(OptionWidgetInfo):
    """A class representing the core informational attributes of a dropdown menu."""

    def __init__(self, title: str, values: List[str]) -> None:
        """Initialize a dropdown menu with several text options.

        Args:
            title (str): The title to be shown on the dropdown button itself.
            values (List[str]): The list of options to choose from the dropdown menu.
        """
        super().__init__(title)
        self.values = values


class CheckboxMenuInfo(OptionWidgetInfo):
    """A class representing the core informational attributes of a checkbox menu."""

    def __init__(self, title: str, values: List[str]) -> None:
        """Initialize a labeled checkbox menu with selectable check boxes.

        Args:
            title (str): The title of the checkbox menu.
            values (List[str]): The titles of the checkbox options (e.g. `["A", "B"]`).
        """
        super().__init__(title)
        self.values = values


class TextEntryFieldInfo(OptionWidgetInfo):
    """A class representing the core informational attributes of a text entry field."""

    def __init__(self, title: str, placeholder: str) -> None:
        """Initialize a text entry field with default, grayed-out placeholder text.

        Args:
            title (str): The title of the text entry field.
            placeholder (str): The default text to shown when the field first appears.
        """
        super().__init__(title)
        self.placeholder = placeholder


class OptionsUI(ctk.CTkScrollableFrame):
    """A class for displaying and interacting with a variety of option widgets.

    This class constructs a dynamic UI layout with options such as sliders, checkboxes,
    dropdowns, and text entry fields based on the provided option information. The
    options are displayed inside a scrollable frame, and the user can save their
    selections through a Save button.

    Attributes:
        WIDTH (int): The width of the options UI frame.
        HEIGHT (int): The height of the options UI frame.
        IMG_SIZE (int): The size of icons used in the UI.
        widgets (Dict[str, ctk.CTkBaseClass]): Stores the widgets for later reference.
        labels (Dict[str, ctk.CTkLabel]): Stores labels corresponding to the options.
        frames (Dict[str, ctk.CTkFrame]): Stores frames to organize the layout of the
            options.
        slider_values (Dict[str, ctk.CTkLabel]): Stores labels displaying the current
            values of sliders.
        controller (BotController): Reference to the `BotController` for handling
            backend operations.
        num_of_options (int): The total number of options to display in the UI.
    """

    WIDTH = 600
    HEIGHT = 600
    IMG_SIZE = 24

    def __init__(
        self,
        parent: ctk.CTkToplevel,
        title: str,
        option_info: Dict[str, OptionWidgetInfo],
        controller: "BotController",
    ) -> None:
        """Initialize the options UI frame.

        Args:
            parent (ctk.CTkToplevel): The parent window in which this UI will appear.
            title (str): The title of the options UI, displayed at the top.
            option_info (Dict[str, OptionWidgetInfo]): A dictionary containing the
                option configuration. Keys represent option names, and values are
                instances of different `OptionWidgetInfo` subclasses.
            controller (BotController): The controller responsible for managing backend
                logic and operations.

        Raises:
            Exception: Raised if an unknown option type is encountered in `option_info`.
        """
        super().__init__(parent)
        corner_icon_path = str(PATH_UI / "logo-corner.ico")
        self.after(
            201,
            lambda: parent.iconbitmap(corner_icon_path),
        )
        parent.geometry(f"{OptionsUI.WIDTH}x{OptionsUI.HEIGHT}")
        parent.configure(fg_color="#2b2b2b")

        self.img_save = ImageTk.PhotoImage(
            Image.open(PATH_UI / "save.png").resize((self.IMG_SIZE, self.IMG_SIZE)),
            Image.LANCZOS,
        )

        # `self.widgets` contains the widgets for option selection. It is queried for
        # the selected option values upon the save button being clicked.
        self.widgets: Dict[str, ctk.CTkBaseClass] = {}
        # The following maps exist to hold references to UI elements so they are not
        # destroyed by the garbage collector.
        self.labels: Dict[str, ctk.CTkLabel] = {}
        self.frames: Dict[str, ctk.CTkFrame] = {}
        self.slider_values: Dict[str, ctk.CTkLabel] = {}

        self.controller = controller

        # Configure a grid layout.
        self.num_of_options = len(option_info.keys())
        self.rowconfigure(0, weight=0)  # Title
        for i in range(self.num_of_options):
            self.rowconfigure(i + 1, weight=0)
        self.rowconfigure(
            self.num_of_options + 1, weight=1
        )  # Spacing between the Save button and the options widgets.
        self.rowconfigure(self.num_of_options + 2, weight=0)  # The Save button row.
        self.columnconfigure(0, weight=3, uniform="column_uniform")
        self.columnconfigure(1, weight=4, uniform="column_uniform")

        # Define the title widget.
        self.lbl_bot_options = ctk.CTkLabel(
            master=self,
            text=f"{title} Options",
            font=fnt.subheading_font(),
            bg_color="#4d4d4d",
        )
        self.lbl_bot_options.grid(
            row=0, column=0, padx=0, ipadx=20, pady=20, sticky="nsew"
        )

        # Dynamically place widgets starting from row 1 (skipping the Save button row).
        for row, (key, value) in enumerate(option_info.items(), start=1):
            if isinstance(value, SliderMenuInfo):
                self.create_slider(key, value, row)
            elif isinstance(value, CheckboxMenuInfo):
                self.create_checkboxes(key, value, row)
            elif isinstance(value, DropdownMenuInfo):
                self.create_dropdown_menu(key, value, row)
            elif isinstance(value, TextEntryFieldInfo):
                self.create_text_entry_field(key, value, row)
            else:
                raise Exception("Unknown option type")

        # Define the Save button.
        self.btn_save = ctk.CTkButton(
            master=self,
            image=self.img_save,
            text="Save",
            compound="left",
            font=fnt.button_med_font(),
            command=lambda: self.save(window=parent),
            height=64,
            corner_radius=0,
        )
        self.btn_save.grid(row=0, column=1, columnspan=1, pady=20, padx=0, sticky="we")

    def change_slider_val(self, key: str, value: Union[int, float]) -> None:
        """Update the display of a slider's current value.

        This method updates the label associated with the slider to show the current
        value as an integer percentage (scaled by 100).

        Args:
            key (str): The identifier of the slider whose value is being changed.
            value (Union[int, float]): The current value of the slider, ranging between
                its min and max value.
        """
        self.slider_values[key].configure(text=str(int(value * 100)))

    def create_slider(self, key: str, value: SliderMenuInfo, row: int) -> None:
        """Create a slider menu widget and add it to the `OptionsUI`.

        The slider allows the user to select a value within a predefined range (min to
        max). It also includes a label to display the current value of the slider.

        Args:
            key (str): The identifier for the slider widget.
            value (SliderMenuInfo): The slider information, including title, min, and
                max values.
            row (int): The row in which to place the slider in the UI layout.
        """
        default_val = round((value.max - value.min) // 2) + 1  # 1-based indexing.
        # Slider label.
        self.labels[key] = ctk.CTkLabel(
            master=self, text=value.title, font=fnt.small_font()
        )
        self.labels[key].grid(row=row, column=0, sticky="nsew", padx=10, pady=20)
        # Slider frame.
        self.frames[key] = ctk.CTkFrame(master=self)
        self.frames[key].columnconfigure(0, weight=1)
        self.frames[key].columnconfigure(1, weight=0)
        self.frames[key].grid(row=row, column=1, sticky="ew", padx=(0, 10))
        # Slider value indicator.
        self.slider_values[key] = ctk.CTkLabel(
            master=self.frames[key], text=str(default_val), font=fnt.small_font()
        )
        self.slider_values[key].grid(row=0, column=1, padx=5)
        # Slider widget.
        self.widgets[key] = ctk.CTkSlider(
            master=self.frames[key],
            from_=value.min / 100,
            to=value.max / 100,
            command=lambda x: self.change_slider_val(key, x),
        )
        self.widgets[key].grid(row=0, column=0, sticky="ew")
        self.widgets[key].set(default_val / 100)

    def create_checkboxes(self, key, value: CheckboxMenuInfo, row: int) -> None:
        """Create a checkbox menu widget and add it to the `OptionsUI`.

        The checkbox menu allows the user to select multiple options from a list of
        checkboxes.

        Args:
            key (str): The identifier for the checkbox menu widget.
            value (CheckboxMenuInfo): The checkbox information, including title and
                available options.
            row (int): The row in which to place the checkbox menu in the UI layout.
        """
        # Checkbox label.
        self.labels[key] = ctk.CTkLabel(
            master=self, text=value.title, font=fnt.small_font()
        )
        self.labels[key].grid(row=row, column=0, padx=10, pady=20)
        # Checkbox frame.
        self.frames[key] = ctk.CTkFrame(master=self)
        for i in range(len(value.values)):
            self.frames[key].columnconfigure(i, weight=1)
        self.frames[key].grid(row=row, column=1, sticky="ew", padx=(10, 10))
        # Checkbox values.
        self.widgets[key] = []  # Type is `List[ctk.CTkCheckBox]`.
        for i, value in enumerate(value.values):
            self.widgets[key].append(
                ctk.CTkCheckBox(
                    master=self.frames[key], text=value, font=fnt.small_font()
                )
            )
            self.widgets[key][i].grid(row=0, column=i, sticky="ew", padx=5, pady=5)

    def create_dropdown_menu(self, key: str, value: DropdownMenuInfo, row: int) -> None:
        """Create a dropdown menu widget and add it to the `OptionsUI`.

        The dropdown menu allows the user to select one option from a predefined list.

        Args:
            key (str): The identifier for the dropdown menu widget.
            value (DropdownMenuInfo): The dropdown menu information, including title
                and available options.
            row (int): The row in which to place the dropdown menu in the UI layout.
        """
        default_val = value.values[0]
        self.labels[key] = ctk.CTkLabel(
            master=self, text=value.title, font=fnt.small_font()
        )
        self.labels[key].grid(row=row, column=0, sticky="nsew", padx=10, pady=20)
        self.widgets[key] = ctk.CTkOptionMenu(
            master=self,
            values=value.values,
            fg_color="#333333",
            font=fnt.small_font(),
            dropdown_font=fnt.small_font(),
        )
        self.widgets[key].grid(row=row, column=1, sticky="ew", padx=(10, 10))
        self.widgets[key].set(default_val)

    def create_text_entry_field(
        self, key: str, value: TextEntryFieldInfo, row: int
    ) -> None:
        """Create a text entry field widget and add it to the `OptionsUI`.

        The text entry field allows the user to input custom text, with an optional
        placeholder.

        Args:
            key (str): The identifier for the text entry field widget.
            value (TextEntryFieldInfo): The text entry information, including title and
                placeholder text.
            row (int): The row in which to place the text entry field in the UI layout.
        """
        self.labels[key] = ctk.CTkLabel(
            master=self, text=value.title, font=fnt.small_font()
        )
        self.labels[key].grid(row=row, column=0, sticky="nsew", padx=10, pady=20)
        self.widgets[key] = ctk.CTkEntry(
            master=self,
            corner_radius=5,
            font=fnt.small_font(),
            placeholder_text=value.placeholder,
        )
        self.widgets[key].grid(row=row, column=1, sticky="ew", padx=(10, 10))
        # Inserting the placeholder text lets users use the default value. Without it,
        # users must enter text every time before closing the options window.
        self.widgets[key].insert(0, value.placeholder)

    def save(self, window: ctk.CTkToplevel) -> None:
        """Save the user-selected options and pass them to the `BotController`.

        This method collects all option values from the widgets, sends them to the
        `BotController` for further processing, and then closes the options pop-up
        window.

        Args:
            window (ctk.CTkToplevel): The parent window that hosts the options UI.
        """
        self.options = {}
        for key, value in self.widgets.items():
            if isinstance(value, ctk.CTkSlider):
                self.options[key] = int(value.get() * 100)
            elif isinstance(value, list):
                self.options[key] = [
                    checkbox.cget("text") for checkbox in value if checkbox.get()
                ]
            elif isinstance(value, (ctk.CTkOptionMenu, ctk.CTkEntry)):
                self.options[key] = value.get()
        # Send the newly-saved options to the controller.
        self.controller.save_options(self.options)
        window.destroy()


class OptionsBuilder:
    """Define the options map for the `Bot` configuration on the `BotView`.

    The options map holds the option name and the UI details that will map to it. An
    instance of this class will go to `OptionsUI` to be interpreted and built.
    """

    def __init__(self, title: str) -> None:
        """Initialize an `OptionsBuilder`.

        Args:
            title (str): The title of the option.
        """
        self.options = {}  # This dictionary will hold all named options.
        self.title = title

    def add_slider_option(self, key: str, title: str, min: int, max: int) -> None:
        """Add a slider option to the options menu.

        Args:
            key (str): The key to map the option to, matching the variable name in its
                associated script (e.g. run_time or take_breaks).
            title (str): The title of the option.
            min (int): The minimum value of the slider.
            max (int): The maximum value of the slider.
        """
        self.options[key] = SliderMenuInfo(title, min, max)

    def add_checkbox_option(self, key: str, title: str, values: list) -> None:
        """Add a checkbox option to the options menu.

        Args:
            key (str): The key to map the option to, matching the variable name in its
                associated script.
            title (str): The title of the option.
            values: A list of values to display for each checkbox.
        """
        self.options[key] = CheckboxMenuInfo(title, values)

    def add_dropdown_option(self, key: str, title: str, values: List[str]) -> None:
        """Add a dropdown option to the options menu.

        Args:
            key (str): The key to map the option to, matching the variable name in its
                associated script.
            title (str): The title of the option.
            values (List[str]): A list of strings to display for each entry in the
                dropdown.
        """
        self.options[key] = DropdownMenuInfo(title, values)

    def add_text_edit_option(self, key: str, title: str, placeholder=None) -> None:
        """Add a text edit option to the options menu.

        Args:
            key (str): The key to map the option to, matching the variable name in its
                associated script.
            title (str): The title of the option.
            placeholder: The placeholder text to display in the text edit box
                (optional).
        """
        self.options[key] = TextEntryFieldInfo(title, placeholder)

    def build_ui(
        self, parent: ctk.CTkToplevel, controller: "BotController"
    ) -> OptionsUI:
        """Get a UI object that can be added to the parent window."""
        return OptionsUI(parent, self.title, self.options, controller)
