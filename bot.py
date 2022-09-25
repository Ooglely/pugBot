import discord
from discord.ext import commands, tasks
from steam import steamid
from steam.steamid import SteamID
import json
import random
import string
import requests
from rcon.source import Client
from rglSearch import rglSearch
from stats import logSearch
import time as unixtime
from servers import ServerCog

with open("config.json") as config_file:
    CONFIG = json.load(config_file)
    
DISCORD_TOKEN = CONFIG["discord"]["token"]
SERVEME_API_KEY = CONFIG["serveme"]["api_key"]

version = "v0.7.0"

# Setting initial variables
lastLog = ""
pug_running = False

roles = [
    [' (Scout Restriction)', '999191878736039957'],
    [' (Soldier Restriction)', '999191955831537665'],
    [' (Pyro Restriction)', '999192009090793492'],
    [' (Demo Restriction)', '999192084420509787'],
    [' (Heavy Restriction)', '999192133426749462'],
    [' (Engi Restriction)', '999192179161436250'],
    [' (Sniper Restriction)', '999192234509488209'],
    [' (Spy Restriction)', '999192279870885982']
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

activity = discord.Activity(name='over my pugs ^_^', type=discord.ActivityType.watching)
bot = commands.Bot(command_prefix='r!', intents=intents, activity = activity)


bot.remove_command('help')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    await bot.load_extension('servers')
    
@bot.listen('on_message')
async def playerListener(message):
    if message.content.startswith('https://rgl.gg/Public/PlayerProfile.aspx?'):
        args = message.content.split('=')
        id = args[1].replace('&r', '')

        open('output.json', 'w').close()
        
        rgl = rglSearch(id)

        url = 'https://rgl.gg/Public/PlayerProfile.aspx?p=' + str(id)
        
        embed=discord.Embed(title=rgl[0], url = url, color=0xf0984d)
        embed.set_thumbnail(url=rgl[1])
        if rgl[2] != "": # Sixes Data
            embed.add_field(name="Sixes", value=rgl[2], inline=False)
        if rgl[3] != "": # HL Data
            embed.add_field(name="Highlander", value=rgl[3], inline=False)
        if rgl[4] != "": # PL Data
            embed.add_field(name="Prolander", value=rgl[4], inline=False)
        embed.set_footer(text=version)
        await message.channel.send(embed=embed)
        open('output.json', 'w').close()
        pass

@bot.command()
async def search(ctx, arg: str):
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
    
    rgl = rglSearch(id)
    
    url = 'https://rgl.gg/Public/PlayerProfile.aspx?p=' + str(id)
    
    embed=discord.Embed(title=rgl[0], url = url, color=0xf0984d)
    embed.set_thumbnail(url=rgl[1])
    if rgl[2] != "": # Sixes Data
        embed.add_field(name="Sixes", value=rgl[2], inline=False)
    if rgl[3] != "": # HL Data
        embed.add_field(name="Highlander", value=rgl[3], inline=False)
    if rgl[4] != "": # PL Data
        embed.add_field(name="Prolander", value=rgl[4], inline=False)
    embed.set_footer(text=version)
    await ctx.send(embed=embed)
    open('output.json', 'w').close()
    pass

@bot.command()
@commands.has_role('Runners')
async def move(ctx):
    if ctx.channel.id == 996415628007186542: # HL Channels
        team1Channel = bot.get_channel(987171351720771644)
        team2Channel = bot.get_channel(994443542707580951)
        selectingChannel = bot.get_channel(996567486621306880)
        
        for member in team1Channel.members:
            await member.move_to(selectingChannel)
            
        for member in team2Channel.members:
            await member.move_to(selectingChannel)
            
        await ctx.send("Players moved.")
    
    if ctx.channel.id == 997602235208962150: # 6s Channels
        team1Channel = bot.get_channel(997602308525404242)
        team2Channel = bot.get_channel(997602346173464587)
        selectingChannel = bot.get_channel(997602270592118854)
        
        for member in team1Channel.members:
            await member.move_to(selectingChannel)
            
        for member in team2Channel.members:
            await member.move_to(selectingChannel)
            
        await ctx.send("Players moved.")
        
@bot.command()
@commands.has_role('Runners')
async def randomize(ctx, num: int):
    team1Players = 0
    team2Players = 0
    if ctx.channel.id == 996415628007186542: # HL Channels
        players = []
        team1Channel = bot.get_channel(987171351720771644)
        team2Channel = bot.get_channel(994443542707580951)
        selectingChannel = bot.get_channel(996567486621306880)
        
        for member in selectingChannel.members:
            for role in member.roles:
                if role.id == 992281832437596180:
                    players[0].append(member.id)
            else: players[1].append(member.id)
        
        random.shuffle(players[0])
        random.shuffle(players[1])
        players = players[0] + players[1]
        
        for player in players:
            if team1Players < num:
                await ctx.message.guild.get_member(player).move_to(team1Channel)
                team1Players += 1
            elif team2Players < num:
                await ctx.message.guild.get_member(player).move_to(team2Channel)
                team2Players += 1
            else:
                break
            
        await ctx.send("Players moved.")
    
    if ctx.channel.id == 997602235208962150: # 6s Channels
        players = [[],[]]
        team1Channel = bot.get_channel(997602308525404242)
        team2Channel = bot.get_channel(997602346173464587)
        selectingChannel = bot.get_channel(997602270592118854)
        
        for member in selectingChannel.members:
            for role in member.roles:
                if role.id == 992281832437596180:
                    players[0].append(member.id)
            else: players[1].append(member.id)
        
        random.shuffle(players[0])
        random.shuffle(players[1])
        players = players[0] + players[1]
        
        for player in players:
            if team1Players < num:
                await ctx.message.guild.get_member(player).move_to(team1Channel)
                team1Players += 1
            elif team2Players < num:
                await ctx.message.guild.get_member(player).move_to(team2Channel)
                team2Players += 1
            else:
                break
            
        await ctx.send("Players moved.")
    
@bot.command()
async def help(ctx):
    embed=discord.Embed(title='pugBot', color=0xf0984d)
    embed.set_thumbnail(url='https://b.catgirlsare.sexy/XoBJQn439QgJ.jpeg')
    embed.add_field(name="Commands", value='r!search [steam/steamid/rgl] - Finds someones RGL page and team history.', inline=False)
    embed.add_field(name="Runners Only", value='r!move - Move all players back to organizing channels.\nr!randomize [num] - Randomly picks teams of [num] size and moves them to the team channels.\nr!startserver - Starts a serveme.tf reservation to be used for pugs.\nr!map - Change map using on last rcon message.\nr!config - Change config using last rcon message.\nr!check - Lists divs of all players in the organizing channel.\nr!randommap - Change to a random map based on the gamemode.', inline=False)
    embed.set_footer(text=version)
    await ctx.send(embed=embed)
    
@bot.command()
async def check(ctx):
    ncPlayers = ""
    plusPlayers = ""
    
    selectingChannel = bot.get_channel(996567486621306880)
    
    for member in selectingChannel.members:
        playerString = ""
        playerString += member.display_name
        for role in member.roles:
            for id in roles:
                if str(role.id) == id[1]:
                    playerString += id[0]
        
        playerString += "\n"
        
        for role in member.roles:
            if role.id == 992286429881303101:
                ncPlayers += playerString
            if role.id == 992281832437596180:
                plusPlayers += playerString
    
    embed=discord.Embed(title='Player Check', color=0xf0984d)
    embed.add_field(name="NC/AM Players", value=ncPlayers, inline=False)
    embed.add_field(name="AM+ Players", value=plusPlayers, inline=False)
    embed.set_footer(text=version)
    await ctx.send(embed=embed)

@bot.command()
async def stats(ctx, id):
    if str(id).startswith('https://steamcommunity.com/id/'):
        id = steamid.steam64_from_url(id)
    if str(id).startswith('[U:1:'):
        obj = SteamID(id)
        id = obj.as_64
    if str(id).startswith('STEAM_'):
        obj = SteamID(id)
        id = obj.as_64
    if str(id).startswith('7656119'):
        id = id

    #info = rglSearch(int(id))
    #logString = f"```\n{info[0]}'s pug stats"
    
    logString = '```\n  Class |  K  |  D  | DPM | Logs'
    stats = await logSearch(int(id))
    for i in stats:
        if i[1] != 0:
            dpm = f'{i[3] / (i[4] / 60):.1f}'
            logString += f'\n{i[0]: >8}|{i[1]: >5}|{i[2]: >5}|{dpm: >5}|{i[5]: >5}'
    logString += '```'
    await ctx.send(logString)
    open('output.json', 'w').close()


@tasks.loop(seconds=5, count=None) # task runs every 30 seconds
async def fatkid_check(self):
    sixes_team_1 = bot.get_channel(997602308525404242)
    sixes_team_2 = bot.get_channel(997602346173464587)
    hl_team_1 = bot.get_channel(987171351720771644)
    hl_team_2 = bot.get_channel(994443542707580951)
    sixes_organizing = bot.get_channel(997602270592118854)
    hl_organizing = bot.get_channel(996567486621306880)
    sixes_pug_channel = bot.get_channel(997602176769732740)
    hl_pug_channel = bot.get_channel(996601879838601329)
    fatkids = []
    fk_string = "FKs: "
    if pug_running == False:
        if len(sixes_team_1.members) >= 6 and len(sixes_team_2.members) >= 6:
            print('Pug has been detected as running.')
            for member in sixes_organizing.members:
                fatkids.append(member.id)
                fk_string += f"<@{member.id}> "
            if fk_string != "FKs: ":
                sixes_pug_channel.send(fk_string)
            pug_running = True
        elif len(hl_team_1.members) >= 9 and len(hl_team_2.members) >= 9:
            print('Pug has been detected as running.')
            for member in hl_organizing.members:
                fatkids.append(member.id)
                fk_string += f"<@{member.id}> "
            if fk_string != "FKs: ":
                hl_pug_channel.send(fk_string)
            pug_running = True
    elif pug_running:
        if len(sixes_team_1.members) >= 4 or len(sixes_team_2.members) >= 4 or len(hl_team_1.members) >= 6 or len(hl_team_2.members) >= 6: return
        elif len(sixes_team_1.members) <= 4 and len(sixes_team_2.members) <= 4:
            print('Pug has been detected as finished.')
            pug_running = False
        elif len(hl_team_1.members) <= 6 and len(hl_team_2.members) <= 6:
            print('Pug has been detected as finished.')
            pug_running = False
bot.run(DISCORD_TOKEN)
