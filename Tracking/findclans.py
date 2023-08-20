
from typing import List

import ujson
import coc
from pydantic import BaseModel
from base64 import b64decode as base64_b64decode
from json import loads as json_loads
from datetime import datetime
from dotenv import load_dotenv
from msgspec.json import decode
from msgspec import Struct
from pymongo import UpdateOne, InsertOne
from pymongo.errors import BulkWriteError

import motor.motor_asyncio
import collections
import time
import aiohttp
import asyncio
import pytz
import random
import numpy as np
import sys
from copy import deepcopy
from coc import Timestamp
import itertools

keys = []
utc = pytz.utc
load_dotenv()
import os
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
looper = client.looper
clan_tags = looper.clan_tags
war_logs = looper.war_logs

EMAIL_PW = os.getenv("COC_PASSWORD")

from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

#DATABASE
import orjson

emails = []
passwords = []
#18-27
for x in range(18,22):
    emails.append(f"apiclashofclans+test{x}@gmail.com")
    passwords.append(EMAIL_PW)

coc_client = coc.Client(key_count=10, throttle_limit=25, cache_max_size=0, raw_attribute=True)

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


@scheduler.scheduled_job("cron", day_of_week="wed", hour=10)
async def broadcast():
    global keys
    async def fetch(url, session: aiohttp.ClientSession, headers):
        async with session.get(url, headers=headers) as response:
            return (await response.read())

    pipeline = [{"$match": {}}, {"$group": {"_id": "$tag"}}]
    all_tags = [x["_id"] for x in (await clan_tags.aggregate(pipeline).to_list(length=None))]
    clan_tags_alr_found = set(all_tags)
    size_break = 50000
    all_tags = [all_tags[i:i + size_break] for i in range(0, len(all_tags), size_break)]

    for tag_group in all_tags:
        tags_to_add = []
        tasks = []
        deque = collections.deque
        connector = aiohttp.TCPConnector(limit=250, ttl_dns_cache=300)
        keys = deque(keys)
        url = "https://api.clashofclans.com/v1/clans/"
        async with aiohttp.ClientSession(connector=connector) as session3:
            for tag in tag_group:
                tag = tag.replace("#", "%23")
                keys.rotate(1)
                tasks.append(fetch(f"{url}{tag}/warlog?limit=200", session3, {"Authorization": f"Bearer {keys[0]}"}))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            await session3.close()
        right_now = int(datetime.now().timestamp())
        for response in responses:
            try:
                warlog = ujson.loads(response)
            except:
                continue

            for item in warlog.get("items", []):
                if item.get("opponent").get("tag") is None:
                    continue
                del item["clan"]["badgeUrls"]
                del item["opponent"]["badgeUrls"]
                t = int(Timestamp(data=item["endTime"]).time.timestamp())
                item["timeStamp"] = t
                if (right_now - t <= 2592000) and item["opponent"]["tag"] not in clan_tags_alr_found:
                    tags_to_add.append(InsertOne({"tag" : item["opponent"]["tag"]}))

        if tags_to_add:
            try:
                results = await clan_tags.bulk_write(tags_to_add, ordered=False)
                print(results.bulk_api_result)
            except Exception:
                print(f"potentially added {len(tags_to_add)} tags")

        '''if items_to_push:
            try:
                results = await war_logs.bulk_write(items_to_push, ordered=False)
                print(results.bulk_api_result)
            except Exception:
                print(f"potentially added {len(items_to_push)} logs")'''

    #sec * min * hour, sleep for 6 hours




loop = asyncio.get_event_loop()
keys = create_keys()
coc_client.login_with_keys(*keys[:10])
loop.run_forever()
