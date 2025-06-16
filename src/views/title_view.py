import webbrowser as wb
from pathlib import Path
from typing import List
import threading
import time
import requests
import platformdirs

import customtkinter as ctk
from PIL import Image, ImageTk

from utilities import settings
from utilities.update_checker import UpdateChecker
from views.auth_view import AuthView
from views.color_filter_view import ColorFilterView
from views.fonts import fonts as fnt
from views.settings_view import SettingsView
from views.sprite_scraper_view import SpriteScraperView

PATH_SRC = Path(__file__).parents[1]
PATH_IMG = PATH_SRC / "img"
PATH_UI = PATH_IMG / "ui"

# --- Default Button Kwargs ---
IMG_SIZE = 24
BTN_WIDTH, BTN_HEIGHT = (140, 64)
PADX = 0
PADY = 0
CORNER_RADIUS = 0
COLOR_HOVER = "#203a4f"  # Dark, muted blue.
DEFAULT_GRAY = ("gray50", "gray30")
BOT_ROW = 6


class TitleView(ctk.CTkFrame):
    """`TitleView` is the first view the user sees when Runecolor starts up."""

    def __init__(self, parent: ctk.CTkFrame, main: ctk.CTk) -> None:
        """Initialize a `TitleView`, the first view the user sees upon startup.

        This view provides the main splash screen and various buttons for navigation
        to different functionalities like settings, scraping, and color filtering.

        Args:
            parent (ctk.CTkFrame): The parent frame in which this view is contained.
            main (ctk.CTk): The main application instance that manages the overall UI.
        """
        super().__init__(parent)
        self.main = main
        self.btns: List = []

        self._setup_grid()
        self._create_main_splash()
        self._create_main_splash_text()
        self._create_cached_settings_text()
        self._create_auth_button()
        self._create_website_button()
        self._create_update_button()
        self._create_settings_button()
        if main.DEV_MODE:
            self._create_scraper_button()
            self._create_color_filter_button()

    # --- Main `TitleView` Creation Steps ---
    def _setup_grid(self) -> None:
        """Configure the title view as a grid for easy button placement."""
        self.grid_rowconfigure(0, weight=1)  # Logo
        self.grid_rowconfigure(1, weight=0)  # Splash text
        self.grid_rowconfigure(2, weight=0)  # Cached settings
        self.grid_rowconfigure(3, weight=0)  # Auth button
        self.grid_rowconfigure(4, weight=0)  # Scraper/Color Filter (DEV_MODE)
        self.grid_rowconfigure(5, weight=0)  # Main action buttons
        for i in range(3):
            self.grid_columnconfigure(i, weight=1)

    def _create_main_splash(self) -> None:
        """Load the main Runecolor logo to be displayed on the title view."""
        self.corner_icon_path = PATH_UI / "logo-corner.ico"
        self.logo = ImageTk.PhotoImage(
            Image.open(PATH_UI / "splash.png"),
            Image.LANCZOS,
        )
        self.label_logo = ctk.CTkLabel(
            self, image=self.logo, text="", font=fnt.body_med_font()
        )
        self.label_logo.grid(
            row=0, column=0, columnspan=3, sticky="nsew", padx=15, pady=15
        )

    def _create_main_splash_text(self) -> None:
        """Load the main text to be placed underneath the splash logo."""
        txt_splash = "Select a folder from the Library or choose an option below."
        self.lbl_splash = ctk.CTkLabel(
            master=self, text=txt_splash, font=fnt.title_font(weight="normal")
        )
        self.lbl_splash.bind(
            "<Configure>",
            lambda x: self.lbl_splash.configure(
                wraplength=self.lbl_splash.winfo_width() - 20
            ),
        )
        self.lbl_splash.grid(
            row=1, column=0, columnspan=3, sticky="nswe", padx=15, pady=(0, 30)
        )

    def _create_cached_settings_text(self) -> None:
        """Display the status of cached settings."""
        username = "Found" if settings.get("username") else "Not Found"
        subscription_key = "Found" if settings.get("subscription_key") else "Not Found"
        keybind = "Found" if settings.get("keybind") else "Not Found"
        txt_cached = (
            "  Cached..."
            f"\n  Username: {username}"
            f"\n   Sub Key: {subscription_key}"
            f"\n   Keybind: {keybind}"
        )
        self.lbl_cached = ctk.CTkLabel(
            master=self,
            text=txt_cached,
            font=fnt.micro_font(family="Courier"),
            anchor="w",
            justify="left",
        )
        self.lbl_cached.bind(
            "<Configure>",
            lambda x: self.lbl_cached.configure(
                wraplength=self.lbl_cached.winfo_width() - 20
            ),
        )
        self.lbl_cached.grid(
            row=2, column=0, columnspan=1, padx=PADX, pady=(0, 10), sticky="nswe"
        )

    def _create_update_button(self) -> None:
        """Create a button to check for updates."""
        self.update_logo = ImageTk.PhotoImage(
            Image.open(PATH_UI / "update.png").resize((IMG_SIZE, IMG_SIZE)),
            Image.LANCZOS,
        )
        self.btn_update = ctk.CTkButton(
            master=self,
            text="Update Runecolor",
            font=fnt.body_large_font(),
            image=self.update_logo,
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            hover_color=COLOR_HOVER,
            corner_radius=CORNER_RADIUS,
            fg_color=DEFAULT_GRAY,
            compound="left",
            command=self.__on_update_clicked,
            state="disabled",
        )
        self.btn_update.grid(row=5, column=1, padx=PADX, pady=(0, 0), sticky="sew")
        self.btns.append(self.btn_update)

    def __on_update_clicked(self) -> None:
        """Check for updates and download if available."""
        update_checker = UpdateChecker()
        has_update, latest_version, download_url = update_checker.check_for_updates()

        if has_update and latest_version and download_url:
            # Create a popup window to confirm the update
            window = ctk.CTkToplevel(master=self)
            window.title("Update Available")
            self.center_popup(self.winfo_toplevel(), window, width=400, height=300)
            window.attributes("-topmost", True)

            # Add message
            msg = f"A new version ({latest_version}) is available!\nWould you like to download it?"
            label = ctk.CTkLabel(
                window,
                text=msg,
                font=fnt.body_large_font(),
                wraplength=350,
            )
            label.pack(pady=20)

            # Add download button
            progress_bar = ctk.CTkProgressBar(window, width=300)
            progress_bar.pack(pady=10)
            progress_bar.set(0)

            speed_label = ctk.CTkLabel(window, text="Speed: 0 KB/s")
            speed_label.pack(pady=5)

            def download():
                """start download update"""
                save_path = str(Path(platformdirs.user_desktop_dir()) / f"Runecolor{latest_version}.exe")
                start_download_thread(download_url, save_path, progress_bar, speed_label, window)

            download_btn = ctk.CTkButton(
                window,
                text="Download Update",
                command=download,
                font=fnt.body_large_font(),
            )
            download_btn.pack(pady=10)

            # Add cancel button
            cancel_btn = ctk.CTkButton(
                window,
                text="Cancel",
                command=window.destroy,
                font=fnt.body_large_font(),
            )
            cancel_btn.pack(pady=10)
        else:
            # Show "No updates available" message
            window = ctk.CTkToplevel(master=self)
            self.center_popup(self.winfo_toplevel(), window, width=400, height=200)
            window.attributes("-topmost", True)
            window.title("No Updates")

            label = ctk.CTkLabel(
                window,
                text="You are running the latest version!",
                font=fnt.body_large_font(),
            )
            label.pack(pady=20)

            ok_btn = ctk.CTkButton(
                window,
                text="OK",
                command=window.destroy,
                font=fnt.body_large_font(),
            )
            ok_btn.pack(pady=10)

    def _create_auth_button(self) -> None:
        """Create a button to enter Runecolor auth information.

        In the future, authentication information will be a combination of Runecolor
        username and an active subscription key.
        """
        self.auth_logo = ImageTk.PhotoImage(
            Image.open(PATH_UI / "authenticate.png").resize((IMG_SIZE, IMG_SIZE)),
            Image.LANCZOS,
        )
        self.btn_auth = ctk.CTkButton(
            master=self,
            text="Authenticate",
            font=fnt.body_large_font(),
            image=self.auth_logo,
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            hover_color=COLOR_HOVER,
            corner_radius=CORNER_RADIUS,
            fg_color=DEFAULT_GRAY,
            compound="left",
            command=self.__on_auth_clicked,
        )
        self.btn_auth.grid(row=3, column=1, padx=PADX, pady=(10, 10), sticky="ew", columnspan=1)
        self.btns.append(self.btn_auth)

    def _create_website_button(self) -> None:
        """Create a button to prompt a website pop-up in a default browser."""
        self.website_logo = ImageTk.PhotoImage(
            Image.open(PATH_UI / "website.png").resize((IMG_SIZE, IMG_SIZE)),
            Image.LANCZOS,
        )
        self.btn_website = ctk.CTkButton(
            master=self,
            text="Website",
            font=fnt.body_large_font(),
            image=self.website_logo,
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            hover_color=COLOR_HOVER,
            corner_radius=CORNER_RADIUS,
            fg_color=DEFAULT_GRAY,
            compound="left",
            command=self.__on_website_clicked,
            state="disabled",
        )
        self.btn_website.grid(row=5, column=2, padx=PADX, pady=(0, 0), sticky="sew")
        self.btns.append(self.btn_website)

    def _create_settings_button(self) -> None:
        """Create a button to access keybind settings."""
        self.img_settings = ImageTk.PhotoImage(
            Image.open(PATH_UI / "settings.png").resize((IMG_SIZE, IMG_SIZE)),
            Image.Resampling.LANCZOS,
        )
        self.btn_settings = ctk.CTkButton(
            master=self,
            text="Settings",
            font=fnt.body_large_font(),
            image=self.img_settings,
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            hover_color=COLOR_HOVER,
            corner_radius=CORNER_RADIUS,
            fg_color=DEFAULT_GRAY,
            compound="left",
            command=self.__on_settings_clicked,
            state="disabled",
        )
        self.btn_settings.grid(row=5, column=0, padx=PADX, pady=PADY, sticky="ew")
        self.btns.append(self.btn_settings)

    def _create_scraper_button(self) -> None:
        """Create a scraper button for the item sprite scraper utility."""
        self.scraper_logo = ImageTk.PhotoImage(
            Image.open(PATH_UI / "scraper.png").resize((IMG_SIZE, IMG_SIZE)),
            Image.LANCZOS,
        )
        self.btn_sprite_scraper = ctk.CTkButton(
            master=self,
            text="Scraper",
            font=fnt.body_large_font(),
            image=self.scraper_logo,
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            hover_color=COLOR_HOVER,
            corner_radius=CORNER_RADIUS,
            fg_color=DEFAULT_GRAY,
            compound="left",
            command=self.__on_scraper_clicked,
            state="disabled",
        )
        self.btn_sprite_scraper.grid(row=4, column=1, padx=PADX, pady=PADY, sticky="ew")
        self.btns.append(self.btn_sprite_scraper)

    def _create_color_filter_button(self) -> None:
        """Create a color filter button for the RGB-HSV color filter utility."""
        self.color_filter_logo = ImageTk.PhotoImage(
            Image.open(PATH_UI / "color.png").resize((IMG_SIZE, IMG_SIZE)),
            Image.LANCZOS,
        )
        self.btn_color_filter = ctk.CTkButton(
            master=self,
            text="Color Filter",
            font=fnt.body_large_font(),
            image=self.color_filter_logo,
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            corner_radius=CORNER_RADIUS,
            hover_color=COLOR_HOVER,
            fg_color=DEFAULT_GRAY,
            compound="left",
            command=self.__on_color_filter_clicked,
            state="disabled",
        )
        self.btn_color_filter.grid(row=4, column=2, padx=PADX, pady=PADY, sticky="ew")
        self.btns.append(self.btn_color_filter)

    # --- Utility Functions ---
    def _toggle_ui(self) -> None:
        """Enable or disable the UI based on whether authentication was successful."""
        state = "normal" if self.main.auth else "disabled"
        btns = (
            self.btns
            + self.main.current_btn_list
            + [self.main.btn_home, self.main.menu_game_selector]
        )
        for btn in btns:
            btn.configure(state=state)
        for bot_btns in self.main.btn_map.values():
            if bot_btns:
                for btn_bot in bot_btns:
                    btn_bot.configure(state=state)

    # --- Button Handlers ---
    def __on_auth_clicked(self) -> None:
        """Open Authentication as a popup after the associated button is clicked.

        Note that this method first submits any cached auth info for the authentication
        process, and if successful, skips opening the auth window, approves the auth,
        and unlocks the ui. If failed, it runs normally with the auth window popping up.
        """
        if self.main.subscription_key:
            result = AuthView._submit_and_authenticate(
                self, subscription_key=self.main.subscription_key
            )
            if result:  # Authentication successful: skip opening the AuthView window.
                self.__on_auth_success()
                return

        # Open the AuthView window if there's no cached key or if authentication failed.
        window = ctk.CTkToplevel(master=self)
        # The following line of code executes after a 201ms delay.
        # See: https://tinyurl.com/mvw55pkd
        self.after(
            201,
            lambda: window.iconbitmap(PATH_UI / "logo-corner.ico"),
        )
        window.attributes("-topmost", True)
        window.title("Authentication")
        window.geometry("430x660")  # [TO DEV] Remove this hardcoding.
        self.update()
        view = AuthView(parent=window, on_success_callback=self.__on_auth_success)
        view.pack(side="top", fill="both", expand=True, padx=PADX, pady=0)

    def __on_auth_success(self):
        """Handle successful auth by updating auth status and toggling the UI."""
        self.btn_auth.configure(text="Validated \u2713")
        self.main.auth = True
        self._toggle_ui()

    def __on_website_clicked(self) -> None:
        """Open a link to a website (e.g. wiki, source) upon clicking the button."""
        wb.open_new_tab("https://github.com/zakyn47/rune-color")

    def __on_settings_clicked(self) -> None:
        """Open Settings as a popup after the associated button is clicked."""
        window = ctk.CTkToplevel(master=self)
        # The following line of code executes after a 201ms delay.
        # See: https://tinyurl.com/mvw55pkd
        self.after(
            201,
            lambda: window.iconbitmap(PATH_UI / "logo-corner.ico"),
        )
        window.attributes("-topmost", True)
        window.title("Settings")
        window.geometry("564x364")  # [TO DEV] Remove this hardcoding.
        self.update()
        view = SettingsView(parent=window)
        view.pack(side="top", fill="both", expand=True, padx=PADX, pady=0)

    def __on_scraper_clicked(self) -> None:
        """Open the sprite scraper window."""
        window = ctk.CTkToplevel(master=self)
        self.after(
            201,
            lambda: window.iconbitmap(self.corner_icon_path),
        )
        window.attributes("-topmost", True)
        window.geometry("430x660")
        window.title("OSRS Wiki Sprite Scraper")
        view = SpriteScraperView(parent=window)
        view.pack(side="top", fill="both", expand=True, padx=0, pady=0)

    def __on_color_filter_clicked(self) -> None:
        """Open the HSV-RGB color filter interface."""
        window = ctk.CTkToplevel(master=self)
        self.after(
            201,
            lambda: window.iconbitmap(self.corner_icon_path),
        )
        window.attributes("-topmost", True)
        window.geometry("906x744")
        window.title("Color Filter")
        view = ColorFilterView(parent=window)
        view.pack(side="top", fill="both", expand=True, padx=0, pady=0)

    def center_popup(self, parent, popup, width=400, height=200):
        """Center a popup window relative to its parent.
        Args:
            parent (ctk.CTkFrame): The parent frame to center the popup relative to.
            popup (ctk.CTkToplevel): The popup window to center.
            width (int): Width of the popup window.
            height (int): Height of the popup window.
        """
        parent.update_idletasks()  # Ensure geometry info is up-to-date
        x = parent.winfo_rootx()
        y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        # Calculate position for the popup to be centered
        pos_x = x + (parent_width // 2) - (width // 2)
        pos_y = y + (parent_height // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{pos_x}+{pos_y}")


def download_with_progress(url, save_path, progress_bar, speed_label, window):
    """Download a file with a progress bar and speed label.
    Args:
        url (str): The URL of the file to download.
        save_path (str): The path where the downloaded file will be saved.
        progress_bar (ctk.CTkProgressBar): The progress bar widget to update.
        speed_label (ctk.CTkLabel): The label to display download speed.
        window (ctk.CTkToplevel): The parent window for the progress bar and label.
    """
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get("content-length", 0))
        if total_size == 0:
            raise ValueError("Failed to retrieve content length.")

        with open(save_path, "wb") as file:
            downloaded_size = 0
            start_time = time.time()

            for data in response.iter_content(chunk_size=4096):
                file.write(data)
                downloaded_size += len(data)

                # Update progress bar
                progress_bar.set(downloaded_size / total_size)
                elapsed_time = time.time() - start_time
                speed = downloaded_size / (1024 * elapsed_time) if elapsed_time > 0 else 0
                speed_label.configure(text=f"Speed: {speed:.2f} KB/s")

            # Download complete
            progress_bar.set(1.0)
            speed_label.configure(text="Download complete!")
            print(f"File downloaded to {save_path}")

    except Exception as e:
        print(f"Error during download: {e}")

def start_download_thread(url, save_path, progress_bar, speed_label, window):
    """Start a download in a separate thread to avoid blocking the UI.
    Args:
        url (str): The URL of the file to download.
        save_path (str): The path where the downloaded file will be saved.
        progress_bar (ctk.CTkProgressBar): The progress bar widget to update.
        speed_label (ctk.CTkLabel): The label to display download speed.
        window (ctk.CTkToplevel): The parent window for the progress bar and label.
    """
    download_thread = threading.Thread(
        target=download_with_progress,
        args=(url, save_path, progress_bar, speed_label, window))
    download_thread.start()