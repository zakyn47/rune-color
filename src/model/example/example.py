import time

from model.example.example_bot import ExampleBot


class OSRSExample(ExampleBot):
    def __init__(self):
        bot_title = "Exhibit A"
        description = (
            "This example is here to highlight how bots can be further organized by"
            " folders while still being dynamically picked up by the `options_builder`."
        )
        super().__init__(bot_title=bot_title, description=description)
        # We can set default option values here if we'd like, and potentially override
        # needing to open the options panel.
        self.run_time = 10
        self.options_set = False

    def create_options(self):
        """Add bot options.

        Use an `OptionsBuilder` to define the options for the bot. For each function
        call below, we define the type of option we want to create, its key, a label
        for the option that the user will see, and the possible values the user can
        select. The key is used in the `save_options` method to unpack the dictionary
        of options after the user has selected them.
        """
        self.options_builder.add_slider_option(
            "run_time", "How long to run (minutes)?", 1, 500
        )
        self.options_builder.add_text_edit_option(
            "text_edit_example", "Text Edit Example", "Placeholder text here"
        )
        self.options_builder.add_checkbox_option(
            "multi_select_example", "Multi-select Example", ["A", "B", "C"]
        )
        self.options_builder.add_dropdown_option(
            "menu_example", "Menu Example", ["A", "B", "C"]
        )

    def save_options(self, options: dict):
        """Load options into the bot object.

        For each option in the dictionary, if it is an expected option, save the value
        as a property of the bot. If any unexpected options are found, log a warning.
        If an option is missing, set the `options_set` flag to False.
        """
        for option in options:
            if option == "run_time":
                self.run_time = options[option]
            elif option == "text_edit_example":
                self.log_msg(f"Text edit example: {options[option]}")
            elif option == "multi_select_example":
                self.log_msg(f"Multi-select example: {options[option]}")
            elif option == "menu_example":
                self.log_msg(f"Menu example: {options[option]}")
            else:
                self.log_msg(f"Unknown option: {option}")
                print("Options are packed incorrectly.")
                self.options_set = False
                return
        self.log_msg(f"Running time: {self.run_time} minutes.")
        self.log_msg("Options set successfully.")
        self.options_set = True

    def main_loop(self):
        """Execute the main logic loop of the bot.

        Responsibilities:
            1. To halt the bot within this function, call `self.stop()`. This action is
                usually necessary when the bot encounters errors or gets stuck.

            2. Call `self.update_progress()` at least once per gameplay loop. Also,
                use `self.log_msg()` frequently to update the bot controller on the
                current status and intended behavior of the bot.

            3. After the main loop execution, remember to call `self.stop()` to
                terminate the daemon thread (`BotThread`) and prevent it from
                unintentionally running in the background.

        Lastly, utilize the numerous quality-of-life-improving methods available in
        `Bot` and `RuneLiteBot` classes. Leveraging these methods significantly
        accelerates the development process.
        """
        run_time_str = f"{self.run_time // 60}h {self.run_time % 60}m"  # e.g. 6h 0m
        self.log_msg(f"[START] ({run_time_str})", overwrite=True)
        start_time = time.time()
        end_time = int(self.run_time) * 60  # Measured in seconds.
        while time.time() - start_time < end_time:
            """
            if something:
                do something
            if something else:
                move somewhere
                check something
                ...
            deposit gold in bank
            """
            self.log_msg(f"{end_time - (time.time() - start_time)}", overwrite=True)
            print(time.time())
            time.sleep(1)
            self.update_progress((time.time() - start_time) / end_time)

        self.update_progress(1)
        self.log_msg("[END]")
        self.stop()
