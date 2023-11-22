"""Elo calculations, storage and utilities."""
from typing import Any

from bson import Int64 as NumberLong

from database import BotCollection
from logs import Player
from logs.searcher import FullLog, PartialLog
from logs.logstf_api import LogsAPI
from pug import PugCategory
from util import get_steam64

default_elo: dict = {
    "elo": 1000,
    "global": {"sixes": 1000, "highlander": 1000, "passtime": 1000},
    "servers": {},
}

player_db: BotCollection = BotCollection("players", "data")
elo_db: BotCollection = BotCollection("players", "elo")
logs_db: BotCollection = BotCollection("logs", "list")


class Elo:
    """Class used to store and interact with elo data.

    Attributes:
        steam (int): The steam64 of the player to get the elo of.
        elo (int): The global elo of the player.
        global_elo (GlobalElo): The gamemode elo of the player.
        server_elo (dict[str, ServerElo]): The server elo of the player.

    Methods:
        as_dict: Return the elo data as a dict.
        retrieve: Retrieve the elo data from the database.
        upload: Upload the elo data to the database.
        get_elo_from_mode: Get the elo of the player from a specific mode.
        update_elo_from_mode: Update the elo of the player from a specific mode.
    """

    def __init__(self, steam: int) -> None:
        self.steam: int = steam
        self.elo: int = 1000
        self.global_elo: GlobalElo = GlobalElo(default_elo)
        self.server_elo: dict[str, ServerElo] = {}

    def as_dict(self) -> dict[str, Any]:
        """Return the elo data as a dict.

        Returns:
            dict[str, Any]: The elo data.
        """
        server_elo_dict = {}
        for guild, data in self.server_elo.items():
            server_elo_dict[guild] = {"elo": data.elo, "categories": data.categories}
        return {
            "steam": self.steam,
            "elo": self.elo,
            "global": {
                "sixes": self.global_elo.sixes,
                "highlander": self.global_elo.highlander,
                "passtime": self.global_elo.passtime,
            },
            "servers": server_elo_dict,
        }

    async def retrieve(self) -> None:
        """Retrieve the elo data from the database."""
        data: dict
        try:
            print(self.steam)
            data = await elo_db.find_item({"steam": NumberLong(str(self.steam))})
        except LookupError:
            print("Player not found in database, creating new entry.")
            data = default_elo

        self.elo = data["elo"]
        self.global_elo = GlobalElo(data)

        try:
            for server in data["servers"]:
                self.server_elo[server] = ServerElo(data, server)
        except KeyError:
            self.server_elo = {}

    async def upload(self) -> None:
        """Upload the elo data to the database."""
        await elo_db.update_item(
            {"steam": self.steam}, {"$set": self.as_dict()}
        )  # pylint: disable=no-member

    async def get_elo_from_mode(
        self, mode: str, guild: int, category: str, num_players: int
    ) -> int:
        # pylint: disable=too-many-return-statements
        """Get the elo of the player from a specific mode.

        Args:
            mode (str): The elo mode to get the elo from.
            guild (int): The guild ID to get the elo from.
            category (str): The category name to get the elo from.
            num_players (int): The number of players in the log.

        Returns:
            int: The elo of the player.
        """
        if mode == "global":
            return self.elo
        if mode == "gamemode":
            if num_players == 8:
                return self.global_elo.passtime
            if 12 <= num_players <= 14:
                return self.global_elo.sixes
            if 18 <= num_players <= 20:
                return self.global_elo.highlander
            return 1000
        if mode == "server":
            try:
                return self.server_elo[str(guild)].elo
            except KeyError:
                self.server_elo[str(guild)] = ServerElo(default_elo, str(guild))
                return 1000
        if mode == "category":
            try:
                return self.server_elo[str(guild)].categories[category]
            except KeyError:
                if str(guild) not in self.server_elo:
                    self.server_elo[str(guild)] = ServerElo(default_elo, str(guild))
                self.server_elo[str(guild)].categories[category] = 1000
                return 1000
        return 1000

    async def update_elo_from_mode(
        self, mode: str, guild: int, category: str, num_players: int, elo_change: int
    ) -> None:
        """Update the elo of the player from a specific mode.

        Args:
            mode (str): The elo mode to update the elo from.
            guild (int): The guild ID to update the elo from.
            category (str): The category name to update the elo from.
            num_players (int): The number of players in the log.
            elo_change (int): The amount to change the elo by.
        """
        if mode == "global":
            self.elo += elo_change
        elif mode == "gamemode":
            if num_players == 8:
                self.global_elo.passtime += elo_change
            elif 12 <= num_players <= 14:
                self.global_elo.sixes += elo_change
            elif 18 <= num_players <= 20:
                self.global_elo.highlander += elo_change
        elif mode == "server":
            try:
                self.server_elo[str(guild)].elo += elo_change
            except KeyError:
                self.server_elo[str(guild)] = ServerElo(default_elo, str(guild))
                self.server_elo[str(guild)].elo += elo_change
        elif mode == "category":
            try:
                self.server_elo[str(guild)].categories[category] += elo_change
            except KeyError:
                if str(guild) not in self.server_elo:
                    self.server_elo[str(guild)] = ServerElo(default_elo, str(guild))
                self.server_elo[str(guild)].categories[category] = 1000 + elo_change


