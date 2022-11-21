import pymongo

client = pymongo.MongoClient(
    "mongodb+srv://alen:u7U^qhc&RBAKoc@rglbot.9v1juuk.mongodb.net/?retryWrites=true&w=majority"
)
# db = client.players


def update_player(name, discord, id, div):
    db = client.players
    db["data"].update_one(
        {"name": str(name)},
        {
            "$set": {
                "name": str(name),
                "discord": int(discord),
                "steam64": int(id),
                "div": str(div),
            }
        },
        upsert=True,
    )
    return

def get_steam_from_discord(discord):
    db = client.players
    return db["data"].find_one({"discord": discord})["steam64"]


def update_server_status(status):
    db = client.servers
    db["pug_status"].update_one(
        {"name": "server"}, {"$set": {"status": status}}, upsert=True
    )


def get_server_status():
    db = client.servers
    return db["pug_status"].find_one({"name": "server"})["status"]
