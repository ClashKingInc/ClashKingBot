import os
from base64 import b64decode as base64_b64decode
from json import loads as json_loads
from datetime import datetime
from dotenv import dotenv_values, load_dotenv
from msgspec.json import decode
from msgspec import Struct
from pymongo import  InsertOne, UpdateOne
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import utc
from typing import List

import pymongo
import motor.motor_asyncio
import collections
import aiohttp
import asyncio
import coc
import string
import random

load_dotenv()
keys = []

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
looper = client.looper
clan_tags = looper.clan_tags
clan_wars = looper.clan_war
warhits = looper.warhits
war_timer = looper.war_timer

db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("STATIC_DB_LOGIN"))
clan_db = db_client.usafam.clans

scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

emails = []
passwords = []
#26-29 (30)
for x in range(26,30):
    emails.append(f"apiclashofclans+test{x}@gmail.com")
    passwords.append(os.getenv("COC_PASSWORD"))

#31-37 (38)
for x in range(31,38):
    emails.append(f"apiclashofclans+test{x}@gmail.com")
    passwords.append(os.getenv("COC_PASSWORD"))

coc_client = coc.Client(key_count=10, throttle_limit=30, cache_max_size=0, raw_attribute=True)

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
                f"Invalid Credentials, {email} | {password}"
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

class Members(Struct):
    tag: str

class Clan(Struct):
    tag: str
    members: List[Members]


class War(Struct):
    state: str
    preparationStartTime: str
    endTime: str
    clan: Clan
    opponent: Clan

in_war = set()

async def broadcast(keys):
    global in_war
    x = 1
    while True:
        async def fetch(url, session: aiohttp.ClientSession, headers, tag):
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return ((await response.read()), tag)
                elif response.status == 503:
                    return (503, 503)
                return (None, None)


        pipeline = [{"$match": {"openWarLog": True}}, {"$group": {"_id": "$tag"}}]
        all_tags = [x["_id"] for x in (await clan_tags.aggregate(pipeline).to_list(length=None))]
        size_break = 50000
        bot_clan_tags = await clan_db.distinct("tag")
        all_tags = [tag for tag in all_tags if tag not in in_war] + bot_clan_tags
        all_tags = list(set(all_tags))

        if x % 20 != 0:
            right_now = datetime.now().timestamp()
            one_week_ago = int(right_now) - 604800

            try:
                clan_side_tags = await clan_wars.distinct("data.clan.tag", filter={"endTime": {"$gte" : one_week_ago}})
            except Exception:
                pipeline = [{"$match": {"endTime": {"$gte": one_week_ago}}}, {"$group": {"_id": "$data.clan.tag"}}]
                clan_side_tags = [x["_id"] for x in (await clan_wars.aggregate(pipeline).to_list(length=None))]

            try:
                opponent_side_tags = await clan_wars.distinct("data.opponent.tag", filter={"endTime": {"$gte" : one_week_ago}})
            except Exception:
                pipeline = [{"$match": {"endTime": {"$gte": one_week_ago}}}, {"$group": {"_id": "$data.opponent.tag"}}]
                opponent_side_tags = [x["_id"] for x in (await clan_wars.aggregate(pipeline).to_list(length=None))]
            combined_tags = set(opponent_side_tags + clan_side_tags)
            all_tags = [tag for tag in all_tags if tag in combined_tags]

        print(len(all_tags))
        all_tags = [all_tags[i:i + size_break] for i in range(0, len(all_tags), size_break)]
        ones_that_tried_again = []

        x += 1
        for count, tag_group in enumerate(all_tags, 1):
            print(f"Group {count}/{len(all_tags)}")
            tasks = []
            connector = aiohttp.TCPConnector(limit=500, ttl_dns_cache=600)
            keys = collections.deque(keys)
            async with aiohttp.ClientSession(connector=connector) as session:
                for tag in tag_group:
                    keys.rotate(1)
                    tasks.append(fetch(f"https://api.clashofclans.com/v1/clans/{tag.replace('#', '%23')}/currentwar", session, {"Authorization": f"Bearer {keys[0]}"}, tag))
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                await session.close()

            responses = [r for r in responses if type(r) is tuple]
            changes = []
            war_timers = []
            for response, tag in responses:
                # we shouldnt have completely invalid tags, they all existed at some point
                if response is None or response == 503:
                    continue
                try:
                    war = decode(response, type=War)
                except:
                    continue
                if war.state != "notInWar":
                    war_end = coc.Timestamp(data=war.endTime)
                    run_time = war_end.time.replace(tzinfo=utc)
                    if war_end.seconds_until < 0:
                        continue
                    war_prep = coc.Timestamp(data=war.preparationStartTime)
                    opponent_tag = war.opponent.tag if war.opponent.tag != tag else war.clan.tag
                    in_war.add(tag)
                    in_war.add(opponent_tag)
                    war_unique_id = "-".join(sorted([war.clan.tag, war.opponent.tag])) + f"-{int(war_prep.time.timestamp())}"
                    for member in war.clan.members + war.opponent.members:
                        war_timers.append(UpdateOne({"_id" : member.tag}, {"$set" : {"clans" : [war.clan.tag, war.opponent.tag], "time" : war_end.time}}, upsert=True))
                    changes.append(InsertOne({"war_id" : war_unique_id,
                                              "clans" : [tag, opponent_tag],
                                              "endTime" : int(war_end.time.replace(tzinfo=utc).timestamp())
                                              }))
                    #schedule getting war
                    try:
                        scheduler.add_job(store_war, 'date', run_date=run_time, args=[tag, opponent_tag, int(coc.Timestamp(data=war.preparationStartTime).time.timestamp())],
                                          id=f"war_end_{tag}_{opponent_tag}", name=f"{tag}_war_end_{opponent_tag}", misfire_grace_time=1200, max_instances=250)
                    except Exception:
                        ones_that_tried_again.append(tag)
                        pass
            if changes:
                try:
                    await clan_wars.bulk_write(changes, ordered=False)
                except Exception:
                    pass

            if war_timers:
                try:
                    await war_timer.bulk_write(war_timers, ordered=False)
                except Exception:
                    pass

        if ones_that_tried_again:
            print(f"{len(ones_that_tried_again)} tried again, examples: {ones_that_tried_again[:5]}")