class GlobalElo:
    """Class used to store and interact with global elo data for each gamemode."""

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
    """Class used to store and interact with server elo data for each server."""

    def __init__(self, data: dict, guild_id: str) -> None:
        try:
            self.elo = data["servers"][str(guild_id)]["elo"]
            self.categories: dict[str, int] = data["servers"][str(guild_id)][
                "categories"
            ]
        except KeyError:
            self.elo = 1000
            self.categories = {}


async def get_elo(steam: int | None = None, discord: int | None = None) -> Elo:
    """Get the elo of a player.

    Args:
        steam (int | None, optional): The steam_64 ID of the player. Defaults to None.
        discord (int | None, optional): The discord ID of the player. Defaults to None.

    Raises:
        ValueError: Either steam or discord must be provided.

    Returns:
        Elo: The elo of the player.
    """
    steam_64: int
    if steam is None and discord is None:
        raise ValueError("Either steam or discord must be provided.")
    if steam is not None:
        steam_64 = steam
    else:
        data = await player_db.find_item({"discord": str(discord)})
        steam_64 = data["steam"]
    elo = Elo(steam=steam_64)
    await elo.retrieve()
    return elo


async def full_elo_update():
    """Update the elo of all players."""
    all_logs = await logs_db.find_all_items()
    for log in all_logs:
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


async def calculate_probability(team1_avg_elo: float, team2_avg_elo: float) -> float:
    """Calculate the probability of team1 winning against team2.

    Args:
        team1_avg_elo (float): The average elo of players in team 1.
        team2_avg_elo (float): The average elo of players in team 2.

    Returns:
        float: The probability of team1 winning against team2.
    """
    # probability that team2 would win against team1
    return 1 / (1 + pow(10, (team1_avg_elo - team2_avg_elo) / 300))


async def calculate_elo_changes(log: FullLog, mode: str) -> None:
    """Calculate the elo changes for each player in the log.

    Args:
        log (FullLog): The log to calculate the elo changes for.
        mode (str): The elo mode to calculate the elo changes for.
    """
    base_elo_change: int = 40
    red_team_elo: float = 0
    blu_team_elo: float = 0
    red_team_players: list[Elo] = []
    blu_team_players: list[Elo] = []
    print(f"Players: {len(log.log.players)}")
    for player in log.log.players:
        player_elo = await get_elo(steam=int(get_steam64(player.steam_3)))
        elo = await player_elo.get_elo_from_mode(
            mode, log.guild, log.category.name, len(log.log.players)
        )
        if player.team == "Red":
            red_team_elo += elo
            red_team_players.append(player_elo)
        else:
            blu_team_elo += elo
            blu_team_players.append(player_elo)
    total_rounds = log.log.red_team.score + log.log.blue_team.score
    if total_rounds != 0:
        red_team_rounds_ratio = log.log.red_team.score / total_rounds
        blu_team_rounds_ratio = log.log.blue_team.score / total_rounds
    else:
        red_team_rounds_ratio = 0.5
        blu_team_rounds_ratio = 0.5
    if log.log.length < 15 * 60 and (
        red_team_rounds_ratio == 0 or blu_team_rounds_ratio == 0
    ):
        base_elo_change = int(base_elo_change * 1.2)
    red_team_elo /= len(red_team_players)
    blu_team_elo /= len(blu_team_players)
    red_team_prob = await calculate_probability(blu_team_elo, red_team_elo)
    blu_team_prob = await calculate_probability(red_team_elo, blu_team_elo)
    red_team_elo_change = round(
        base_elo_change * (red_team_rounds_ratio - red_team_prob)
    )
    blu_team_elo_change = round(
        base_elo_change * (blu_team_rounds_ratio - blu_team_prob)
    )
    print(f"red_team_elo: {red_team_elo}")
    print(f"blu_team_elo: {blu_team_elo}")
    print(f"red_team_prob: {red_team_prob}")
    print(f"blu_team_prob: {blu_team_prob}")
    print(f"red_team_elo_change: {red_team_elo_change}")
    print(f"blu_team_elo_change: {blu_team_elo_change}")

    for red_player_elo in red_team_players:
        await red_player_elo.update_elo_from_mode(
            mode,
            log.guild,
            log.category.name,
            len(log.log.players),
            red_team_elo_change,
        )
        await red_player_elo.upload()

    for blu_player_elo in blu_team_players:
        await blu_player_elo.update_elo_from_mode(
            mode,
            log.guild,
            log.category.name,
            len(log.log.players),
            blu_team_elo_change,
        )
        await blu_player_elo.upload()


async def process_elo(log: FullLog) -> None:
    """Process elo changes for each gamemode.

    Args:
        log (FullLog): The log to process the elo changes for.
    """
    print("Processing global elo")
    await calculate_elo_changes(log, "global")
    print("Processing gamemode elo")
    await calculate_elo_changes(log, "gamemode")
    print("Processing server elo")
    await calculate_elo_changes(log, "server")
    print("Processing category elo")
    await calculate_elo_changes(log, "category")
