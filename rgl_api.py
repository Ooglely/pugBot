"""File containing the rglAPI class, which is used to interact with the RGL API."""
import asyncio
from datetime import datetime, timedelta

import aiohttp


divs = {
    "Newcomer": 1,
    "Amateur": 2,
    "Intermediate": 3,
    "Main": 4,
    "Advanced": 5,
    "Advanced-1": 6,
    "Advanced-2": 5,
    "Challenger": 6,
    "Invite": 7,
    "Admin Placement": 0,
    "Dead Teams": 0,
}


class Player:
    """Class representing an RGL player."""

    def __init__(self, steamid, name, pfp, sixes, highlander, bans):
        self.steamid = steamid
        self.name = name
        self.pfp = pfp
        self.sixes = sixes
        self.highlander = highlander
        self.bans = bans

    def __str__(self):
        return f"""ID: {self.steamid}\nName: {self.name}\nPFP: {self.pfp}\n
                Sixes: {self.sixes}\nHL: {self.highlander}\nBans: {self.bans}"""


class RGL_API:
    """Class used to interact with the RGL API.

    Attributes:
        apiURL (str): The base URL for the RGL API.
    """

    def __init__(self):
        self.api_url = "https://api.rgl.gg/v0/"

    async def get_player(self, steam_id: int):
        """Gets a player from the RGL API.

        Args:
            steamid (int): The steamid of the player to get.

        Raises:
            LookupError: If the player does not exist in RGL.

        Returns:
            dict: The player data.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.api_url + "profile/" + str(steam_id)
            ) as player_data:
                player = await player_data.json()
                if "statusCode" in player:
                    raise LookupError("Player does not exist in RGL")
                return player

    async def get_all_teams(self, steam_id: int):
        """Gets all teams a player has been on.

        Args:
            steamid (int): The steamid of the player to get.

        Returns:
            dict: The team data.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.api_url + "profile/" + str(steam_id) + "/teams"
            ) as team_data:
                teams = await team_data.json()
                return teams

    async def get_core_teams(self, steam_id: int):
        """Gets all 6s and HL season teams a player has been on.

        Args:
            steamid (int): The steamid of the player to get.

        Returns:
            dict: The team data.
        """
        all_teams = await self.get_all_teams(steam_id)
        if "statusCode" in all_teams:
            if all_teams["statusCode"] == 429:
                raise LookupError("Rate limit exceeded")
        core_seasons = {}
        sixes_teams = []
        hl_teams = []
        for season in all_teams:
            if season["leftAt"] is None:
                pass
            else:  # Check if the team lasted at least 30 days
                team_start = datetime.fromisoformat(season["startedAt"])
                team_end = datetime.fromisoformat(season["leftAt"])
                team_length = team_end - team_start
                if team_length < timedelta(days=30):
                    continue
            if (
                season["formatId"] == 3 and season["regionId"] == 40
            ):  # NA Sixes region code
                sixes_teams.append(season)
            elif (
                season["formatId"] == 2 and season["regionId"] == 24
            ):  # NA HL region code
                hl_teams.append(season)
        core_seasons["sixes"] = sixes_teams
        core_seasons["hl"] = hl_teams
        return core_seasons

    async def check_banned(self, steam_id: int):
        """Checks if a player is currently banned.

        Args:
            steamid (int): The steamid of the player to check.

        Returns:
            bool: True if the player is currently banned, False if not.
        """
        player = await self.get_player(steam_id)
        if player["status"]["isBanned"]:
            return True

        return False

    async def get_top_div(self, steam_id: int):
        """Gets the highest division a player has played in for 6s and HL.

        Args:
            steamid (int): The steamid of the player to get.

        Returns:
            list: A list containing the highest division for 6s and HL.
        """
        player = await self.get_core_teams(steam_id)
        if player is None:
            return [[-1, -1], [-1, -1]]
        sixesdiv = [0, 0]
        hldiv = [0, 0]
        for season in player["sixes"]:
            division_name: str = season["divisionName"].replace("RGL-", "")
            if division_name in divs:
                if divs[division_name] > sixesdiv[0]:
                    sixesdiv[0] = divs[division_name]
                    sixesdiv[1] = 1
                elif divs[division_name] == sixesdiv[0]:
                    sixesdiv[1] += 1
            else:
                print(f"Division not found: {division_name}")
        for season in player["hl"]:
            division_name = season["divisionName"].replace("RGL-", "")
            if division_name in divs:
                if divs[division_name] > hldiv[0]:
                    hldiv[0] = divs[division_name]
                    hldiv[1] = 1
                elif divs[division_name] == hldiv[0]:
                    hldiv[1] += 1
            else:
                print(f"Division not found: {division_name}")
        return [sixesdiv, hldiv]

    async def get_div_data(self, steam_id: int):
        """Get both the highest div and the last div played for both 6s and HL.

        Args:
            steam_id (int): The steamid of the player to get.
        """
        player = await self.get_core_teams(steam_id)
        player_divs = {
            "sixes": {"highest": -1, "current": -1},
            "hl": {"highest": -1, "current": -1},
        }
        if player is None:
            return player_divs  # Return -1 if the player is not found, so that it won't be updated in the db
        player_divs = {
            "sixes": {"highest": 0, "current": 0},
            "hl": {"highest": 0, "current": 0},
        }
        for season in player["sixes"]:
            division_name: str = season["divisionName"].replace("RGL-", "")
            if division_name in divs:  # Getting the highest division played here
                if divs[division_name] > player_divs["sixes"]["highest"]:
                    player_divs["sixes"]["highest"] = divs[division_name]
            else:
                print(f"Division not found: {division_name}")
            if (
                player_divs["sixes"]["current"] == 0
            ):  # If the current div hasn't been set yet
                if (
                    divs[division_name] > 0
                ):  # We only want to set the current div if it's not an admin placement team
                    player_divs["sixes"]["current"] = divs[division_name]
        for season in player["hl"]:
            division_name = season["divisionName"].replace("RGL-", "")
            if division_name in divs:
                if divs[division_name] > player_divs["hl"]["highest"]:
                    player_divs["hl"]["highest"] = divs[division_name]
            else:
                print(f"Division not found: {division_name}")
            if player_divs["hl"]["current"] == 0:
                if divs[division_name] > 0:
                    player_divs["hl"]["current"] = divs[division_name]
        return player_divs

    async def create_player(self, steam_id: int) -> Player:
        """Creates a Player object from a steamid.

        Args:
            steamid (int): The steamid of the player to create.

        Returns:
            Player: The Player object.
        """
        sixes = []
        highlander = []
        player_data = await self.get_player(steam_id)
        await asyncio.sleep(2)
        team_data = await self.get_core_teams(steam_id)

        for season in team_data["sixes"]:
            if (
                season["divisionName"] != "Dead Teams"
                and season["divisionName"] != "Admin Placement"
                and not season["teamName"].startswith("Free Agent -")
            ):
                sixes.append(
                    {
                        "team": season["teamName"],
                        "division": season["divisionName"],
                        "season": season["seasonName"],
                    }
                )

        for season in team_data["hl"]:
            if (
                season["divisionName"] != "Dead Teams"
                and season["divisionName"] != "Admin Placement"
                and not season["teamName"].startswith("Free Agent -")
            ):
                highlander.append(
                    {
                        "team": season["teamName"],
                        "division": season["divisionName"],
                        "season": season["seasonName"],
                    }
                )

        if player_data["status"]["isBanned"]:
            ban_info = [True, player_data["banInformation"]["reason"]]
        else:
            ban_info = [False, None]

        return Player(
            int(player_data["steamId"]),
            player_data["name"],
            player_data["avatar"],
            sixes,
            highlander,
            ban_info,
        )
