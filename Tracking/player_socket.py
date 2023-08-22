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
import redis
from redis import asyncio as redis

keys = []
utc = pytz.utc
load_dotenv()
emails = []
passwords = []

BETA = False

if not BETA:
    #1-12
    for x in range(1,13):
        emails.append(f"apiclashofclans+test{x}@gmail.com")
        passwords.append(os.getenv("COC_PASSWORD"))
else:
    # 14-17
    for x in range(14, 18):
        emails.append(f"apiclashofclans+test{x}@gmail.com")
        passwords.append(os.getenv("COC_PASSWORD"))


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

async def main(PLAYER_CLIENTS):
    global keys

    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
    player_stats = client.new_looper.player_stats
    clan_stats = client.new_looper.clan_stats

    db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
    clan_db = db_client.usafam.clans
    player_search = db_client.usafam.player_search


    cache = redis.Redis(host='localhost', port=6379, db=0, password=os.getenv("REDIS_PW"), decode_responses=False)

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

    loop_spot = -1
    while True:
        loop_spot += 1

        clan_tags = await clan_db.distinct("tag")

        tasks = []
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
                        except:
                            return None
                tasks.append(fetch(url, session, headers))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            await session.close()

        CLAN_MEMBERS = []
        for response in responses:
            try:
                CLAN_MEMBERS += [member["tag"] for member in response["memberList"]]
            except:
                pass


        #people only become unpaused by joining a clan again or being tracked in legends again
        gone_for_a_month = int(datetime.now().timestamp()) - 2592000
        await player_stats.update_many({"last_online" : {"$lte" : gone_for_a_month}}, {"$set" : {"paused" : True}})
        await player_stats.update_many({"tag": {"$in": CLAN_MEMBERS}}, {"$set" : {"paused" : False}})


        #9/10 loops, only track legend members & clan members
        if loop_spot % 10 != 0:
            db_tags = await player_stats.distinct("tag", filter= {"league": "Legend League"})
            all_tags_to_track = list(set(db_tags + CLAN_MEMBERS))
        #1/10 loops, track anyone not paused + clan members
        else:
            db_tags = await player_stats.distinct("tag", filter={"paused": {"$ne": True}})
            all_tags_to_track = list(set(db_tags + CLAN_MEMBERS))
            autocomplete_tags = await player_search.distinct("tag")
            autocomplete_tags = set(autocomplete_tags)
            add_to_autocomplete = [tag for tag in all_tags_to_track if tag not in autocomplete_tags]
            auto_changes = []
            for tag in add_to_autocomplete:
                try:
                    r = await cache.get(tag)
                    if r is None:
                        continue
                    r = ujson.loads(r)
                    clan_tag = r.get("clan", {}).get("tag", "Unknown")
                    league = r.get("league", {}).get("name", "Unranked")
                    auto_changes.append(InsertOne(
                        {"name": r.get("name"), "clan": clan_tag, "league": league, "tag": r.get("tag"),
                         "th": r.get("townHallLevel")}))
                except:
                    continue
            if auto_changes:
                await player_search.bulk_write(auto_changes)



        if BETA:
            all_tags_to_track = all_tags_to_track[:5000]

        print(f"{len(all_tags_to_track)} tags")

        time_inside = time.time()

        class Player(Struct):
            tag: str

        bulk_db_changes = []
        bulk_insert = []
        bulk_clan_changes = []
        auto_complete = []

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

        players_tracked = set()

        tasks = []
        deque = collections.deque
        connector = aiohttp.TCPConnector(limit=2000, ttl_dns_cache=300)
        keys = deque(keys)
        url = "https://api.clashofclans.com/v1/players/"
        timeout = aiohttp.ClientTimeout(total=1800)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session3:
            for tag in all_tags_to_track:
                tag = tag.replace("#", "%23")
                keys.rotate(1)

                async def fetch(url, session: aiohttp.ClientSession, headers):
                    async with session.get(url, headers=headers) as new_response:
                        if new_response.status == 404:  # remove banned players
                            t = url.split("%23")[-1]
                            await player_stats.delete_one({"tag": f"#{t}"})
                            await cache.getdel(f"#{t}")
                            await player_search.delete_one({"tag": f"#{t}"})
                            return None
                        new_response = await new_response.read()

                        obj = decode(new_response, type=Player)

                        previous_response = await cache.get(obj.tag)
                        players_tracked.add(obj.tag)
                        if new_response != previous_response:
                            await cache.set(obj.tag, new_response, ex=86400)
                            if previous_response is None:
                                return None
                            BEEN_ONLINE = False
                            previous_response = ujson.loads(previous_response)
                            new_response = ujson.loads(new_response)

                            tag = obj.tag
                            clan_tag = new_response.get("clan", {}).get("tag", "Unknown")
                            league = new_response.get("league", {}).get("name", "Unranked")
                            prev_league = previous_response.get("league", {}).get("name", "Unranked")
                            if league != prev_league:
                                bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {"league": league}}))
                                auto_complete.append(UpdateOne({"tag": tag}, {"$set": {"league": league}}))

                            is_clan_member = clan_tag in set_clan_tags

                            changes, fields_to_update = get_changes(previous_response, new_response)
                            online_types = {"donations", "Gold Grab", "Most Valuable Clanmate", "attackWins",
                                            "War League Legend",
                                            "Wall Buster", "name", "Well Seasoned", "Games Champion", "Elixir Escapade",
                                            "Heroic Heist",
                                            "warPreference", "warStars", "Nice and Tidy", "builderBaseTrophies"}
                            skip_store_types = {"War League Legend", "Wall Buster", "Aggressive Capitalism",
                                                "Baby Dragon",
                                                "Elixir Escapade",
                                                "Gold Grab", "Heroic Heist", "Nice and Tidy", "Well Seasoned",
                                                "attackWins",
                                                "builderBaseTrophies", "donations", "donationsReceived", "trophies",
                                                "versusBattleWins", "versusTrophies"}

                            special_types = {"War League Legend", "warStars", "Aggressive Capitalism", "Nice and Tidy", "Well Seasoned",
                                         "clanCapitalContributions", "Games Champion"}
                            ws_types = {"clanCapitalContributions", "name", "troops", "heroes", "spells",
                                        "townHallLevel",
                                        "league", "trophies", "Most Valuable Clanmate"}
                            only_once = {"troops": 0, "heroes": 0, "spells": 0}
                            ws_tasks = []
                            if changes:
                                for (parent, type_), (old_value, value) in changes.items():
                                    if type_ in special_types:
                                        bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                         {"$set": {f"{type_.replace(' ','_').lower()}": value}},
                                                                         upsert=True))

                                    if type_ not in skip_store_types:
                                        if old_value is None:
                                            bulk_insert.append(InsertOne({"tag": tag, "type": type_, "value": value,
                                                                          "time": int(datetime.now().timestamp()),
                                                                          "clan": clan_tag}))
                                        else:
                                            bulk_insert.append(InsertOne(
                                                {"tag": tag, "type": type_, "p_value": old_value, "value": value,
                                                 "time": int(datetime.now().timestamp()), "clan": clan_tag}))
                                    if type_ == "donations":
                                        previous_dono = 0 if (previous_dono := previous_response["donations"]) > (
                                            current_dono := new_response["donations"]) else previous_dono
                                        bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                         {"$inc": {f"donations.{season}.donated": (
                                                                                 current_dono - previous_dono)}},
                                                                         upsert=True))
                                        if clan_tag != "Unknown":
                                            bulk_clan_changes.append(UpdateOne({"tag": clan_tag}, {
                                                "$inc": {f"{season}.{tag}.donated": (current_dono - previous_dono)}},
                                                                               upsert=True))
                                    elif type_ == "donationsReceived":
                                        previous_dono = 0 if (previous_dono := previous_response[
                                            "donationsReceived"]) > (
                                                                 current_dono := new_response[
                                                                     "donationsReceived"]) else previous_dono
                                        bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                         {"$inc": {f"donations.{season}.received": (
                                                                                 current_dono - previous_dono)}},
                                                                         upsert=True))
                                        if clan_tag != "Unknown":
                                            bulk_clan_changes.append(UpdateOne({"tag": clan_tag}, {
                                                "$inc": {f"{season}.{tag}.received": (current_dono - previous_dono)}},
                                                                               upsert=True))
                                    elif type_ == "clanCapitalContributions":
                                        bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                         {"$push":
                                                                              {f"capital_gold.{raid_date}.donate":
                                                                                   (new_response[
                                                                                        "clanCapitalContributions"] -
                                                                                    previous_response[
                                                                                        "clanCapitalContributions"])}},
                                                                         upsert=True))
                                        type_ = "Most Valuable Clanmate"  # temporary
                                    elif type_ == "Gold Grab":
                                        diff = value - old_value
                                        bulk_db_changes.append(
                                            UpdateOne({"tag": tag}, {"$inc": {f"gold.{season}": diff}}, upsert=True))
                                        if clan_tag != "Unknown":
                                            bulk_clan_changes.append(
                                                UpdateOne({"tag": clan_tag},
                                                          {"$inc": {f"{season}.{tag}.gold_looted": value}},
                                                          upsert=True))
                                    elif type_ == "Elixir Escapade":
                                        diff = value - old_value
                                        bulk_db_changes.append(
                                            UpdateOne({"tag": tag}, {"$inc": {f"elixir.{season}": diff}}, upsert=True))
                                        if clan_tag != "Unknown":
                                            bulk_clan_changes.append(
                                                UpdateOne({"tag": clan_tag},
                                                          {"$inc": {f"{season}.{tag}.elixir_looted": value}},
                                                          upsert=True))
                                    elif type_ == "Heroic Heist":
                                        diff = value - old_value
                                        bulk_db_changes.append(
                                            UpdateOne({"tag": tag}, {"$inc": {f"dark_elixir.{season}": diff}},
                                                      upsert=True))
                                        if clan_tag != "Unknown":
                                            bulk_clan_changes.append(UpdateOne({"tag": clan_tag}, {
                                                "$inc": {f"{season}.{tag}.dark_elixir_looted": value}}, upsert=True))
                                    elif type_ == "Well Seasoned":
                                        diff = value - old_value
                                        bulk_db_changes.append(
                                            UpdateOne({"tag": tag}, {"$inc": {f"season_pass.{games_season}": diff}},
                                                      upsert=True))
                                    elif type_ == "Games Champion":
                                        diff = value - old_value
                                        bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                         {"$inc": {
                                                                             f"clan_games.{games_season}.points": diff},
                                                                          "$set": {
                                                                              f"clan_games.{games_season}.clan": clan_tag}
                                                                          }, upsert=True))
                                        if clan_tag != "Unknown":
                                            bulk_clan_changes.append(
                                                UpdateOne({"tag": clan_tag},
                                                          {"$inc": {f"{season}.{tag}.clan_games": diff}},
                                                          upsert=True))
                                    elif type_ == "attackWins":  # remove in a future version, use cache instead
                                        bulk_db_changes.append(
                                            UpdateOne({"tag": tag}, {"$set": {f"attack_wins.{season}": value}},
                                                      upsert=True))
                                        if clan_tag != "Unknown":
                                            bulk_clan_changes.append(
                                                UpdateOne({"tag": clan_tag},
                                                          {"$set": {f"{season}.{tag}.attack_wins": value}},
                                                          upsert=True))
                                    elif type_ == "name":
                                        bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {"name": value}}, upsert=True))
                                        auto_complete.append(UpdateOne({"tag": tag}, {"$set": {"name": value}}))
                                    elif type_ == "clan":
                                        bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {"clan_tag": clan_tag}}, upsert=True))
                                        auto_complete.append(UpdateOne({"tag": tag}, {"$set": {"clan": clan_tag}}))

                                    elif type_ == "townHallLevel":
                                        bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {"townhall": value}}, upsert=True))
                                        auto_complete.append(UpdateOne({"tag": tag}, {"$set": {"th": value}}))

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
                                        for ws in pc_copy:  # type: fastapi.WebSocket
                                            json_data = {"type": type_, "old_player": previous_response,
                                                         "new_player": new_response}
                                            ws_tasks.append(asyncio.ensure_future(send_ws(ws=ws, json=json_data)))

                            # LEGENDS CODE, dont fix what aint broke
                            if new_response["trophies"] != previous_response["trophies"] and new_response["trophies"] >= 4900 and league == "Legend League":
                                diff_trophies = new_response["trophies"] - previous_response["trophies"]
                                diff_attacks = new_response["attackWins"] - previous_response["attackWins"]
                                if diff_trophies <= - 1:
                                    diff_trophies = abs(diff_trophies)
                                    if diff_trophies <= 100:
                                        bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                         {"$push": {
                                                                             f"legends.{legend_date}.defenses": diff_trophies}},
                                                                         upsert=True))
                                elif diff_trophies >= 1:
                                    bulk_db_changes.append(
                                        UpdateOne({"tag": tag},
                                                  {"$inc": {f"legends.{legend_date}.num_attacks": diff_attacks}},
                                                  upsert=True))
                                    # if one attack
                                    if diff_attacks == 1:
                                        bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                         {"$push": {
                                                                             f"legends.{legend_date}.attacks": diff_trophies}},
                                                                         upsert=True))
                                        if diff_trophies == 40:
                                            bulk_db_changes.append(
                                                UpdateOne({"tag": tag}, {"$inc": {f"legends.streak": 1}}))
                                        else:
                                            bulk_db_changes.append(
                                                UpdateOne({"tag": tag}, {"$set": {f"legends.streak": 0}}))
                                    # if multiple attacks, but divisible by 40
                                    elif int(diff_trophies / 40) == diff_attacks:
                                        for x in range(0, diff_attacks):
                                            bulk_db_changes.append(
                                                UpdateOne({"tag": tag},
                                                          {"$push": {f"legends.{legend_date}.attacks": 40}},
                                                          upsert=True))
                                        bulk_db_changes.append(
                                            UpdateOne({"tag": tag}, {"$inc": {f"legends.streak": diff_attacks}}))
                                    else:
                                        bulk_db_changes.append(UpdateOne({"tag": tag},
                                                                         {"$push": {
                                                                             f"legends.{legend_date}.attacks": diff_trophies}},
                                                                         upsert=True))
                                        bulk_db_changes.append(
                                            UpdateOne({"tag": tag}, {"$set": {f"legends.streak": 0}}, upsert=True))

                                if new_response["defenseWins"] != previous_response["defenseWins"]:
                                    diff_defenses = new_response["defenseWins"] - previous_response["defenseWins"]
                                    for x in range(0, diff_defenses):
                                        bulk_db_changes.append(
                                            UpdateOne({"tag": tag}, {"$push": {f"legends.{legend_date}.defenses": 0}},
                                                      upsert=True))

                            if BEEN_ONLINE:
                                _time = int(datetime.now().timestamp())
                                bulk_db_changes.append(
                                    UpdateOne({"tag": tag}, {
                                        "$inc": {f"activity.{season}": 1},
                                        "$push" : {f"last_online_times.{season}" : _time},
                                        "$set": {"last_online": _time}
                                    }, upsert=True))
                                bulk_clan_changes.append(
                                    UpdateOne({"tag": clan_tag},
                                              {"$inc": {f"{season}.{tag}.activity": 1}},
                                              upsert=True))

                            await asyncio.gather(*ws_tasks)

                tasks.append(fetch(f"{url}{tag}", session3, {"Authorization": f"Bearer {keys[0]}"}))
            await asyncio.gather(*tasks, return_exceptions=True)
            await session3.close()

        print(f"{time.time() - time_inside} seconds inside")
        print(f"{len(players_tracked)} players tracked")


        print(f"{len(bulk_db_changes)} db changes")
        if bulk_db_changes != []:
            results = await player_stats.bulk_write(bulk_db_changes)
            print(results.bulk_api_result)
            print(f"STAT CHANGES INSERT: {time.time() - time_inside}")

        if auto_complete != []:
            results = await player_search.bulk_write(auto_complete)
            print(results.bulk_api_result)
            print(f"AUTOCOMPLETE CHANGES: {time.time() - time_inside}")

        if bulk_insert != []:
            results = await client.new_looper.player_history.bulk_write(bulk_insert)
            print(results.bulk_api_result)
            print(f"HISTORY CHANGES INSERT: {time.time() - time_inside}")

        if bulk_clan_changes != []:
            results = await clan_stats.bulk_write(bulk_clan_changes)
            print(results.bulk_api_result)
            print(f"CLAN CHANGES UPDATE: {time.time() - time_inside}")

        fix_changes = []
        not_set_entirely = await player_stats.distinct("tag", filter={"$and": [{"paused": False}, {
            "$or": [{"name": None}, {"league": None}, {"townhall": None}, {"clan_tag": None}]}]})
        print(f'{len(not_set_entirely)} tags to fix')
        for tag in not_set_entirely:
            try:
                response = await cache.get(tag)
                response = ujson.loads(response)
                clan_tag = response.get("clan", {}).get("tag", "Unknown")
                league = response.get("league", {}).get("name", "Unranked")
                fix_changes.append(UpdateOne({"tag": tag}, {
                    "$set": {"name": response.get('name'), "townhall": response.get('townHallLevel'), "league": league,
                             "clan_tag": clan_tag}}))
            except:
                continue

        if fix_changes != []:
            results = await player_stats.bulk_write(fix_changes)
            print(results.bulk_api_result)
            print(f"FIX CHANGES: {time.time() - time_inside}")



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
    PLAYER_CLIENTS = set()


    @app.websocket("/players")
    async def player_websocket(websocket: WebSocket, token: str = Query(...), Authorize: AuthJWT = Depends()):
        await websocket.accept()
        PLAYER_CLIENTS.add(websocket)
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            PLAYER_CLIENTS.remove(websocket)

    config = Config(app=app, loop="asyncio", host= "85.10.200.219", port=65001, ws_ping_interval=3600, ws_ping_timeout=3600, timeout_keep_alive=3600, timeout_notify=3600)
    #config = Config(app=app, loop="asyncio", host = "localhost", port=60125, ws_ping_interval=3600, ws_ping_timeout=3600, timeout_keep_alive=3600, timeout_notify=3600)

    server = Server(config)

    keys = create_keys()
    loop.create_task(server.serve())
    loop.create_task(main(PLAYER_CLIENTS))
    loop.run_forever()


