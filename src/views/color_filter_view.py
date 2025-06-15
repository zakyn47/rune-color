from pathlib import Path
from tkinter import IntVar
from typing import Callable

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageOps, ImageTk

from utilities.img_search import BOT_IMAGES
from views.fonts import fonts as fnt

PATH_SRC = Path(__file__).parents[1]
PATH_IMG = BOT_IMAGES.parent
PATH_UI = PATH_IMG / "ui"
PATH_SCREENSHOTTER = BOT_IMAGES / "screenshotter"
SPLASH_FILENAME = "rgb-hsv.png"
IMG_SIZE = 24
PADX_SLIDER = 10


class ColorFilterView(ctk.CTkFrame):
    # Note importantly that Hue varies from 0 to 179 in the OpenCV library, unlike many
    # online color pickers which vary from 0 to 255 or 0 to 99.
    H_minval, S_minval, V_minval = 0, 0, 0
    H_maxval, S_maxval, V_maxval = 179, 255, 255

    # These flags indicate which screenshot is currently being analyzed.
    minimap, game_view, control_panel = False, False, False

    image_to_load = None
    __start_up = True  # Whether the Color Filter was just freshly started.

    def __init__(self, parent: ctk.CTkToplevel) -> None:
        """Initialize a view for the Color Filter utility.

        Color Filter allows for applying HSV color filters to screenshots.

        Args:
            parent (ctk.CTkToplevel): The top-level customtkinter window.
        """
        super().__init__(parent)
        self.parent = parent
        self.parent.resizable(False, False)
        self.parent.protocol("WM_DELETE_WINDOW", self.__on_closing)
        self._setup_grid()
        self._create_title_label()
        self._create_hsv_frame()
        self._create_image_frames()
        self._create_radiobutton_frame()
        self._create_slider_controls()
        self._create_color_profile_text_entry()
        self._create_save_button()

    # --- Color Filter UI Creation Steps ---
    def _setup_grid(self) -> None:
        """Set up the grid configuration for the view's main frame."""
        self.grid_columnconfigure(0, weight=3, uniform="column_uniform")
        self.grid_columnconfigure(1, weight=4, uniform="column_uniform")
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)

    def _create_title_label(self) -> None:
        """Create the title label for the main frame."""
        self.search_label = ctk.CTkLabel(
            master=self,
            text="Create custom HSV color filters for in-game objects.",
            font=fnt.title_font(),
            wraplength=900,
            height=64,
        )
        self.search_label.grid(
            row=0,
            column=0,
            sticky="n",
            padx=0,
            pady=(0, 10),
            columnspan=2,
        )

    def _create_hsv_frame(self) -> None:
        """Create the sub-frame to contain HSV slider bars."""
        self.hsv_frame = self._create_frame(
            self,
            row=1,
            col=0,
            sticky="nswe",
            corner_radius=0,
            width=self.parent.winfo_width() // 3,
            fg_color="#2b2b2b",
        )
        self.hsv_frame.grid_columnconfigure(0, weight=1)
        self.hsv_frame.grid_rowconfigure((0, 1, 2, 3), weight=0)

    def _create_image_frames(self) -> None:
        """Create the overall containing frame for images."""
        self.images_frame = self._create_frame(
            self,
            row=1,
            col=1,
            sticky="ns",
            fg_color="#2b2b2b",
        )
        self.images_frame.grid_columnconfigure(0, weight=1)
        self.images_frame.grid_rowconfigure((0, 1), weight=0)
        # Create the bottom screenshot panel.
        self.screenshot_frame = self._create_frame(
            self.images_frame, row=0, col=0, sticky="n"
        )
        self.after(
            100, self.__import_screenshot
        )  # Load screenshot after a short delay.
        # Create the mask frame.
        self.mask_frame = self._create_frame(
            self.images_frame, row=1, col=0, sticky="s"
        )
        self.after(100, self.__update_image)  # Resize/update screenshot after delay.

    def _create_radiobutton_frame(self) -> None:
        """Create a sub-frame of three checkable radio buttons."""
        self.radio_var = IntVar(self)
        self.radiobutton_frame = self._create_frame(
            self.hsv_frame,
            row=0,
            col=0,
            sticky="nswe",
            corner_radius=0,
        )
        self.radiobutton_frame.grid_rowconfigure((0, 1), weight=1)
        self.radiobutton_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Create the label for the Screen Region radio buttons.
        ctk.CTkLabel(
            master=self.radiobutton_frame,
            text="Select Screen Region",
            font=fnt.heading_font_normal(),
        ).grid(row=0, column=0, columnspan=3, padx=PADX_SLIDER, pady=(0, 20))

        # Create and pack each checkbox.
        self.gameview_box = self._create_radiobutton(
            text="Game View",
            command=self.__game_view_check,
            value=0,
            row=1,
            col=0,
        )
        self.minimap_box = self._create_radiobutton(
            text="Minimap",
            command=self.__minimap_check,
            value=1,
            row=1,
            col=1,
        )
        self.controlpanel_box = self._create_radiobutton(
            text="Control Panel",
            command=self.__control_panel_check,
            value=2,
            row=1,
            col=2,
        )

    def _create_slider_controls(self) -> None:
        """Create slider bars for defining the range of the HSV color filter."""
        self.slider_controls_frame = self._create_frame(
            self.hsv_frame,
            row=1,
            col=0,
            sticky="nswe",
            corner_radius=0,
        )
        self.slider_controls_frame.grid(padx=0, columnspan=2)
        self.slider_controls_frame.grid_rowconfigure(tuple(range(18)), weight=1)
        self.slider_controls_frame.grid_columnconfigure(0, weight=1)

        self.lbl_H_minval = self._create_slider(
            master=self.slider_controls_frame,
            label="H-min",
            max_value=179,
            callback=self.__on_slider_event_Hmin,
            value=self.H_minval,
            row=0,
        )
        self.lbl_S_minval = self._create_slider(
            master=self.slider_controls_frame,
            label="S-min",
            max_value=255,
            callback=self.__on_slider_event_Smin,
            value=self.S_minval,
            row=3,
        )
        self.lbl_V_minval = self._create_slider(
            master=self.slider_controls_frame,
            label="V-min",
            max_value=255,
            callback=self.__on_slider_event_Vmin,
            value=self.V_minval,
            row=6,
        )
        self.lbl_H_maxval = self._create_slider(
            master=self.slider_controls_frame,
            label="H-max",
            max_value=179,
            callback=self.__on_slider_event_Hmax,
            value=self.H_maxval,
            row=9,
        )
        self.lbl_S_maxval = self._create_slider(
            master=self.slider_controls_frame,
            label="S-max",
            max_value=255,
            callback=self.__on_slider_event_Smax,
            value=self.S_maxval,
            row=12,
        )
        self.lbl_V_maxval = self._create_slider(
            master=self.slider_controls_frame,
            label="V-max",
            max_value=255,
            callback=self.__on_slider_event_Vmax,
            value=self.V_maxval,
            row=15,
        )

    def _create_color_profile_text_entry(self) -> None:
        """Create the text entry box for naming an HSV color range."""
        self.enter_color_name = ctk.CTkEntry(
            master=self.hsv_frame,
            placeholder_text=" Enter color profile name (e.g. default_cyan).",
            corner_radius=0,
            font=fnt.body_large_font(),
        )
        self.enter_color_name.grid(row=2, column=0, sticky="swe", pady=(30, 0))

    def _create_save_button(self) -> None:
        """Create the Save Color Profile button."""
        self.img_save = ImageTk.PhotoImage(
            Image.open(str(PATH_UI / "save.png")).resize((IMG_SIZE, IMG_SIZE)),
            Image.Resampling.LANCZOS,
        )
        self.save_color_button = ctk.CTkButton(
            master=self.hsv_frame,
            height=64,
            image=self.img_save,
            compound="left",
            text="Save Color Profile",
            command=self.__on_save_color_profile,
            corner_radius=0,
            font=fnt.body_large_font(),
        )
        self.save_color_button.grid(row=3, column=0, sticky="swe")

    # --- customtkinter Object Creation ---
    def _create_frame(
        self, master: ctk.CTkFrame, row: int, col: int, sticky: str = "nswe", **kwargs
    ) -> ctk.CTkFrame:
        """Create and return a `ctk.CTkFrame` placed at a specific grid location.

        Args:
            master (ctk.CTkFrame): The parent frame in which the new frame will be created.
            row (int): The grid row number to place the frame.
            col (int): The grid column number to place the frame.
            sticky (str, optional): Determines which sides of the cell the frame should
                stick to. Defaults to "nswe" (i.e. all sides).
            **kwargs: Additional keyword arguments for configuring the `CTkFrame`.

        Returns:
            ctk.CTkFrame: The created `CTkFrame` object.
        """
        frame = ctk.CTkFrame(master=master, **kwargs)
        frame.grid(row=row, column=col, sticky=sticky)
        return frame

    def _create_radiobutton(
        self, text: str, command: Callable, value: int, row: int, col: int
    ) -> ctk.CTkRadioButton:
        """Create and return a `ctk.CTkRadioButton` placed at a specific grid location.

        Args:
            text (str): The label for the radio button.
            command (Callable): The function to be executed when the radio button is
                selected.
            value (int): The value assigned to the radio button.
            row (int): The grid row number to place the radio button.
            col (int): The grid column number to place the radio button.

        Returns:
            ctk.CTkRadioButton: The created `CTkRadioButton` object.
        """
        radiobutton = ctk.CTkRadioButton(
            master=self.radiobutton_frame,
            variable=self.radio_var,
            text=text,
            command=command,
            value=value,
        )
        radiobutton.grid(row=row, column=col, padx=PADX_SLIDER, pady=5)
        return radiobutton

    def _create_slider(
        self,
        master: ctk.CTkFrame,
        label: str,
        max_value: int,
        callback: Callable,
        value: int,
        row: int,
    ) -> ctk.CTkLabel:
        """Create and return a labeled slider placed at a specific of grid location.

        Note that the placed location actually spans three sequential rows (i.e. 2 more
        rows in addition to the first). This is because each slider is composed of a:
            - Text Label (e.g. "H-min")
            - Value Label (e.g. 99)
            - Slider Widget

        Args:
            master (ctk.CTkFrame): The parent frame in which the slider and its label
                will be created.
            label (str): The label for the slider.
            max_value (int): The maximum value of the slider.
            callback (Callable): The function to be executed when the slider is moved.
            value (int): The initial value of the slider.
            row (int): The grid row number to place the slider and its components.

        Returns:
            ctk.CTkLabel: The label displaying the current value of the slider. This is
                returned so it can be dynamically updated via the `callback`.
        """
        ctk.CTkLabel(master=master, text=label, font=fnt.body_large_font()).grid(
            row=row,
            column=0,
            sticky="wne",
            padx=PADX_SLIDER,
            pady=1,
        )  # The label of the slider.
        lbl_val = ctk.CTkLabel(master=master, text=value, font=fnt.body_med_font())
        lbl_val.grid(
            row=row + 1,
            column=0,
            sticky="wne",
            padx=PADX_SLIDER,
            pady=1,
        )  # The value of the slider as text.

        slider = ctk.CTkSlider(
            master=master,
            from_=0,
            to=max_value,
            number_of_steps=max_value,
            command=callback,
        )
        slider.grid(
            row=row + 2,
            column=0,
            sticky="wne",
            padx=PADX_SLIDER,
            pady=1,
        )
        slider.set(value)
        return lbl_val

    # --- Screenshot Load and Update ---
    def __import_screenshot(self) -> None:
        """Import the appropriate screenshot per the selected radio button."""
        conditions = {
            self.minimap: "screenshotter-minimap.png",
            self.game_view: "screenshotter-game-view.png",
            self.control_panel: "screenshotter-control-panel.png",
        }
        self.screenshot = self.__load_pil_image(conditions.get(True, SPLASH_FILENAME))
        self.__update_screenshot(self.screenshot)

    def __load_pil_image(self, image_name: str) -> Image.Image:
        """Load a PIL `Image.Image` given an screenshot name.

        Args:
            image_name (str): The string name of the image (including extension).

        Returns:
            Image: The screenshot as an `Image.Image` object.
        """
        img_path = PATH_SCREENSHOTTER / image_name
        return Image.open(str(img_path))

    def __update_screenshot(self, img: Image.Image) -> None:
        """Update an old screenshot with a new one.

        Args:
            img (Image.Image): The new screenshot to replace the old.
        """
        # Resize the top-half static image. Note the full panel is 535 wide x 670 tall.
        if self.game_view or self.control_panel:
            img = ImageOps.contain(img, (515, 335))
        self.screenshot_tk = ImageTk.PhotoImage(img)

        # Remove the previous screenshot label from the `self.screenshot_frame`.
        for child in self.screenshot_frame.winfo_children():
            child.destroy()

        # Put the new label (which only has an image and no text) on the grid.
        ctk.CTkLabel(
            master=self.screenshot_frame,
            image=self.screenshot_tk,
            text="",
            font=fnt.body_large_font(),
        ).grid(row=0, column=0, sticky="ew")

    def __update_image(self) -> None:
        """Update a given screenshot after an HSV color filter is applied."""
        # Use the image data already in memory if the image has been loaded previously.
        if isinstance(self.image_to_load, np.ndarray):
            img = self.image_to_load
        if not isinstance(self.image_to_load, np.ndarray) and not self.image_to_load:
            # If the image is empty, load the image from the hard drive.
            conditions = {
                self.minimap: "screenshotter-minimap.png",
                self.game_view: "screenshotter-game-view.png",
                self.control_panel: "screenshotter-control-panel.png",
            }
            screenshot_filename = conditions.get(True, SPLASH_FILENAME)
            img_path = PATH_SCREENSHOTTER / screenshot_filename
            img = cv2.imread(str(img_path))  # Returns `np.ndarray`, not `Image.Image`.
            self.image_to_load = img

        # Set minimum and maximum HSV display values.
        lo = np.array([self.H_minval, self.S_minval, self.V_minval])
        hi = np.array([self.H_maxval, self.S_maxval, self.V_maxval])

        # Convert to HSV format and color threshold.
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lo, hi)
        result = cv2.bitwise_and(img, img, mask=mask)

        # Convert the OpenCV image to a PIL image.
        image_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        # Resize the bottom-half color-filtered image. Dimensions are width x height.
        if self.minimap:
            pil_image = ImageOps.contain(pil_image, (515, 510))  # Presumed enlarged.
        if self.game_view:
            pil_image = ImageOps.contain(pil_image, (515, 335))  # Half-and-half.

        # Create a `PhotoImage` from the resized PIL image
        self.image_to_display = ImageTk.PhotoImage(pil_image)
        if self.__start_up:
            self.image_to_display = self.screenshot_tk
            self.__start_up = False

        # Add the new screenshot label to the screenshot frame.
        maskshotlabel_new = ctk.CTkLabel(
            master=self.mask_frame,
            image=self.image_to_display,
            text="",
            font=fnt.body_large_font(),
        )
        maskshotlabel_new.grid(row=1, column=0, sticky="nsew")

        # Remove previous screenshot label from screenshot frame.
        for child in reversed(self.mask_frame.winfo_children()):
            if child != maskshotlabel_new:
                child.destroy()

        self.maskshotlabel = maskshotlabel_new

    # --- Handlers --
    def __on_closing(self) -> None:
        """Handle the event where the Color Filter is closed (e.g. clicking X)."""
        self.parent.destroy()

    def __on_slider_event_Hmin(self, value) -> None:
        """Handle the event where the H-min Slider is slid left or right."""
        self.H_minval = int(value)
        self.lbl_H_minval.configure(text=str(self.H_minval))
        self.__update_image()

    def __on_slider_event_Hmax(self, value) -> None:
        """Handle the event where the H-max Slider is slid left or right."""
        self.H_maxval = int(value)
        self.lbl_H_maxval.configure(text=str(self.H_maxval))
        self.__update_image()

    def __on_slider_event_Smin(self, value) -> None:
        """Handle the event where the S-min Slider is slid left or right."""
        self.S_minval = int(value)
        self.lbl_S_minval.configure(text=str(self.S_minval))
        self.__update_image()

    def __on_slider_event_Smax(self, value) -> None:
        """Handle the event where the S-max Slider is slid left or right."""
        self.S_maxval = int(value)
        self.lbl_S_maxval.configure(text=str(self.S_maxval))
        self.__update_image()

    def __on_slider_event_Vmin(self, value) -> None:
        """Handle the event where the V-min Slider is slid left or right."""
        self.V_minval = int(value)
        self.lbl_V_minval.configure(text=str(self.V_minval))
        self.__update_image()

    def __on_slider_event_Vmax(self, value) -> None:
        """Handle the event where the V-max Slider is slid left or right."""
        self.V_maxval = int(value)
        self.lbl_V_maxval.configure(text=str(self.V_maxval))
        self.__update_image()

    def __on_save_color_profile(self) -> None:
        """Dynamically update HSV color tuples within `utilities.mappings`."""
        color_file = PATH_SRC / "utilities/mappings/colors_hsv.py"
        color_name = self.enter_color_name.get().strip()
        color_range = (
            f"{color_name} ="
            f" (({self.H_minval}, {self.S_minval}, {self.V_minval}),"
            f" ({self.H_maxval}, {self.S_maxval}, {self.V_maxval}))\n"
        )
        if not color_name or (len(color_name) > 1 and color_name[0].isdigit()):
            return
        with open(color_file, "r", encoding="utf8") as file:
            file.seek(0, 2)  # Move the cursor to the end of the file.
            file_length = file.tell()  # Number of bytes from beginning to end.
            if file_length == 0:
                has_newline = False
            if file_length != 0:
                file.seek(file_length - 1)  # Move the cursor to the 2nd-to-last char.
                last_char = file.read(1)  # Read the last character.
                has_newline = last_char == "\n"
            n_ = "\n" if not has_newline else ""
            file.seek(0)  # Now move the cursor back to the top of the file.
            lines = []
            for line in file:  # Read in all lines to potentially replace them.
                lines.append(line)
            file.seek(0)
            replacement = False
            for i, line in enumerate(lines):
                if line.startswith(f"{color_name} = "):
                    lines[i] = color_range
                    replacement = True
            if not replacement:
                lines.append(f"{n_}{color_range}")  # Append if no match is found.
        # Lastly, overwrite the file with the new lines.
        with open(color_file, "w", encoding="utf8") as file:
            for line in lines:
                file.write(line)

    # --- Radio Button State Checkers ---
    def __minimap_check(self) -> None:
        """Check whether the Minimap Radio Button is selected or not."""
        if self.minimap_box._check_state:
            self.minimap = True
            self.game_view = False
            self.control_panel = False
            self.image_to_load = None
            self.__import_screenshot()
            self.__update_image()

    def __game_view_check(self) -> None:
        """Check whether the Game View Radio Button is selected or not."""
        if self.gameview_box._check_state:
            self.minimap = False
            self.game_view = True
            self.control_panel = False
            self.image_to_load = None
            self.__import_screenshot()
            self.__update_image()

    def __control_panel_check(self) -> None:
        """Check whether the Control Panel Radio Button is selected or not."""
        if self.controlpanel_box._check_state:
            self.minimap = False
            self.game_view = False
            self.control_panel = True
            self.image_to_load = None
            self.__import_screenshot()
            self.__update_image()
