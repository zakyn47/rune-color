import json
import os
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

import requests
from packaging import version

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
        # For now, we'll use a hardcoded version since we don't have version tracking
        # In the future, this could be read from a version file or git tags
        return "0.0.0"

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

    def download_update(self, download_url: str) -> bool:
        """Download the latest update.

        Args:
            download_url (str): The URL to download the update from.

        Returns:
            bool: Whether the download was successful.
        """
        try:
            # Create a temporary directory for the download
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download the file
                response = requests.get(download_url, stream=True)
                response.raise_for_status()

                # Save to temporary file
                temp_file = Path(temp_dir) / "runecolor_update.exe"
                with open(temp_file, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # Open the download in the default browser
                webbrowser.open(download_url)
                return True

        except Exception as e:
            print(f"Error downloading update: {e}")
            return False
