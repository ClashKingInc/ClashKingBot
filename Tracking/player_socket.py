import os
from typing import List, Dict, Tuple, Union
from pydantic import BaseModel
from base64 import b64decode as base64_b64decode
from json import loads as json_loads
from datetime import datetime
from dotenv import load_dotenv
from msgspec.json import decode
from msgspec import Struct
from pymongo import UpdateOne, InsertOne
from datetime import timedelta
from asyncio_throttle import Throttler
from uvicorn import Config, Server
from fastapi import FastAPI, WebSocket, Depends, Query, WebSocketDisconnect
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from aiomultiprocess import Worker
from expiring_dict import ExpiringDict

import ujson
import coc
import fastapi
import motor.motor_asyncio
import collections
import time
import aiohttp
import asyncio
import pytz
import numpy as np
import sys

keys = []
utc = pytz.utc
load_dotenv()
emails = []
passwords = []
#1-12
for x in range(24,28):
    emails.append(f"apiclashofclans+test{x}@gmail.com")
    passwords.append(EMAIL_PW)
'''#14-17
for x in range(14,18):
    emails.append(f"apiclashofclans+test{x}@gmail.com")
    passwords.append(EMAIL_PW)'''


async def get_keys(emails: list, passwords: list, key_names: str, key_count: int):
    total_keys = []

    for count, email in enumerate(emails):
        _keys = []
        password = passwords[count]

        session = aiohttp.ClientSession()

        body = {"email": email, "password": password}
        resp = await session.post("https://developer.clashofclans.com/api/login", json=body)
        if resp.status == 403:
            raise RuntimeError(
                "Invalid Credentials"
            )

        resp_paylaod = await resp.json()
        ip = json_loads(base64_b64decode(resp_paylaod["temporaryAPIToken"].split(".")[1] + "====").decode("utf-8"))[
            "limits"][1]["cidrs"][0].split("/")[0]

        resp = await session.post("https://developer.clashofclans.com/api/apikey/list")
        keys = (await resp.json())["keys"]
        _keys.extend(key["key"] for key in keys if key["name"] == key_names and ip in key["cidrRanges"])

        for key in (k for k in keys if ip not in k["cidrRanges"]):
            await session.post("https://developer.clashofclans.com/api/apikey/revoke", json={"id": key["id"]})

        print(len(_keys))
        while len(_keys) < key_count:
            data = {
                "name": key_names,
                "description": "Created on {}".format(datetime.now().strftime("%c")),
                "cidrRanges": [ip],
                "scopes": ["clash"],
            }
            resp = await session.post("https://developer.clashofclans.com/api/apikey/create", json=data)
            key = await resp.json()
            _keys.append(key["key"]["key"])

        if len(keys) == 10 and len(_keys) < key_count:
            print("%s keys were requested to be used, but a maximum of %s could be "
                  "found/made on the developer site, as it has a maximum of 10 keys per account. "
                  "Please delete some keys or lower your `key_count` level."
                  "I will use %s keys for the life of this client.", )

        if len(_keys) == 0:
            raise RuntimeError(
                "There are {} API keys already created and none match a key_name of '{}'."
                "Please specify a key_name kwarg, or go to 'https://developer.clashofclans.com' to delete "
                "unused keys.".format(len(keys), key_names)
            )

        await session.close()
        #print("Successfully initialised keys for use.")
        for k in _keys:
            total_keys.append(k)

    print(len(total_keys))
    return (total_keys)

def create_keys():
    done = False
    while done is False:
        try:
            loop = asyncio.get_event_loop()
            keys = loop.run_until_complete(get_keys(emails=emails,
                                     passwords=passwords, key_names="test", key_count=10))
            done = True
            return keys
        except Exception as e:
            done = False
            print(e)

class UpdateList(BaseModel):
    add : List[str]
    remove : List[str]
    token : str

class User(BaseModel):
    username: str
    password: str

last_changed: Dict[str, Tuple[int, dict]] = {}

