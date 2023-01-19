import pymongo

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
