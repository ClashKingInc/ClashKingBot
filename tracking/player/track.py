from collections import deque
from redis import asyncio as redis
import aiohttp
import asyncio
import pendulum as pend
import ujson
import time
import snappy

from msgspec.json import decode
from loguru import logger
from tracking.player.utils import Player, get_player_changes, gen_legend_date, gen_season_date, gen_raid_date, gen_games_season

from pymongo import InsertOne, UpdateOne


async def get_clan_member_tags(clan_db, keys: deque):
    clan_tags = await clan_db.distinct("tag")

    tasks = []
    connector = aiohttp.TCPConnector(limit=250)
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
    return CLAN_MEMBERS, set(clan_tags)


async def get_tags_to_track(CLAN_MEMBERS: list, loop_spot: int, player_stats):
    # people only become unpaused by joining a clan again or being tracked in legends again
    gone_for_a_month = int(pend.now(tz=pend.UTC).timestamp()) - 2_592_000
    # 1/15 loops, only track legend members & clan members
    if loop_spot % 15 != 0 and loop_spot % 150 != 0:
        db_tags = await player_stats.distinct("tag", filter={"league": "Legend League"})
        all_tags_to_track = list(set(db_tags + CLAN_MEMBERS))
    else:
        # every 150 loops track those that have been gone for a month, every 15th loop we check those that have been gone for less (active)
        if loop_spot % 150 == 0:
            pipeline = [{"$match": {"last_online": {"$lte": gone_for_a_month}}}, {"$project": {"tag": "$tag"}}, {"$unset": "_id"}]
        else:
            pipeline = [{"$match": {"last_online": {"$gte": gone_for_a_month}}}, {"$project": {"tag": "$tag"}}, {"$unset": "_id"}]
        db_tags = [x["tag"] for x in (await player_stats.aggregate(pipeline).to_list(length=None))]
        all_tags_to_track = list(set(db_tags + CLAN_MEMBERS))

    return all_tags_to_track


async def add_new_autocomplete_additions(cache: redis.Redis, all_tags: list, player_search):
    # add any new additions to the autocomplete
    pipeline = [{"$match": {}}, {"$project": {"tag": "$tag"}}, {"$unset": "_id"}]
    autocomplete_tags = [x["tag"] for x in (await player_search.aggregate(pipeline).to_list(length=None))]
    autocomplete_tags = set(autocomplete_tags)
    add_to_autocomplete = [tag for tag in all_tags if tag not in autocomplete_tags]
    auto_changes = []
    for tag in add_to_autocomplete:
        try:
            r = await cache.get(tag)
            if r is None:
                continue
            r = snappy.decompress(r)
            r = ujson.loads(r)
            clan_tag = r.get("clan", {}).get("tag", "Unknown")
            league = r.get("league", {}).get("name", "Unranked")
            auto_changes.append(InsertOne({"name": r.get("name"), "clan": clan_tag, "league": league, "tag": r.get("tag"), "th": r.get("townHallLevel")}))
        except Exception:
            continue
    if auto_changes:
        await player_search.bulk_write(auto_changes)


async def get_player_responses(keys: deque, tags: list[str], cache: redis.Redis, player_stats, player_search):
    tasks = []
    connector = aiohttp.TCPConnector(limit=2000, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=1800)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for tag in tags:
            keys.rotate(1)
            async def fetch(url, session: aiohttp.ClientSession, headers):
                async with session.get(url, headers=headers) as new_response:
                    if new_response.status == 404:  # remove banned players
                        t = url.split("%23")[-1]
                        await player_stats.delete_one({"tag": f"#{t}"})
                        await cache.getdel(f"#{t}")
                        await player_search.delete_one({"tag": f"#{t}"})
                        return None
                    elif new_response.status != 200:
                        return None
                    new_response = await new_response.read()
                    return new_response
            tasks.append(fetch(url=f'https://api.clashofclans.com/v1/players/{tag.replace("#", "%23")}', session=session, headers={"Authorization": f"Bearer {keys[0]}"}))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await session.close()
    return results


