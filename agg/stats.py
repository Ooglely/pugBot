from typing import Optional
import aiohttp
from steam.steamid import SteamID
from database import get_player_stats, update_player_stats, get_steam_from_discord
from agg import AGG_SERVER_ID
from util import get_steam64
import json
import nextcord
from nextcord.ext import commands
from rglAPI import rglAPI
from datetime import timedelta

rglAPI = rglAPI()


class ClassStats:
    def __init__(self, kills: int, deaths: int, dmg: int, total_time: int, logs: int):
        self.kills = kills
        self.deaths = deaths
        self.dmg = dmg
        self.total_time = total_time
        self.logs = logs

    def __str__(self) -> str:
        return json.dumps(self.__dict__)

    async def add_log(self, log: dict):
        self.kills += log["kills"]
        self.deaths += log["deaths"]
        self.dmg += log["dmg"]
        self.total_time += log["total_time"]
        self.logs += 1


class PlayerStats:
    def __init__(self, steam: int):
        self.steam64: int = steam
        self.steam3: str = SteamID(steam).as_steam3
        self.stats = {
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
        self.logs: list(int) = []

    def __dict__(self):
        dict_form = {"steam": self.steam64, "stats": {}, "logs": self.logs}
        for class_stat in self.stats.items():
            dict_form["stats"][class_stat[0]] = class_stat[1].__dict__
        return dict_form

    async def import_logs_from_db(self):
        player = get_player_stats(self.steam64)
        if player == None:
            return
        else:
            for stat in player["stats"].items():
                self.stats[stat[0]] = ClassStats(**stat[1])
            self.logs = player["logs"]

    async def find_new_logs(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://logs.tf/api/v1/log?uploader=76561198171178258&player="
                + str(self.steam64)
            ) as resp:
                logs = await resp.json()

                for log in logs["logs"]:
                    logID = log["id"]
                    if logID in self.logs:
                        continue
                    else:
                        self.logs.append(logID)

                    print(f"Checking log #{logID}...")
                    async with session.get(
                        "http://logs.tf/json/" + str(log["id"])
                    ) as resp:
                        log = await resp.json()

                        for class_stats in log["players"][self.steam3]["class_stats"]:
                            if class_stats["type"] not in self.stats:
                                if class_stats["type"] == "heavyweapons":
                                    class_stats["type"] = "heavy"
                                else:
                                    continue
                            print(f"Adding log #{logID} to {class_stats['type']}...")
                            await self.stats[class_stats["type"]].add_log(class_stats)
                        print(f"Done checking log #{logID}")

    async def update_db_player_stats(self):
        update_player_stats(self.steam64, self.__dict__())


async def get_total_logs(steamID):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://logs.tf/api/v1/log?player=" + str(steamID)
        ) as resp:
            logs = await resp.json()
            return logs["results"]


class StatsCog(commands.Cog):
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
        id: Optional[str] = nextcord.SlashOption(
            name="steam",
            description="A steam ID, steam URL, or RGL link.",
            required=False,
        ),
    ):
        if id == None:
            steamID = get_steam_from_discord(interaction.user.id)
        else:
            steamID = get_steam64(id)

        if steamID == None:
            await interaction.send(
                "Unable to find player. Either register with the bot at <#1026980468807184385> or specify a steam ID/URL in the command."
            )
            return

        await interaction.send("Give me a moment, grabbing all logs...")
        print(f"ID: {steamID}")
        info = await rglAPI.get_player(int(steamID))
        print(info)
        logString = f"```\n{info['name']}'s pug stats"

        player = PlayerStats(int(steamID))
        await player.import_logs_from_db()
        await player.find_new_logs()
        await player.update_db_player_stats()

        logString += "\n  Class |  K  |  D  | DPM | KDR | Logs | Playtime"
        stats = get_player_stats(int(steamID))

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
                logString += f"\n{class_name: >8}|{class_stats['kills']: >5}|{class_stats['deaths']: >5}|{dpm: >5}|{kdr: >5}|{class_stats['logs']: >5} | {playtime}"
        logString += "```"
        await interaction.edit_original_message(content=logString)
