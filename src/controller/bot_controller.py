if __name__ == "__main__":
    import os
    import sys

    # Go up a level to facilitate importing from `model`.
    sys.path[0] = os.path.dirname(sys.path[0])
from customtkinter import CTkFrame
from customtkinter.windows.ctk_toplevel import CTkToplevel

from model.bot import Bot, BotStatus
from views.bot_view import BotView


class BotController:
    """An intermediary between the bot's functions and its user interface (UI).

    `BotController` facilitates communication and coordination between the bot and the
    UI, ensuring that actions taken by the bot are reflected in the UI and vice versa.
    Since the `BotController` plays a critical role in the UI's compilation and
    functionality, its methods should generally remain unmodified to avoid disrupting
    core behavior.

    Attributes and methods in this class handle key processes essential to the bot-UI
    interaction.
    """

    def __init__(self, model: Bot, view: BotView) -> None:
        """Instantiate a `BotController`.

        The controller operates the `Bot` model while returning relevant information
        to the main scrollable output log known as the `BotView`.
        """
        self.model = model
        self.view = view

    def play(self) -> None:
        """Launch the `Bot` in response to the Play button being left-clicked.

        The view tells the model to run with its current settings.
        """
        self.model.play()

    def stop(self) -> None:
        """Pause the script in response to the Stop button being left-clicked.

        The view tells the model to stop running.

        Each `Bot` runs in its own daemon thread, so when the Stop button is
        left-clicked, the thread stops immediately afterward. The `BotView` will still
        persist though to allow for resuming via left-clicking the Play button again or
        potentially changing options.
        """
        self.model.stop()

    def get_options_view(self, parent: CTkToplevel) -> CTkFrame:
        """Open the options view in response to the Options button being left-clicked.

        The view tells the model to populate its options pane.

        Args:
            parent (CTkToplevel): An independent window that can be moved, minimized,
                or closed, much like the root window.

        Returns:
            CTkFrame: The bot's options window, derived from the UI.
        """
        self.model.set_status(BotStatus.CONFIGURING)
        return self.model.get_options_view(parent)

    def save_options(self, options) -> None:
        """Save the options view in response to left-clicking Save.

        The view tells the model to save the given options. Note that this process is
        aborted if the user closes the popup options window.
        """
        self.model.save_options(options)
        if self.model.options_set:
            self.model.set_status(BotStatus.CONFIGURED)
        else:
            self.model.set_status(BotStatus.STOPPED)

    def abort_options(self) -> None:
        """Stop configuring options upon closing the options window.

        The view tells the model to stop configuring when the options window is closed.
        """
        self.update_log("Bot configuration aborted.")
        self.model.set_status(BotStatus.STOPPED)

    def update_status(self) -> None:
        """Update the bot's general status as displayed on the `BotView`.

        The model tells the view to update bot's status."""
        status = self.model.status
        if status == BotStatus.RUNNING:
            self.view.frame_info.update_status_running()
        elif status == BotStatus.STOPPED:
            self.view.frame_info.update_status_stopped()
        elif status == BotStatus.CONFIGURING:
            self.view.frame_info.update_status_configuring()
        elif status == BotStatus.CONFIGURED:
            self.view.frame_info.update_status_configured()

    def update_progress(self) -> None:
        """Update the bot's progress bar and percentage as displayed on the `BotView`.

        The model tells the view to update the bot's current progress."""
        self.view.frame_info.update_progress(self.model.progress)

    def update_log(self, msg: str, overwrite: bool = False) -> None:
        """Update the output log with a given message.

        The model tells the view to update the log.

        Args:
            msg (str): The message the update the console log with.
            overwrite (bool, optional): Overwrites the previous message in the console
                log. Defaults to False.
        """
        self.view.frame_output_log.update_log(msg, overwrite)

    def clear_log(self) -> None:
        """Clear the output log.

        The model tells the view to clear the log.
        """
        self.view.frame_output_log.clear_log()

    def change_model(self, model: Bot) -> None:
        """Swap the controller's model, halting the old one.

        The view tells the controller to swap its model (i.e. `change_model` is called
        from the view). Note that this method reconfigures the `InfoFrame`.

        Args:
            model: The new model to use.
        """
        if self.model is not None:
            self.view.frame_info.stop_keyboard_listener()
            try:
                self.model.stop()
            except AttributeError:
                print(
                    "Unable to stop the bot thread while changing views because it is"
                    " not currently running. This is expected behavior and can be"
                    " safely ignored."
                )
            self.model.options_set = False
        self.model = model
        if self.model is not None:
            self.view.frame_info.setup(
                title=model.bot_title, description=model.description
            )
            self.view.frame_info.start_keyboard_listener()
        else:
            self.view.frame_info.setup(title="", description="")
        self.clear_log()


class MockBotController:
    def __init__(self, model: Bot) -> None:
        """Run a mock controller for a bot without a UI.

        Args:
            model (Bot): The model to coordinate with the controller.
        """
        self.model = model

    def update_status(self) -> None:
        """Update the bot's general status.

        The model tells the view to update the bot's general status."""
        print(f"Status: {self.model.status}")

    def update_progress(self) -> None:
        """Update the percentage progress shown above the console log.

        The model tells the view to update the bot's percentage progress."""
        print(f"Progress: {int(self.model.progress * 100)}%")

    def update_log(self, msg: str, overwrite: bool = False) -> None:
        """Update the console log with a message.

        The model tells the view to update the console log.

        Args:
            msg (str): The message the update the console log with.
            overwrite (bool, optional): Overwrites the previous message in the console
                log. Defaults to False.
        """
        print(f"Log: {msg}")

    def clear_log(self) -> None:
        """Clear the console log.

        The model tells the view to clear the log."""
        print("--- Log Cleared ---")
