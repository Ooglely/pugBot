"""Implements the log searcher file, which takes the players from a team generation or moved back and searches for the log associated with the game that was played/being played."""
import time

import nextcord
from nextcord.ext import tasks

from constants import DEV_SUCCESSFUL_LOGS, DEV_FAILED_LOGS
from pug import PugCategory
from logs import Player, LogData
from logs.logstf_api import LogsAPI
from logs.elo import process_elo
from database import BotCollection
from util import get_steam64

queue_db = BotCollection("logs", "queue")
searcher_db = BotCollection("logs", "searcher")
logs_list_db = BotCollection("logs", "list")
guild_settings_db = BotCollection("guilds", "config")
guild_categories_db = BotCollection("guilds", "categories")


class PartialLog:
    """A partial log, used to search for a log on logs.tf.

    Args:
        guild (int): The guild ID the game was played in.
        category (PugCategory): The category the game was played in.
        players (list[Player]): The players in the game.
        timestamp (int, optional): The timestamp of when the game was played. Defaults to time.time().__round__().
    """

    def __init__(
        self,
        guild: int,
        category: PugCategory,
        players: list[Player],
        timestamp=None,
    ) -> None:
        self.guild: int = guild
        self.timestamp: int = timestamp or time.time().__round__()
        print(f"Timestamp is {self.timestamp}")
        self.category: PugCategory = category
        self.players: list[Player] = players

    def export(self) -> dict:
        """Export the partial log to a dictionary.

        Returns:
            dict: The partial log as a dictionary.
        """
        return {
            "guild": self.guild,
            "timestamp": self.timestamp,
            "category": self.category.__dict__(),
            "players": [player.__dict__ for player in self.players],
        }


class FullLog(PartialLog):
    """A full log, used to store a log that has been found on logs.tf.

    Args:
        partial_log (PartialLog): The partial log that was used to find the log.
        log_id (str): The ID of the log.
        log_data (dict): The log data.
    """

    def __init__(self, partial_log: PartialLog, log_id: int, log_data: dict) -> None:
        super().__init__(
            partial_log.guild,
            partial_log.category,
            partial_log.players,
            partial_log.timestamp,
        )
        self.log_id: int = log_id
        self.log: LogData = LogData(log_data)

    def export(self):
        return {
            "guild": self.guild,
            "timestamp": self.timestamp,
            "category": self.category.__dict__(),
            "players": [player.__dict__ for player in self.players],
            "log_id": self.log_id,
        }


