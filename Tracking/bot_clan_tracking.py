import os
import time

from redis import asyncio as redis
from dotenv import load_dotenv
load_dotenv()
import asyncio
import collections
import pytz

from pymongo import UpdateOne, InsertOne
from datetime import timedelta


import ujson
import coc
import motor.motor_asyncio
import aiohttp
from Tracking.utils import HTTPClient, Route
from datetime import datetime
from Tracking.utils import create_keys


from kafka import KafkaProducer

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

coc_client= coc.Client(key_names="keys for my windows pc", key_count=5, raw_attribute=True)

async def send_ws(ws, json: dict, client: set):
    try:
        await ws.send_json(json)
    except Exception:
        try:
            client.remove(ws)
        except Exception:
            pass


WAR_CACHE = {}
CAPITAL_CACHE = {}
CAPITAL_ATTACK_CACHE = {}
CLAN_CACHE = {}
REMINDERS = []

async def broadcast(keys: list):
    producer = KafkaProducer(bootstrap_servers=["85.10.200.219:9092"], api_version=(3, 6, 0))
    while True:
        r = time.time()
        print("start loop")
        http_client = HTTPClient()
        keys = collections.deque(keys)
        clan_tags = await clan_db.distinct("tag")

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
                    return [clan_tag, return_value]
                else:
                    return [clan_tag, (next_round, current_round)]

            war_tasks.append(get_war(clan_tag=tag, headers=headers))
        war_responses = await asyncio.gather(*war_tasks)

        #print(responses)
        print(f"{len(war_responses)} wars")

        for response in war_responses:
            clan_tag = response[0]
            next_war, current_war = response[1]
            wars = [next_war, current_war]
            for war in wars:
                if war is None:
                    continue
                war = coc.ClanWar(data=war, client=coc_client, clan_tag=clan_tag)

                league_group = None
                if war.is_cwl:
                    league_group: coc.ClanWarLeagueGroup = war.league_group
                    league_group = league_group._raw_data

                war_unique_id = "-".join(sorted([war.clan_tag, war.opponent.tag])) + f"-{int(war.preparation_start_time.time.timestamp())}"
                previous_war: coc.ClanWar = WAR_CACHE.get(war_unique_id)
                WAR_CACHE[war_unique_id] = war

                if previous_war is None:
                    continue

                if previous_war.attacks:
                    new_attacks = (a for a in war.attacks if a not in set(previous_war.attacks))
                else:
                    new_attacks = war.attacks

                for attack in new_attacks:
                    json_data = {"type": "new_attack", "war": war._raw_data, "league_group": league_group,
                            "attack": attack._raw_data, "clan_tag": clan_tag}
                    producer.send("war", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))

                previous_league_group = None
                if previous_war.is_cwl:
                    previous_league_group: coc.ClanWarLeagueGroup = previous_war.league_group
                    previous_league_group = previous_league_group._raw_data

                #NEW WAR
                if previous_war.preparation_start_time and war.preparation_start_time and previous_war.preparation_start_time.time != war.preparation_start_time.time:
                    if previous_war.state != "warEnded":
                        json_data = {"type": "war_ended", "war": previous_war._raw_data, "league_group": previous_league_group, "clan_tag": clan_tag}
                        producer.send("war", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))
                    json_data = {"type": "new_war", "war": war._raw_data, "league_group": league_group, "clan_tag": clan_tag}
                    producer.send("war", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))
                elif war.preparation_start_time and not previous_war.preparation_start_time:
                    json_data = {"type": "new_war", "war": war._raw_data, "league_group": league_group, "clan_tag": clan_tag}
                    producer.send("war", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))

                if war.state != previous_war.state and previous_war.state == "warEnded":
                    json_data = {"type": "war_ended", "war": previous_war._raw_data, "league_group": previous_league_group, "clan_tag": clan_tag}
                    producer.send("war", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))
                #if war state is "warEnded", send war_end event

        if is_raids():
            capital_tasks = []
            for tag in clan_tags:
                headers = {"Authorization": f"Bearer {keys[0]}"}
                keys.rotate(1)

                async def get_raid(clan_tag: str, headers):
                    clan_tag_for_url = clan_tag.replace('#', '%23')
                    raid_log = await http_client.request(Route("GET", f"/clans/{clan_tag_for_url}/capitalraidseasons?limit=1"), headers=headers)
                    if len(raid_log.get("items", [])) == 0:
                        return None
                    raid = coc.RaidLogEntry(data=raid_log.get("items")[0], client=coc_client, clan_tag=clan_tag)
                    previous_raid = CAPITAL_CACHE.get(clan_tag)
                    CAPITAL_CACHE[clan_tag] = raid

                    if previous_raid is None:
                        return None

                    if previous_raid.attack_log:
                        new_clans = (clan for clan in raid.attack_log if clan not in previous_raid.attack_log)
                    else:
                        new_clans = raid.attack_log

                    for clan in new_clans:
                        json_data = {"type": "new_offensive_opponent", "clan": clan._raw_data, "clan_tag": clan_tag, "raid" : raid._raw_data}
                        producer.send("capital", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))

                    changes = []
                    for member in raid.members:
                        CAPITAL_ATTACK_CACHE[member.tag] = (member.attack_count, member.attack_limit + member.bonus_attack_limit)
                        old_member = coc.utils.get(previous_raid.members, tag=member.tag)
                        if old_member is None:
                            continue
                        if old_member.attack_count != member.attack_count:
                            changes.append((old_member, member))

                    for old_member, member in changes:
                        json_data = {"type": "raid_attacks",
                                     "clan_tag": raid.clan_tag,
                                     "old_member": old_member._raw_data,
                                     "new_member": member._raw_data,
                                     "raid": raid._raw_data}
                        producer.send("capital", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))

                    if raid.state != previous_raid.state:
                        json_data = {"type": "raid_state", "clan_tag": raid.clan_tag, "old_raid": previous_raid._raw_data, "raid": raid._raw_data}
                        producer.send("capital", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))

                capital_tasks.append(get_raid(clan_tag=tag, headers=headers))

            await asyncio.gather(*capital_tasks)


        clan_tasks = []
        connector = aiohttp.TCPConnector(limit=500)
        async with aiohttp.ClientSession(connector=connector) as session:
            for tag in clan_tags:
                headers = {"Authorization": f"Bearer {keys[0]}"}
                tag = tag.replace("#", "%23")
                url = f"https://api.clashofclans.com/v1/clans/{tag}"
                keys.rotate(1)

                async def fetch(url, session, headers):
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            return (await response.json())
                        return None

                clan_tasks.append(fetch(url, session, headers))
            clan_responses = await asyncio.gather(*clan_tasks, return_exceptions=True)
            await session.close()

        print(f"{len(clan_responses)} clans")
        for count, clan_response in enumerate(clan_responses):
            if clan_response is None:
                continue
            clan = coc.Clan(data=clan_response, client=coc_client)

            previous_clan: coc.Clan = CLAN_CACHE.get(clan.tag)
            CLAN_CACHE[clan.tag] = clan

            if previous_clan is None:
                continue

            attributes = ["level", "type", "description", "location", "capital_league", "required_townhall", "required_trophies", "war_win_streak", "war_league", "member_count"]
            for attribute in attributes:
                if getattr(clan, attribute) != getattr(previous_clan, attribute):
                    json_data = {"type": attribute, "old_clan": previous_clan._raw_data, "new_clan": clan._raw_data}
                    producer.send("clan", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))
            current_tags = set(n.tag for n in previous_clan.members)
            if current_tags:
                # we can't check the member_count first incase 1 person left and joined within the 60sec.
                members_joined = (n for n in clan.members if n.tag not in current_tags)
                for member in members_joined:
                    json_data = {"type": "member_join", "clan": clan._raw_data, "member" : member._raw_data}
                    producer.send("clan", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))

            current_tags = set(n.tag for n in clan.members)
            if current_tags:
                members_left = (n for n in previous_clan.members if n.tag not in current_tags)
                for member in members_left:
                    json_data = {"type": "member_leave", "clan": clan._raw_data, "member": member._raw_data}
                    producer.send("clan", ujson.dumps(json_data).encode("utf-8"), timestamp_ms=int(datetime.now(tz=pytz.utc).timestamp() * 1000))

        print(f"finished: {time.time() - r}")





def is_raids():
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    current_dayofweek = now.weekday()
    if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (current_dayofweek == 0 and now.hour < 9):
        raid_on = True
    else:
        raid_on = False
    return raid_on

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    keys = create_keys(emails=EMAILS, passwords=PASSWORDS)
    loop.create_task(broadcast(keys=keys))
    loop.run_forever()