async def player_response_handler(new_response: bytes, cache: redis.Redis, bulk_db_changes: list, auto_complete: list, set_clan_tags: set, bulk_insert: list, bulk_clan_changes: list):
    obj = decode(new_response, type=Player)
    compressed_new_response = snappy.compress(new_response)
    previous_compressed_response = await cache.get(obj.tag)

    if compressed_new_response != previous_compressed_response:
        await cache.set(obj.tag, compressed_new_response, ex=2_592_000)
        if previous_compressed_response is None:
            return None

        BEEN_ONLINE = False
        new_response = ujson.loads(new_response)

        previous_response = snappy.decompress(previous_compressed_response)
        previous_response = ujson.loads(previous_response)

        season = gen_season_date()
        raid_date = gen_raid_date()
        games_season = gen_games_season()
        legend_date = gen_legend_date()

        tag = obj.tag
        clan_tag = new_response.get("clan", {}).get("tag", "Unknown")
        league = new_response.get("league", {}).get("name", "Unranked")
        prev_league = previous_response.get("league", {}).get("name", "Unranked")
        if league != prev_league:
            bulk_db_changes.append(UpdateOne({"tag": tag}, {"$set": {"league": league}}))
            auto_complete.append(UpdateOne({"tag": tag}, {"$set": {"league": league}}))

        is_clan_member = clan_tag in set_clan_tags

        changes, fields_to_update = get_player_changes(previous_response, new_response)
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
        ws_types = {"clanCapitalContributions", "name", "troops", "heroes", "spells", "heroEquipment",
                    "townHallLevel",
                    "league", "trophies", "Most Valuable Clanmate"}
        only_once = {"troops": 0, "heroes": 0, "spells": 0, "heroEquipment": 0}
        ws_tasks = []
        if changes:
            player_level_changes = {}
            clan_level_changes = {}
            for (parent, type_), (old_value, value) in changes.items():
                if type_ in special_types:
                    bulk_db_changes.append(UpdateOne({"tag": tag},
                                                     {"$set": {f"{type_.replace(' ', '_').lower()}": value}},
                                                     upsert=True))

                if type_ not in skip_store_types:
                    if old_value is None:
                        bulk_insert.append(InsertOne({"tag": tag, "type": type_, "value": value,
                                                      "time": int(pend.now(tz=pend.UTC).timestamp()),
                                                      "clan": clan_tag, "th": new_response.get("townHallLevel")}))
                    else:
                        bulk_insert.append(InsertOne(
                            {"tag": tag, "type": type_, "p_value": old_value, "value": value,
                             "time": int(pend.now(tz=pend.UTC).timestamp()), "clan": clan_tag, "th": new_response.get("townHallLevel")}))


                if type_ == "donations":
                    previous_dono = 0 if (previous_dono := previous_response["donations"]) > (current_dono := new_response["donations"]) else previous_dono
                    player_level_changes.update({"$inc": {f"donations.{season}.donated": (current_dono - previous_dono)}})
                    clan_level_changes.update({"$inc": {f"{season}.{tag}.donations": (current_dono - previous_dono)}})

                elif type_ == "donationsReceived":
                    previous_dono = 0 if (previous_dono := previous_response["donationsReceived"]) > (current_dono := new_response["donationsReceived"]) else previous_dono
                    player_level_changes.update({"$inc": {f"donations.{season}.received": (current_dono - previous_dono)}})
                    clan_level_changes.update({"$inc": {f"{season}.{tag}.received": (current_dono - previous_dono)}})

                elif type_ == "clanCapitalContributions":
                    player_level_changes.update({"$push": {f"capital_gold.{raid_date}.donate": (new_response["clanCapitalContributions"] -previous_response["clanCapitalContributions"])}})
                    clan_level_changes.update({"$inc": {f"{season}.{tag}.capital_gold_dono": (new_response["clanCapitalContributions"] - previous_response["clanCapitalContributions"])}})
                    type_ = "Most Valuable Clanmate"  # temporary

                elif type_ == "Gold Grab":
                    diff = value - old_value
                    player_level_changes.update({"$inc": {f"gold.{season}": diff}})
                    clan_level_changes.update({"$inc": {f"{season}.{tag}.gold_looted": diff}})

                elif type_ == "Elixir Escapade":
                    diff = value - old_value
                    player_level_changes.update({"$inc": {f"elixir.{season}": diff}})
                    clan_level_changes.update({"$inc": {f"{season}.{tag}.elixir_looted": diff}})

                elif type_ == "Heroic Heist":
                    diff = value - old_value
                    player_level_changes.update({"$inc": {f"dark_elixir.{season}": diff}})
                    clan_level_changes.update({"$inc": {f"{season}.{tag}.dark_elixir_looted": diff}})

                elif type_ == "Well Seasoned":
                    diff = value - old_value
                    player_level_changes.update({"$inc": {f"season_pass.{games_season}": diff}})

                elif type_ == "Games Champion":
                    diff = value - old_value
                    player_level_changes.update({"$inc": {f"clan_games.{games_season}.points": diff},
                                                "$set": {f"clan_games.{games_season}.clan": clan_tag}})
                    clan_level_changes.update({"$inc": {f"{games_season}.{tag}.clan_games": diff}})


                elif type_ == "attackWins":
                    player_level_changes.update({"$set": {f"attack_wins.{season}": value}})
                    clan_level_changes.update({"$set": {f"{season}.{tag}.attack_wins": value}})


                elif type_ == "trophies":
                    player_level_changes.update({"$set": {f"season_trophies.{season}": value}})
                    clan_level_changes.update({"$set": {f"{season}.{tag}.trophies": value}})


                elif type_ == "name":
                    player_level_changes.update({"$set": {f"name": value}})
                    auto_complete.append(UpdateOne({"tag": tag}, {"$set": {"name": value}}))

                elif type_ == "clan":
                    player_level_changes.update({"$set": {f"clan_tag": clan_tag}})
                    auto_complete.append(UpdateOne({"tag": tag}, {"$set": {"clan": clan_tag}}))

                elif type_ == "townHallLevel":
                    player_level_changes.update({"$set": {f"townhall": value}})
                    auto_complete.append(UpdateOne({"tag": tag}, {"$set": {"th": value}}))

                elif parent in {"troops", "heroes", "spells", "heroEquipment"}:
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
                    json_data = {"type": type_, "old_player": previous_response,
                                 "new_player": new_response, "timestamp" : int(pend.now(tz=pend.UTC).timestamp())}
                    await cache.publish(channel="player", message=ujson.dumps(json_data).encode("utf-8"))

            if player_level_changes:
                bulk_db_changes.append(UpdateOne(
                    {"tag": tag},
                    player_level_changes,
                    upsert=True
                ))

            if clan_level_changes and is_clan_member:
                clan_level_changes.update({"$set" : {f"{season}.{tag}.name": new_response.get("name")}})
                clan_level_changes.update({"$set" : {f"{season}.{tag}.townhall" : new_response.get("townHallLevel")}})
                bulk_clan_changes.append(UpdateOne(
                    {"tag": clan_tag},
                    clan_level_changes,
                    upsert=True
                ))
        # LEGENDS CODE, dont fix what aint broke


        if new_response["trophies"] != previous_response["trophies"] and new_response["trophies"] >= 4900 and league == "Legend League":
            diff_trophies = new_response["trophies"] - previous_response["trophies"]
            diff_attacks = new_response["attackWins"] - previous_response["attackWins"]

            if diff_trophies <= - 1:
                diff_trophies = abs(diff_trophies)
                if diff_trophies <= 100:
                    bulk_db_changes.append(UpdateOne({"tag": tag},
                                                     {"$push": {f"legends.{legend_date}.defenses": diff_trophies}}, upsert=True))

                    bulk_db_changes.append(UpdateOne({"tag": tag},
                                                     {"$push": {f"legends.{legend_date}.new_defenses": {
                                                         "change": diff_trophies,
                                                         "time": int(pend.now(tz=pend.UTC).timestamp()),
                                                         "trophies": new_response["trophies"]
                                                     }}}, upsert=True))

            elif diff_trophies >= 1:
                heroes = new_response.get("heroes", [])
                equipment = []
                for hero in heroes:
                    for gear in hero.get("equipment", []):
                        equipment.append({"name": gear.get("name"), "level": gear.get("level")})

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
                    bulk_db_changes.append(UpdateOne({"tag": tag},
                                                     {"$push": {f"legends.{legend_date}.new_attacks": {
                                                         "change": diff_trophies,
                                                         "time": int(pend.now(tz=pend.UTC).timestamp()),
                                                         "trophies": new_response["trophies"],
                                                         "hero_gear": equipment
                                                     }}}, upsert=True))
                    if diff_trophies == 40:
                        bulk_db_changes.append(
                            UpdateOne({"tag": tag}, {"$inc": {f"legends.streak": 1}}))

                    else:
                        bulk_db_changes.append(
                            UpdateOne({"tag": tag}, {"$set": {f"legends.streak": 0}}))

                # if multiple attacks, but divisible by 40
                elif diff_attacks > 1 and diff_trophies / 40 == diff_attacks:
                    for x in range(0, diff_attacks):
                        bulk_db_changes.append(
                            UpdateOne({"tag": tag},
                                      {"$push": {f"legends.{legend_date}.attacks": 40}},
                                      upsert=True))
                        bulk_db_changes.append(UpdateOne({"tag": tag},
                                                         {"$push": {f"legends.{legend_date}.new_attacks": {
                                                             "change": 40,
                                                             "time": int(pend.now(tz=pend.UTC).timestamp()),
                                                             "trophies": new_response["trophies"],
                                                             "hero_gear": equipment
                                                         }}}, upsert=True))
                    bulk_db_changes.append(
                        UpdateOne({"tag": tag}, {"$inc": {f"legends.streak": diff_attacks}}))
                else:
                    bulk_db_changes.append(UpdateOne({"tag": tag},
                                                     {"$push": {
                                                         f"legends.{legend_date}.attacks": diff_trophies}},
                                                     upsert=True))
                    bulk_db_changes.append(UpdateOne({"tag": tag},
                                                     {"$push": {f"legends.{legend_date}.new_attacks": {
                                                         "change": diff_trophies,
                                                         "time": int(pend.now(tz=pend.UTC).timestamp()),
                                                         "trophies": new_response["trophies"],
                                                         "hero_gear": equipment
                                                     }}}, upsert=True))

                    bulk_db_changes.append(
                        UpdateOne({"tag": tag}, {"$set": {f"legends.streak": 0}}, upsert=True))

            if new_response["defenseWins"] != previous_response["defenseWins"]:
                diff_defenses = new_response["defenseWins"] - previous_response["defenseWins"]
                for x in range(0, diff_defenses):
                    bulk_db_changes.append(
                        UpdateOne({"tag": tag}, {"$push": {f"legends.{legend_date}.defenses": 0}},
                                  upsert=True))
                    bulk_db_changes.append(UpdateOne({"tag": tag},
                                                     {"$push": {f"legends.{legend_date}.new_defenses": {
                                                         "change": 0,
                                                         "time": int(pend.now(tz=pend.UTC).timestamp()),
                                                         "trophies": new_response["trophies"]
                                                     }}}, upsert=True))

        if BEEN_ONLINE:
            _time = int(pend.now(tz=pend.UTC).timestamp())
            bulk_db_changes.append(
                UpdateOne({"tag": tag}, {
                    "$inc": {f"activity.{season}": 1},
                    "$push": {f"last_online_times.{season}": _time},
                    "$set": {"last_online": _time}
                }, upsert=True))
            bulk_clan_changes.append(
                UpdateOne({"tag": clan_tag},
                          {"$inc": {f"{season}.{tag}.activity": 1}},
                          upsert=True))

        await asyncio.gather(*ws_tasks)