class LogSearcher:
    """The log searcher class, used to search for logs on logs.tf and store them in the database."""

    def __init__(self, bot: nextcord.Client) -> None:
        self.bot = bot

    @tasks.loop(minutes=1)
    async def searcher(self):
        """Goes through the searcher queue and tries to find a corresponding logs.tf log for each game.

        The list of players and the timestamp of the game is used to filter and find the log.
        If a log is found, it is added to the queue.
        If 6 hours has passed and no log has been found, the game is deleted from the searcher.
        If a log ID matches a log ID already registered in the bot, the game is deleted from the searcher.
        """
        print("Running searcher...")
        searcher_logs = await searcher_db.find_all_items()
        for searcher_log in searcher_logs:  # pylint: disable=too-many-nested-blocks
            print(f"Searcher Log: {searcher_log['_id']}")

            players = [Player(data=player) for player in searcher_log["players"]]
            print(players)
            partial_log = PartialLog(
                searcher_log["guild"],
                PugCategory(searcher_log["category"]["name"], searcher_log["category"]),
                players,
                searcher_log["timestamp"],
            )
            print(f"Timestamp: {partial_log.timestamp}")
            print(f"Current time: {round(time.time())}")

            if round(time.time()) - partial_log.timestamp > 21600:
                await LogSearcher._delete_searcher_game(searcher_log["_id"])
                await self.log_failed_log(
                    partial_log, "Searcher timed out (6 hours without finding a log)"
                )
                continue

            steam_ids = []
            for player in partial_log.players:
                if player.steam_64 is not None:
                    steam_ids.append(player.steam_64)
            print(steam_ids)

            query = await LogsAPI.search_for_log(players=steam_ids, limit=3)
            print(f"Result: {query}")
            try:
                if query["success"] and query["results"] > 0:
                    for log in query["logs"]:
                        log_data = await LogsAPI.get_single_log(log["id"])
                        if (
                            log["date"] < partial_log.timestamp - 240
                        ):  # Reduced by 4 minutes to account for machine differences
                            print("Log is too old.")
                            continue
                        if not log_data["success"]:
                            print("Log query was not successful.")
                            continue
                        if log["id"] in await list_all_logs():
                            print(
                                "Log is either already in the database or is being processed."
                            )
                            continue
                        print(f"Log: {log}")
                        full_log = FullLog(partial_log, log["id"], log_data)
                        await LogSearcher._add_queue_game(full_log)
                        await LogSearcher._delete_searcher_game(searcher_log["_id"])
                        break
            except KeyError:
                continue

            # Incase not all players are in the game, check for logs with only some of the players
            for steam_id in steam_ids:
                print(f"Steam ID: {steam_id}")
                query = await LogsAPI.search_for_log(players=[steam_id], limit=3)
                print(f"Result: {query}")
                try:
                    if query["success"] and query["results"] > 0:
                        for log in query["logs"]:
                            log_data = await LogsAPI.get_single_log(log["id"])
                            # Check if at least half the players are in the log
                            player_count = 0
                            for player_id in log_data["players"]:
                                if get_steam64(player_id) in steam_ids:
                                    player_count += 1
                            if player_count < (len(steam_ids) / 2):
                                print("Not enough players in log.")
                                continue
                            if log["date"] < partial_log.timestamp - 240:
                                print("Log is too old.")
                                continue
                            if not log_data["success"]:
                                print("Log query was not successful.")
                                continue
                            if log["id"] in await list_all_logs():
                                print(
                                    "Log is either already in the database or is being processed."
                                )
                                continue

                            # If passes...
                            print(f"Log: {log}")
                            full_log = FullLog(partial_log, log["id"], log_data)
                            await LogSearcher._add_queue_game(full_log)
                            await LogSearcher._delete_searcher_game(searcher_log["_id"])
                            break
                except KeyError:
                    continue

    @tasks.loop(minutes=1)
    async def queue(self):
        """The queue looks through each log in it and checks to see if the log has been completed.

        Here are the conditions for a match being considered done (may change):
        - Map score has been reached
        OR
        - Game time has reached 30 minutes
        OR
        - Log data isn't changing anymore
        """
        print("Running queue...")
        queue_logs = await queue_db.find_all_items()
        for queue_log in queue_logs:
            print(f"Queue Log: {queue_log['_id']}")

            players = [Player(data=player) for player in queue_log["players"]]
            full_log = FullLog(
                PartialLog(
                    queue_log["guild"],
                    PugCategory(queue_log["category"]["name"], queue_log["category"]),
                    players,
                    queue_log["timestamp"],
                ),
                queue_log["log_id"],
                await LogsAPI.get_single_log(queue_log["log_id"]),
            )

            print(round(time.time()) - full_log.timestamp)

            if (round(time.time()) - full_log.timestamp) > 3600:
                print("Log has hit 1 hour old, deleting...")
                await self.log_completed_log(full_log)
                await LogSearcher._delete_queue_game(queue_log["_id"])
                continue

            time_reached = await check_game_time(full_log)
            score_reached = await check_map_score(full_log)
            if time_reached or score_reached:
                await self.log_completed_log(full_log)
                await LogSearcher._delete_queue_game(queue_log["_id"])

    async def log_failed_log(self, log: PartialLog, reason: str):
        """Log a failed log to the database"""
        print(f"Logging failed log... {reason}")
        print(log.export())
        guild_settings = await guild_settings_db.find_item({"guild": log.guild})

        if "logs" in guild_settings:
            if not guild_settings["logs"]["enabled"]:
                return
        else:
            return
        player_string = ""
        for player in log.players:
            player_string += f"<@{player.discord}>\n"

        log_embed = nextcord.Embed(color=nextcord.Color.red())
        log_embed.title = "Failed Log"
        log_embed.description = (
            f"**Category:** {log.category.name}\n**Reason:** {reason}"
        )
        log_embed.add_field(name="Players", value=player_string)
        log_embed.add_field(name="Guild", value=log.guild)
        await self.bot.get_channel(DEV_FAILED_LOGS).send(embed=log_embed)

    async def log_completed_log(self, log: FullLog):
        """Log a completed log to the database"""
        print("Logging completed log...")
        print(log.export())

        guild_settings = await guild_settings_db.find_item({"guild": log.guild})

        if "logs" in guild_settings:
            if not guild_settings["logs"]["enabled"]:
                return
            logs_channel = guild_settings["logs"]["channel"]
        else:
            return

        try:
            guild_categories = await guild_categories_db.find_item({"_id": log.guild})
            if len(guild_categories["categories"]) > 1:
                category_string = f"**Category:** {log.category.name}\n"
            else:
                category_string = ""
        except LookupError:
            category_string = ""

        if guild_settings["logs"]["loogs"]:
            log_url = f"https://loogs.tf/{log.log_id}"
        else:
            log_url = f"https://logs.tf/{log.log_id}"

        await self.bot.get_channel(logs_channel).send(
            content=f"{category_string}{log_url}"
        )
        await self.bot.get_channel(DEV_SUCCESSFUL_LOGS).send(
            content=f"{category_string}{log_url}\nGuild: {log.guild}"
        )

        # Process elo changes
        await process_elo(log)
        await logs_list_db.add_item(log.export())

    @staticmethod
    async def add_searcher_game(
        guild: int, category: PugCategory, players: list[Player], timestamp=None
    ) -> None:
        """Add a game to the log searcher.

        Args:
            guild (int): The guild ID to add the game to.
            category (PugCategory): The category the game was played in.
            players (list[Player]): The players in the game.
        """
        for player in players:
            await player.link_player()
        await searcher_db.add_item(
            PartialLog(guild, category, players, timestamp=timestamp).export()
        )

    @staticmethod
    async def _delete_searcher_game(database_id: str) -> None:
        """Delete a game from the log searcher.

        Args:
            database_id (int | str): The database ID of the game to delete.
        """
        print(f"Deleting game {database_id}...")
        await searcher_db.delete_item({"_id": database_id})

    @staticmethod
    async def _add_queue_game(log: FullLog) -> None:
        print("Adding to queue...")
        await queue_db.add_item(log.export())

    @staticmethod
    async def _delete_queue_game(database_id: str) -> None:
        print(f"Deleting queue game {database_id}...")
        await queue_db.delete_item({"_id": database_id})


