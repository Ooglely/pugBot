import pymongo
import constants

client = pymongo.MongoClient(constants.DB_URL)


def is_server_setup(guild):
    db = client.guilds.config
    if db.find_one({"guild": guild}) == None:
        return False
    else:
        return True


def add_new_guild(guild, role, connect, rcon):
    db = client.guilds.config
    db.update_one(
        {"guild": guild},
        {"$set": {"role": role, "connect": connect, "rcon": rcon}},
        upsert=True,
    )


def get_server(guild):
    db = client.guilds.config
    if db.find_one({"guild": guild}) == None:
        return None
    return db.find_one({"guild": guild})


def set_guild_serveme(guild, serveme):
    db = client.guilds.config
    db.update_one(
        {"guild": guild},
        {"$set": {"serveme": serveme}},
        upsert=True,
    )
