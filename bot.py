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
import time as unixtime

with open("config.json") as config_file:
    CONFIG = json.load(config_file)
    
DISCORD_TOKEN = CONFIG["discord"]["token"]
SERVEME_API_KEY = CONFIG["serveme"]["api_key"]

version = "v0.4.2"

# Setting initial variables
serverStatus = False
lastLog = ""
timestamp = unixtime.time()

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
intents.messages = True
intents.presences = True

activity = discord.Activity(name='over my pugs ^_^', type=discord.ActivityType.watching)
bot = commands.Bot(command_prefix='r!', intents=intents, activity = activity)
bot.remove_command('help')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    server_status.start(bot)
    
@bot.listen('on_message')
async def playerListener(message):
    if message.content.startswith('https://rgl.gg/Public/PlayerProfile.aspx?'):
        args = message.content.split('=')
        id = args[1].replace('&r', '')
        
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
            players.append(member.id)
        
        random.shuffle(players)
        
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
        team1Channel = bot.get_channel(997602308525404242)
        team2Channel = bot.get_channel(997602346173464587)
        selectingChannel = bot.get_channel(997602270592118854)
        
        for member in selectingChannel.members:
            players.append(member.id)
        
        random.shuffle(players)
        
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
@commands.has_role('Runners')
async def startserver(ctx):
    headers = {'Content-type': 'application/json'}
    new = requests.get('https://na.serveme.tf/api/reservations/new?api_key=' + SERVEME_API_KEY, headers=headers)
    times = new.text

    headers = {'Content-type': 'application/json'}
    find_servers = requests.post('https://na.serveme.tf/api/reservations/find_servers?api_key=' + SERVEME_API_KEY, data=times, headers=headers)

    for server in find_servers.json()['servers']:
        if "chi" in server['ip']:
            print(server)
            reserve = server
            break

    connectPassword = 'andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    rconPassword = 'rcon.andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=20))

    reserveString = {
        "reservation": {
            "starts_at": new.json()['reservation']['starts_at'], 
            "ends_at": new.json()['reservation']['ends_at'], 
            "rcon": rconPassword, 
            "password": connectPassword,
            "server_id": reserve['id'],
            "enable_plugins": True,
            "enable_demos_tf": True,
            "first_map": "koth_ashville_rc2d",
            "server_config_id": 54,
            "whitelist_id": 22,
            "custom_whitelist_id": None
        }}

    reserveJSON = json.dumps(reserveString)

    sendReservation = requests.post('https://na.serveme.tf/api/reservations?api_key=' + SERVEME_API_KEY, data=reserveJSON, headers=headers)
    server = sendReservation.json()
    
    serverStatus = True

    connect = 'connect ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; password "' + server['reservation']['password'] + '"'
    rcon = 'rcon_address ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; rcon_password "' + server['reservation']['rcon'] + '"'
    
    embed=discord.Embed(title='Server started!', color=0xf0984d)
    embed.add_field(name="Server", value=server['reservation']['server']['name'], inline=False)
    embed.add_field(name="Connect", value=connect, inline=False)
    embed.add_field(name="RCON", value='RCON has been sent in the rcon channel.', inline=False)
    embed.set_footer(text=version)
    await ctx.send(embed=embed)
    
    channel = bot.get_channel(1000161175859900546)
    await channel.send(rcon)
    
    channel = bot.get_channel(996980099486322798)
    await channel.send(connect)
    
@bot.command()
@commands.has_role('Runners')
async def config(ctx, config: str):
    channel = bot.get_channel(1000161175859900546)
    rconMessage = await channel.fetch_message(channel.last_message_id)
    rconCommand = rconMessage.content
    
    ip = rconCommand.split(' ')[1].split(':')[0]
    port = rconCommand.split(' ')[1].split(':')[1].split(';')[0]
    password = rconCommand.split(' ')[3].split('"')[1]
    
    with Client(str(ip), int(port), passwd=password) as client:
        response = client.run('exec', config)

    print(response)
    
    await ctx.send("Config executed.")

@bot.command()
@commands.has_role('Runners')
async def map(ctx, map: str):
    channel = bot.get_channel(1000161175859900546)
    rconMessage = await channel.fetch_message(channel.last_message_id)
    rconCommand = rconMessage.content
    
    ip = rconCommand.split(' ')[1].split(':')[0]
    port = rconCommand.split(' ')[1].split(':')[1].split(';')[0]
    password = rconCommand.split(' ')[3].split('"')[1]
    
    with Client(str(ip), int(port), passwd=password) as client:
        response = client.run('changelevel', map)

    print(response)
    
    await ctx.send("Changing map to " + map + ".")
    
@bot.command()
async def help(ctx):
    embed=discord.Embed(title='pugBot', color=0xf0984d)
    embed.set_thumbnail(url='https://b.catgirlsare.sexy/XoBJQn439QgJ.jpeg')
    embed.add_field(name="Commands", value='r!search [steam/steamid/rgl] - Finds someones RGL page and team history.', inline=False)
    embed.add_field(name="Runners Only", value='r!move - Move all players back to organizing channels.\nr!randomize [num] - Randomly picks teams of [num] size and moves them to the team channels.\nr!startserver - Starts a serveme.tf reservation to be used for pugs.\nr!map - Change map using on last rcon message.\nr!config - Change config using last rcon message.\nr!check - Lists divs of all players in the organizing channel.', inline=False)
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

@tasks.loop(seconds=60) # task runs every 60 seconds
async def server_status(self):
    print('running task')
    status = requests.get('https://na.serveme.tf/api/reservations?api_key=' + SERVEME_API_KEY, headers={'Content-type': 'application/json'}).json()
    if status["reservations"][0]["status"] == "Ended":
        serverStatus = False
        
    if serverStatus == True:
        logs = requests.get("https://logs.tf/api/v1/log?uploader=76561198171178258").json()
        if timestamp - logs["logs"][0]["date"] < 20000:
            if logs["logs"][0]["id"] != lastLog:
                lastLog = logs["logs"][0]["id"]
                
                logChannel = self.get_channel(996985303220879390)
                await logChannel.send('https://logs.tf/' + str(logs["logs"][0]["id"]))
    
bot.run(DISCORD_TOKEN)