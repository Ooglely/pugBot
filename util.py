from steam import steamid
from steam.steamid import SteamID

def get_steam64(arg):
    if arg.startswith('https://steamcommunity.com/id/'):
        id = steamid.steam64_from_url(arg)
    if arg.startswith('[U:1:'):
        obj = SteamID(arg)
        id = obj.as_64
    if arg.startswith('STEAM_'):
        obj = SteamID(arg)
        id = obj.as_64
    if arg.startswith('7656119'):
        id = arg
    if arg.startswith('https://rgl.gg/Public/PlayerProfile.aspx?'):
        args = arg.split('=')
        id = args[1].replace('&r', '')

    return id