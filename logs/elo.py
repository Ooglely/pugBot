"""Elo calculations, storage and utilities."""
from database import BotCollection

default_elo: dict = {
    "global": {"sixes": 1000, "highlander": 1000, "passtime": 1000},
    "servers": [],
}

player_db: BotCollection = BotCollection("players", "data")


class Elo:
    def __init__(self, steam: int | None, discord: int | None) -> None:
        data: dict
        if steam is None and discord is None:
            raise ValueError("Either steam or discord must be provided.")
        elif steam is not None:
            data = player_db.find_item({"steam": steam})
        else:
            data = player_db.find_item({"discord": discord})

        if "elo" in data:
            self.data = data["elo"]
        else:
            self.data = default_elo


class GlobalElo:
    def __init__(self, data: dict) -> None:
        try:
            self.sixes: int = data["global"]["sixes"]
            self.highlander: int = data["global"]["highlander"]
            self.passtime: int = data["global"]["passtime"]
        except KeyError:
            self.sixes = 1000
            self.highlander = 1000
            self.passtime = 1000


class ServerElo:
    def __init__(self, data: dict, guild_id: int) -> None:
        try:
            self.elo = data[guild_id]["elo"]
            self.categories: dict[str, int] = data[guild_id]["categories"]
        except KeyError:
            self.elo = 1000
            self.categories = []
