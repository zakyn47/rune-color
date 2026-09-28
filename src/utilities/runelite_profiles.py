"""Where each script's RuneLite profile lives, and what RuneLite calls it."""

from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parents[1] / "profiles"
USE_OWN_PROFILE_SETTING = "use_own_runelite_profile"


def profile_path(key: str) -> Path:
    """Return the committed profile file for a script.

    Args:
        key (str): The script's `runelite_profile`, e.g. "power_chopper".

    Returns:
        Path: The absolute path of `src/profiles/<key>.properties`.
    """
    return PROFILES_DIR / f"{key}.properties"


def profile_name(bot_title: str) -> str:
    """Return the name the profile gets inside RuneLite.

    Args:
        bot_title (str): The script's title as the UI shows it.

    Returns:
        str: For example "RuneColor - Power Chopper & Firemaking".
    """
    return f"RuneColor - {bot_title}"
