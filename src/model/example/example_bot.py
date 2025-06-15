from abc import ABCMeta

from model.runelite_bot import RuneLiteBot, RuneLiteWindow


class ExampleBot(RuneLiteBot, metaclass=ABCMeta):
    win: RuneLiteWindow = None

    def __init__(self, bot_title, description) -> None:
        super().__init__(
            game_title="Example", bot_title=bot_title, description=description
        )
