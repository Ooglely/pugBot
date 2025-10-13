"""Functions for interacting with the database throughout the bot."""
import motor.motor_asyncio

import constants
from rglapi import RglApi

RGL: RglApi = RglApi()

db_client: motor.motor_asyncio.AsyncIOMotorClient = (
    motor.motor_asyncio.AsyncIOMotorClient(constants.DB_URL + "/?w=majority")
)


class BotCollection:
    """Class used to interact with different parts of the bots database in an easier way."""

    def __init__(self, database: str, collection: str) -> None:
        self.client = db_client
        self.database = db_client[database][collection]

    async def add_item(self, item: dict):
        """Insert an item to the collection.

        Args:
            item (dict): The item to add.
        """
        await self.database.insert_one(item)

    async def update_item(self, search: dict, item: dict):
        """Update an item in the collection.

        Args:
            search (dict): The key to look for in the collection.
            item (dict): The thing to insert into the item.
        """
        await self.database.update_one(search, item, upsert=True)

    async def find_item(self, search: dict):
        """Search for an item in the collection.

        Args:
            search (dict): The key to look for.
        """
        result = await self.database.find_one(search)
        if result is None:
            raise LookupError
        return result
    
    async def aggregate(self, search: list[dict]) -> list:
        result = await self.database.aggregate(search)
        if result is None:
            raise LookupError
        return result

    async def delete_item(self, search: dict):
        """Delete an item from the collection.

        Args:
            search (dict): The key to look for.
        """
        await self.database.delete_one(search)

    async def find_all_items(self) -> list[dict]:
        """Returns all items in the collection."""
        results = []
        async for item in self.database.find():
            results.append(item)
        return results


async def is_server_setup(guild: int):
    """Check if a server is setup.

    Args:
        guild (int): The guild ID to check.

    Returns:
        bool: True if the server is setup, False otherwise.
    """
    database = db_client.guilds.config
    if await database.find_one({"guild": guild}) is None:
        return False
    return True


async def add_new_guild(guild: int, role: int, connect: int | None, rcon: int | None):
    """Add a new guild to the database.

    Args:
        guild (int): The guild ID to add.
        role (int): The runner role ID.
        connect (int | None): The connect channel ID.
        rcon (int | None): The rcon channel ID.
    """
    database = db_client.guilds.config
    await database.update_one(
        {"guild": guild},
        {"$set": {"role": role, "connect": connect, "rcon": rcon, "immune": []}},
        upsert=True,
    )


async def get_server(guild: int):
    """Get the server data from the database.

    Args:
        guild (int): The guild ID to get.

    Returns:
        dict: The server data from the db.
    """
    database = db_client.guilds.config
    if await database.find_one({"guild": guild}) is None:
        return None
    return await database.find_one({"guild": guild})


def get_all_servers():
    """Get all servers from the database."""
    database = db_client.guilds.config
    return database.find()


async def set_registration_settings(guild: int, registration):
    """Set the registration settings for a guild.

    Args:
        guild (int): The guild ID to set.
        registration (dict): The registration settings to set.
    """
    database = db_client.guilds.config
    await database.update_one(
        {"guild": guild},
        {"$set": {"registration": registration}},
        upsert=True,
    )


async def set_guild_serveme(guild: int, serveme: str):
    """Set the serveme key for a guild.

    Args:
        guild (int): The guild ID to set.
        serveme (str): The serveme key to set.
    """
    database = db_client.guilds.config
    await database.update_one(
        {"guild": guild},
        {"$set": {"serveme": serveme}},
        upsert=True,
    )


async def add_player(steam: str, discord: str):
    """Add a new player to the database.

    Args:
        steam (int): The steam ID to add.
        discord (int): The discord ID to add.
    """
    database = db_client.players.data
    await database.update_one(
        {"steam": str(steam)},
        {"$set": {"steam": str(steam), "discord": discord}},
        upsert=True,
    )


