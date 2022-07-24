import discord
from discord.ext import commands, tasks
import requests
import json
import random
import string
from rcon.source import Client
import time as unixtime

version = "v0.4.3"
timestamp = unixtime.time()
lastLog = 0

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
                "custom_whitelist_id": None,
                "auto_end": True
            }}

        reserveJSON = json.dumps(reserveString)

        sendReservation = requests.post('https://na.serveme.tf/api/reservations?api_key=' + SERVEME_API_KEY, data=reserveJSON, headers=headers)
        server = sendReservation.json()

        connect = 'connect ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; password "' + server['reservation']['password'] + '"'
        rcon = 'rcon_address ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; rcon_password "' + server['reservation']['rcon'] + '"'
        
        embed=discord.Embed(title='Server started!', color=0xf0984d)
        embed.add_field(name="Server", value=server['reservation']['server']['name'], inline=False)
        embed.add_field(name="Connect", value=connect, inline=False)
        embed.add_field(name="RCON", value='RCON has been sent in the rcon channel.', inline=False)
        embed.set_footer(text=version)
        await ctx.send(embed=embed)
        
        channel = self.bot.get_channel(1000161175859900546)
        await channel.send(rcon)
        
        channel = self.bot.get_channel(996980099486322798)
        await channel.send(connect)
        
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
        
        with Client(str(ip), int(port), passwd=password) as client:
            response = client.run('changelevel', map)

        print(response)
        
        await ctx.send("Changing map to " + map + ".")
    
    @tasks.loop(seconds=60) # task runs every 60 seconds
    async def server_status(self):
        with open("logs.json") as log_file:
            LOGS = json.load(log_file)
        lastLog = LOGS["lastLog"]
            
        status = requests.get('https://na.serveme.tf/api/reservations?api_key=' + SERVEME_API_KEY, headers={'Content-type': 'application/json'}).json()
        if status["reservations"][0]["status"] == "Ended":
            print('Server not up.')
        else:
            logs = requests.get("https://logs.tf/api/v1/log?uploader=76561198171178258").json()
            if timestamp - logs["logs"][0]["date"] < 20000:
                if logs["logs"][0]["id"] != lastLog:
                    newLog = {"lastLog": logs["logs"][0]["id"]}
                    with open("logs.json", "w") as outfile:
                        json.dump(newLog, outfile)
                    
                    logChannel = self.bot.get_channel(996985303220879390)
                    await logChannel.send('https://logs.tf/' + str(logs["logs"][0]["id"]))
    
    @server_status.before_loop
    async def server_status_wait(self):
        print('waiting...')
        await self.bot.wait_until_ready()