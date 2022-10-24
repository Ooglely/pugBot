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