async def broadcast(tags, keys, loop, cache, loops):
    throttler = Throttler(rate_limit=15000, period=60)
    if loops in (1, 2):
        throttler = Throttler(rate_limit=60000, period=60)

    class Player(Struct):
        tag: str

    exceptions = []
    rtime = time.time()

    print(f"{len(tags)} tags, loop {loop}")

    #PLAYER EVENTS
    async def fetch(url, session: aiohttp.ClientSession, headers):
        async with session.get(url, headers=headers) as response:
            async with throttler:
                return (await response.read())

    change_cache = {}
    tasks = []
    deque = collections.deque
    connector = aiohttp.TCPConnector(limit=250, ttl_dns_cache=300)
    keys = deque(keys)
    url = "https://api.clashofclans.com/v1/players/"
    async with aiohttp.ClientSession(connector=connector) as session3:
        for tag in tags:
            tag = tag.replace("#", "%23")
            keys.rotate(1)
            tasks.append(fetch(f"{url}{tag}", session3, {"Authorization": f"Bearer {keys[0]}"}))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        await session3.close()

    for response in responses:
        try:
            obj = decode(response, type=Player)
        except:
            continue

        #response is bytes
        if response != cache.get(obj.tag):
            change_cache[obj.tag] = response

    print(f"{len(change_cache)} cache size, DONE: {time.time() - rtime}, loop {loop}")
    return change_cache

async def background_cache():
    await asyncio.sleep(0.1)

    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
    player_cache = client.new_looper.player_cache

    while True:
        bulk_cache = []
        for tag, response in last_changed.copy().items():
            bulk_cache.append(UpdateOne({"tag": tag}, {"$set": {"data": response}}, upsert=True))
            del last_changed[tag]
        if bulk_cache:
            results = await player_cache.bulk_write(bulk_cache, ordered=False)
            print(f"BACKGROUND_CACHE: {results.bulk_api_result}")
        await asyncio.sleep(30)


