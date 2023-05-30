import aiohttp
from steam.steamid import SteamID
from database import get_player_stats, update_player_stats
import json


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


async def test_func():
    print(await get_total_logs(76561198171178258))
