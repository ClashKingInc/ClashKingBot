import coc
import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
import motor.motor_asyncio

coc_client = coc.Client(key_count=10, key_names="DiscordBot", throttle_limit=25, cache_max_size=50000,
                        load_game_data=coc.LoadGameData(always=False), raw_attribute=True, stats_max_size=10000)
asyncio.get_event_loop().run_until_complete(coc_client.login(os.getenv("COC_EMAIL"), os.getenv("COC_PASSWORD")))

db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
player_search = db_client.usafam.player_search