async def main(keys, app):
    @app.post('/login')
    async def login(user: User, Authorize: AuthJWT = Depends()):
        return {"access_token": "5"}

    PLAYER_CLIENTS = set()
    @app.websocket("/players")
    async def player_websocket(websocket: WebSocket, token: str = Query(...), Authorize: AuthJWT = Depends()):
        await websocket.accept()
        PLAYER_CLIENTS.add(websocket)
        try:
            '''Authorize.jwt_required("websocket", token=token)
            await websocket.send_text("Successfully Login!")
            decoded_token = Authorize.get_raw_jwt(token)
            await websocket.send_text(f"Here your decoded token: {decoded_token}")'''
            try:
                while True:
                    data = await websocket.receive_text()
            except WebSocketDisconnect:
                PLAYER_CLIENTS.remove(websocket)
        except AuthJWTException as err:
            await websocket.send_text(err.message)
            await websocket.close()

    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))

    player_stats = client.new_looper.player_stats

    db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
    clan_db = db_client.usafam.clans


    def get_changes(previous_response: dict, response: dict):
        new_json = {}
        fields_to_update = []
        ok_achievements = {"Gold Grab", "Elixir Escapade", "Heroic Heist", "Games Champion", "Aggressive Capitalism",
                           "Well Seasoned", "Nice and Tidy", "War League Legend", "Wall Buster"}
        for key, item in response.items():
            old_item = previous_response.get(key)
            if old_item != item:
                fields_to_update.append(key)
            not_ok_fields = {"labels", "legendStatistics", "playerHouse", "versusBattleWinCount"}
            if key in not_ok_fields:
                continue
            if old_item != item:
                if isinstance(item, list):
                    for count, spot in enumerate(item):
                        spot_name = spot["name"]
                        if key == "achievements" and spot_name not in ok_achievements:
                            continue
                        old_ = next((item for item in old_item if item["name"] == spot_name), None)
                        if old_ != spot:
                            if key == "achievements":
                                if old_ is not None:
                                    new_json[(key, spot_name.replace(".", ""))] = (old_["value"], spot["value"])
                                else:
                                    new_json[(key, spot_name.replace(".", ""))] = (None, spot["value"])
                            else:
                                if old_ is not None:
                                    new_json[(key, spot_name.replace(".", ""))] = (old_["level"], spot["level"])
                                else:
                                    new_json[(key, spot_name.replace(".", ""))] = (None, spot["level"])
                else:
                    if key == "clan":
                        new_json[(key, key)] = (None, {"tag" : item["tag"], "name" : item["name"]})
                    elif key == "league":
                        new_json[(key, key)] = (None, {"tag" : item["id"], "name" : item["name"]})
                    else:
                        new_json[(key, key)] = (old_item, item)

        return (new_json, fields_to_update)

    CLAN_MEMBER_CACHE = ExpiringDict(600)
    IS_UPDATE = {}
    PLAYER_CACHE = {}
    global last_changed
    loops = 0
    while True:
        loops += 1
        try:
            start_time = time.time()
            try:
                all_tags_to_track = CLAN_MEMBER_CACHE["clan_tags"]
                print(len(all_tags_to_track))
            except Exception:
                clan_tags = await clan_db.distinct("tag")

                async def fetch(url, session, headers):
                    async with session.get(url, headers=headers) as response:
                        try:
                            clan = await response.json()
                            return clan
                        except:
                            return None

                tasks = []
                connector = aiohttp.TCPConnector(limit=100)
                async with aiohttp.ClientSession(connector=connector) as session:
                    for tag in clan_tags:
                        headers = {"Authorization": f"Bearer {keys[0]}"}
                        tag = tag.replace("#", "%23")
                        url = f"https://api.clashofclans.com/v1/clans/{tag}"
                        keys = collections.deque(keys)
                        keys.rotate(1)
                        keys = list(keys)
                        task = asyncio.ensure_future(fetch(url, session, headers))
                        tasks.append(task)
                    responses = await asyncio.gather(*tasks, return_exceptions=True)
                    await session.close()

                CLAN_MEMBERS = []
                for response in responses:
                    try:
                        CLAN_MEMBERS += [member["tag"] for member in response["memberList"]]
                    except Exception:
                        pass

                db_tags = await player_stats.distinct("tag")
                all_tags_to_track = list(set(db_tags + CLAN_MEMBERS))
                CLAN_MEMBER_CACHE["clan_tags"] = all_tags_to_track

            split_tags = list(np.array_split(all_tags_to_track, 6))
            print(f"{len(all_tags_to_track)} tags")
            print(f"{time.time() - start_time}, starting workers")

            start_time = time.time()
            workers = []
            for x in range(6):
                set_keys = set(split_tags[x])
                worker = Worker(target=broadcast, kwargs={"cache" : {key: PLAYER_CACHE.get(key) for key in PLAYER_CACHE.keys() if key in set_keys},
                                                          "tags" : split_tags[x], "keys" : keys, "loop" : x, "loops" : loops})
                worker.start()
                workers.append(worker)
            print(f"{time.time() - start_time} seconds to start up")

            time_inside = time.time()
            cache_result_list = []
            for _ in workers:
                cache_results = await _.join()
                cache_result_list.append(cache_results)
                _.close()
            print(f"{time.time() - time_inside} seconds inside")

            ltime = time.time()
            bulk_db_changes = []
            bulk_insert = []
            ws_tasks = []
            async def send_ws(ws, json):
                try:
                    await ws.send_json(json)
                except:
                    try:
                        PLAYER_CLIENTS.remove(ws)
                    except:
                        pass

            season = gen_season_date()
            raid_date = gen_raid_date()
            games_season = gen_games_season()
            legend_date = gen_legend_date()

            pc_copy = PLAYER_CLIENTS.copy()
            set_clan_tags = set(await clan_db.distinct("tag"))
            for cache_result in cache_result_list:
                if not cache_result or cache_result is None:
                    continue
                for tag, bytes_response in cache_result.items():

                    previous_bytes = PLAYER_CACHE.get(tag)
                    if previous_bytes is None:
                        PLAYER_CACHE[tag] = bytes_response
                        continue
                    try:
                        previous_response = ujson.loads(previous_bytes)
                    except Exception:
                        #PLAYER_CACHE[tag] = bytes_response
                        #removing, should store fault responses anyways
                        continue

                    BEEN_ONLINE = False
                    PLAYER_CACHE[tag] = bytes_response
                    response = ujson.loads(bytes_response)

                    last_changed[tag] = response
                    first_run = IS_UPDATE.get(tag, True)
                    if first_run:
                        IS_UPDATE[tag] = False

                    clan_tag = response.get("clan", {}).get("tag", "Unknown")
                    league = response.get("league", {}).get("name", "Unranked")
                    prev_league = previous_response.get("league", {}).get("name", "Unranked")
                    if first_run or league != prev_league:
                        bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {"league": league}}))

                    is_clan_member = clan_tag in set_clan_tags

                    changes, fields_to_update = get_changes(previous_response, response)
                    online_types = {"donations", "Gold Grab", "Most Valuable Clanmate", "attackWins", "War League Legend",
                                    "Wall Buster", "name", "Well Seasoned", "Games Champion", "Elixir Escapade", "Heroic Heist",
                                    "warPreference", "warStars", "Nice and Tidy", "builderBaseTrophies"}
                    skip_store_types = {"War League Legend", "Wall Buster", "Aggressive Capitalism", "Baby Dragon", "Elixir Escapade",
                                        "Gold Grab", "Heroic Heist", "Nice and Tidy", "Well Seasoned", "attackWins",
                                        "builderBaseTrophies", "donations", "donationsReceived", "trophies", "versusBattleWins", "versusTrophies"}
                    ws_types = {"clanCapitalContributions", "name", "troops", "heroes", "spells", "townHallLevel", "league", "trophies", "Most Valuable Clanmate"}
                    only_once = {"troops" : 0, "heroes" : 0, "spells" : 0}
                    ws_tasks = []
                    if changes:
                        for (parent, type_), (old_value, value) in changes.items():
                            if type_ not in skip_store_types:
                                if old_value is None:
                                    bulk_insert.append(InsertOne({"tag": tag, "type": type_, "value": value, "time": int(datetime.now().timestamp()), "clan": clan_tag}))
                                else:
                                    bulk_insert.append(InsertOne({"tag": tag, "type": type_, "p_value" : old_value, "value": value, "time": int(datetime.now().timestamp()), "clan": clan_tag}))
                            if type_ == "donations":
                                previous_dono = 0 if (previous_dono := previous_response["donations"]) > (current_dono := response["donations"]) else previous_dono
                                bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                 {"$inc": {f"donations.{season}.donated": (current_dono-previous_dono)}}, upsert=True))
                            elif type_ == "donationsReceived":
                                previous_dono = 0 if (previous_dono := previous_response["donationsReceived"]) > (current_dono := response["donationsReceived"]) else previous_dono
                                bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                 {"$inc": {f"donations.{season}.received": (current_dono-previous_dono)}},upsert=True))
                            elif type_ == "clanCapitalContributions":
                                bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                 {"$push":
                                                                      {f"capital_gold.{raid_date}.donate":
                                                                           (response["clanCapitalContributions"]-previous_response["clanCapitalContributions"])}}, upsert=True))
                                type_ = "Most Valuable Clanmate" #temporary
                            elif type_ == "Gold Grab":
                                diff = value - old_value
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$push": {f"gold_looted.{season}": diff}}, upsert=True))
                            elif type_ == "Elixir Escapade":
                                diff = value - old_value
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$push": {f"elixir_looted.{season}": diff}}, upsert=True))
                            elif type_ == "Heroic Heist":
                                diff = value - old_value
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$push": {f"dark_elixir_looted.{season}": diff}}, upsert=True))
                            elif type_ == "Well Seasoned":
                                diff = value - old_value
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$inc": {f"season_pass.{games_season}": diff}}, upsert=True))
                            elif type_ == "Games Champion":
                                diff = value - old_value
                                bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                 {   "$inc": {f"clan_games.{games_season}.points": diff},
                                                                     "$set": {f"clan_games.{games_season}.clan": clan_tag}
                                                                 }, upsert=True))
                            elif type_ == "attackWins": #remove in a future version, use cache instead
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {f"attack_wins.{season}": value}}, upsert=True))
                            elif type_ == "name":
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {"name": value}}, upsert=True))
                            elif type_ == "clan":
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {"clan_tag": clan_tag}}, upsert=True))
                            elif type_ == "townHallLevel":
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {"townhall": value}}, upsert=True))
                            elif parent in {"troops", "heroes", "spells"}:
                                type_ = parent
                                if only_once[parent] == 1:
                                    continue
                                only_once[parent] += 1

                            if type_ in online_types:
                                BEEN_ONLINE = True

                            if type_ in ws_types and is_clan_member:
                                if type_ == "trophies":
                                    if not (value >= 4900 and league == "Legend League"):
                                        continue
                                for ws in pc_copy: #type: fastapi.WebSocket
                                    json_data = {"type": type_, "old_player": previous_response, "new_player": response}
                                    ws_tasks.append(asyncio.ensure_future(send_ws(ws=ws, json=json_data)))


                    # LEGENDS CODE, dont fix what aint broke
                    if response["trophies"] != previous_response["trophies"] and response["trophies"] >= 4900 and league == "Legend League":
                        diff_trophies = response["trophies"] - previous_response["trophies"]
                        diff_attacks = response["attackWins"] - previous_response["attackWins"]
                        if diff_trophies <= - 1:
                            diff_trophies = abs(diff_trophies)
                            if diff_trophies <= 100:
                                bulk_db_changes.append(UpdateOne({"tag": tag},
                                                         {"$push": {f"legends.{legend_date}.defenses": diff_trophies}}, upsert=True))
                        elif diff_trophies >= 1:
                            bulk_db_changes.append(
                                UpdateOne({"tag": tag}, {"$inc": {f"legends.{legend_date}.num_attacks": diff_attacks}}, upsert=True))
                            #if one attack
                            if diff_attacks == 1:
                                bulk_db_changes.append(UpdateOne({"tag": tag},
                                                         {"$push": {f"legends.{legend_date}.attacks": diff_trophies}}, upsert=True))
                                if diff_trophies == 40:
                                    bulk_db_changes.append(UpdateOne({"tag": tag}, {"$inc": {f"legends.streak": 1}}))
                                else:
                                    bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {f"legends.streak": 0}}))
                            #if multiple attacks, but divisible by 40
                            elif int(diff_trophies / 40) == diff_attacks:
                                for x in range(0, diff_attacks):
                                    bulk_db_changes.append(UpdateOne({"tag": tag}, {"$push": {f"legends.{legend_date}.attacks": 40}}, upsert=True))
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$inc": {f"legends.streak": diff_attacks}}))
                            else:
                                bulk_db_changes.append(UpdateOne({"tag": tag},
                                                         {"$push": {f"legends.{legend_date}.attacks": diff_trophies}}, upsert=True))
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {f"legends.streak": 0}}, upsert=True))

                        if response["defenseWins"] != previous_response["defenseWins"]:
                            diff_defenses = response["defenseWins"] - previous_response["defenseWins"]
                            for x in range(0, diff_defenses):
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$push": {f"legends.{legend_date}.defenses": 0}}, upsert=True))

                    if BEEN_ONLINE:
                        _time = int(datetime.now().timestamp())
                        bulk_db_changes.append(
                            UpdateOne({"tag": tag}, {
                                "$push": {f"last_online_times.{season}": _time},
                                "$set": {"last_online": _time}
                            }, upsert=True))

            print(f"takes {time.time() - ltime} seconds to go thru changes")
            await asyncio.gather(*ws_tasks)
            other_changes = []
            if len(PLAYER_CACHE) != 0:
                no_name_tags = await player_stats.distinct("tag", filter={"name": None})
                for tag in no_name_tags:
                    try:
                        name = ujson.loads(PLAYER_CACHE[tag])["name"]
                        other_changes.append(UpdateOne({"tag": tag}, {"$set": {"name": name}}))
                    except Exception:
                        continue
                no_th = await player_stats.distinct("tag", filter={"townhall": None})
                for tag in no_th:
                    try:
                        th_level = ujson.loads(PLAYER_CACHE[tag])["townHallLevel"]
                        other_changes.append(UpdateOne({"tag": tag}, {"$set": {"townhall": th_level}}))
                    except Exception:
                        continue

                print(f"{len(bulk_db_changes)} db changes")
                if bulk_db_changes != []:
                    results = await player_stats.bulk_write(bulk_db_changes, ordered=False)
                    print(results.bulk_api_result)
                    print(f"STAT CHANGES INSERT: {time.time() - start_time}")

                if other_changes != []:
                    results = await player_stats.bulk_write(other_changes)
                    print(results.bulk_api_result)
                    print(f"OTHER CHANGES: {time.time() - start_time}")

                if bulk_insert != []:
                    results = await client.new_looper.player_history.bulk_write(bulk_insert)
                    print(results.bulk_api_result)
                    print(f"HISTORY CHANGES INSERT: {time.time() - start_time}")

                print(f"cache: {len(PLAYER_CACHE)} items, cache is {sys.getsizeof(PLAYER_CACHE)} bytes, {time.time() - start_time} seconds")
        except:
            continue

