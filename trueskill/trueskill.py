import json
import asyncio

from numpy import cumsum

from logs import Player
from logs.logstf_api import LogsAPI
from logs.searcher import FullLog, PartialLog
from pug import PugCategory


class Rating:
    def __init__(self, mu=1000, sigma=333.33) -> None:
        self.mu = mu
        self.sigma = sigma


async def test():
    with open("logs.list.json", "r") as f:
        logs = json.load(f)

    for log in logs[0:5]:
        print(log)
        players = [Player(data=player) for player in log["players"]]
        full_log = FullLog(
            PartialLog(
                log["guild"],
                PugCategory(log["category"]["name"], log["category"]),
                players,
                log["timestamp"],
            ),
            log["log_id"],
            await LogsAPI.get_single_log(log["log_id"]),
        )
        await process_elo(full_log)
        await asyncio.sleep(10)


async def process_elo(log: FullLog):
    pass
