import requests
from bs4 import BeautifulSoup


def rglSearch(id):
    URL = "https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(id)
    page = requests.get(URL)

    soup = BeautifulSoup(page.content, "html.parser")
    name = soup.find(
        id="ContentPlaceHolder1_ContentPlaceHolder1_ContentPlaceHolder1_lblPlayerName"
    ).get_text()
    pfp = soup.find(
        id="ContentPlaceHolder1_ContentPlaceHolder1_ContentPlaceHolder1_imgProfileImage"
    ).get("src")
    seasonList = soup.select("tr > td > a")
    banList = soup.find(id="banhistory").nextSibling.nextSibling.find_all("td")

    bans = []
    for i in banList:
        element = i.get_text()
        if element.strip() != "":
            bans.append(element.strip())

    num = 0
    banHistory = []
    for count, i in enumerate(bans):
        if count == num:
            banHistory.append(
                [bans[count].strip(), bans[count + 1].strip(), bans[count + 2].strip()]
            )
            num += 3

    seasons = []
    for i in seasonList:
        seasons.append(i.get_text())

    num = 0
    seasonHistory = []
    for count, i in enumerate(seasons):
        if i.strip() == "":
            del seasons[count]
        if not "\r\n" in i:
            del seasons[count]

    for count, i in enumerate(seasons):
        if count == num:
            seasonHistory.append(
                [
                    seasons[count].strip(),
                    seasons[count + 1].strip(),
                    seasons[count + 2].strip(),
                ]
            )
            num += 3

    sixes = ""
    hl = ""
    pl = ""
    for i in seasonHistory:
        if i[0].startswith("Sixes S"):
            sixes += i[0] + " - " + i[1] + " - " + i[2] + "\n"
        if i[0].startswith("HL Season"):
            hl += i[0] + " - " + i[1] + " - " + i[2] + "\n"
        if i[0].startswith("P7 Season"):
            pl += i[0] + " - " + i[1] + " - " + i[2] + "\n"

    bans = ""
    for i in banHistory:
        bans += i[0] + " - " + i[1] + ": " + i[2] + "\n"

    divs = {
        "Newcomer": 1,
        "Amateur": 2,
        "Intermediate": 3,
        "Main": 4,
        "Advanced": 5,
        "Invite": 6,
    }
    divNum = 0
    for i in seasonHistory:
        if i[0].startswith("Sixes S"):
            if i[1] in divs:
                if divs[i[1]] > divNum:
                    divNum = divs[i[1]]
        if i[0].startswith("HL Season"):
            if i[1] in divs:
                if divs[i[1]] > divNum:
                    divNum = divs[i[1]]

    return [name, pfp, sixes, hl, pl, bans, divNum]


class rglAPI:
    def __init__(self):
        self.apiURL = "https://api.rgl.gg/v0/"

    def get_player(self, steamid: int):
        player = requests.get(self.apiURL + "profile/" + str(steamid)).json()
        if "statusCode" in player:
            raise LookupError("Player does not exist in RGL")
        else:
            return player

    def get_all_teams(self, steamid: int):
        return requests.get(self.apiURL + "profile/" + str(steamid) + "/teams").json()

    def get_core_teams(self, steamid: int):
        all_teams = self.get_all_teams(steamid)
        core_seasons = {}
        sixes_teams = []
        hl_teams = []
        for season in all_teams:
            if season["formatId"] == 3:  # 6s format
                if season["regionId"] == 40:  # NA Sixes region code
                    sixes_teams.append(season)
            elif season["formatId"] == 2:  # HL format
                if season["regionId"] == 24:  # NA HL region code
                    hl_teams.append(season)
        core_seasons["sixes"] = sixes_teams
        core_seasons["hl"] = hl_teams
        return core_seasons

    def check_banned(self, steamid: int):
        player = self.get_player(steamid)
        if player["status"]["isBanned"] or player["status"]["isOnProbation"]:
            return True
        else:
            return False

    def get_top_div(self, steamid: int):
        player = self.get_core_teams(steamid)
        divs = {
            "Newcomer": 1,
            "Amateur": 2,
            "Intermediate": 3,
            "Main": 4,
            "Advanced": 5,
            "Advanced-1": 6,
            "Advanced-2": 5,
            "Invite": 7,
            "Admin Placement": 0,
            "Dead Teams": 0,
        }
        sixesdiv = [0, 0]
        hldiv = [0, 0]
        for season in player["sixes"]:
            if divs[season["divisionName"]] > sixesdiv[0]:
                sixesdiv[0] = divs[season["divisionName"]]
                sixesdiv[1] = 1
            elif divs[season["divisionName"]] == sixesdiv[0]:
                sixesdiv[1] += 1
        for season in player["hl"]:
            if divs[season["divisionName"]] > hldiv[0]:
                hldiv[0] = divs[season["divisionName"]]
                hldiv[1] = 1
            elif divs[season["divisionName"]] == hldiv[0]:
                hldiv[1] += 1
        return [sixesdiv, hldiv]


if __name__ == "__main__":
    sixes, hl = rglAPI().get_top_div(76561198171178258)
    print(sixes)
    print(hl)
