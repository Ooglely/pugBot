import asyncio
import requests
from bs4 import BeautifulSoup

class Player:
    def __init__(self, steamid, name, pfp, sixes, hl, bans):
        self.steamid = steamid
        self.name = name
        self.pfp = pfp
        self.sixes = sixes
        self.hl = hl
        self.bans = bans
    
    def __str__(self):
        return f"ID: {self.steamid}\nName: {self.name}\nPFP: {self.pfp}\nSixes: {self.sixes}\nHL: {self.hl}\nBans: {self.bans}"


class rglAPI:
    def __init__(self):
        self.apiURL = "https://api.rgl.gg/v0/"

    async def get_player(self, steamid: int):
        player = requests.get(self.apiURL + "profile/" + str(steamid)).json()
        if "statusCode" in player:
            raise LookupError("Player does not exist in RGL")
        else:
            return player

    async def get_all_teams(self, steamid: int):
        return requests.get(self.apiURL + "profile/" + str(steamid) + "/teams").json()

    async def get_core_teams(self, steamid: int):
        all_teams = await self.get_all_teams(steamid)
        core_seasons = {}
        sixes_teams = []
        hl_teams = []
        try:
            for season in all_teams:
                if season["formatId"] == 3 and season["regionId"] == 40:  # NA Sixes region code
                    sixes_teams.append(season)
                elif season["formatId"] == 2 and season["regionId"] == 24:  # NA HL region code
                    hl_teams.append(season)
            core_seasons["sixes"] = sixes_teams
            core_seasons["hl"] = hl_teams
            return core_seasons
        except:
            print(f"Error getting core teams for {steamid}: {all_teams}")
            return None

    async def check_banned(self, steamid: int):
        player = await self.get_player(steamid)
        if player["status"]["isBanned"]:
            return True
        else:
            return False

    async def get_top_div(self, steamid: int):
        player = await self.get_core_teams(steamid)
        if player == None:
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
            divisionName = season["divisionName"].replace("RGL-", "")
            if divisionName in divs:
                if divs[divisionName] > sixesdiv[0]:
                    sixesdiv[0] = divs[divisionName]
                    sixesdiv[1] = 1
                elif divs[divisionName] == sixesdiv[0]:
                    sixesdiv[1] += 1
            else:
                print(f"Division not found: {divisionName}")
        for season in player["hl"]:
            divisionName = season["divisionName"].replace("RGL-", "")
            if divisionName in divs:
                if divs[divisionName] > hldiv[0]:
                    hldiv[0] = divs[divisionName]
                    hldiv[1] = 1
                elif divs[divisionName] == hldiv[0]:
                    hldiv[1] += 1
            else:
                print(f"Division not found: {divisionName}")
        return [sixesdiv, hldiv]
    
    async def create_player(self, steamid: int) -> Player:
        sixes = []
        hl = []
        player_data = await self.get_player(steamid)
        team_data = await self.get_core_teams(steamid)

        for season in team_data["sixes"]:
            if season["divisionName"] != "Dead Teams" and season["divisionName"] != "Admin Placement" and season["teamName"].startswith("Free Agent -") != True:
                sixes.append({"team": season["teamName"], "division": season["divisionName"], "season": season["seasonName"]})

        for season in team_data["hl"]:
            if season["divisionName"] != "Dead Teams" and season["divisionName"] != "Admin Placement" and season["teamName"].startswith("Free Agent -") != True:
                hl.append({"team": season["teamName"], "division": season["divisionName"], "season": season["seasonName"]})

        if player_data["status"]["isBanned"]:
            ban_info = [True, player_data["banInformation"]["reason"]]
        else:
            ban_info = [False, None]

        return Player(int(player_data["steamId"]), player_data["name"], player_data["avatar"], sixes, hl, ban_info)


async def test_func():
    print(await rglAPI().create_player(76561199067925855))


if __name__ == "__main__":
    asyncio.run(test_func())
