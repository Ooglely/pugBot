import scrapy
from scrapy.crawler import CrawlerProcess
import sys
import requests
import json
from steam import steamid
from steam.steamid import SteamID


async def logSearch(id):
    # Constants
    stats = [  # class, kills, deaths, dmg, total_time, # of logs
        ["scout", 0, 0, 0, 0, 0],
        ["soldier", 0, 0, 0, 0, 0],
        ["pyro", 0, 0, 0, 0, 0],
        ["demoman", 0, 0, 0, 0, 0],
        ["heavy", 0, 0, 0, 0, 0],
        ["engineer", 0, 0, 0, 0, 0],
        ["medic", 0, 0, 0, 0, 0],
        ["sniper", 0, 0, 0, 0, 0],
        ["spy", 0, 0, 0, 0, 0],
    ]
    steamid = SteamID(id)
    steam3 = steamid.as_steam3

    # https://logs.tf/api/v1/log?uploader=76561198171178258&player=Y
    logs = requests.get(
        "https://logs.tf/api/v1/log?uploader=76561198171178258&player=" + str(id)
    ).json()["logs"]
    for i in logs:
        log = requests.get("http://logs.tf/json/" + str(i["id"])).json()
        # print(log['players'][steam3])
        for i in log["players"][steam3]["class_stats"]:
            for char in stats:
                if i["type"] == char[0]:
                    char[1] += int(i["kills"])
                    char[2] += int(i["deaths"])
                    char[3] += int(i["dmg"])
                    char[4] += int(i["total_time"])
                    char[5] += 1
    return stats
