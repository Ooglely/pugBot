"""Implements the log searcher file, which takes the players from a team generation or moved back and searches for the log associated with the game that was played/being played."""
from util import get_steam64
import time
from pug import PugCategory
from logs import Player, LogData
from database import BotCollection
from nextcord.ext import tasks
from logs.logstf_api import LogsAPI

queue_db = BotCollection("logs", "queue")
searcher_db = BotCollection("logs", "searcher")


class PartialLog:
    def __init__(
        self, guild: int, category: PugCategory, players: list[Player]
    ) -> None:
        self.guild: int = guild
        self.timestamp: int = time.time().__round__()
        self.category: PugCategory = category
        self.players: list[Player] = players

    def export(self):
        return {
            "guild": self.guild,
            "timestamp": self.timestamp,
            "category": self.category.__dict__(),
            "players": [player.__dict__ for player in self.players],
        }


class FullLog(PartialLog):
    def __init__(
        self, partial_log: PartialLog, log_id: str, log_data: dict | None = None
    ) -> None:
        self.guild = partial_log.guild
        self.timestamp = partial_log.timestamp
        self.category = partial_log.category
        self.players = partial_log.players
        self.log_id: str = log_id
        self.log: dict | None = LogData(log_data)

    def __dict__(self):
        return {
            "guild": self.guild,
            "timestamp": self.timestamp,
            "category": self.category.__dict__(),
            "players": [player.__dict__ for player in self.players],
            "log_id": self.log_id,
        }

    def update_log_data(self, log_data: dict) -> None:
        self.log = LogData(log_data)


class LogSearcher:
    def __init__(self) -> None:
        pass

    @staticmethod
    @tasks.loop(minutes=1)
    async def searcher():
        """Goes through the searcher queue and tries to find a corresponding logs.tf log for each game.

        The list of players and the timestamp of the game is used to filter and find the log.
        If a log is found, it is added to the queue.
        If 6 hours has passed and no log has been found, the game is deleted from the searcher.
        If a log ID matches a log ID already registered in the bot, the game is deleted from the searcher.
        """
        print("Running searcher...")
        searcher_logs = await searcher_db.find_all_items()
        for log in searcher_logs:
            print(f"Log: {log['_id']}")
            players = [Player(data=player) for player in log["players"]]
            partial_log = PartialLog(
                log["guild"],
                PugCategory(log["category"]["name"], log["category"]),
                players,
            )
            print(f"Timestamp: {partial_log.timestamp}")

            steam_ids = [player.steam_64 for player in partial_log.players]
            print(steam_ids)

            query = await LogsAPI.search_for_log(players=steam_ids, limit=10)
            print(f"Result: {query}")

    @staticmethod
    @tasks.loop(minutes=1)
    async def queue():
        """The queue looks through each log in it and checks to see if the log has been completed.

        Here are the conditions for a match being considered done (may change):
        - Map score has been reached
        OR
        - Game time has reached 30 minutes
        OR
        - Log data isn't changing anymore
        """
        print("Running queue...")

    @staticmethod
    async def add_searcher_game(
        guild: int, category: PugCategory, players: list[Player]
    ) -> None:
        """Add a game to the log searcher.

        Args:
            guild (int): The guild ID to add the game to.
            category (PugCategory): The category the game was played in.
            players (list[Player]): The players in the game.
        """
        for player in players:
            await player.link_player()
        await searcher_db.add_item(PartialLog(guild, category, players).export())

    @staticmethod
    async def delete_searcher_game(database_id: int | str) -> None:
        """Delete a game from the log searcher.

        Args:
            database_id (int | str): The database ID of the game to delete.
        """
        await searcher_db.delete_item({"_id": database_id})

    @staticmethod
    async def _add_queue_game(log: FullLog) -> None:
        await queue_db.add_item(log.__dict__)

    @staticmethod
    async def _delete_queue_game(database_id: int | str) -> None:
        await queue_db.delete_item({"_id": database_id})


async def test():
    category_db = BotCollection("guilds", "categories")

    guild = 727627956058325052
    category_data = await category_db.find_item({"_id": guild})
    category = PugCategory("test", category_data["categories"]["AM - A Pugs"])
    players = [
        Player(steam=76561199487903742),
        Player(steam=76561198960637154),
        Player(steam=76561199154478125),
        Player(steam=76561198289262787),
        Player(steam=76561198309306120),
        Player(steam=76561198099514566),
        Player(steam=76561199026794527),
        Player(steam=76561199083479139),
        Player(steam=76561199478391681),
        Player(steam=76561198971354161),
        Player(steam=76561199388123242),
        Player(steam=76561198067994868),
    ]

    # await LogSearcher.add_searcher_game(guild, category, players)
    await LogSearcher().searcher()
    # The resulting log should be 3490943
