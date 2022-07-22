import discord
from discord.ext import commands
from steam import steamid
from steam.steamid import SteamID
import scrapy
from scrapy.crawler import CrawlerProcess
import json
import os
import sys
import random
import string
import requests

version = "v0.4.0 | by oog"

description = '''An example bot to showcase the discord.ext.commands extension
module.
There are a number of utility commands being showcased here.'''

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.presences = True

activity = discord.Activity(name='over my pugs ^_^', type=discord.ActivityType.watching)
bot = commands.Bot(command_prefix='r!', description=description, intents=intents, activity = activity)

class PlayerSpider(scrapy.Spider):
    name = "PlayerSpider"
    
    def __init__(self, input = None):
        self.input = input  # source file name

    def start_requests(self):
        url = 'https://rgl.gg/Public/PlayerProfile.aspx?p=' + self.input
        yield scrapy.Request(url=url, callback=self.parse)
        
    def parse(self, response):
        for player in response.css('body'):
            yield {
                'name': response.xpath("//*[@id='ContentPlaceHolder1_ContentPlaceHolder1_ContentPlaceHolder1_lblPlayerName']/descendant-or-self::*/text()").get(),
                'pfp': player.css("img#ContentPlaceHolder1_ContentPlaceHolder1_ContentPlaceHolder1_imgProfileImage").xpath("@src").get(),
                'seasons': player.css("tr > td > a::text").getall()
            }
    
process = CrawlerProcess(settings={'FEED_FORMAT': 'json', 'FEED_URI': 'output.json'})

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    
@bot.listen('on_message')
async def playerListener(message):
    if message.content.startswith('https://rgl.gg/Public/PlayerProfile.aspx?'):
        args = message.content.split('=')
        id = args[1].replace('&r', '')
        process.crawl(PlayerSpider, input = str(id))
        if "twisted.internet.reactor" in sys.modules:
            del sys.modules["twisted.internet.reactor"]
        process.start()
        
        f = open('output.json')
        data = json.load(f)
        
        number = 0
        seasons = []
        for count, i in enumerate(data[0]['seasons']):
            if i.strip() == "":
                del data[0]['seasons'][count]
                
        for count, i in enumerate(data[0]["seasons"]):
            if count == number:
                res = i.strip()
                seasons.append([data[0]["seasons"][count].strip(), data[0]["seasons"][count + 1].strip(), data[0]["seasons"][count + 2].strip()])
                number += 3

        sixes = ""
        hl = ""
        pl = ""
        for i in seasons:
            if i[0].startswith("Sixes S"):
                sixes += i[0] + " - " + i[1] + " - " + i[2] + "\n"
            if i[0].startswith("HL Season"):
                hl += i[0] + " - " + i[1] + " - " + i[2] + "\n"
            if i[0].startswith("P7 Season"):
                pl += i[0] + " - " + i[1] + " - " + i[2] + "\n"

        
        url = 'https://rgl.gg/Public/PlayerProfile.aspx?p=' + str(id)
        
        embed=discord.Embed(title=data[0]['name'], url = url, color=0xf0984d)
        embed.set_thumbnail(url=data[0]['pfp'])
        if sixes != "":
            embed.add_field(name="Sixes", value=sixes, inline=False)
        if hl != "":
            embed.add_field(name="Highlander", value=hl, inline=False)
        if pl != "":
            embed.add_field(name="Prolander", value=pl, inline=False)
        embed.set_footer(text=version)
        await message.channel.send(embed=embed)
        open('output.json', 'w').close()
        pass

@bot.command()
async def add(ctx, left: int, right: int):
    """Adds two numbers together."""
    await ctx.send(left + right)

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
    process.crawl(PlayerSpider, input = str(id))
    if "twisted.internet.reactor" in sys.modules:
        del sys.modules["twisted.internet.reactor"]
    process.start()
    
    f = open('output.json')
    data = json.load(f)
    
    number = 0
    seasons = []
    for count, i in enumerate(data[0]['seasons']):
        if i.strip() == "":
            del data[0]['seasons'][count]
            
    for count, i in enumerate(data[0]["seasons"]):
        if count == number:
            res = i.strip()
            seasons.append([data[0]["seasons"][count].strip(), data[0]["seasons"][count + 1].strip(), data[0]["seasons"][count + 2].strip()])
            number += 3

    sixes = ""
    hl = ""
    pl = ""
    for i in seasons:
        if i[0].startswith("Sixes S"):
            sixes += i[0] + " - " + i[1] + " - " + i[2] + "\n"
        if i[0].startswith("HL Season"):
            hl += i[0] + " - " + i[1] + " - " + i[2] + "\n"
        if i[0].startswith("P7 Season"):
            pl += i[0] + " - " + i[1] + " - " + i[2] + "\n"

    
    url = 'https://rgl.gg/Public/PlayerProfile.aspx?p=' + str(id)
    
    embed=discord.Embed(title=data[0]['name'], url = url, color=0xf0984d)
    embed.set_thumbnail(url=data[0]['pfp'])
    if sixes != "":
        embed.add_field(name="Sixes", value=sixes, inline=False)
    if hl != "":
        embed.add_field(name="Highlander", value=hl, inline=False)
    if pl != "":
        embed.add_field(name="Prolander", value=pl, inline=False)
    embed.set_footer(text=version)
    await ctx.send(embed=embed)
    open('output.json', 'w').close()
    pass

@bot.command()
@commands.has_role('pug runners')
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
@commands.has_role('pug runners')
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
@commands.has_role('pug runners')
async def startserver(ctx):
    headers = {'Content-type': 'application/json'}
    stepOne = requests.get('https://na.serveme.tf/api/reservations/new?api_key=da8501910f804b4abebdfe8e8e048c2c', headers=headers)
    times = stepOne.text

    headers = {'Content-type': 'application/json'}
    stepTwo = requests.post('https://na.serveme.tf/api/reservations/find_servers?api_key=da8501910f804b4abebdfe8e8e048c2c', data=times, headers=headers)

    for server in stepTwo.json()['servers']:
        if "chi" in server['ip']:
            print(server)
            reserve = server
            break

    connectPassword = 'andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    rconPassword = 'rcon.andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=20))

    reserveString = {"reservation": {"starts_at": stepOne.json()['reservation']['starts_at'], "ends_at": stepOne.json()['reservation']['ends_at'], "rcon": rconPassword, "password": connectPassword, "server_id": reserve['id']}}

    reserveJSON = json.dumps(reserveString)

    stepThree = requests.post('https://na.serveme.tf/api/reservations?api_key=da8501910f804b4abebdfe8e8e048c2c', data=reserveJSON, headers=headers)
    server = stepThree.json()

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
    
bot.run('OTg5MjUwMTQ0ODk1NjU1OTY2.G0x6ss.ZYt-cfz_wVzXO6MZJbfAodStbBvrl3JDVU9_Rs')