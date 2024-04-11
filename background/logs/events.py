import asyncio

import disnake
import ujson
import orjson
import websockets

from classes.config import Config
from pymitter import EventEmitter
from loguru import logger

config = Config()
player_ee = EventEmitter()
clan_ee = EventEmitter()
war_ee = EventEmitter()
raid_ee = EventEmitter()
reminder_ee = EventEmitter()
reddit_ee = EventEmitter()


async def kafka_events(bot):
    await bot.wait_until_ready()
    await asyncio.sleep(120)
    count = 0
    while True:
        try:
            async with websockets.connect(f"ws://85.10.200.219:8001/events", ping_timeout=None, ping_interval=None, open_timeout=None, max_queue=500_000) as websocket:
                async for message in websocket:
                    #every 1000 events, update which clans we get events for
                    if count % 1000 == 0:
                        clans = await bot.clan_db.distinct("tag", filter={"server" : {"$in" : [g.id for g in bot.guilds]}})
                        await websocket.send(ujson.dumps({"clans" : clans}).encode("utf-8"))
                    count += 1

                    if "Login!" in str(message):
                        logger.info(message)
                    else:
                        try:
                            json_message = orjson.loads(message)
                            topic = json_message.get("topic")
                            value = json_message.get("value")

                            if (f := value.get("type")) is not None:
                                fields = [f]
                            else:
                                fields = value.get("types", [])

                            for field in fields:
                                value["trigger"] = field
                                awaitable = None
                                if topic == "player":
                                    awaitable = player_ee.emit_async(field, value)
                                elif topic == "war":
                                    awaitable = war_ee.emit_async(field, value)
                                if topic == "clan":
                                    awaitable = clan_ee.emit_async(field, value)
                                elif topic == "capital":
                                    awaitable = raid_ee.emit_async(field, value)
                                elif topic == "reminder":
                                    awaitable = reminder_ee.emit_async(field, value)
                                elif topic == "reddit":
                                    awaitable = reddit_ee.emit_async(field, value)
                                if awaitable is not None:
                                    await awaitable
                        except Exception:
                            pass
        except Exception as e:
            continue


