import pymongo
import os

from rglSearch import rglAPI

MONGO_URL = os.environ["MONGO_URL"]

client = pymongo.MongoClient(MONGO_URL + "/?retryWrites=true&w=majority")


# db = client.players
def get_player_from_steam(steam):
    db = client.data.players
    if db.find_one({"steam": str(steam)}) == None:
        return None
    return db.find_one({"steam": str(steam)})


def get_steam_from_discord(discord):
    db = client.data
    if db["players"].find_one({"discord": str(discord)}) == None:
        return None
    return db["players"].find_one({"discord": str(discord)})["steam"]


def get_player_stats(steam):
    db = client.data.stats
    if db.find_one({"steam": steam}) == None:
        return None
    return db.find_one({"steam": steam})


def add_player_stats(player):
    db = client.data.stats
    db.update_one({"steam": player["steam"]}, {"$set": player}, upsert=True)


def get_all_players():
    db = client.data.players
    return db.find()


def get_divisions(discordID):
    db = client.data.players
    if db.find_one({"discord": str(discordID)}) == None:
        return None
    return db.find_one({"discord": str(discordID)})["divison"]


async def update_divisons(steamID: int):
    db = client.data.players
    sixes_top, hl_top = await rglAPI().get_top_div(steamID)
    db.update_one(
        {"steam": str(steamID)},
        {"$set": {"divison": {"sixes": sixes_top[0], "hl": hl_top[0]}}},
        upsert=True,
    )


async def update_rgl_ban_status(steamID: int) -> bool:
    db = client.data.players
    try:
        ban_status = await rglAPI().check_banned(steamID)
    except LookupError:
        ban_status = False
    db.update_one(
        {"steam": str(steamID)},
        {"$set": {"rgl_ban": ban_status}},
        upsert=True,
    )
    return ban_status
