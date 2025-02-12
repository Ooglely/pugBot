"""Utility functions for use throughout the code."""
import aiohttp
import nextcord
from steam import steamid
from steam.steamid import SteamID
from nextcord.ext import application_checks

from database import get_server, is_server_setup, BotCollection

config_db = BotCollection("guilds", "config")


class ServerNotSetupError(Exception):
    """Exception raised when the server setup process has not been completed.

    Attributes:
        message -- explanation of the error
    """

    def __init__(
        self, message="Server is not setup. Please run /setup."
    ):  # pylint: disable=super-init-not-called
        self.message = message


class NoServemeKey(Exception):
    """Exception raised when the server does not have a serveme API key setup.

    Attributes:
        message -- explanation of the error
    """

    def __init__(  # pylint: disable=super-init-not-called
        self, message="No serveme key setup for the server. Please run /serveme."
    ):
        self.message = message


def get_steam64(arg: str) -> str:
    """Converts a steam id, steam link, or RGL link to a steam64 id.

    Args:
        arg (str): The steam id, steam link, or RGL link to convert.

    Returns:
        str: The steam64 id.
    """
    if arg.startswith("https://steamcommunity.com/id/"):
        steam64 = steamid.steam64_from_url(arg)
    elif arg.startswith("[U:1:"):
        obj = SteamID(arg)
        steam64 = obj.as_64
    elif arg.startswith("STEAM_"):
        obj = SteamID(arg)
        steam64 = obj.as_64
    elif arg.startswith("7656119"):
        steam64 = arg
    elif arg.startswith("https://rgl.gg/Public/PlayerProfile.aspx?"):
        args = arg.split("=")
        steam64 = args[1].replace("&r", "")
    else:
        steam64 = steamid.steam64_from_url(f"https://steamcommunity.com/id/{arg}")
    if steam64 is None:
        raise ValueError(f"Invalid steam id: {arg}")
    return steam64


def is_runner():
    """A decorator to check if the user has the runner role for the guild."""

    async def predicate(interaction: nextcord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, nextcord.Member):
            raise application_checks.ApplicationNoPrivateMessage(
                "This command must be run in a server."
            )
        if not await is_server_setup(interaction.guild.id):
            raise ServerNotSetupError(
                "Guild id: " + str(interaction.guild.id) + " is not setup."
            )
        try:
            required_role = (await get_server(interaction.guild.id))["role"]
        except KeyError:
            await interaction.send(
                "A runner role could not be found for this server. Please run /setup."
            )
            return False
        if required_role not in [role.id for role in interaction.user.roles]:
            raise application_checks.ApplicationMissingRole(required_role)

        return True

    return nextcord.ext.application_checks.check(predicate)


def is_setup():
    """A decorator to check if the server has gone through the setup process."""

    async def predicate(interaction: nextcord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, nextcord.Member):
            raise application_checks.ApplicationNoPrivateMessage(
                "This command must be run in a server."
            )
        if not await is_server_setup(interaction.guild.id):
            raise ServerNotSetupError(
                "Guild id: " + str(interaction.guild.id) + " is not setup."
            )
        if (await get_server(interaction.guild.id)).get("serveme") is None:
            raise NoServemeKey(
                f"Guild id: {str(interaction.guild.id)}  does not have a serveme key setup."
            )

        return True

    return nextcord.ext.application_checks.check(predicate)


def guild_config_check():
    """A decorator to check if the server has guild configs setup."""

    async def predicate(interaction: nextcord.Interaction):
        if not interaction.guild:
            raise application_checks.ApplicationNoPrivateMessage(
                "This command must be run in a server."
            )
        try:
            await config_db.find_item({"guild": interaction.guild.id})
        except LookupError:
            await interaction.send(
                "This server has not been setup yet. Please run /setup first."
            )
            return False

        return True

    return nextcord.ext.application_checks.check(predicate)


async def get_exec_command(reservation: dict, tf_map: str) -> str:
    """Creates the correct exec command depending on the desired map and reservation.

    Args:
        reservation (dict): The reservation data retrieved from the serveme API.
        map (str): The desired map to switch to.

    Raises:
        Exception: If the whitelist ID in the reservation doesn't match a RGL whitelist.

    Returns:
        str: The exec command to run.
    """
    whitelist_id: int = reservation["whitelist_id"]
    custom_whitelist: str = reservation["custom_whitelist_id"]
    new_config: str

    if whitelist_id == 20:  # 6s whitelist ID
        if tf_map.startswith("cp_"):
            new_config = "rgl_6s_5cp_scrim"
        elif tf_map.startswith("koth_"):
            new_config = "rgl_6s_koth_bo5"
        else:
            new_config = "rgl_off"
    elif whitelist_id == 22:  # HL whitelist ID
        if tf_map.startswith("pl_"):
            new_config = "rgl_hl_stopwatch"
        elif tf_map.startswith("koth_"):
            new_config = "rgl_hl_koth_bo5"
        else:
            new_config = "rgl_off"
    elif whitelist_id == 26:  # PT whitelist ID
        new_config = "rgl_pt_push"
    elif custom_whitelist in ("13798", "13797"):
        if tf_map.startswith("cp_"):
            return f"changelevel {tf_map}"
        if tf_map.startswith("koth_"):
            new_config = "rgl_6s_koth_bo5"
        else:
            new_config = "rgl_off"
    else:
        return "changelevel " + tf_map

    command: str = "exec " + new_config + "; changelevel " + tf_map
    return command


async def get_log(log_id: int):
    """Returns log data from the logs.tf API.

    Returns:
        log: dict of log
    """
    async with aiohttp.ClientSession() as session:
        async with session.get("https://logs.tf/api/v1/log/" + str(log_id)) as resp:
            log = await resp.json()
            return log


async def get_total_logs(steam_id: str):
    """Returns the total number of logs for a player

    Args:
        steam_id (int): The steam ID to look up

    Returns:
        int: Total number of logs
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://logs.tf/api/v1/log?limit=10000&player=" + str(steam_id)
        ) as resp:
            logs = await resp.json()
            return logs["results"]
