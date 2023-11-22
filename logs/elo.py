"""Elo calculations, storage and utilities."""
from database import BotCollection
from logs.searcher import FullLog, PartialLog
from logs.logstf_api import LogsAPI
from pug import PugCategory
from logs import Player
from util import get_steam64


default_elo: dict = {
    "global": {"sixes": 1000, "highlander": 1000, "passtime": 1000},
    "servers": {},
}

player_db: BotCollection = BotCollection("players", "data")
elo_db: BotCollection = BotCollection("players", "elo")
logs_db: BotCollection = BotCollection("logs", "list")


class Elo:
    def __init__(self, steam: int) -> None:
        self.steam: int = steam
        self.global_elo: GlobalElo = GlobalElo(default_elo)
        self.server_elo: dict[str, ServerElo] = {}

    def __dict__(self) -> dict:
        server_elo_dict = {}
        for guild, data in self.server_elo.items():
            server_elo_dict[guild] = {"elo": data.elo, "categories": data.categories}
        return {
            "steam": self.steam,
            "global": {
                "sixes": self.global_elo.sixes,
                "highlander": self.global_elo.highlander,
                "passtime": self.global_elo.passtime,
            },
            "servers": server_elo_dict,
        }

    async def retrieve(self) -> None:
        data: dict
        try:
            data = await elo_db.find_item({"steam": self.steam})
        except LookupError:
            data = default_elo

        self.global_elo: GlobalElo = GlobalElo(data)
        self.server_elo: dict[str, ServerElo]

        try:
            for server in data["servers"]:
                self.server_elo[server] = ServerElo(data, server)
        except KeyError:
            self.server_elo = {}

    async def upload(self) -> None:
        await elo_db.update_item(
            {"steam": self.steam}, {"$set": self.__dict__()}
        )  # pylint: disable=no-member

    async def get_elo_from_mode(
        self, mode: str, guild: int, category: str, num_players: int
    ) -> int:
        if mode == "global":
            if num_players == 8:
                return self.global_elo.passtime
            elif 12 <= num_players <= 14:
                return self.global_elo.sixes
            elif 18 <= num_players <= 20:
                return self.global_elo.highlander
            else:
                return 1000
        elif mode == "server":
            try:
                return self.server_elo[str(guild)].elo
            except KeyError:
                self.server_elo[str(guild)] = ServerElo(default_elo, str(guild))
                return 1000
        elif mode == "category":
            try:
                return self.server_elo[str(guild)].categories[category]
            except KeyError:
                if str(guild) not in self.server_elo:
                    self.server_elo[str(guild)] = ServerElo(default_elo, str(guild))
                self.server_elo[str(guild)].categories[category] = 1000
                return 1000

    async def update_elo_from_mode(
        self, mode: str, guild: int, category: str, num_players: int, elo_change: int
    ) -> None:
        if mode == "global":
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
    steam_64: int
    if steam is None and discord is None:
        raise ValueError("Either steam or discord must be provided.")
    if steam is not None:
        steam_64 = steam
    else:
        data = await player_db.find_item({"discord": discord})
        steam_64 = data["steam"]
    elo = Elo(steam=steam_64)
    await elo.retrieve()
    return elo


async def full_elo_update():
    all_logs = await logs_db.find_all_items()
    for log in all_logs:
        print(log)
        players = [Player(data=player) for player in log["players"]]
        log = FullLog(
            PartialLog(
                log["guild"],
                PugCategory(log["category"]["name"], log["category"]),
                players,
                log["timestamp"],
            ),
            log["log_id"],
            await LogsAPI.get_single_log(log["log_id"]),
        )
        await process_elo(log)


async def elo_test():
    item = await logs_db.find_item({"log_id": 3518330})
    print(item)
    elo = await get_elo(steam=get_steam64("[U:1:204857450]"))
    print(elo.__dict__())
    players = [Player(data=player) for player in item["players"]]
    log = FullLog(
        PartialLog(
            item["guild"],
            PugCategory(item["category"]["name"], item["category"]),
            players,
            item["timestamp"],
        ),
        item["log_id"],
        await LogsAPI.get_single_log(item["log_id"]),
    )
    await process_elo(log)


async def calculate_probability(team1_avg_elo: float, team2_avg_elo: float) -> float:
    # probability that team2 would win against team1
    return 1 / (1 + pow(10, (team1_avg_elo - team2_avg_elo) / 300))


async def calculate_elo_changes(log: FullLog, mode: str) -> None:
    base_elo_change: int = 40
    red_team_elo: float = 0
    blu_team_elo: float = 0
    red_team_players: list[Elo] = []
    blu_team_players: list[Elo] = []
    print(f"Players: {len(log.log.players)}")
    for player in log.log.players:
        player_elo = await get_elo(steam=get_steam64(player.steam_3))
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
        base_elo_change *= 1.2
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

    for player in red_team_players:
        await player.update_elo_from_mode(
            mode,
            log.guild,
            log.category.name,
            len(log.log.players),
            red_team_elo_change,
        )
        await player.upload()

    for player in blu_team_players:
        await player.update_elo_from_mode(
            mode,
            log.guild,
            log.category.name,
            len(log.log.players),
            blu_team_elo_change,
        )
        await player.upload()


async def process_elo(log: FullLog) -> None:
    print("Processing global elo")
    await calculate_elo_changes(log, "global")
    print("Processing server elo")
    await calculate_elo_changes(log, "server")
    print("Processing category elo")
    await calculate_elo_changes(log, "category")
