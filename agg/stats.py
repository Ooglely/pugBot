"""Contains the stats cog for storing and displaying player stats"""
import json
from datetime import timedelta
from typing import Optional

import aiohttp
import nextcord
from nextcord.ext import commands
from steam.steamid import SteamID

from agg import AGG_SERVER_ID
from database import get_player_stats, update_player_stats, get_steam_from_discord
from rglAPI import rglAPI
from util import get_steam64


RGL: rglAPI = rglAPI()


class ClassStats:
    """Class for storing the stats for a players certain class

    Attributes:
        kills (int): Amount of kills on the class
        deaths (int): Amount of deaths on the class
        dmg (int): Total amount of damage dealt on the class
        total_time (int): Total playtime across all logs
        logs (int): Amount of logs with the class
    """

    def __init__(self, kills: int, deaths: int, dmg: int, total_time: int, logs: int):
        self.kills = kills
        self.deaths = deaths
        self.dmg = dmg
        self.total_time = total_time
        self.logs = logs

    def __str__(self) -> str:
        return json.dumps(self.__dict__)

    async def add_log(self, log: dict):
        """Adds a singular logs stats to the class

        Args:
            log (dict): The log data to import
        """
        self.kills += log["kills"]
        self.deaths += log["deaths"]
        self.dmg += log["dmg"]
        self.total_time += log["total_time"]
        self.logs += 1


class PlayerStats:
    """Class for storing player log stats

    Attributes:
        steam64 (int): Steam ID in steam64 format
        steam3 (str): Steam ID in steam3 format
        stats (dict[str, ClassStats]): ClassStats for every class
        logs (list[int]): List of all the logs parsed through
    """

    def __init__(self, steam: int):
        self.steam64: int = steam
        self.steam3: str = SteamID(steam).as_steam3
        self.stats: dict[str, ClassStats] = {
            "scout": ClassStats(0, 0, 0, 0, 0),
            "soldier": ClassStats(0, 0, 0, 0, 0),
            "pyro": ClassStats(0, 0, 0, 0, 0),
            "demoman": ClassStats(0, 0, 0, 0, 0),
            "heavy": ClassStats(0, 0, 0, 0, 0),
            "engineer": ClassStats(0, 0, 0, 0, 0),
            "medic": ClassStats(0, 0, 0, 0, 0),
            "sniper": ClassStats(0, 0, 0, 0, 0),
            "spy": ClassStats(0, 0, 0, 0, 0),
        }
        self.logs: list[int] = []

    def __dict__(self):
        dict_form = {"steam": self.steam64, "stats": {}, "logs": self.logs}
        for class_stat in self.stats.items():
            dict_form["stats"][class_stat[0]] = class_stat[1].__dict__  # type: ignore
        return dict_form

    async def import_logs_from_db(self):
        """Imports the current stats stored for the player in the database."""
        player = get_player_stats(self.steam64)
        if player is None:
            return

        for stat in player["stats"].items():
            self.stats[stat[0]] = ClassStats(**stat[1])
        self.logs = player["logs"]

    async def find_new_logs(self):
        """Finds any logs not yet parsed through and adds the stats to the class"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://logs.tf/api/v1/log?uploader=76561198171178258&player="
                + str(self.steam64)
            ) as resp:
                logs = await resp.json()

                for log in logs["logs"]:
                    log_id = log["id"]
                    if log_id in self.logs:
                        continue

                    self.logs.append(log_id)

                    print(f"Checking log #{log_id}...")
                    async with session.get(
                        "http://logs.tf/json/" + str(log_id)
                    ) as resp:
                        log = await resp.json()

                        for class_stats in log["players"][self.steam3]["class_stats"]:
                            if class_stats["type"] not in self.stats:
                                if class_stats["type"] == "heavyweapons":
                                    class_stats["type"] = "heavy"
                                else:
                                    continue
                            print(f"Adding log #{log_id} to {class_stats['type']}...")
                            await self.stats[class_stats["type"]].add_log(class_stats)
                        print(f"Done checking log #{log_id}")

    async def update_db_player_stats(self):
        """Updates the database with the stats stored in the class"""
        update_player_stats(self.steam64, self.__dict__)


async def get_total_logs(steam_id: str):
    """Returns the total number of logs for a player

    Args:
        steam_id (int): The steam ID to look up

    Returns:
        int: Total number of logs
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://logs.tf/api/v1/log?player=" + str(steam_id)
        ) as resp:
            logs = await resp.json()
            return logs["results"]


class StatsCog(commands.Cog):
    """Cog storing all the commands revolving around stats"""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    # TODO: Add stats command
    @nextcord.slash_command(
        name="stats",
        description="Retrieve pug stats for a player",
        guild_ids=AGG_SERVER_ID,
    )
    async def stats(
        self,
        interaction: nextcord.Interaction,
        player_id: Optional[str] = nextcord.SlashOption(
            name="steam",
            description="A steam ID, steam URL, or RGL link.",
            required=False,
        ),
    ):
        """Displays the stats for a player

        Args:
            interaction (nextcord.Interaction): Interaction object
            id (Optional[str], optional): The steam ID to lookup. Defaults to the user's steam ID.
        """
        if player_id is None:
            steam_id = get_steam_from_discord(interaction.user.id)
        else:
            steam_id = get_steam64(player_id)

        if steam_id is None:
            await interaction.send(
                """Unable to find player. Either register with the bot
                at <#1026980468807184385> or specify a steam ID/URL in the command."""
            )
            return

        await interaction.send("Give me a moment, grabbing all logs...")
        print(f"ID: {steam_id}")
        info = await RGL.get_player(int(steam_id))
        print(info)
        log_string = f"```\n{info['name']}'s pug stats"

        player = PlayerStats(int(steam_id))
        await player.import_logs_from_db()
        await player.find_new_logs()
        await player.update_db_player_stats()

        log_string += "\n  Class |  K  |  D  | DPM | KDR | Logs | Playtime"
        stats = get_player_stats(int(steam_id))

        for class_stats in stats["stats"].items():
            print(class_stats)
            class_name = class_stats[0].capitalize()
            class_stats = class_stats[1]
            playtime = timedelta(seconds=class_stats["total_time"])
            if class_stats["logs"] != 0:
                dpm = f"{class_stats['dmg'] / (class_stats['total_time'] / 60):.1f}"
                if class_stats["deaths"] == 0:
                    kdr = f"{class_stats['kills']:.1f}"
                else:
                    kdr = f"{class_stats['kills'] / class_stats['deaths']:.1f}"
                log_string += f"""\n{class_name: >8}|
                    {class_stats['kills']: >5}|
                    {class_stats['deaths']: >5}|
                    {dpm: >5}|
                    {kdr: >5}|
                    {class_stats['logs']: >5} |
                    {playtime}"""
        log_string += "```"
        await interaction.edit_original_message(content=log_string)
