import os
import re
from enum import IntEnum
from pathlib import Path
from typing import Callable, List, Optional, Union

import cv2
import numpy as np
import requests

# When `sprite_scraper` is run directly, go up one directory to import `img_search`.
if __name__ == "__main__":
    import sys

    sys.path[0] = os.path.dirname(sys.path[0])

import utilities.img_search as imsearch


class ImageType(IntEnum):
    NORMAL = 0
    BANK = 1
    ALL = 2


class SpriteScraper:
    """Download game sprites via the OSRS wiki API."""

    def __init__(self):
        """Instantiate a `SpriteScraper` to scrape sprites from the Wiki."""
        self.BASE_URL = "https://oldschool.runescape.wiki/"
        self.DEFAULT_DESTINATION = imsearch.BOT_IMAGES.joinpath("scraper")

    def search_and_download(self, search_string: str, **kwargs) -> Path:
        """Search for and downloads the image(s) specified `search_string`.

        Args:
            search_string (str): The search string to use (e.g. "Dragon axe").
            **kwargs: Arbitrary keyword arguments used in the context of...?

        Notable Kwargs:
            image_type (`ImageType`): The type of image to save. Defaults to
                `ImageType.NORMAL`.
            destination (str | Path): Directory for saving images within.
                Defaults to `DEFAULT_DESTINATION`.
            notify_callback (Callable): Callback function to notify the user. Defaults
                to `print`.
        Returns:
            Path: Directory containing the downloaded images.
        """
        # Extract and validate keyword arguments.
        image_type, destination, notify_callback = self.__extract_kwargs(kwargs)
        img_names = self._format_args(search_string)
        if not img_names:
            notify_callback("No search terms entered.")
            return

        # Search for each image, and if found, download it.
        notify_callback("Beginning search...\n")
        completed_with_errors = False
        for img_name in img_names:
            notify_callback(f"Searching for {img_name}...")
            img_url = self.__find_image_url(img_name, notify_callback)
            if not img_url:
                notify_callback(f"No image found for {img_name}.\n")
                completed_with_errors = True
                continue
            success = self.__download_and_save_image(
                img_name, img_url, image_type, destination, notify_callback
            )
            if not success:
                completed_with_errors = True
        if completed_with_errors:
            notify_callback(
                "Search completed with errors. Some images may not have been saved."
                f" See:\n{destination}.\n"
            )
        notify_callback(f"Search complete. Images saved to:\n{destination}.\n")
        return Path(destination)

    def _bankify_image(self, image: cv2.Mat) -> cv2.Mat:
        """Crop a base item sprite to match a bank menu sprite.

        This function centers the image in a 36x32 frame, and deletes some pixels at
        the top of the image to remove the stack number. Cropping away the gold
        quantity numbers increases the accuracy of `utilities.imagesearch` functions.

        Args:
            image (cv2.Mat): The image to crop, stored as matrix.

        Returns:
            Path: Path to the the bankified PNG image.
        """
        height, width = image.shape[:2]
        max_height, max_width = 32, 36
        if height > max_height or width > max_width:
            msg = (
                "Warning: Image is already larger than bank slot."
                "This sprite is unlikely to be relevant for bank functions."
            )
            print(msg)
            return image
        height_diff = max_height - height
        width_diff = max_width - width
        # Create a padded border around the sprite to center it within the 36x32 frame.
        image = cv2.copyMakeBorder(
            image,
            height_diff // 2,
            height_diff // 2,
            width_diff // 2,
            width_diff // 2,
            cv2.BORDER_CONSTANT,
            value=0,
        )
        image[:9, :] = 0  # Set the top 9 rows of pixels to 0.
        return image

    def _capitalize_each_word(self, string: str) -> str:
        """Capitalize words in a string separated by underscores, keeping them.

        Args:
            string (str): The snake case string (e.g. "Sapphire_amulet_noted").

        Returns:
            str: The snake case string, but with each substring capitalized.

        Examples:
            self._capitalize_each_word("Golden_ring_of_mordor")
            >>> "Golden_Ring_of_Mordor"
        """
        exclude = ["from", "of", "to", "in", "with", "on", "at", "by", "for"]
        return "_".join(
            word if word in exclude else word.capitalize() for word in string.split("_")
        )

    def _format_args(self, arg_str: str) -> Union[List[str], List]:
        """Turn a comma-separated string to a list of capitalized words and underscores.

        Args:
            arg_str (str): The provided string of potentially space-separated arguments.

        Returns:
            Union[List[str], List]: A list of the snake case arguments or an empty list
                if `arg_str` is just an empty string.

        Examples:
            "apple, banana, orange"
            >>> ['Apple', 'Banana', 'Orange']

            "apple,banana,orange"
            >>> ['Apple', 'Banana', 'Orange']

            "red_blue_green, yellow, _purple"
            >>> ['Red_Blue_Green', 'Yellow', '_Purple']

            ""
            >>> []
        """
        if not arg_str.strip():  # If the string is empty, return an empty list
            return []
        arg_str = " ".join(arg_str.split())  # Reduce multiple spaces to a single space.
        # Strip whitespace and replace spaces with underscores
        return [
            word.strip().replace(" ", "_").capitalize() for word in arg_str.split(",")
        ]

    def __extract_kwargs(self, kwargs):
        """Extract and validate keyword arguments from the input dictionary.

        Args:
            kwargs (dict): Keyword arguments dictionary.

        Returns:
            tuple: A tuple containing image type, destination directory, and user
                callback function.
        """
        image_type = kwargs.get("image_type", ImageType.NORMAL)
        destination = kwargs.get("destination", self.DEFAULT_DESTINATION)
        notify_callback = kwargs.get("notify_callback", print)
        if image_type not in iter(ImageType):
            notify_callback("Invalid image type argument. Assigning default value.\n")
            image_type = ImageType.NORMAL
        return image_type, str(destination), notify_callback

    def __get_item_infobox_data(self, item: str) -> Optional[str]:
        """Return a string of data from the info box for a specific item from the Wiki.

        Args:
            item (str): The item name.

        Returns:
            Optional[str]: JSON string of the info box, or None if the item does not
                exist or if an error occurred.
        """
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "format": "json",
            "titles": item,
        }

        try:
            response = requests.get(url=f"{self.BASE_URL}/api.php", params=params)
            data = response.json()
            pages = data["query"]["pages"]
            page_id = list(pages.keys())[0]
            return None if int(page_id) < 0 else pages[page_id]["revisions"][0]["*"]
        except requests.exceptions.ConnectionError as e:
            print("Network error:", e)
            return
        except requests.exceptions.RequestException as e:
            print("Request failed:", e)
            return

    def __sprite_url(self, item: str) -> Optional[str]:
        """Return the sprite URL associated with `item`.

        Args:
            item (Optional[str]): The item name.

        Returns:
            str: URL of the sprite image, or None if the sprite name wasn't found.
        """
        info_box = self.__get_item_infobox_data(item)
        if not info_box:
            print(f"{item}: Page doesn't exist.")
            return
        pattern = r"\[\[File:(.*?)\]\]"
        if match := re.search(pattern, info_box):
            filename = match[1]
            filename = filename.replace(" ", "_")
            return f"{self.BASE_URL}images/{filename}"
        print(f"{item}: Sprite couldn't be found in the info box.")

    def __find_image_url(
        self, img_name: str, notify_callback: Callable
    ) -> Optional[str]:
        """Find the image URL with two attempts.

        This function tries again after the first attempt, capitalizing each word in
        `image_name` on the second attempt.

        Args:
            img_name (str): The name of the image to search for.
            notify_callback (Callback): Callback function to notify the user.

        Returns:
            Optional[str]: The image URL, or None if not found.
        """
        for attempt in range(2):
            if attempt == 1:
                img_name = self._capitalize_each_word(img_name)
            img_url = self.__sprite_url(img_name)
            if img_url is not None:
                notify_callback(f"Found sprite: {img_name}")
                return img_url

    def __download_and_save_image(
        self,
        img_name: str,
        img_url: str,
        image_type: ImageType,
        destination: str,
        notify_callback,
    ) -> bool:
        """Download the image and save it according to `image_type`.

        Args:
            img_name (str): Name of the image to save.
            img_url (str): URL of the image to download.
            image_type (ImageType): Type of image to save.
            destination (str): Destination folder to save the image within.
            notify_callback (function): Callback function to notify the user.

        Returns:
            bool: True if the image was download and then saved successfully, False
                otherwise.
        """
        notify_callback("Downloading image...")
        try:
            response = requests.get(img_url)
            downloaded_img = np.frombuffer(response.content, dtype="uint8")
            downloaded_img = cv2.imdecode(downloaded_img, cv2.IMREAD_UNCHANGED)
            self.__save_image(
                img_name, downloaded_img, image_type, destination, notify_callback
            )
            return True
        except requests.exceptions.RequestException as e:
            notify_callback(f"Network error: {e}\n")
            return False
        except cv2.error as e:
            notify_callback(f"Image decoding error: {e}\n")
            return False

    def __save_image(
        self,
        img_name: str,
        downloaded_img: np.ndarray,
        image_type: ImageType,
        destination: str,
        notify_callback,
    ) -> bool:
        """Save the image according to `image_type`.

        Args:
            img_name (str): Name of the image to save.
            downloaded_img (np.ndarray): Image to save.
            image_type (ImageType): Type of image to save.
            destination (str): Destination folder to save the image within.
            notify_callback (function): Callback function to notify the user.

        Returns:
            bool: True if the image was successfully saved, False otherwise.
        """
        destination: Path = Path(destination)
        # Create the destination folder if it doesn't already exist.
        destination.mkdir(parents=True, exist_ok=True)
        img_name = img_name.lower().replace("_", "-")
        filepath = destination / f"{img_name}.png"
        filepath_bank = destination / f"{img_name}-bank.png"
        try:
            if image_type in {ImageType.NORMAL, ImageType.ALL}:
                cv2.imwrite(str(filepath), downloaded_img)
                nl = "\n"
                notify_callback(
                    "Normal sprite saved as:"
                    f" {filepath.name}.{nl if image_type != 2 else ''}"
                )
            if image_type in {ImageType.BANK, ImageType.ALL}:
                cropped_img = self._bankify_image(downloaded_img)
                cv2.imwrite(str(filepath_bank), cropped_img)
                notify_callback(f"Bankified sprite saved as: {filepath_bank.name}.\n")
            return True
        except Exception as e:
            notify_callback(f"Error saving image: {e}\n")
            return False


