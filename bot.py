import discord
from discord.ext import commands
from steam import steamid
from steam.steamid import SteamID
import scrapy
from scrapy.crawler import CrawlerProcess
import json
import os
import sys

description = '''An example bot to showcase the discord.ext.commands extension
module.
There are a number of utility commands being showcased here.'''

intents = discord.Intents.default()
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix='r!', description=description, intents=intents)

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
        embed.set_footer(text="v0.2")
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
    embed.set_footer(text="v0.2")
    await ctx.send(embed=embed)
    open('output.json', 'w').close()
    pass

bot.run('OTg5MjUwMTQ0ODk1NjU1OTY2.G0x6ss.ZYt-cfz_wVzXO6MZJbfAodStbBvrl3JDVU9_Rs')