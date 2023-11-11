import os
from redis import asyncio as redis
from dotenv import load_dotenv
load_dotenv()
import asyncio
import collections

from pymongo import UpdateOne, InsertOne
from datetime import timedelta
from uvicorn import Config, Server
from fastapi import FastAPI, WebSocket, Depends, Query, WebSocketDisconnect
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from aiomultiprocess import Worker
from expiring_dict import ExpiringDict
from redis.commands.json.path import Path

import ujson
import coc
import fastapi
import motor.motor_asyncio
import aiohttp
from Tracking.utils import HTTPClient, Route
from datetime import datetime

from Tracking.utils import create_keys

EMAILS = ["apiclashofclans+test44@gmail.com",
          "apiclashofclans+test45@gmail.com",
          "apiclashofclans+test46@gmail.com",
          "apiclashofclans+test47@gmail.com"]
PASSWORDS = [os.getenv("COC_PASSWORD") for x in range(len(EMAILS))]

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
player_stats = client.new_looper.player_stats
clan_stats = client.new_looper.clan_stats
clan_war = client.looper.clan_war

db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
clan_db = db_client.usafam.clans
player_search = db_client.usafam.player_search


async def send_ws(ws, json: dict, client: set):
    try:
        await ws.send_json(json)
    except:
        try:
            client.remove(ws)
        except:
            pass


WAR_CACHE = {}

async def broadcast(keys: list, WAR_CLIENTS: set, RAID_CLIENTS: set):
    http_client = HTTPClient()
    while True:
        keys = collections.deque(keys)
        clan_tags = await clan_db.distinct("tag")

        '''tasks = []
        connector = aiohttp.TCPConnector(limit=250)
        keys = collections.deque(keys)
        async with aiohttp.ClientSession(connector=connector) as session:
            for tag in clan_tags:
                headers = {"Authorization": f"Bearer {keys[0]}"}
                tag = tag.replace("#", "%23")
                url = f"https://api.clashofclans.com/v1/clans/{tag}"
                keys.rotate(1)

                async def fetch(url, session, headers):
                    async with session.get(url, headers=headers) as response:
                        try:
                            clan = await response.json()
                            return clan
                        except Exception:
                            return None

                tasks.append(fetch(url, session, headers))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            await session.close()

        for response in responses:
            pass'''

        wc_copy = WAR_CLIENTS.copy()
        war_tasks = []
        for tag in clan_tags:
            headers = {"Authorization": f"Bearer {keys[0]}"}
            keys.rotate(1)
            async def get_war(clan_tag: str, headers):

                clan_tag_for_url = clan_tag.replace('#', '%23')
                war_response = await http_client.request(Route("GET", f"/clans/{clan_tag_for_url}/currentwar"), headers=headers)
                if war_response is None:
                    now = datetime.utcnow().timestamp()
                    result = await clan_war.find_one({"$and": [{"endTime": {"$gte": now}}, {"opponent": clan_tag}]})
                    if result is not None:
                        war_response = await http_client.request(Route("GET", f"/clans/{clan_tag_for_url}/currentwar"), headers=headers)
                        if war_response is not None:
                            return_value = (None, war_response)
                        else:
                            return_value = (None, None)
                    else:
                        return_value = (None, None)
                else:
                    return_value = (None, war_response)

                if return_value == (None, None) or (return_value[1] is not None and return_value[1].get("state") == "notInWar"):
                    league_group_response = await http_client.request(Route("GET", f"/clans/{clan_tag_for_url}/currentwar/leaguegroup"), headers=headers)
                    if league_group_response is None:
                        return_value = (None, None)
                    else:
                        return_value = (True, True)

                current_round = next_round = None
                if return_value == (True, True):
                    rounds: list = league_group_response.get("rounds")
                    current_round_war_tags = []
                    next_round_war_tags = []
                    for count, round in enumerate(reversed(rounds), 1):
                        current_round_war_tags = round.get("warTags")
                        if "#0" in current_round_war_tags:
                            continue
                        current_round = -(count)
                    if current_round is None:
                        return_value = (None, None)
                    else:
                        num_rounds = len(rounds)
                        if current_round + 1 == 0: #we are on last round
                            next_round = None
                        else:
                            next_round = rounds[current_round + 1]
                            next_round_war_tags = next_round.get("warTags")
                            if "#0" in next_round_war_tags:
                                next_round = None

                    if current_round is not None:
                        for war_tag in current_round_war_tags:
                            league_war_response = await http_client.request(Route("GET", f"/clanwarleagues/wars/{war_tag.replace('#', '%23')}"), headers=headers)
                            if league_war_response is not None:
                                if league_war_response.get("clan").get("tag") == clan_tag or league_war_response.get("opponent").get("tag") == clan_tag:
                                    current_round = league_war_response
                                    break

                    if next_round is not None:
                        for war_tag in next_round_war_tags:
                            league_war_response = await http_client.request(Route("GET", f"/clanwarleagues/wars/{war_tag.replace('#', '%23')}"), headers=headers)
                            if league_war_response is not None:
                                if league_war_response.get("clan").get("tag") == clan_tag or league_war_response.get("opponent").get("tag") == clan_tag:
                                    next_round = league_war_response
                                    break

                if current_round is None and next_round is None:
                    return return_value
                else:
                    return (next_round, current_round)

            war_tasks.append(get_war(clan_tag=tag, headers=headers))
        responses = await asyncio.gather(*war_tasks)
        print(responses)
        print(len(responses))
        '''raid_tasks = []
        for tag in clan_tags:
            async def get_raid(clan_tag: str):
                try:
                    r = await coc_client.get_raidlog(clan_tag=tag, limit=1)
                    return (clan_tag, r[0])
                except:
                    return (clan_tag, None)

            raid_tasks.append(get_raid(clan_tag=tag))
        raid_responses = await asyncio.gather(*raid_tasks, return_exceptions=True)
        raid_responses = [(tag, raid) for tag, raid in raid_responses if raid is not None]
        print(len(raid_responses))'''


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    WAR_CLIENTS = set()
    RAID_CLIENTS = set()
    CLAN_CLIENTS = set()

    @app.websocket("/wars")
    async def war_websocket(websocket: WebSocket, token: str = Query(...), Authorize: AuthJWT = Depends()):
        await websocket.accept()
        WAR_CLIENTS.add(websocket)
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            WAR_CLIENTS.remove(websocket)


    @app.websocket("/raids")
    async def raid_websocket(websocket: WebSocket, token: str = Query(...), Authorize: AuthJWT = Depends()):
        await websocket.accept()
        RAID_CLIENTS.add(websocket)
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            RAID_CLIENTS.remove(websocket)


    @app.websocket("/clans")
    async def clan_websocket(websocket: WebSocket, token: str = Query(...), Authorize: AuthJWT = Depends()):
        await websocket.accept()
        CLAN_CLIENTS.add(websocket)
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            CLAN_CLIENTS.remove(websocket)


    #config = Config(app=app, loop="asyncio", host= "85.10.200.219", port=65100, ws_ping_interval=3600, ws_ping_timeout=3600, timeout_keep_alive=3600, timeout_notify=3600)
    config = Config(app=app, loop="asyncio", host = "localhost", port=60125, ws_ping_interval=3600, ws_ping_timeout=3600, timeout_keep_alive=3600, timeout_notify=3600)

    server = Server(config)

    keys = create_keys(emails=EMAILS, passwords=PASSWORDS)
    loop.create_task(server.serve())
    loop.create_task(broadcast(keys=keys, WAR_CLIENTS=WAR_CLIENTS, RAID_CLIENTS=RAID_CLIENTS))
    loop.run_forever()


