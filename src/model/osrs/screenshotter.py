import cv2

from model.osrs.osrs_bot import OSRSBot
from utilities.img_search import BOT_IMAGES


class Screenshotter(OSRSBot):
    PATH_SCREENS = BOT_IMAGES / "screenshotter"

    def __init__(self) -> None:
        bot_title = "Screenshotter"
        description = "Take screenshots to use in the Color Filter utility."
        super().__init__(bot_title=bot_title, description=description)
        self.options_set = True

    def create_options(self) -> None:
        """Add bot options (placeholder). See `utilities.options_builder` for more."""
        pass

    def save_options(self, options: dict) -> None:
        """Load options into the bot object (placeholder).

        `options` is necessary here so the `BotController` executes as expected when
        options are saved.
        """
        self.options_set = True

    def main_loop(self) -> None:
        """Run the main screenshotter loop."""
        self.export_game_view()
        self.export_minimap()
        self.export_control_panel()
        self.stop()

    def export_game_view(self) -> None:
        """Screenshot and export the game view."""
        image = self.win.game_view.screenshot()
        cv2.imwrite(str(self.PATH_SCREENS / "screenshotter-game-view.png"), image)
        self.log_msg("Game view screenshot saved.")

    def export_control_panel(self) -> None:
        """Screenshot and export the control panel."""
        image = self.win.control_panel.screenshot()
        cv2.imwrite(str(self.PATH_SCREENS / "screenshotter-control-panel.png"), image)
        self.log_msg("Control panel screenshot saved.")

    def export_minimap(self) -> None:
        """Screenshot and export the minimap."""
        image = self.win.minimap.screenshot()
        cv2.imwrite(str(self.PATH_SCREENS / "screenshotter-minimap.png"), image)
        self.log_msg("Minimap screenshot saved.")
