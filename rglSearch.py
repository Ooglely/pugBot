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
