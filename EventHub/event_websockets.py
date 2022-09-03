from pymitter import EventEmitter
import websockets
import aiohttp
import orjson
import os

player_ee = EventEmitter()
clan_ee = EventEmitter()
war_ee = EventEmitter()

WEBSOCKET_URL = os.getenv("WEBSOCKET_URL")
WEBSOCKET_USER = os.getenv("WEBSOCKET_USER")
WEBSOCKET_PW = os.getenv("WEBSOCKET_PW")

async def player_websocket():
    while True:
        try:
            url = f"{WEBSOCKET_URL}/login"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"username": f"{WEBSOCKET_USER}", "password": f"{WEBSOCKET_PW}"}) as response:
                    token = await response.json()
                    token = token["access_token"]
                await session.close()
            async with websockets.connect(f"ws://{WEBSOCKET_URL}/players?token={token}", ping_timeout=None, ping_interval=None, open_timeout=None) as websocket:
                async for message in websocket:
                    if "Login!" in str(message) or "decoded token" in str(message):
                        print(message)
                    else:
                        json_message = orjson.loads(message)
                        field = json_message["type"]
                        awaitable = player_ee.emit_async(field, json_message)
                        await awaitable
        except Exception as e:
            print(e)
            continue


async def war_websocket():
    while True:
        try:
            url = f"{WEBSOCKET_URL}/login"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"username": f"{WEBSOCKET_USER}", "password": f"{WEBSOCKET_PW}"}) as response:
                    token = await response.json()
                    token = token["access_token"]
                await session.close()
            async with websockets.connect(f"ws://{WEBSOCKET_URL}/wars?token={token}", ping_timeout=None, ping_interval=None, open_timeout=None) as websocket:
                async for message in websocket:
                    if "Login!" in str(message) or "decoded token" in str(message):
                        print(message)
                    else:
                        json_message = orjson.loads(message)
                        field = json_message["type"]
                        awaitable = war_ee.emit_async(field, json_message)
                        await awaitable
        except Exception as e:
            print(e)
            continue


async def clan_websocket():
    while True:
        try:
            url = f"{WEBSOCKET_URL}/login"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"username" : f"{WEBSOCKET_USER}", "password" : f"{WEBSOCKET_PW}"}) as response:
                    token = await response.json()
                    token = token["access_token"]

            async with websockets.connect(f"ws://{WEBSOCKET_URL}/clans?token={token}", ping_timeout=None, ping_interval=None, open_timeout=None) as websocket:
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
            print(e)
            continue