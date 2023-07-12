import websockets
import orjson
import os

from dotenv import load_dotenv
from pymitter import EventEmitter
from pymongo import InsertOne
from datetime import datetime
load_dotenv()

player_ee = EventEmitter()
clan_ee = EventEmitter()
war_ee = EventEmitter()

WEBSOCKET_IP = os.getenv("WEBSOCKET_IP")
NEW_WEBSOCKET_IP = os.getenv("NEW_WEBSOCKET_IP")
WEBSOCKET_USER = os.getenv("WEBSOCKET_USER")
WEBSOCKET_PW = os.getenv("WEBSOCKET_PW")
import os
import pytz
import motor.motor_asyncio
looper_db = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
new_looper = looper_db.get_database("new_looper")
bot_stats= looper_db.clashking.bot_stats

async def player_websocket():
    player_changes = []
    while True:
        try:
            async with websockets.connect(f"ws://{WEBSOCKET_IP}/players?token=5", ping_timeout=None, ping_interval=None, open_timeout=None, max_queue=5000000) as websocket:
                async for message in websocket:
                    if "Login!" in str(message) or "decoded token" in str(message):
                        print(message)
                    else:
                        try:
                            json_message = orjson.loads(message)
                            field = json_message["type"]
                            time = json_message.get("time")
                            awaitable = player_ee.emit_async(field, json_message)
                            await awaitable
                            player_changes.append(InsertOne({"field" : field, "time_sent": time, "time_dealt" : int(datetime.now(tz=pytz.utc).timestamp())}))
                            if len(player_changes) >= 250:
                                await bot_stats.bulk_write(player_changes)
                                player_changes = []
                        except:
                            pass
        except Exception as e:
            print(e)
            #sentry_sdk.capture_exception(e)
            continue


async def war_websocket():
    while True:
        try:
            async with websockets.connect(f"ws://{NEW_WEBSOCKET_IP}/wars?token=5", ping_timeout=None, ping_interval=None, open_timeout=None, max_queue=10000) as websocket:
                async for message in websocket:
                    if "Login!" in str(message) or "decoded token" in str(message):
                        print(message)
                    else:
                        try:
                            json_message = orjson.loads(message)
                            field = json_message["type"]
                            awaitable = war_ee.emit_async(field, json_message)
                            await awaitable
                        except:
                            pass
        except Exception as e:
            #sentry_sdk.capture_exception(e)
            continue


async def clan_websocket():
    clan_changes = []
    while True:
        try:
            async with websockets.connect(f"ws://{NEW_WEBSOCKET_IP}/clans?token=5", ping_timeout=None, ping_interval=None, open_timeout=None, max_queue=10000) as websocket:
                async for message in websocket:
                    if "Login!" in str(message) or "decoded token" in str(message):
                        print(message)
                    else:
                        try:
                            json_message = orjson.loads(message)
                            field = json_message["type"]
                            time = json_message.get("time")
                            awaitable = clan_ee.emit_async(field, json_message)
                            await awaitable
                            clan_changes.append(InsertOne({"field": field, "time_sent": time, "time_dealt": int(datetime.now(tz=pytz.utc).timestamp())}))
                            if len(clan_changes) >= 250:
                                await bot_stats.bulk_write(clan_changes)
                                clan_changes = []
                        except:
                            pass

        except Exception as e:
            #sentry_sdk.capture_exception(e)
            print(e)
            continue