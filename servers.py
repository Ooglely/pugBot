from multiprocessing.connection import wait
import discord
from discord.ext import commands, tasks
import requests
import json
import random
import string
from rcon.source import Client
import time as unixtime
import asyncio

version = "v0.8.1"
timestamp = unixtime.time()
lastLog = 0

hl_maps = [
    ['koth_product', 'koth_product_final'],
    ['pl_upward', 'pl_upward_f10'],
    ['koth_lakeside', 'koth_lakeside_r2'],
    ['pl_swiftwater', 'pl_swiftwater_final1'],
    ['koth_ashville', 'koth_ashville_final'],
    ['pl_vigil', 'pl_vigil_rc9'],
    ['cp_steel', 'cp_steel_f12'],
    ['koth_proot', 'koth_proot_b4b']
]

sixes_maps = [
    ['cp_gullywash', 'cp_gullywash_f9'],
    ['koth_bagel', 'koth_bagel_rc5'],
    ['cp_metalworks', 'cp_metalworks_f4'],
    ['cp_snakewater', 'cp_snakewater_final1'],
    ['koth_product', 'koth_product_final'],
    ['cp_process', 'cp_process_f11'],
    ['koth_clearcut', 'koth_clearcut_b15d'],
    ['cp_granary', 'cp_granary_pro_rc8'], 
    ['cp_badlands', 'cp_prolands_rc2ta'],
    ['cp_reckoner', 'cp_reckoner_rc6']
]

kothmaps = ['koth_product_final', 'koth_proot_b4b', 'koth_ashville_rc2d', 'koth_cascade']

with open("config.json") as config_file:
    CONFIG = json.load(config_file)

SERVEME_API_KEY = CONFIG["serveme"]["api_key"]

class ServerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_status.start()
    
    @commands.command()
    @commands.has_role('Runners')
    async def startserver(self, ctx):
        headers = {'Content-type': 'application/json'}
        new = requests.get('https://na.serveme.tf/api/reservations/new?api_key=' + SERVEME_API_KEY, headers=headers)
        times = new.text

        headers = {'Content-type': 'application/json'}
        find_servers = requests.post('https://na.serveme.tf/api/reservations/find_servers?api_key=' + SERVEME_API_KEY, data=times, headers=headers)

        for server in find_servers.json()['servers']:
            if "chi" in server['ip']:
                if 536 != server['id']:
                    print(server)
                    reserve = server
                    break

        connectPassword = 'andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        rconPassword = 'rcon.andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=20))
        
        if ctx.channel.id == 996415628007186542: # HL Channels
            map = random.choice(kothmaps)
        
        elif ctx.channel.id == 997602235208962150: # 6s Channels
            map = random.choice(sixes_maps)[1]
            
        else:
            map = 'koth_product_final'

        reserveString = {
            "reservation": {
                "starts_at": new.json()['reservation']['starts_at'], 
                "ends_at": new.json()['reservation']['ends_at'], 
                "rcon": rconPassword, 
                "password": connectPassword,
                "server_id": reserve['id'],
                "enable_plugins": True,
                "enable_demos_tf": True,
                "first_map": map,
                "server_config_id": 54,
                "whitelist_id": 22,
                "custom_whitelist_id": None,
                "auto_end": True
            }}

        reserveJSON = json.dumps(reserveString)

        sendReservation = requests.post('https://na.serveme.tf/api/reservations?api_key=' + SERVEME_API_KEY, data=reserveJSON, headers=headers)
        server = sendReservation.json()

        connect = 'connect ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; password "' + server['reservation']['password'] + '"'
        rcon = 'rcon_address ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; rcon_password "' + server['reservation']['rcon'] + '"'
        connectLink = 'steam://connect/' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '/' + server['reservation']['password']
        
        embed=discord.Embed(title='Server started!', color=0xf0984d)
        embed.add_field(name="Server", value=server['reservation']['server']['name'], inline=False)
        embed.add_field(name="Connect", value=connect, inline=False)
        embed.add_field(name="RCON", value='RCON has been sent in the rcon channel.', inline=False)
        embed.add_field(name="Map", value=map, inline=False)
        embed.set_footer(text=version)
        await ctx.send(embed=embed)
        
        # RCON Message
        channel = self.bot.get_channel(1000161175859900546)
        await channel.send(rcon)
        
        # Connect Message
        channel = self.bot.get_channel(996980099486322798)
        connectEmbed=discord.Embed(title = connectLink, color = 0x3dff1f)
        connectEmbed.add_field(name="Command", value=connect, inline=False)
        await channel.send(embed=connectEmbed)
        
    @commands.command()
    @commands.has_role('Runners')
    async def config(self, ctx, config: str):
        channel = self.bot.get_channel(1000161175859900546)
        rconMessage = await channel.fetch_message(channel.last_message_id)
        rconCommand = rconMessage.content
        
        ip = rconCommand.split(' ')[1].split(':')[0]
        port = rconCommand.split(' ')[1].split(':')[1].split(';')[0]
        password = rconCommand.split(' ')[3].split('"')[1]
        
        with Client(str(ip), int(port), passwd=password) as client:
            response = client.run('exec', config)

        print(response)
        
        await ctx.send("Config executed.")

    @commands.command()
    @commands.has_role('Runners')
    async def map(self, ctx, map: str):
        channel = self.bot.get_channel(1000161175859900546)
        rconMessage = await channel.fetch_message(channel.last_message_id)
        rconCommand = rconMessage.content
        
        ip = rconCommand.split(' ')[1].split(':')[0]
        port = rconCommand.split(' ')[1].split(':')[1].split(';')[0]
        password = rconCommand.split(' ')[3].split('"')[1]
        
        if ctx.channel.id == 996415628007186542: # HL Channels
            for hlmap in hl_maps:
                if map == hlmap[0]:
                    map = hlmap[1]
                    break
            if map.startswith('cp_'):
                config = 'rgl_HL_stopwatch'
            elif map.startswith('koth_'):
                config = 'rgl_HL_koth_bo5'
            elif map.startswith('pl_'):
                config = 'rgl_HL_stopwatch'
            whitelist_command = 'tftrue_whitelist_id 13297'
        
        elif ctx.channel.id == 997602235208962150: # 6s Channels
            for sixesmap in sixes_maps:
                if map == sixesmap[0]:
                    map = sixesmap[1]
                    break
            if map.startswith('cp_'):
                config = 'rgl_6s_5cp_scrim'
            elif map.startswith('koth_'):
                config = 'rgl_6s_koth_bo5'
            whitelist_command = 'tftrue_whitelist_id 12241'
        
        command = 'exec ' + config + '; changelevel ' + map
            
        with Client(str(ip), int(port), passwd=password) as client:
            client.run(command)
            await ctx.send("Changing config to " + config + ".")
            await ctx.send("Changing map to " + map + ".")
        
        with Client(str(ip), int(port), passwd=password) as client:
            await asyncio.sleep(10)
            client.run(whitelist_command)

        if map.startswith('pl_'):
            await asyncio.sleep(20)
            with Client(str(ip), int(port), passwd=password) as client:
                client.run(command)
                await ctx.send("Reloading map to ensure config executed.")

    @commands.command()
    @commands.has_role('Runners')
    async def randommap(self, ctx):
        channel = self.bot.get_channel(1000161175859900546)
        rconMessage = await channel.fetch_message(channel.last_message_id)
        rconCommand = rconMessage.content
        
        ip = rconCommand.split(' ')[1].split(':')[0]
        port = rconCommand.split(' ')[1].split(':')[1].split(';')[0]
        password = rconCommand.split(' ')[3].split('"')[1]
        
        if ctx.channel.id == 996415628007186542: # HL Channels
            map = random.choice(hl_maps)[1]
            if map.startswith('cp_'):
                config = 'rgl_HL_stopwatch'
            elif map.startswith('koth_'):
                config = 'rgl_HL_koth_bo5'
            elif map.startswith('pl_'):
                config = 'rgl_HL_stopwatch'
        
        elif ctx.channel.id == 997602235208962150: # 6s Channels
            map = random.choice(sixes_maps)[1]
            if map.startswith('cp_'):
                config = 'rgl_6s_5cp_scrim'
            elif map.startswith('koth_'):
                config = 'rgl_6s_koth_bo5'
                
        command = 'exec ' + config + '; changelevel ' + map
            
        with Client(str(ip), int(port), passwd=password) as client:
            client.run(command)
            await ctx.send("Changing config to " + config + ".")
            await ctx.send("Changing map to " + map + ".")
        
        if map.startswith('pl_'):
            await asyncio.sleep(20)
            with Client(str(ip), int(port), passwd=password) as client:
                client.run(command)
                await ctx.send("Reloading map to ensure config executed.")

    @tasks.loop(seconds=30, count=None) # task runs every 30 seconds
    async def server_status(self):
        players = []
        guild = self.bot.get_guild(952817189893865482)
        for channel in guild.voice_channels:
            for member in channel.members:
                players.append(member.id)
        
        if len(players) > 8:
            with open("logs.json") as log_file:
                LOGS = json.load(log_file)
            lastLog = LOGS["lastLog"]
                
            status = requests.get('https://na.serveme.tf/api/reservations?api_key=' + SERVEME_API_KEY, headers={'Content-type': 'application/json'}).json()
            logs = requests.get("https://logs.tf/api/v1/log?uploader=76561198171178258").json()
            if str(status['reservations'][0]['id']) in logs["logs"][0]["title"]:
                if logs["logs"][0]["id"] != lastLog:
                    newLog = {"lastLog": logs["logs"][0]["id"]}
                    with open("logs.json", "w") as outfile:
                        json.dump(newLog, outfile)
                    
                    logChannel = self.bot.get_channel(996985303220879390)
                    await logChannel.send('https://logs.tf/' + str(logs["logs"][0]["id"]))
    
    @server_status.before_loop
    async def server_status_wait(self):
        await self.bot.wait_until_ready()
        
async def setup(bot):
	await bot.add_cog(ServerCog(bot))