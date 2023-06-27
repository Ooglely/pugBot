"""File containing the rglAPI class, which is used to interact with the RGL API."""
import aiohttp


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
        print(all_teams)
        core_seasons = {}
        sixes_teams = []
        hl_teams = []
        try:
            for season in all_teams:
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
        except ValueError:
            print(f"Error getting core teams for {steam_id}: {all_teams}")
            return None

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
