import nextcord
from nextcord.ext import commands, tasks
import os
import json

with open("config.json") as json_file:
    config_file = json.load(json_file)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or config_file["discord_token"]
SERVEME_API_KEY = os.getenv("SERVEME_API_KEY") or config_file["serveme_api_key"]
NEW_COMMIT_NAME = os.getenv("RAILWAY_GIT_COMMIT_SHA") or "Local Test"

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.voice_states = True

activity = nextcord.Activity(name="tf.oog.pw :3", type=nextcord.ActivityType.watching)
bot = commands.Bot(command_prefix="r!", intents=intents, activity=activity)

bot.remove_command("help")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

    startEmbed = nextcord.Embed(title="Rewrite: Bot deployed!", color=0xF0984D)
    startEmbed.add_field(name="Latest Commit", value=NEW_COMMIT_NAME, inline=False)
    debug_channel = bot.get_channel(1026985050677465148)
    await debug_channel.send(embed=startEmbed)


bot.run(DISCORD_TOKEN)