async def main(keys: deque, cache: redis.Redis, stats_mongo_client, static_mongo_client, config):
    player_stats = stats_mongo_client.new_looper.player_stats
    clan_stats = stats_mongo_client.new_looper.clan_stats

    clan_db = static_mongo_client.usafam.clans
    player_search = static_mongo_client.usafam.player_search


    loop_spot = -1
    while True:
        try:
            loop_spot += 1
            CLAN_MEMBERS, clan_tag_set = await get_clan_member_tags(clan_db=clan_db, keys=keys)
            all_tags = await get_tags_to_track(CLAN_MEMBERS=CLAN_MEMBERS, loop_spot=loop_spot, player_stats=player_stats)
            await add_new_autocomplete_additions(cache=cache, all_tags=all_tags, player_search=player_search)

            logger.info(f"LOOP{loop_spot}: {len(all_tags)} tags")
            split_tags = [all_tags[i:i + config.max_tag_split] for i in range(0, len(all_tags), config.max_tag_split)]
            logger.info(f"{len(split_tags)} tag groups created")

            time_inside = time.time()
            bulk_db_changes = []
            bulk_insert = []
            bulk_clan_changes = []
            auto_complete = []

            for count, tag_group in enumerate(split_tags, 1):
                group_time_inside = time.time()
                responses = await get_player_responses(keys=keys, tags=tag_group, cache=cache, player_stats=player_stats, player_search=player_search)
                for response in responses:
                    if not isinstance(response, bytes):
                        continue
                    await player_response_handler(new_response=response, cache=cache, bulk_db_changes=bulk_db_changes,
                                                  bulk_insert=bulk_insert, bulk_clan_changes=bulk_clan_changes, auto_complete=auto_complete,
                                                  set_clan_tags=clan_tag_set)
                logger.info(f"GROUP {count} | {len(tag_group)} tags: {time.time() - group_time_inside} sec inside")


            logger.info(f"{len(bulk_db_changes)} db changes")
            if bulk_db_changes != []:
                results = await player_stats.bulk_write(bulk_db_changes)
                logger.info(results.bulk_api_result)
                logger.info(f"STAT CHANGES INSERT: {time.time() - time_inside}")

            if auto_complete != []:
                results = await player_search.bulk_write(auto_complete)
                logger.info(results.bulk_api_result)
                logger.info(f"AUTOCOMPLETE CHANGES: {time.time() - time_inside}")

            if bulk_insert != []:
                results = await stats_mongo_client.new_looper.player_history.bulk_write(bulk_insert)
                logger.info(results.bulk_api_result)
                logger.info(f"HISTORY CHANGES INSERT: {time.time() - time_inside}")

            if bulk_clan_changes != []:
                results = await clan_stats.bulk_write(bulk_clan_changes)
                logger.info(results.bulk_api_result)
                logger.info(f"CLAN CHANGES UPDATE: {time.time() - time_inside}")

            fix_changes = []
            not_set_entirely = await player_stats.distinct("tag", filter={"$or": [{"name": None}, {"league": None}, {"townhall": None}, {"clan_tag": None}]})
            logger.info(f'{len(not_set_entirely)} tags to fix')
            for tag in not_set_entirely:
                try:
                    response = await cache.get(tag)
                    response = snappy.decompress(response)
                    response = ujson.loads(response)
                    clan_tag = response.get("clan", {}).get("tag", "Unknown")
                    league = response.get("league", {}).get("name", "Unranked")
                    fix_changes.append(UpdateOne({"tag": tag}, {
                        "$set": {"name": response.get('name'), "townhall": response.get('townHallLevel'), "league": league,
                                 "clan_tag": clan_tag}}))
                except Exception:
                    continue

            if fix_changes != []:
                results = await player_stats.bulk_write(fix_changes)
                logger.info(results.bulk_api_result)
                logger.info(f"FIX CHANGES: {time.time() - time_inside}")
        except Exception:
            continue









