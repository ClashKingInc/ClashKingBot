import asyncio
import coc
import motor.motor_asyncio
import os
from coc.ext import discordlinks
from coc.ext.fullwarapi import FullWarClient
from coc.ext import fullwarapi
from dotenv import load_dotenv
load_dotenv()


looper_db = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
link_client: coc.ext.discordlinks.DiscordLinkClient = asyncio.get_event_loop().run_until_complete(discordlinks.login(os.getenv("LINK_API_USER"), os.getenv("LINK_API_PW")))
coc_client = coc.EventsClient(key_count=10, key_names="DiscordBot", throttle_limit=25, cache_max_size=50000, load_game_data=coc.LoadGameData(always=True), raw_attribute=True, stats_max_size=10000)
xyz = asyncio.get_event_loop().run_until_complete(coc_client.login(os.getenv("COC_EMAIL"), os.getenv("COC_PASSWORD")))

war_client: FullWarClient = asyncio.get_event_loop().run_until_complete(fullwarapi.login(username=os.getenv("FW_USER"), password=os.getenv("FW_PW"), coc_client=  coc_client))