async def add_med_immune_player(guild: int, discord: int):
    """Add a player to the med immunity array for the guild

    Args:
        guild (int): The guild ID to set in
        discord (str): The discord ID of the player to set
    """
    database = db_client.guilds.config
    await database.update_one({"guild": guild}, {"$push": {"immune": discord}})


async def remove_med_immune_player(guild: int, discord: int):
    """Remove a player from the med immunity array for the guild

    Args:
        guild (int): The guild ID to remove from
        discord (str): The discord ID of the player to remove
    """
    database = db_client.guilds.config
    await database.update_one({"guild": guild}, {"$pull": {"immune": discord}})


async def clear_med_immunity_by_guild(guild: int):
    """Clear the med immunity field of all discord ids for a given guild

    Args:
        guild: The guild ID to clear the med immunity field of
    """
    database = db_client.guilds.config
    await database.update_one({"guild": guild}, {"$set": {"immune": []}})


async def clear_med_immunity_all_guilds():
    """Clear the med immunity field for all guilds
    THIS FUNCTION SHOULD NEVER BE CALLED WITHIN A SLASH COMMAND
    """
    database = db_client.guilds.config
    await database.update_many({}, {"$set": {"immune": []}})


async def get_player_stats(steam: int):
    """Get the player stats from the database.

    Args:
        steam (int): The steam ID to get.

    Returns:
        dict: The player stats from the db.
    """
    database = db_client.players.stats
    if await database.find_one({"steam": steam}) is None:
        return None
    return await database.find_one({"steam": steam})


async def update_player_stats(steam: str, stats: dict):
    """Update the player stats in the database.

    Args:
        steam (str): The steam ID to update.
        stats (dict): The stats to update.
    """
    database = db_client.players.stats
    await database.update_one({"steam": steam}, {"$set": stats}, upsert=True)


async def get_steam_from_discord(discord: int):
    """Get the steam ID from the database.

    Args:
        discord (int): The discord ID to get.

    Returns:
        dict: The steam ID from the db.
    """
    database = db_client.players.data
    player = await database.find_one({"discord": str(discord)})
    if player is None:
        return None
    return player["steam"]


async def get_player_from_steam(steam: int) -> dict:
    """Get the player from the database.

    Args:
        steam (int): The steam ID to get.

    Returns:
        dict: Player data
    """
    database = db_client.players.data
    player = await database.find_one({"steam": str(steam)})
    if player is None:
        raise LookupError
    return player


async def get_player_from_discord(discord: int):
    """Get the player from the database.

    Args:
        discord (int): The discord ID to get.

    Returns:
        dict: Player data
    """
    database = db_client.players.data
    player = await database.find_one({"discord": str(discord)})
    if player is None:
        raise LookupError("Player not found in database")
    return player


def get_all_players():
    """Get all players from the database."""
    database = db_client.players.data
    return database.find()


async def player_count():
    """Returns the amount of players in the database."""
    database = db_client.players.data
    return await database.count_documents({})


async def log_count():
    """Returns the amount of logs in the database."""
    database = db_client.logs.list
    return await database.count_documents({})


async def get_divisions(discord: int):
    """Get the RGL divisons of a player.

    Args:
        discord (int): The discord ID to get.

    Returns:
        dict: The top divs of the player.
    """
    database = db_client.players.data
    if database.find_one({"discord": str(discord)}) is None:
        return None
    try:
        player = await database.find_one({"discord": str(discord)})
        if player:
            return player["divison"]
        return None
    except KeyError:
        return None


async def update_divisons(steam: int, divisons):
    """Update the RGL divisons of a player.

    Args:
        steam (int): The steam ID to update.
        divisons (dict): The divisons to set for the player.
    """
    database = db_client.players.data
    if divisons["hl"]["highest"] == -1 and await get_divisions(steam) is not None:
        print("Skipping updating divs as there is no data.")
        return
    await database.update_one(
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
    database = db_client.players.data
    try:
        ban_status = await RGL.check_banned(steam)
    except LookupError:
        return False
    await database.update_one(
        {"steam": str(steam)},
        {"$set": {"rgl_ban": ban_status}},
        upsert=True,
    )
    return ban_status
