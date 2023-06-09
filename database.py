"""Functions for interacting with the database throughout the bot."""
import pymongo
import constants

client = pymongo.MongoClient(constants.DB_URL)


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


def update_player_stats(steam: int, stats: dict):
    """Update the player stats in the database.

    Args:
        steam (int): The steam ID to update.
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
