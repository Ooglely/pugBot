import discord
from discord.ext import commands, tasks
import requests
import json
import random
import string
from rcon.source import Client
import time as unixtime
import asyncio

with open("config.json") as config_file:
    CONFIG = json.load(config_file)

SERVEME_API_KEY = CONFIG["serveme"]["api_key"]

class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @commands.has_role('Runners')
    async def test(self, ctx):
        await ctx.send("Starting server...")
    
    @tasks.loop(seconds=5, count=None) # task runs every 30 seconds
    async def match_status(self):
        sixes_team_1 = self.bot.get_channel(997602308525404242)
        sixes_team_2 = self.bot.get_channel(997602346173464587)
        hl_team_1 = self.bot.get_channel(987171351720771644)
        hl_team_2 = self.bot.get_channel(994443542707580951)
        if pug_running == False:
            if len(sixes_team_1.members) >= 6 and len(sixes_team_2.members) >= 6:
                print('Pug has been detected as running.')
                pug_running = True
            elif len(hl_team_1.members) >= 9 and len(hl_team_2.members) >= 9:
                print('Pug has been detected as running.')
                pug_running = True
        elif pug_running:
            if len(sixes_team_1.members) <= 4 and len(sixes_team_2.members) <= 4:
                print('Pug has been detected as finished.')
                pug_running = False
            elif len(hl_team_1.members) <= 6 and len(hl_team_2.members) <= 6:
                print('Pug has been detected as finished.')
                pug_running = False
    
    @match_status.before_loop
    async def server_status_wait(self):
        await self.bot.wait_until_ready()
        
        
async def setup(bot):
	await bot.add_cog(MatchCog(bot))