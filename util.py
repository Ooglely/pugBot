from steam import steamid
from steam.steamid import SteamID
from database import get_server, is_server_setup
from nextcord.ext import application_checks

import nextcord


class ServerNotSetupError(Exception):
    def __init__(self, message="Server is not setup. Please run /setup."):
        self.message = message


class NoServemeKey(Exception):
    def __init__(
        self, message="No serveme key setup for the server. Please run /serveme."
    ):
        self.message = message


def get_steam64(arg: str | int) -> str:
    if arg.startswith("https://steamcommunity.com/id/"):
        id = steamid.steam64_from_url(arg)
    if arg.startswith("[U:1:"):
        obj = SteamID(arg)
        id = obj.as_64
    if arg.startswith("STEAM_"):
        obj = SteamID(arg)
        id = obj.as_64
    if arg.startswith("7656119"):
        id = arg
    if arg.startswith("https://rgl.gg/Public/PlayerProfile.aspx?"):
        args = arg.split("=")
        id = args[1].replace("&r", "")

    return id


def is_runner():
    def predicate(interaction: nextcord.Interaction):
        if is_server_setup(interaction.guild.id) == False:
            raise ServerNotSetupError(
                "Guild id: " + str(interaction.guild.id) + " is not setup."
            )
        required_role = get_server(interaction.guild.id)["role"]
        if required_role not in [role.id for role in interaction.user.roles]:
            raise application_checks.ApplicationMissingRole(required_role)
        else:
            return True

    return nextcord.ext.application_checks.check(predicate)


# TODO: Need to add a check in here for if the serveme is there or not
def is_setup():
    def predicate(interaction: nextcord.Interaction):
        if is_server_setup(interaction.guild.id) == False:
            raise ServerNotSetupError(
                "Guild id: " + str(interaction.guild.id) + " is not setup."
            )
        elif get_server(interaction.guild.id).get("serveme") == None:
            raise NoServemeKey(
                "Guild id: "
                + str(interaction.guild.id)
                + " does not have a serveme key setup."
            )
        else:
            return True

    return nextcord.ext.application_checks.check(predicate)


async def get_exec_command(reservation: dict, map: str) -> str:
    whitelist_id: int = reservation["whitelist_id"]
    new_config: str

    if whitelist_id == 20:  # 6s whitelist ID
        if map.startswith("cp_"):
            new_config = "rgl_6s_5cp_scrim"
        elif map.startswith("koth_"):
            new_config = "rgl_6s_koth_bo5"
        else:
            new_config = "rgl_off"
    elif whitelist_id == 22:  # HL whitelist ID
        if map.startswith("pl_"):
            new_config = "rgl_hl_stopwatch"
        elif map.startswith("koth_"):
            new_config = "rgl_hl_koth_bo5"
        else:
            new_config = "rgl_off"
    else:
        raise Exception("Invalid whitelist ID.")

    command: str = "exec " + new_config + "; changelevel " + map
    return command
