from abc import ABCMeta

from model.runelite_bot import RuneLiteBot, RuneLiteWindow


class OSRSBot(RuneLiteBot, metaclass=ABCMeta):
    win: RuneLiteWindow = None

    def __init__(self, bot_title, description) -> None:
        super().__init__(
            game_title="OSRS", bot_title=bot_title, description=description
        )
        self.test_attribute = 0

    def test_function(self):
        print("test")
