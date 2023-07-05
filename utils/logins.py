import asyncio
import coc
import os
from dotenv import load_dotenv
load_dotenv()


coc_client = coc.Client(key_count=10, key_names="DiscordBot", throttle_limit=25, cache_max_size=50000, load_game_data=coc.LoadGameData(always=True), raw_attribute=True, stats_max_size=10000)
xyz = asyncio.get_event_loop().run_until_complete(coc_client.login(os.getenv("COC_EMAIL"), os.getenv("COC_PASSWORD")))

