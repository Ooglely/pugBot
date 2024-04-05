import asyncio
from logs.searcher import PartialLog, FullLog
from database import BotCollection
from logs import Player
from logs.logstf_api import LogsAPI
from pug import PugCategory, CategoryButton, CategorySelect
from util import get_steam64


log_data_db = BotCollection("logs", "data")
log_list_db = BotCollection("logs", "list")
guild_settings_db = BotCollection("guilds", "config")
guild_categories_db = BotCollection("guilds", "categories")

async def parse_log(log: FullLog):
    print(log.log.__dict__)
    print(log.log.red_team.__dict__)
    print(log.log.players[0].__dict__)
    
    
async def _get_log():
    logs = await log_list_db.find_all_items()
    for log in logs:
        print(log)
        break
    
    logstf_id = logs[0]["log_id"]
    guild_id = logs[0]["guild"]
    category_name = logs[0]["category"]["name"]
    category_data = logs[0]["category"]
    timestamp = logs[0]["timestamp"]
    
    players: list[Player] = []
    log = await LogsAPI.get_single_log(logstf_id)
    for player in log["players"]:
        print(player)
        log_player = Player(steam=get_steam64(player))
        await log_player.link_player()
        players.append(log_player)

    # Need the category that the log was played in
    result = await guild_categories_db.find_item({"_id": guild_id})

    chosen_category: PugCategory = PugCategory(
        category_name, category_data
    )

    full_log = FullLog(
        PartialLog(
            guild_id,
            chosen_category,
            players,
            timestamp,
        ),
        logstf_id,
        log,
    )
    await parse_log(full_log)


    
if __name__ == "__main__":
    asyncio.run(_get_log())
    