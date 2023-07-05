import websockets
import aiohttp
import orjson
import os

from dotenv import load_dotenv
from pymitter import EventEmitter
from pymongo import InsertOne
load_dotenv()

player_ee = EventEmitter()
clan_ee = EventEmitter()
war_ee = EventEmitter()

WEBSOCKET_IP = os.getenv("WEBSOCKET_IP")
NEW_WEBSOCKET_IP = os.getenv("NEW_WEBSOCKET_IP")
WEBSOCKET_USER = os.getenv("WEBSOCKET_USER")
WEBSOCKET_PW = os.getenv("WEBSOCKET_PW")


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
                            awaitable = player_ee.emit_async(field, json_message)
                            await awaitable
                        except:
                            pass
        except Exception as e:
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
                        json_message = orjson.loads(message)
                        field = json_message["type"]
                        awaitable = war_ee.emit_async(field, json_message)
                        await awaitable
        except Exception as e:
            #sentry_sdk.capture_exception(e)
            continue


async def clan_websocket():
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
                            awaitable = clan_ee.emit_async(field, json_message)
                            await awaitable
                        except:
                            pass

        except Exception as e:
            #sentry_sdk.capture_exception(e)
            continue