"""Stores classes for storing log data and player stats"""
import asyncio
from steam.steamid import SteamID

from logs.logstf_api import LogsAPI
from database import BotCollection

player_db = BotCollection("players", "data")

example_log = {
    "version": 3,
    "teams": {
        "Red": {
            "score": 4,
            "kills": 98,
            "deaths": 0,
            "dmg": 32541,
            "charges": 9,
            "drops": 1,
            "firstcaps": 5,
            "caps": 17,
        },
        "Blue": {
            "score": 4,
            "kills": 70,
            "deaths": 0,
            "dmg": 28844,
            "charges": 5,
            "drops": 2,
            "firstcaps": 3,
            "caps": 16,
        },
    },
    "length": 1511,
    "players": {
        "[U:1:135747267]": {
            "team": "Red",
            "class_stats": [
                {
                    "type": "demoman",
                    "kills": 26,
                    "assists": 8,
                    "deaths": 9,
                    "dmg": 8401,
                    "weapon": {
                        "tf_projectile_pipe_remote": {
                            "kills": 7,
                            "dmg": 4144,
                            "avg_dmg": 53.12820512820513,
                            "shots": 326,
                            "hits": 70,
                        },
                        "tf_projectile_pipe": {
                            "kills": 17,
                            "dmg": 4062,
                            "avg_dmg": 70.03448275862068,
                            "shots": 266,
                            "hits": 53,
                        },
                        "world": {
                            "kills": 1,
                            "dmg": 0,
                            "avg_dmg": 0,
                            "shots": 0,
                            "hits": 0,
                        },
                        "demokatana": {
                            "kills": 1,
                            "dmg": 195,
                            "avg_dmg": 65,
                            "shots": 0,
                            "hits": 0,
                        },
                    },
                    "total_time": 1511,
                }
            ],
            "kills": 26,
            "deaths": 9,
            "assists": 8,
            "suicides": 0,
            "kapd": "3.8",
            "kpd": "2.9",
            "dmg": 8401,
            "dmg_real": 1279,
            "dt": 7349,
            "dt_real": 524,
            "hr": 9375,
            "lks": 6,
            "as": 2,
            "dapd": 933,
            "dapm": 333,
            "ubers": 0,
            "ubertypes": {},
            "drops": 0,
            "medkits": 29,
            "medkits_hp": 920,
            "backstabs": 0,
            "headshots": 0,
            "headshots_hit": 0,
            "sentries": 0,
            "heal": 0,
            "cpc": 6,
            "ic": 0,
        },
    },
    "names": {
        "[U:1:135747267]": "brutechomp",
        "[U:1:238550246]": "im literally a gymnast",
        "[U:1:301884169]": "Scoobert Doobert",
        "[U:1:280661020]": "c.G-Groggy Gary",
        "[U:1:196604649]": "-Magnus",
        "[U:1:317981219]": "Pumpkin",
        "[U:1:296417871]": "heck",
        "[U:1:210912530]": "oog",
        "[U:1:275885026]": "BrookS",
        "[U:1:893485704]": "Ampere",
        "[U:1:133362217]": "aurkah",
        "[U:1:919085644]": "\u300e\u1d0eio\u0186\u300f",
    },
    "rounds": [
        {
            "start_time": 1689275132,
            "winner": "Blue",
            "team": {
                "Blue": {"score": 1, "kills": 11, "dmg": 3712, "ubers": 2},
                "Red": {"score": 0, "kills": 8, "dmg": 3043, "ubers": 1},
            },
            "events": [
                {"type": "pointcap", "time": 43, "team": "Red", "point": 3},
                {
                    "type": "charge",
                    "medigun": "medigun",
                    "time": 83,
                    "steamid": "[U:1:210912530]",
                    "team": "Blue",
                },
                {
                    "type": "charge",
                    "medigun": "medigun",
                    "time": 87,
                    "steamid": "[U:1:238550246]",
                    "team": "Red",
                },
                {
                    "type": "medic_death",
                    "time": 98,
                    "team": "Red",
                    "steamid": "[U:1:238550246]",
                    "killer": "[U:1:893485704]",
                },
                {"type": "pointcap", "time": 136, "team": "Blue", "point": 3},
                {"type": "pointcap", "time": 152, "team": "Blue", "point": 4},
                {
                    "type": "charge",
                    "medigun": "medigun",
                    "time": 157,
                    "steamid": "[U:1:210912530]",
                    "team": "Blue",
                },
                {"type": "pointcap", "time": 172, "team": "Blue", "point": 5},
                {"type": "round_win", "time": 172, "team": "Blue"},
            ],
            "players": {
                "[U:1:301884169]": {"team": "Red", "kills": 0, "dmg": 386},
                "[U:1:919085644]": {"team": "Blue", "kills": 2, "dmg": 1363},
                "[U:1:317981219]": {"team": "Blue", "kills": 2, "dmg": 455},
                "[U:1:135747267]": {"team": "Red", "kills": 3, "dmg": 1071},
                "[U:1:196604649]": {"team": "Red", "kills": 4, "dmg": 956},
                "[U:1:133362217]": {"team": "Red", "kills": 1, "dmg": 374},
                "[U:1:275885026]": {"team": "Blue", "kills": 0, "dmg": 486},
                "[U:1:296417871]": {"team": "Blue", "kills": 4, "dmg": 885},
                "[U:1:280661020]": {"team": "Red", "kills": 0, "dmg": 256},
                "[U:1:893485704]": {"team": "Blue", "kills": 2, "dmg": 414},
                "[U:1:210912530]": {"team": "Blue", "kills": 1, "dmg": 109},
                "[U:1:238550246]": {"team": "Red", "kills": 0, "dmg": 0},
                "[U:1:229064914]": {"team": None, "kills": 0, "dmg": 0},
            },
            "firstcap": "Red",
            "length": 172,
        }
    ],
    "healspread": {
        "[U:1:238550246]": {
            "[U:1:135747267]": 9375,
            "[U:1:301884169]": 3521,
            "[U:1:280661020]": 5744,
            "[U:1:133362217]": 1760,
            "[U:1:196604649]": 5453,
        },
        "[U:1:210912530]": {
            "[U:1:893485704]": 2413,
            "[U:1:317981219]": 2286,
            "[U:1:275885026]": 4594,
            "[U:1:296417871]": 4960,
            "[U:1:919085644]": 3793,
        },
    },
    "classkills": {
        "[U:1:135747267]": {
            "demoman": 5,
            "scout": 9,
            "heavyweapons": 2,
            "soldier": 7,
            "sniper": 1,
            "medic": 1,
            "pyro": 1,
        },
    },
    "classdeaths": {
        "[U:1:919085644]": {"demoman": 5, "soldier": 6, "scout": 3},
    },
    "classkillassists": {
        "[U:1:135747267]": {
            "demoman": 6,
            "scout": 13,
            "heavyweapons": 2,
            "soldier": 10,
            "sniper": 1,
            "medic": 1,
            "pyro": 1,
        }
    },
    "chat": [
        {
            "steamid": "[U:1:229064914]",
            "name": "mango muncher",
            "msg": "old man forgot where he wasd",
        },
        {
            "steamid": "[U:1:893485704]",
            "name": "Ampere",
            "msg": "old man forgot where he was",
        },
        {
            "steamid": "[U:1:317981219]",
            "name": "Pumpkin",
            "msg": "old man forgot where he was",
        },
    ],
    "info": {
        "map": "cp_process_f12",
        "supplemental": True,
        "total_length": 1511,
        "hasRealDamage": True,
        "hasWeaponDamage": True,
        "hasAccuracy": True,
        "hasHP": True,
        "hasHP_real": True,
        "hasHS": True,
        "hasHS_hit": True,
        "hasBS": True,
        "hasCP": True,
        "hasSB": False,
        "hasDT": True,
        "hasAS": True,
        "hasHR": True,
        "hasIntel": False,
        "AD_scoring": False,
        "notifications": [],
        "title": "na.serveme.tf #521350: uwu vs BLU",
        "date": 1689301928,
        "uploader": {
            "id": "76561197960497430",
            "name": "Arie - VanillaTF2.org",
            "info": "LogsTF 2.5.0",
        },
    },
    "killstreaks": [
        {"steamid": "[U:1:317981219]", "streak": 3, "time": 443},
        {"steamid": "[U:1:919085644]", "streak": 3, "time": 891},
    ],
    "success": True,
}


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


async def test_log_data():
    """Test the log data class"""
    example_log_data = LogData(await LogsAPI.get_single_log(3490943))
    await example_log_data.link_all_players()

    for player in example_log_data.players:
        print(player.linked.__dict__)

    # await LogsAPI.search_for_log()


if __name__ == "__main__":
    asyncio.run(test_log_data())
