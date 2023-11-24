"""Stores classes for storing log data and player stats"""
from steam.steamid import SteamID

from database import BotCollection

player_db = BotCollection("players", "data")


class LogTeamData:
    """Stores team data from a log"""

    def __init__(self, data: dict) -> None:
        self.score = data["score"]
        self.kills = data["kills"]
        self.deaths = data["deaths"]
        self.dmg = data["dmg"]
        self.charges = data["charges"]
        self.drops = data["drops"]
        self.firstcaps = data["firstcaps"]
        self.caps = data["caps"]
        self.players: list[PlayerData] = []


class PlayerData:
    """Stores player data from a log"""

    def __init__(self, steam_3: str, data: dict) -> None:
        self.steam_3 = steam_3
        self.team = data["team"]
        self.class_stats: list[ClassData] = []
        self.kills = data["kills"]
        self.deaths = data["deaths"]
        self.assists = data["assists"]
        self.kpd = data["kpd"]
        self.dmg = data["dmg"]
        self.dmg_taken = data["dt"]
        self.time = 0

        for class_played in data["class_stats"]:
            self.class_stats.append(ClassData(class_played))
            self.time += class_played["total_time"]

        self.linked: None | Player = None

    async def link_player(self) -> None:
        """Add database data from the associated steam ID to the player data"""
        try:
            player = await player_db.find_item(
                {"steam": str(SteamID(self.steam_3).as_64)}
            )
            self.linked = Player(self.steam_3, player["discord"])
            await self.linked.link_player()
        except LookupError:
            print(f"Player {str(SteamID(self.steam_3).as_64)} not found in database")
            self.linked = None
            return


class Player:
    """Stores player data from the database"""

    def __init__(
        self,
        steam: str | int | None = None,
        discord: int | None = None,
        data: dict | None = None,
    ) -> None:
        self.steam_3: str | None = SteamID(steam).as_steam3 if steam else None
        self.steam_64: int | None = SteamID(steam).as_64 if steam else None
        self.discord: int | None = discord if discord else None
        self.registered: bool = False

        if data:
            self.steam_64 = data["steam_64"]
            self.steam_3 = data["steam_3"]
            self.discord = data["discord"]
            self.registered = data["registered"]

    async def link_player(self) -> None:
        """Add database data from the associated steam ID to the player data"""
        if not self.registered:
            try:
                if self.steam_64:
                    data = await player_db.find_item({"steam": str(self.steam_64)})
                elif self.discord:
                    data = await player_db.find_item({"discord": str(self.discord)})
                else:
                    return
                self.steam_64 = data["steam"]
                self.discord = data["discord"]
                self.registered = True
            except LookupError:
                self.registered = False
                return


class ClassData:
    """Stores class data from a log"""

    def __init__(self, data: dict) -> None:
        self.kills = data["kills"]
        self.assists = data["assists"]
        self.deaths = data["deaths"]
        self.dmg = data["dmg"]
        self.time = data["total_time"]
        self.dpm = self.dmg / (self.time / 60)


class LogData:
    """Stores log data from logs.tf"""

    def __init__(self, data: dict) -> None:
        self.red_team: LogTeamData = LogTeamData(data["teams"]["Red"])
        self.blue_team: LogTeamData = LogTeamData(data["teams"]["Blue"])
        self.players: list[PlayerData] = []
        self.map_name: str = data["info"]["map"]
        self.length: int = data["length"]

        for player in data["players"]:
            if data["players"][player]["team"] == "Red":
                self.red_team.players.append(
                    PlayerData(player, data["players"][player])
                )
            elif data["players"][player]["team"] == "Blue":
                self.blue_team.players.append(
                    PlayerData(player, data["players"][player])
                )
            self.players.append(PlayerData(player, data["players"][player]))

    async def link_all_players(self) -> None:
        """Link all players in the log to their database entries"""
        for player in self.players:
            await player.link_player()
