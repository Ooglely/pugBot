import json
import os

with open("config.json") as json_file:
    config_file = json.load(json_file)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or config_file["discord_token"]
NEW_COMMIT_NAME = os.getenv("RAILWAY_GIT_COMMIT_SHA") or "Local Test"
TESTING_GUILDS = config_file["testing_guild_ids"] or None
DB_URL = os.getenv("DB_URL") or config_file["db_connection_string"]
VERSION = config_file["version"] or "dev"
