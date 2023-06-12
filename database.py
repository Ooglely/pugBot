"""Functions for interacting with the database throughout the bot."""
import pymongo
import constants
from rgl_api import RGL_API

RGL: RGL_API = RGL_API()

client = pymongo.MongoClient(constants.DB_URL + "/?retryWrites=true&w=majority")


def is_server_setup(guild: int):
    """Check if a server is setup.

    Args:
        guild (int): The guild ID to check.

    Returns:
        bool: True if the server is setup, False otherwise.
    """
    database = client.guilds.config
    if database.find_one({"guild": guild}) is None:
        return False
    return True


def add_new_guild(guild: int, role: int, connect: int, rcon: int):
    """Add a new guild to the database.

    Args:
        guild (int): The guild ID to add.
        role (int): The runner role ID.
        connect (int): The connect channel ID.
        rcon (int): The rcon channel ID.
    """
    database = client.guilds.config
    database.update_one(
        {"guild": guild},
        {"$set": {"role": role, "connect": connect, "rcon": rcon}},
        upsert=True,
    )


def get_server(guild: int):
    """Get the server data from the database.

    Args:
        guild (int): The guild ID to get.

    Returns:
        dict: The server data from the db.
    """
    database = client.guilds.config
    if database.find_one({"guild": guild}) is None:
        return None
    return database.find_one({"guild": guild})


def set_guild_serveme(guild: int, serveme: str):
    """Set the serveme key for a guild.

    Args:
        guild (int): The guild ID to set.
        serveme (str): The serveme key to set.
    """
    database = client.guilds.config
    database.update_one(
        {"guild": guild},
        {"$set": {"serveme": serveme}},
        upsert=True,
    )


def add_player(steam: str, discord: str):
    """Add a new player to the database.

    Args:
        steam (int): The steam ID to add.
        discord (int): The discord ID to add.
    """
    database = client.players.data
    database.update_one(
        {"steam": steam},
        {"$set": {"steam": steam, "discord": discord, "rgl_registered": False}},
        upsert=True,
    )


def get_player_stats(steam: int):
    """Get the player stats from the database.

    Args:
        steam (int): The steam ID to get.

    Returns:
        dict: The player stats from the db.
    """
    database = client.players.stats
    if database.find_one({"steam": steam}) is None:
        return None
    return database.find_one({"steam": steam})


def update_player_stats(steam: str, stats: dict):
    """Update the player stats in the database.

    Args:
        steam (str): The steam ID to update.
        stats (dict): The stats to update.
    """
    database = client.players.stats
    database.update_one({"steam": steam}, {"$set": stats}, upsert=True)


def get_steam_from_discord(discord: int):
    """Get the steam ID from the database.

    Args:
        discord (int): The discord ID to get.

    Returns:
        dict: The steam ID from the db.
    """
    database = client.players.data
    if database.find_one({"discord": str(discord)}) is None:
        return None
    return database.find_one({"discord": str(discord)})["steam"]


def get_player_from_steam(steam: int):
    """Get the player from the database.

    Args:
        steam (int): The steam ID to get.

    Returns:
        dict: Player data
    """
    database = client.players.data
    if database.find_one({"steam": str(steam)}) is None:
        return None
    return database.find_one({"steam": str(steam)})


def get_all_players():
    """Get all players from the database."""
    database = client.players.data
    print(database.count_documents({}))
    return database.find()


def get_divisions(discord: int):
    """Get the RGL divisons of a player.

    Args:
        discord (int): The discord ID to get.

    Returns:
        dict: The top divs of the player.
    """
    database = client.players.data
    if database.find_one({"discord": str(discord)}) is None:
        return None
    return database.find_one({"discord": str(discord)})["divison"]


async def update_divisons(steam: int):
    """Update the RGL divisons of a player.

    Args:
        steam (int): The steam ID to update.
    """
    database = client.players.data
    sixes_top, hl_top = await RGL.get_top_div(steam)
    database.update_one(
        {"steam": str(steam)},
        {"$set": {"divison": {"sixes": sixes_top[0], "hl": hl_top[0]}}},
        upsert=True,
    )


async def update_rgl_ban_status(steam: int) -> bool:
    """Update the RGL ban status of a player.

    Args:
        steam (int): The steam ID to update.

    Returns:
        bool: True if the player is banned, False otherwise.
    """
    database = client.players.data
    try:
        ban_status = await RGL.check_banned(steam)
    except LookupError:
        ban_status = False
    database.update_one(
        {"steam": str(steam)},
        {"$set": {"rgl_ban": ban_status}},
        upsert=True,
    )
    return ban_status