if __name__ == "__main__":
    scraper = SpriteScraper()

    assert scraper._format_args("") == []
    assert scraper._format_args("a, b, c") == ["A", "B", "C"]
    assert scraper._format_args(" shark ") == ["Shark"]
    assert scraper._format_args(" swordfish ,lobster, lobster   pot ") == [
        "Swordfish",
        "Lobster",
        "Lobster_pot",
    ]
    assert scraper._format_args("Swordfish ,lobster, Lobster_Pot ") == [
        "Swordfish",
        "Lobster",
        "Lobster_pot",
    ]

    assert scraper._capitalize_each_word("swordfish") == "Swordfish"
    assert scraper._capitalize_each_word("Lobster_pot") == "Lobster_Pot"
    assert (
        scraper._capitalize_each_word("arceuus_home_teleport")
        == "Arceuus_Home_Teleport"
    )
    assert scraper._capitalize_each_word("protect_from_magic") == "Protect_from_Magic"
    assert scraper._capitalize_each_word("teleport_to_house") == "Teleport_to_House"
    assert scraper._capitalize_each_word("claws_of_guthix") == "Claws_of_Guthix"

    # Test saving to non-existent directory in string format.
    new_destination = str(scraper.DEFAULT_DESTINATION.joinpath("lobster_stuff"))
    scraper.search_and_download(
        search_string=" lobster , lobster  Pot",
        image_type=ImageType.BANK,
        destination=new_destination,
    )

    # Test saving without using Enum, and with a non-existent item query.
    scraper.search_and_download(
        search_string="protect from magic, arceuus home teleport, nonexistent_sprite",
        image_type=0,
    )

    print("Test cleared.")
