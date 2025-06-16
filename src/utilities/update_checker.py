import json
import os
import sys
import platformdirs
from pathlib import Path
from typing import Optional, Tuple

import requests
from packaging import version

sys.path.append(str(Path(__file__).parents[1]))
from runecolor_version import __version__

# Constants
REPO_OWNER = "zakyn47"
REPO_NAME = "rune-color"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"


class UpdateChecker:
    """Utility class to check for and download updates from GitHub releases."""

    def __init__(self):
        """Initialize the update checker."""
        self.current_version = self._get_current_version()

    def _get_current_version(self) -> str:
        """Get the current version of the application.

        Returns:
            str: The current version string.
        """
        return __version__

    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check if there are any updates available.

        Returns:
            Tuple[bool, Optional[str], Optional[str]]: A tuple containing:
                - bool: Whether an update is available
                - Optional[str]: The latest version if available
                - Optional[str]: The download URL if available
        """
        try:
            response = requests.get(GITHUB_API_URL)
            response.raise_for_status()

            release_data = response.json()
            latest_version = release_data["tag_name"].lstrip("v")
            download_url = None

            # Find .exe asset
            for asset in release_data.get("assets", []):
                if asset["name"].endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    break

            if version.parse(latest_version) > version.parse(self.current_version):
                return True, latest_version, download_url

            return False, None, None

        except Exception as e:
            print(f"Error checking for updates: {e}")
            return False, None, None