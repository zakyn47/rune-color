import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import pynput.keyboard as keyboard
import platformdirs

# Define the application name for the AppData directory
APP_NAME = "Runecolor"

# Get the user data directory using platformdirs
USER_DATA_DIR = Path(platformdirs.user_data_dir(appname=APP_NAME))
SETTINGS_PATH = USER_DATA_DIR / "settings.pickle"


def load_settings_file() -> Dict[str, Any]:
    """Open `src/settings.pickle` and load its data into a dictionary.

    Returns:
        Dict[str, Any]: A dictionary containing the loaded data.
    """
    with open(SETTINGS_PATH, "rb") as file:
        data = pickle.load(file)
    return data


def set(key: str, value: Any) -> None:
    """Set a value in `settings.pickle` corresponding to the given key.

    Note that if a `src/settings.pickle` file doesn't exist, a new one is dynamically
    created.

    Args:
        key (str): The key set a value for within `settings.pickle`.
        value (Any): The value to set for the given key.
    """
    # Ensure the directory exists before writing the file
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = load_settings_file()
    except FileNotFoundError:
        data = {}
    data[key] = value  # Update the value in the given key.
    with open(SETTINGS_PATH, "wb") as file:  # Save the data back to the file.
        pickle.dump(data, file)


def get(key: str) -> Optional[Any]:
    """Retrieve a value from `settings.pickle` based on the given key.

    Args:
        key (str): The key corresponding to the value to retrieve.

    Returns:
        Optional[Any]: The value associated with the provided key, or None if the key
            was not found.
    """
    try:
        data = load_settings_file()
    except FileNotFoundError:
        return None
    return data.get(key)  # Return the value corresponding to the given key.


def delete(key: str) -> None:
    """Delete a value from `settings.pickle` based on the given key.

    Note that if the settings file is not found, this function returns without
    performing any deletion.

    Args:
        key (str): The key corresponding to the desired value to delete.

    Raises:
        FileNotFoundError: Raised if `settings.pickle` cannot be found.
    """
    try:
        data = load_settings_file()
    except FileNotFoundError:
        return
    del data[key]  # Delete the given key.
    with open(SETTINGS_PATH, "wb") as file:  # Save the data back to the file.
        pickle.dump(data, file)


def keybind_to_text(current_keys: List[keyboard.Key]) -> str:
    """Convert a list of keys into their corresponding symbolic representations.

    Args:
        current_keys (List[keyboard.Key]): A list of `pynput.keyboard.Key` elements
            representing a sequence of keystrokes.

    Returns:
        str: The matching keys together in a string, each key separated by a plus sign.
    """
    hotkeys = []
    if current_keys:
        for key in current_keys:
            match key:
                case keyboard.Key.enter:
                    hotkeys.append("↵")
                case keyboard.Key.space:
                    hotkeys.append("␣")
                case keyboard.Key.ctrl | keyboard.Key.ctrl_l | keyboard.Key.ctrl_r:
                    hotkeys.append("ctrl")
                case keyboard.Key.alt | keyboard.Key.alt_l | keyboard.Key.alt_r:
                    hotkeys.append("⌥")
                case keyboard.Key.shift_l:
                    hotkeys.append("L⇧")
                case keyboard.Key.shift_r:
                    hotkeys.append("R⇧")
                case keyboard.Key.cmd | keyboard.Key.cmd_l | keyboard.Key.cmd_r:
                    hotkeys.append("⌘")
                case keyboard.Key.caps_lock:
                    hotkeys.append("⇪")
                case keyboard.Key.tab:
                    hotkeys.append("⇥")
                case keyboard.Key.backspace:
                    hotkeys.append("⌫")
                case _:
                    hotkeys.append(key)
    return " + ".join(map(str, hotkeys)).replace("'", "")
