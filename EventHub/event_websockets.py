from pymitter import EventEmitter
import asyncio
import websockets
import aiohttp
import orjson

player_ee = EventEmitter()
clan_ee = EventEmitter()

async def player_websocket():
    url = "http://127.0.0.1:8000/login"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"username" : "admin", "password" : "test"}) as response:
            token = await response.json()
            token = token["access_token"]

    async with websockets.connect(f"ws://localhost:8000/players?token={token}") as websocket:
        async for message in websocket:
            try:
                json_message = orjson.loads(message)
                field = json_message["type"]
                awaitable = player_ee.emit_async(field, message)
                await awaitable
            except:
                print(message)


async def clan_websocket():
    url = "http://127.0.0.1:8000/login"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"username" : "admin", "password" : "test"}) as response:
            token = await response.json()
            token = token["access_token"]

    async with websockets.connect(f"ws://localhost:8000/clans?token={token}") as websocket:
        async for message in websocket:
            try:
                json_message = orjson.loads(message)
                field = json_message["type"]
                awaitable = clan_ee.emit_async(field, message)
                await awaitable
            except:
                print(message)