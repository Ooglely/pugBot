from steam import steamid
from steam.steamid import SteamID
from database import get_server

import nextcord


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


async def check_if_runner(guild: nextcord.Guild, user: nextcord.Member) -> bool:
    required_role = get_server(guild.id)["role"]
    if required_role not in [role.id for role in user.roles]:
        return False
    else:
        return True


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