def gen_raid_date():
    now = datetime.utcnow().replace(tzinfo=utc)
    current_dayofweek = now.weekday()
    if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
            current_dayofweek == 0 and now.hour < 7):
        if current_dayofweek == 0:
            current_dayofweek = 7
        fallback = current_dayofweek - 4
        raidDate = (now - timedelta(fallback)).date()
        return str(raidDate)
    else:
        forward = 4 - current_dayofweek
        raidDate = (now + timedelta(forward)).date()
        return str(raidDate)

def gen_season_date():
    end = coc.utils.get_season_end().replace(tzinfo=utc).date()
    month = end.month
    if month <= 9:
        month = f"0{month}"
    return f"{end.year}-{month}"

def gen_legend_date():
    now = datetime.utcnow()
    hour = now.hour
    if hour < 5:
        date = (now - timedelta(1)).date()
    else:
        date = now.date()
    return str(date)

def gen_games_season():
    now = datetime.utcnow()
    month = now.month
    if month <= 9:
        month = f"0{month}"
    return f"{now.year}-{month}"


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    config = Config(app=app, loop="asyncio", host = "85.10.200.219", port=60125, ws_ping_interval=3600, ws_ping_timeout=3600, timeout_keep_alive=3600, timeout_notify=3600)
    #config = Config(app=app, loop="asyncio", host = "localhost", port=60125, ws_ping_interval=3600, ws_ping_timeout=3600, timeout_keep_alive=3600, timeout_notify=3600)

    server = Server(config)

    keys = create_keys()
    loop.create_task(server.serve())
    loop.create_task(main(keys, app))
    loop.create_task(background_cache())
    loop.run_forever()


