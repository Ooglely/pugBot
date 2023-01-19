import requests
import aiohttp
from steam import steamid
from steam.steamid import SteamID
from database import get_player_stats, add_player_stats


async def logSearch(id):
    if get_player_stats(id) == None:
        player = {
            "steam": id,
            "stats": [  # class, kills, deaths, dmg, total_time, # of logs
                ["scout", 0, 0, 0, 0, 0],
                ["soldier", 0, 0, 0, 0, 0],
                ["pyro", 0, 0, 0, 0, 0],
                ["demoman", 0, 0, 0, 0, 0],
                ["heavy", 0, 0, 0, 0, 0],
                ["engineer", 0, 0, 0, 0, 0],
                ["medic", 0, 0, 0, 0, 0],
                ["sniper", 0, 0, 0, 0, 0],
                ["spy", 0, 0, 0, 0, 0],
            ],
            "logs": [],
        }
    else:
        player = get_player_stats(id)

    # Constants
    steamid = SteamID(id)
    steam3 = steamid.as_steam3

    # https://logs.tf/api/v1/log?uploader=76561198171178258&player=Y
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://logs.tf/api/v1/log?uploader=76561198171178258&player=" + str(id)
        ) as resp:
            logs = await resp.json()

            for i in logs["logs"]:
                logID = i["id"]
                if logID in player["logs"]:
                    continue
                else:
                    player["logs"].append(logID)

                print(f"Checking log #{logID}...")
                async with session.get("http://logs.tf/json/" + str(i["id"])) as resp:
                    log = await resp.json()

                    for i in log["players"][steam3]["class_stats"]:
                        for char in player["stats"]:
                            player_class = i["type"]
                            if i["type"] == "heavyweapons":
                                player_class = "heavy"
                            if player_class == char[0]:
                                char[1] += int(i["kills"])
                                char[2] += int(i["deaths"])
                                char[3] += int(i["dmg"])
                                char[4] += int(i["total_time"])
                                char[5] += 1
                        print(f"Done checking log #{logID}")

    add_player_stats(player)
    return player["stats"]


async def get_total_logs(steamID):
    player_lookup = requests.get(
        "https://logs.tf/api/v1/log?player=" + str(steamID)
    ).json()
    return player_lookup["results"]
