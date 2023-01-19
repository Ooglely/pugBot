import discord
from discord.ext import commands, tasks
import json
import random

import os

from rglSearch import rglSearch
from stats import logSearch
from util import get_steam64
from database import get_steam_from_discord
from servers import ServerCog
from webserver import WebserverCog
import asyncio

DISCORD_TOKEN = os.environ["discord_token"]
SERVEME_API_KEY = os.environ["serveme_key"]
NEW_COMMIT_NAME = os.environ["RAILWAY_GIT_COMMIT_SHA"]

version = "v0.9.0"

# Setting initial variables
lastLog = ""
pug_running = False

roles = [
    [" (Scout Restriction)", "999191878736039957"],
    [" (Soldier Restriction)", "999191955831537665"],
    [" (Pyro Restriction)", "999192009090793492"],
    [" (Demo Restriction)", "999192084420509787"],
    [" (Heavy Restriction)", "999192133426749462"],
    [" (Engi Restriction)", "999192179161436250"],
    [" (Sniper Restriction)", "999192234509488209"],
    [" (Spy Restriction)", "999192279870885982"],
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

activity = discord.Activity(name="tf.oog.pw :3", type=discord.ActivityType.watching)
bot = commands.Bot(command_prefix="r!", intents=intents, activity=activity)

bot.remove_command("help")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    await bot.add_cog(ServerCog(bot))
    # await bot.add_cog(WebserverCog(bot))
    # fatkid_check.start()

    startEmbed = discord.Embed(title="Railway: Bot deployed!", color=0xF0984D)
    startEmbed.add_field(name="Latest Commit", value=NEW_COMMIT_NAME, inline=False)
    debug_channel = bot.get_channel(1026985050677465148)
    await debug_channel.send(embed=startEmbed)


@bot.listen("on_message")
async def playerListener(message):
    if message.content.startswith("https://rgl.gg/Public/PlayerProfile.aspx?"):

        rgl = rglSearch(get_steam64(message.content))

        url = "https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(
            get_steam64(message.content)
        )

        if rgl[5] == "":
            embedColor = 0xF0984D
        else:
            embedColor = 0xFF0000

        embed = discord.Embed(title=rgl[0], url=url, color=embedColor)
        embed.set_thumbnail(url=rgl[1])
        if rgl[2] != "":  # Sixes Data
            embed.add_field(name="Sixes", value=rgl[2], inline=False)
        if rgl[3] != "":  # HL Data
            embed.add_field(name="Highlander", value=rgl[3], inline=False)
        if rgl[4] != "":  # PL Data
            embed.add_field(name="Prolander", value=rgl[4], inline=False)
        if rgl[5] != "":  # Ban History
            embed.add_field(name="Ban History", value=rgl[5], inline=False)

        embed.set_footer(text=version)
        await message.channel.send(embed=embed)
        pass


@bot.command()
async def search(ctx, arg: str):

    rgl = rglSearch(get_steam64(arg))

    url = "https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(get_steam64(arg))

    if rgl[5] == "":
        embedColor = 0xF0984D
    else:
        embedColor = 0xFF0000

    embed = discord.Embed(title=rgl[0], url=url, color=embedColor)
    embed.set_thumbnail(url=rgl[1])
    if rgl[2] != "":  # Sixes Data
        embed.add_field(name="Sixes", value=rgl[2], inline=False)
    if rgl[3] != "":  # HL Data
        embed.add_field(name="Highlander", value=rgl[3], inline=False)
    if rgl[4] != "":  # PL Data
        embed.add_field(name="Prolander", value=rgl[4], inline=False)
    if rgl[5] != "":  # Ban History
        embed.add_field(name="Ban History", value=rgl[5], inline=False)

    embed.set_footer(text=version)
    await ctx.send(embed=embed)
    pass


@bot.command()
@commands.has_role("Runners")
async def move(ctx):
    if ctx.channel.id == 996415628007186542:  # HL Channels
        nextPugChannel = bot.get_channel(1009978053528670371)
        team1Channel = bot.get_channel(987171351720771644)
        team2Channel = bot.get_channel(994443542707580951)
        selectingChannel = bot.get_channel(996567486621306880)

        for member in selectingChannel.members:
            await member.move_to(nextPugChannel)

        for member in team1Channel.members:
            await member.move_to(selectingChannel)

        for member in team2Channel.members:
            await member.move_to(selectingChannel)

        await ctx.send("Players moved.")

    if ctx.channel.id == 997602235208962150:  # 6s Channels
        team1Channel = bot.get_channel(997602308525404242)
        team2Channel = bot.get_channel(997602346173464587)
        selectingChannel = bot.get_channel(997602270592118854)

        for member in team1Channel.members:
            await member.move_to(selectingChannel)

        for member in team2Channel.members:
            await member.move_to(selectingChannel)

        await ctx.send("Players moved.")


@bot.command()
@commands.has_role("Runners")
async def randomize(ctx, num: int):
    team1Players = 0
    team2Players = 0
    if ctx.channel.id == 996415628007186542:  # HL Channels
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

    if ctx.channel.id == 997602235208962150:  # 6s Channels
        players = []
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
async def help(ctx):
    embed = discord.Embed(title="pugBot", color=0xF0984D)
    embed.set_thumbnail(url="https://b.catgirlsare.sexy/XoBJQn439QgJ.jpeg")
    embed.add_field(
        name="Commands",
        value="r!search [steam/steamid/rgl] - Finds someones RGL page and team history.",
        inline=False,
    )
    embed.add_field(
        name="Runners Only",
        value="r!move - Move all players back to organizing channels.\nr!randomize [num] - Randomly picks teams of [num] size and moves them to the team channels.\nr!startserver - Starts a serveme.tf reservation to be used for pugs.\nr!map - Change map using on last rcon message.\nr!config - Change config using last rcon message.\nr!check - Lists divs of all players in the organizing channel.\nr!randommap - Change to a random map based on the gamemode.",
        inline=False,
    )
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

    embed = discord.Embed(title="Player Check", color=0xF0984D)
    embed.add_field(name="NC/AM Players", value=ncPlayers, inline=False)
    embed.add_field(name="AM+ Players", value=plusPlayers, inline=False)
    embed.set_footer(text=version)
    await ctx.send(embed=embed)


@bot.command()
async def stats(ctx, *args):
    print(args)
    if args == ():
        id = get_steam_from_discord(ctx.author.id)
    else:
        id = get_steam64(args[0])

    if id == None:
        await ctx.send(
            "Unable to find player. Either register with the bot at <#1026980468807184385> or specify a steam ID in the command."
        )
        return

    wait = await ctx.send("Give me a moment, grabbing all logs...")
    print(f"ID: {id}")
    info = rglSearch(int(id))
    logString = f"```\n{info[0]}'s pug stats"

    logString += "\n  Class |  K  |  D  | DPM | Logs"
    stats = await logSearch(int(id))
    for i in stats:
        if i[1] != 0:
            dpm = f"{i[3] / (i[4] / 60):.1f}"
            logString += f"\n{i[0]: >8}|{i[1]: >5}|{i[2]: >5}|{dpm: >5}|{i[5]: >5}"
    logString += "```"
    await wait.delete()
    await ctx.send(logString)


# bot.run(DISCORD_TOKEN)
bot.run("OTk5ODM0NzEyNDA1MjAwOTA2.G9Qd1b.T-JiOb-mf2n_uU3yuqSpMwMkLlp_N-CHbYOLYQ")
