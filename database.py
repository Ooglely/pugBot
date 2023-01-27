import pymongo

from rglSearch import rglAPI

client = pymongo.MongoClient(
    "mongodb://mongo:qE2c9UY1P0WT92vAXlbn@containers-us-west-157.railway.app:7516/?retryWrites=true&w=majority"
)
# db = client.players


def get_steam_from_discord(discord):
    db = client.data
    if db["players"].find_one({"discord": str(discord)}) == None:
        return None
    return db["players"].find_one({"discord": str(discord)})["steam"]


def get_player_stats(steam):
    db = client.data
    if db["stats"].find_one({"steam": steam}) == None:
        return None
    return db["stats"].find_one({"steam": steam})


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


def update_divisons(steamID: int):
    db = client.data.players
    sixes_top, hl_top = rglAPI().get_top_div(steamID)
    db.update_one(
        {"steam": str(steamID)},
        {"$set": {"divison": {"sixes": sixes_top[0], "hl": hl_top[0]}}},
        upsert=True,
    )


def update_rgl_ban_status(steamID: int) -> bool:
    db = client.data.players
    ban_status = rglAPI().check_banned(steamID)
    db.update_one(
        {"steam": str(steamID)},
        {"$set": {"rgl_ban": ban_status}},
        upsert=True,
    )
    return ban_status
