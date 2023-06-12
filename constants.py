"""Constants for the bot."""
import json
import os

if os.path.isfile("./config.json"):
    with open("config.json", encoding="UTF-8") as config:
        config_file = json.load(config)
else:
    with open("example_config.json", encoding="UTF-8") as example_config:
        config_file = json.load(example_config)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or config_file["discord_token"]
NEW_COMMIT_NAME = os.getenv("RAILWAY_GIT_COMMIT_SHA") or "Local Test"
TESTING_GUILDS = config_file["testing_guild_ids"] or None
DB_URL = os.getenv("DB_URL") or config_file["db_connection_string"]
VERSION = os.getenv("BOT_VERSION") or config_file["version"] or "dev"
API_PASSWORD = os.getenv("BOT_API_PASSWORD") or None
PORT = os.getenv("PORT") or 8000
BOT_COLOR = 0xF0984D
