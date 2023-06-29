import asyncio
import coc
import motor.motor_asyncio
import os
from coc.ext import discordlinks
from coc.ext.fullwarapi import FullWarClient
from coc.ext import fullwarapi
from dotenv import load_dotenv
load_dotenv()


coc_client = coc.EventsClient(key_count=10, key_names="DiscordBot", throttle_limit=25, cache_max_size=50000, load_game_data=coc.LoadGameData(always=True), raw_attribute=True, stats_max_size=10000)
xyz = asyncio.get_event_loop().run_until_complete(coc_client.login(os.getenv("COC_EMAIL"), os.getenv("COC_PASSWORD")))