async def store_war(clan_tag: str, opponent_tag: str, prep_time: int):
    global in_war

    if clan_tag in in_war:
        in_war.remove(clan_tag)
    if opponent_tag in in_war:
        in_war.remove(opponent_tag)

    async def get_war(clan_tag : str):
        try:
            war = await coc_client.get_clan_war(clan_tag=clan_tag)
            return war
        except (coc.NotFound, coc.errors.Forbidden, coc.errors.PrivateWarLog):
            return "no access"
        except coc.errors.Maintenance:
            return "maintenance"
        except Exception:
            return "error"

    switched = False
    war = None
    war_found = False
    while not war_found:
        war = await get_war(clan_tag=clan_tag)
        if isinstance(war, coc.ClanWar):
            if war.preparation_start_time is None or int(war.preparation_start_time.time.timestamp()) != prep_time:
                if not switched:
                    clan_tag = opponent_tag
                    switched = True
                    continue
                else:
                    break
            elif war.state == "warEnded":
                war_found = True
                break
        elif war == "maintenance":
            await asyncio.sleep(30)
            continue
        elif war == "no access":
            if not switched:
                clan_tag = opponent_tag
                switched = True
                continue
            else:
                break
        elif war == "error":
            break
        await asyncio.sleep(war._response_retry)

    if not war_found:
        return

    war_unique_id = "-".join(sorted([war.clan.tag, war.opponent.tag])) + f"-{int(war.preparation_start_time.time.timestamp())}"

    war_result = await clan_wars.find_one({"war_id" : war_unique_id})
    if war_result.get("data") is not None:
        return

    source = string.ascii_letters
    custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()
    is_used = await clan_wars.find_one({"custom_id": custom_id})
    while is_used is not None:
        custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()
        is_used = await clan_wars.find_one({"custom_id": custom_id})

    await clan_wars.update_one({"war_id": war_unique_id},
        {"$set" : {
        "custom_id": custom_id,
        "data": war._raw_data,
        "type" : war.type}}, upsert=True)




loop = asyncio.get_event_loop()
keys = create_keys()
coc_client.login_with_keys(*keys[:10])
loop.create_task(broadcast(keys[11:]))
loop.run_forever()
