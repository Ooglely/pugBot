"""Functions for interacting with the database throughout the bot."""
import pymongo
import constants
from rgl_api import RGL_API

RGL: RGL_API = RGL_API()


class BotDatabase(pymongo.MongoClient):
    """Class that represents the bot's database."""

    def __init__(self):
        super().__init__(constants.DB_URL + "/?w=majority")


class BotCollection:
    """Class used to interact with different parts of the bots database in an easier way."""

    def __init__(
        self,
        database: str,
        collection: str,
        mongo_client: pymongo.MongoClient = BotDatabase(),
    ) -> None:
        self.client = mongo_client
        self.database = client[database][collection]

    async def add_item(self, item: dict):
        """Insert an item to the collection.

        Args:
            item (dict): The item to add.
        """
        self.database.insert_one(item)

    async def update_item(self, search: dict, item: dict):
        """Update an item in the collection.

        Args:
            search (dict): The key to look for in the collection.
            item (dict): The thing to insert into the item.
        """
        self.database.update_one(search, item, upsert=True)

    async def find_item(self, search: dict):
        """Search for an item in the collection.

        Args:
            search (dict): The key to look for.
        """
        result = self.database.find_one(search)
        if result is None:
            raise LookupError
        return result

    async def find_all_items(self) -> list[dict]:
        """Returns all items in the collection."""
        results = []
        for item in self.database.find():
            results.append(item)
        return results


client = BotDatabase()


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


def get_all_servers():
    """Get all servers from the database."""
    database = client.guilds.config
    return database.find()


def set_registration_settings(guild: int, registration):
    """Set the registration settings for a guild.

    Args:
        guild (int): The guild ID to set.
        registration (dict): The registration settings to set.
    """
    database = client.guilds.config
    database.update_one(
        {"guild": guild},
        {"$set": {"registration": registration}},
        upsert=True,
    )


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


def add_med_immune_player(guild: int, discord: int):
    """Add a player to the med immunity array for the guild

    Args:
        guild (int): The guild ID to set in
        discord (str): The discord ID of the player to set
    """
    database = client.guilds.config
    database.update_one(
        {"guild": guild},
        {"$push": {"immune": discord}}
    )


def remove_med_immune_player(guild: int, discord: int):
    """Remove a player from the med immunity array for the guild

    Args:
        guild (int): The guild ID to remove from
        discord (str): The discord ID of the player to remove
    """
    database = client.guilds.config
    database.update_one(
        {"guild": guild},
        {"pull": {"immune": discord}}
    )

def clear_med_immuninty_by_guild(guild: int):
    """Clear the med immunity field of all discord ids for a given guild

    Args:
        guild: The guild ID to clear the med immunity field of
    """
    database = client.guilds.config
    database.update_one(
        {"guild": guild},
        {"$set": {"immune": []}}
    )


def clear_med_immuninty():
    """Clear the med immunity field for all guilds

    Args:
        guild: The guild ID to clear the med immunity field of
    """
    database = client.guilds.config
    database.update_many(
        {},
        {"$set": {"immune": []}}
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
        raise LookupError
    return database.find_one({"steam": str(steam)})


def get_player_from_discord(discord: int):
    """Get the player from the database.

    Args:
        discord (int): The discord ID to get.

    Returns:
        dict: Player data
    """
    database = client.players.data
    if database.find_one({"discord": str(discord)}) is None:
        raise LookupError("Player not found in database")
    return database.find_one({"discord": str(discord)})


def get_all_players():
    """Get all players from the database."""
    database = client.players.data
    return database.find()


def player_count():
    """Returns the amount of players in the database."""
    database = client.players.data
    return database.count_documents({})


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
    try:
        division = database.find_one({"discord": str(discord)})["divison"]
        return division
    except KeyError:
        return None


async def update_divisons(steam: int, divisons):
    """Update the RGL divisons of a player.

    Args:
        steam (int): The steam ID to update.
        divisons (dict): The divisons to set for the player.
    """
    database = client.players.data
    if divisons["hl"]["highest"] == -1 and get_divisions(steam) is not None:
        print("Skipping updating divs as there is no data.")
        return
    database.update_one(
        {"steam": str(steam)},
        {"$set": {"divison": divisons}},
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
        return False
    database.update_one(
        {"steam": str(steam)},
        {"$set": {"rgl_ban": ban_status}},
        upsert=True,
    )
    return ban_status