async def check_map_score(log: FullLog) -> bool:
    """Checks to see if the map score has been reached, meaning that a log is complete.

    Args:
        log (FullLog): The log to check.

    Returns:
        bool: Whether or not the log is complete.
    """
    map_name: str = log.log.map_name
    if map_name.startswith("cp_"):
        if (log.log.red_team.score == 5) or (log.log.blue_team.score == 5):
            return True
    elif map_name.startswith("koth_"):
        if (log.log.red_team.score == 5) or (log.log.blue_team.score == 5):
            return True
    elif map_name.startswith("pt_"):
        if (log.log.red_team.score >= 2) or (log.log.blue_team.score >= 2):
            return True
    return False


async def check_game_time(log: FullLog) -> bool:
    """Checks to see if the game time has reached 30 minutes, meaning that a log is complete.

    Args:
        log (FullLog): The log to check.

    Returns:
        bool: Whether or not the log is complete.
    """
    map_name: str = log.log.map_name
    if map_name.startswith("pl_"):
        if log.log.length > 2400:
            return True
    else:
        if log.log.length > 1680:
            return True
    return False


async def list_all_logs():
    """List all completed logs."""
    logs = await logs_list_db.find_all_items()
    log_ids = [log["log_id"] for log in logs]
    for log in await queue_db.find_all_items():
        log_ids.append(log["log_id"])
    print(log_ids)
    return log_ids
