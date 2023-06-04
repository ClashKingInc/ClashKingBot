import pytz
from disnake.ext import commands
import disnake
from typing import List, TYPE_CHECKING
import coc
from datetime import datetime
import pandas as pd
from utils.general import notate_number as B, custom_round
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from collections import defaultdict
from utils.constants import SHORT_PLAYER_LINK, item_to_name, TOWNHALL_LEVELS
from utils.graphing import graph_creator
import stringcase

async def donation_board(bot: CustomClient, players: List[MyCustomPlayer], season: str, footer_icon: str, title_name: str, type: str,
                         limit: int = 50,
                         embed_color: disnake.Color = disnake.Color.green(), **kwargs) -> disnake.Embed:
    if type == "donations":
        players.sort(key=lambda x: x.donos(date=season).donated, reverse=True)
    elif type == "received":
        players.sort(key=lambda x: x.donos(date=season).received, reverse=True)

    if type == "donations":
        text = "`  #  DON     REC     NAME     `\n"
    else:
        text = "`  #  REC     DON     NAME     `\n"

    total_donated = 0
    total_received = 0
    our_tags = kwargs.get("account_tags", [])
    for count, player in enumerate(players, 1):
        tag = player.tag.strip("#")
        star = "⭐" if player.tag in our_tags else ""
        if count <= limit:
            if type == "donations":
                text += f"[⌕]({SHORT_PLAYER_LINK}{tag})`{count:2} {player.donos(date=season).donated:5} {player.donos(date=season).received:5} {player.clear_name[:13]:13}`{star}\n"
            else:
                text += f"[⌕]({SHORT_PLAYER_LINK}{tag})`{count:2} {player.donos(date=season).received:5} {player.donos(date=season).donated:5} {player.clear_name[:13]:13}`{star}\n"

        total_donated += player.donos(date=season).donated
        total_received += player.donos(date=season).received
    if kwargs.get("total_donos") is not None:
        total_donated = kwargs.get("total_donos")
    if kwargs.get("total_received") is not None:
        total_received = kwargs.get("total_received")

    embed = disnake.Embed(description=f"{text}", color=embed_color)
    embed.set_author(name=f"{title_name} Top {min(limit, len(players))} {type.capitalize()}",
                     icon_url=bot.emoji.clan_castle.partial_emoji.url)
    if footer_icon is None:
        footer_icon = bot.user.avatar.url
    embed.set_footer(icon_url=footer_icon,
                     text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {season}")
    embed.timestamp = datetime.now()
    return embed

async def hero_progress(bot: CustomClient, player_tags: List[str], season: str, footer_icon: str, title_name: str, limit: int = 50, embed_color: disnake.Color = disnake.Color.green()):
    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))

    pipeline = [
        {"$match": {"$and": [{"tag": {"$in": player_tags}}, {"type": {"$in" : list(coc.enums.HERO_ORDER + coc.enums.PETS_ORDER)}},
                             {"time" : {"$gte" : season_start.timestamp()}}, {"time" : {"$lte" : season_end.timestamp()}}]}},
        {"$group": {"_id": {"tag" : "$tag", "type" : "$type"}, "num": {"$sum": 1}}},
        {"$group" : {"_id" : "$_id.tag", "hero_counts" : {"$push" : {"hero_name" : "$_id.type", "count" : "$num"}}}},
        {"$lookup" : {"from" : "player_stats", "localField" : "_id", "foreignField" : "tag", "as" : "name"}},
        {"$set" : {"name" : "$name.name"} }
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)

    class ItemHolder():
        def __init__(self, data: dict):
            self.tag = data.get("_id")
            self.name = data.get("name", ["unknown"])[0]
            self.king = next((item["count"] for item in data["hero_counts"] if item["hero_name"] == "Barbarian King"), 0)
            self.queen = next((item["count"] for item in data["hero_counts"] if item["hero_name"] == "Archer Queen"), 0)
            self.warden = next((item["count"] for item in data["hero_counts"] if item["hero_name"] == "Grand Warden"), 0)
            self.rc = next((item["count"] for item in data["hero_counts"] if item["hero_name"] == "Royal Champion"), 0)
            self.pets = sum(
                next((item["count"] for item in data["hero_counts"] if item["hero_name"] == pet), 0) for pet in coc.enums.PETS_ORDER
            )
            self.total_upgraded = self.king + self.queen + self.warden + self.rc + self.pets

    all_items = []
    for result in results:
        all_items.append(
            ItemHolder(data=result)
        )
    all_items = sorted(all_items, key=lambda x: x.total_upgraded, reverse=True)[:min(limit, len(all_items))]
    if not all_items:
        embed = disnake.Embed(title=title_name, description="**No Upgrades Yet**",
                              colour=disnake.Color.red())
    else:
        text = f"BK AQ WD RC Pet Name          \n"
        for item in all_items:
            text += f"{item.king:<2} {item.queen:<2} {item.warden:<2} {item.rc:<2}  {item.pets:<2} {item.name[:13]}\n"
        embed = disnake.Embed(title=title_name, description=f"```{text}```",
                              colour=embed_color)
    embed.timestamp = datetime.now()
    embed.set_footer(text=season, icon_url=footer_icon)
    return embed


async def troops_spell_siege_progress(bot: CustomClient, player_tags: List[str], season: str, footer_icon: str, title_name: str, limit: int = 50, embed_color: disnake.Color = disnake.Color.green()):
    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))

    pipeline = [
        {"$match": {"$and": [{"tag": {"$in": player_tags}}, {"type": {"$in" : list(coc.enums.HOME_TROOP_ORDER + coc.enums.SPELL_ORDER + coc.enums.BUILDER_TROOPS_ORDER)}},
                             {"time" : {"$gte" : season_start.timestamp()}}, {"time" : {"$lte" : season_end.timestamp()}}]}},
        {"$group": {"_id": {"tag" : "$tag", "type" : "$type"}, "num": {"$sum": 1}}},
        {"$group" : {"_id" : "$_id.tag", "counts" : {"$push" : {"name" : "$_id.type", "count" : "$num"}}}},
        {"$lookup" : {"from" : "player_stats", "localField" : "_id", "foreignField" : "tag", "as" : "name"}},
        {"$set" : {"name" : "$name.name"} }
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)
    class ItemHolder():
        def __init__(self, data: dict):
            self.tag = data.get("_id")
            self.name = data.get("name", ["unknown"])[0]
            self.troops = sum(
                next((item["count"] for item in data["counts"] if item["name"] == troop and troop != "Baby Dragon"), 0) for troop in list(set(coc.enums.HOME_TROOP_ORDER) - set(coc.enums.SIEGE_MACHINE_ORDER))
            )
            self.spells = sum(
                next((item["count"] for item in data["counts"] if item["name"] == spell), 0) for spell in coc.enums.SPELL_ORDER
            )
            self.sieges = sum(
                next((item["count"] for item in data["counts"] if item["name"] == siege), 0) for siege in coc.enums.SIEGE_MACHINE_ORDER
            )
            self.builder_troops = sum(
                next((item["count"] for item in data["counts"] if item["name"] == b_troop and b_troop != "Baby Dragon"), 0) for b_troop in coc.enums.BUILDER_TROOPS_ORDER
            )
            self.total_upgraded = self.troops + self.spells + self.sieges + self.builder_troops

    all_items = []
    for result in results:
        all_items.append(
            ItemHolder(data=result)
        )
    all_items = sorted(all_items, key=lambda x: x.total_upgraded, reverse=True)[:min(limit, len(all_items))]
    if not all_items:
        embed = disnake.Embed(title=title_name, description="**No Upgrades Yet**",
                              colour=disnake.Color.red())
    else:
        text = f"HT SP SG BT Name          \n"
        for item in all_items:
            if item.total_upgraded == 0:
                continue
            text += f"{item.troops:<2} {item.spells:<2} {item.sieges:<2} {item.builder_troops:<2} {item.name[:13]}\n"
        embed = disnake.Embed(title=title_name, description=f"```{text}```",
                              colour=embed_color)
        embed.set_footer(icon_url=footer_icon, text="HT=Home Troops, SP=Spells, SG=Sieges, BT=Builder Troops")
    embed.timestamp = datetime.now()
    embed.set_footer(text=season, icon_url=footer_icon)
    return embed


async def trophies_progress(bot: CustomClient, player_tags: List[str], season: str, footer_icon: str, title_name: str, type: str, limit: int = 50, embed_color: disnake.Color = disnake.Color.green()):
    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))

    pipeline = [
        {"$match": {"$and": [{"tag": {"$in": player_tags}}, {"type": {"$in" : ["trophies", "builderBaseTrophies"]}},
                             {"time" : {"$gte" : season_start.timestamp()}}, {"time" : {"$lte" : season_end.timestamp()}}]}},
        {"$sort": {"tag" : 1, "time" : 1}},
        {"$group": {"_id": {"tag" : "$tag", "type" : "$type"}, "first": {"$first": "$value"}, "last" : {"$last" : "$value"}}},
        {"$group" : {"_id" : "$_id.tag", "items" : {"$push" : {"name" : "$_id.type", "first" : "$first", "last" : "$last"}}}},
        {"$lookup" : {"from" : "player_stats", "localField" : "_id", "foreignField" : "tag", "as" : "name"}},
        {"$set" : {"name" : "$name.name"} }
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)

    class ItemHolder():
        def __init__(self, data: dict):
            self.data = data
            self.tag = data.get("_id")
            self.name = data.get("name", ["unknown"])[0]
            self.home_trophy_data = next((item for item in self.data["items"] if item["name"] == "trophies"), {})
            self.builder_trophy_data = next((item for item in self.data["items"] if item["name"] == "builderBaseTrophies"), {})

            self.home_trophy_start = self.home_trophy_data.get("first", 0)
            self.home_trophy_end = self.home_trophy_data.get("last", 0)

            self.builder_trophy_start = self.builder_trophy_data.get("first", 0)
            self.builder_trophy_end = self.builder_trophy_data.get("last", 0)

        @property
        def trophies_change(self):
            trophy_change = self.home_trophy_data.get("last", 0) - self.home_trophy_data.get("first", 0)
            if trophy_change >= 0:
                trophy_change = f"+{trophy_change}"
            return trophy_change

        @property
        def builder_trophies_change(self):
            trophy_change = self.builder_trophy_data.get("last", 0) - self.builder_trophy_data.get("first", 0)
            if trophy_change >= 0:
                trophy_change = f"+{trophy_change}"
            return trophy_change

    all_items = []
    for result in results:
        all_items.append(
            ItemHolder(data=result)
        )
    if type == "home":
        all_items = sorted(all_items, key=lambda x: int(str(x.trophies_change).replace("+", "")), reverse=True)[:min(limit, len(all_items))]
    else:
        all_items = sorted(all_items, key=lambda x: int(str(x.builder_trophies_change).replace("+", "")), reverse=True)[:min(limit, len(all_items))]

    if not all_items:
        embed = disnake.Embed(title=title_name, description="**No Progress Yet**",
                              colour=disnake.Color.red())
    else:
        text = f"STRT END  +/-  Name          \n"
        for item in all_items:
            if type == "home":
                if item.home_trophy_start == 0:
                    continue
                text += f"{item.home_trophy_start:>4} {item.home_trophy_end:>4} {item.trophies_change:>4} {item.name[:13]}\n"
            else:
                if item.builder_trophy_start == 0:
                    continue
                text += f"{item.builder_trophy_start:>4} {item.builder_trophy_end:>4} {item.builder_trophies_change:>4} {item.name[:13]}\n"
        embed = disnake.Embed(title=title_name, description=f"```{text}```",
                              colour=disnake.Color.green())
    embed.set_footer(text=season, icon_url=footer_icon)
    embed.timestamp = datetime.now()
    return embed


async def loot_progress(bot: CustomClient, player_tags: List[str], season: str, footer_icon: str, title_name: str, limit: int = 50, embed_color: disnake.Color = disnake.Color.green()):

    pipeline = [
        {"$match": {"tag": {"$in": player_tags}}},
        {"$set" : {
            "de_looted" : {"$sum" : f"$dark_elixir_looted.{season}"},
            "elixir_looted" : {"$sum" : f"$elixir_looted.{season}"},
            "gold_looted" : {"$sum" : f"$gold_looted.{season}"}
            }
        },
        {"$project" : {"tag" : 1, "de_looted" : 1, "elixir_looted" : 1, "gold_looted" : 1, "name" : 1}}
    ]
    results: List[dict] = await bot.player_stats.aggregate(pipeline).to_list(length=None)
    class ItemHolder():
        def __init__(self, data: dict):
            self.data = data
            self.tag = data.get("_id")
            self.name = data.get("name", "unknown")
            self.de_looted = data.get("de_looted")
            self.gold_looted = data.get("gold_looted")
            self.elixir_looted = data.get("elixir_looted")
            self.total_looted = self.de_looted + self.gold_looted + self.elixir_looted

    all_items = []
    for result in results:
        all_items.append(
            ItemHolder(data=result)
        )
    all_items = sorted(all_items, key=lambda x: x.total_looted, reverse=True)[:min(limit, len(all_items))]

    if not all_items:
        embed = disnake.Embed(title=title_name, description="**No Progress Yet**",colour=disnake.Color.red())
    else:
        text = f"GOLD ELIX DELIX Name          \n"
        for item in all_items:
            text += f"{B(item.gold_looted):>4} {B(item.elixir_looted):>4} {B(item.de_looted):>5} {bot.clean_string(item.name)[:13]}\n"
        embed = disnake.Embed(title=title_name, description=f"```{text}```",
                              colour=disnake.Color.green())
    embed.set_footer(text=season, icon_url=footer_icon)
    embed.timestamp = datetime.now()
    return embed


async def activity_board(bot: CustomClient, players: List[MyCustomPlayer], season: str, footer_icon: str, title_name: str, embed_color: disnake.Color = disnake.Color.green()) -> disnake.Embed:
    players.sort(key=lambda x: len(x.season_last_online(season_date=season)), reverse=True)
    text = "`  #  ACT NAME      `\n"
    total_activities = 0
    for count, player in enumerate(players, 1):
        tag = player.tag.strip("#")
        if count <= 50:
            text += f"[⌕]({SHORT_PLAYER_LINK}{tag})`{count:2} {len(player.season_last_online(season_date=season)):4} {player.clear_name[:15]:15}`\n"
        total_activities += len(player.season_last_online(season_date=season))

    embed = disnake.Embed(title=f"**{title_name} Top {len(players)} Activities**", description=f"{text}",
                          color=embed_color)
    if footer_icon is None:
        footer_icon = bot.user.avatar.url
    embed.set_footer(icon_url=footer_icon, text=f"Activities: {'{:,}'.format(total_activities)} | {season}")
    embed.timestamp = datetime.now()
    return embed


async def player_sort(bot: CustomClient, player_tags: List[str], sort_by: str, footer_icon: str, title_name: str, limit: int = 50, embed_color: disnake.Color = disnake.Color.green()):
    sort_by = item_to_name[sort_by]
    sort_by = sort_by.replace("-", "_")
    new_sort_by = stringcase.camelcase(sort_by)
    if not player_tags:
        player_tags = await bot.player_stats.distinct("tag")


    if "ach_" not in sort_by and sort_by not in ["heroes"]:
        sort_way = -1
        if sort_by == "legendStatistics.bestSeason.rank":
            new_sort_by = sort_by
            sort_way = 1

        players = await bot.player_cache.find({"tag": {"$in": player_tags}}).sort([(f"data.{new_sort_by}", sort_way)]).limit(limit).to_list(length=None)

    elif "ach_" in sort_by:
        pipeline = [
            {"$match": {"tag": {"$in": player_tags}}},
            {"$addFields": {
                "order": {
                    "$filter": {
                        "input": "$data.achievements",
                        "as": "p",
                        "cond": {"$eq": ["$$p.name", sort_by.replace('ach_','')]}
                    }
                }
            }},
            {"$sort": {"order": -1}},
            {"$limit" : limit}
        ]
        players = await bot.player_cache.aggregate(pipeline=pipeline).to_list(length=None)
    else:
        pipeline = [
            {"$match": {"tag": {"$in": player_tags}}},
            {"$unwind" : {"path" : "$data.heroes"}},
            {"$match": {"data.heroes.name": {"$in": list(coc.enums.HOME_BASE_HERO_ORDER)}}},
            {"$group": {"_id": {"tag" : "$tag"}, "hero_sum": {"$sum": "$data.heroes.level"}}},
            {"$sort": {"hero_sum": -1}},
            {"$limit": limit},
            {"$lookup": {"from": "player_cache", "localField": "_id.tag", "foreignField": "tag", "as": "data"}},
        ]


        players = await bot.player_cache.aggregate(pipeline=pipeline).to_list(length=None)
        players = [{"data" : player.get("data")[0].get("data")} for player in players]

    def get_longest(players, attribute):
        longest = 0
        for player in players:
            if "ach_" not in attribute and attribute not in ["legendStatistics.bestSeason.rank", "heroes"]:
                spot = len(str(player.__getattribute__(sort_by)))
            elif "ach_" in sort_by:
                spot = len(str(player.get_achievement(name=sort_by.split('_')[-1], default_value=0).value))
            elif sort_by == "season_rank":
                def sort_func(a_player):
                    try:
                        a_rank = a_player.legend_statistics.best_season.rank
                    except:
                        return 0

                spot = len(str(sort_func(player))) + 1
            else:
                spot = len(str(sum([hero.level for hero in player.heroes if hero.is_home_base])))
            if spot > longest:
                longest = spot
        return longest
    players = [coc.Player(data=data.get("data"), client=bot.coc_client) for data in players]
    longest = get_longest(players=players, attribute=sort_by)

    text = ""
    for count, player in enumerate(players, 1):
        if sort_by in ["role", "tag", "heroes", "ach_Friend in Need", "town_hall"]:
            emoji = bot.fetch_emoji(player.town_hall)
        elif sort_by in ["versus_trophies", "versus_attack_wins", "ach_Champion Builder"]:
            emoji = bot.emoji.versus_trophy
        elif sort_by in ["trophies", "ach_Sweet Victory!"]:
            emoji = bot.emoji.trophy
        elif sort_by in ["legendStatistics.bestSeason.rank"]:
            emoji = bot.emoji.legends_shield
        elif sort_by in ["clan_capital_contributions", "ach_Aggressive Capitalism"]:
            emoji = bot.emoji.capital_gold
        elif sort_by in ["exp_level"]:
            emoji = bot.emoji.xp
        elif sort_by in ["ach_Nice and Tidy"]:
            emoji = bot.emoji.clock
        elif sort_by in ["ach_Heroic Heist"]:
            emoji = bot.emoji.dark_elixir
        elif sort_by in ["ach_War League Legend", "war_stars"]:
            emoji = bot.emoji.war_star
        elif sort_by in ["ach_Conqueror", "attack_wins"]:
            emoji = bot.emoji.thick_sword
        elif sort_by in ["ach_Unbreakable"]:
            emoji = bot.emoji.shield
        elif sort_by in ["ach_Games Champion"]:
            emoji = bot.emoji.clan_games

        spot = f"{count}."
        if "ach_" not in sort_by and sort_by not in ["legendStatistics.bestSeason.rank", "heroes"]:
            text += f"`{spot:3}`{emoji}`{player.__getattribute__(sort_by):{longest}} {bot.clean_string(player.name)[:13]}`\n"
        elif "ach_" in sort_by:
            text += f"`{spot:3}`{emoji}`{player.get_achievement(name=sort_by.split('_')[-1], default_value=0).value:{longest}} {bot.clean_string(player.name)[:13]:13}`\n"
        elif sort_by == "legendStatistics.bestSeason.rank":
            try:
                rank = player.legend_statistics.best_season.rank
            except:
                rank = " N/A"
            text += f"`{spot:3}`{emoji}`#{rank:<{longest}} {player.name[:13]}`\n"
        else:
            cum_heroes = sum([hero.level for hero in player.heroes if hero.is_home_base])
            text += f"`{spot:3}`{emoji}`{cum_heroes:3} {player.name[:13]}`\n"

    embed = disnake.Embed(title=title_name, description=text, color=embed_color)
    return embed


async def th_composition(bot: CustomClient, player_tags: List[str], title: str, thumbnail: str, embed_color: disnake.Color = disnake.Color.green()):
    pipeline = [
        {"$match": {"tag": {"$in": player_tags}}},
        {"$group": {"_id": "$data.townHallLevel", "count" : {"$sum" : 1}, "list_tags" : {"$push" : "$tag"}}},
        {"$sort" : {"_id" : -1}}
    ]
    results = await bot.player_cache.aggregate(pipeline=pipeline).to_list(length=None)

    th_count_dict = defaultdict(int)
    th_sum = 0
    for result in results:
        th_sum += (result["_id"] * result["count"])
        th_count_dict[result["_id"]] += result["count"]

    tags_found = []
    for t in results:
        tags_found += t["list_tags"]
    missing = set(player_tags) - set(tags_found)
    players = await bot.get_players(tags=list(missing), custom=False, use_cache=False)
    for player in players:
        th_sum += player.town_hall
        th_count_dict[player.town_hall] += 1

    embed_description = ""
    for th_level, th_count in sorted(th_count_dict.items(), reverse=True):
        if th_level <= 9:
            th_emoji = bot.fetch_emoji(th_level)
            embed_description += f"{th_emoji} `TH{th_level} ` {th_count}\n"

        else:
            th_emoji = bot.fetch_emoji(th_level)
            embed_description += f"{th_emoji} `TH{th_level}` {th_count}\n"

    th_average = round((th_sum / len(player_tags)), 2)

    embed = disnake.Embed(title=title, description=embed_description, color=embed_color)

    embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text=f"Average Th: {th_average}\nTotal: {len(player_tags)} accounts")

    return embed


async def th_hitrate(bot: CustomClient, player_tags: List[str], title: str, thumbnail: str, embed_color: disnake.Color = disnake.Color.green()):
    text = f""
    for th in TOWNHALL_LEVELS:
        num_total = await bot.warhits.count_documents({"$and": [{"tag" : {"$in" : player_tags}}, {"townhall": th}, {"defender_townhall": th}]})
        if num_total == 0:
            continue
        num_zeros = await bot.warhits.count_documents(
            {"$and": [{"tag" : {"$in" : player_tags}}, {"townhall": th}, {"stars": 0}, {"defender_townhall": th}]})
        num_ones = await bot.warhits.count_documents(
            {"$and": [{"tag" : {"$in" : player_tags}}, {"townhall": th}, {"stars": 1}, {"defender_townhall": th}]})
        num_twos = await bot.warhits.count_documents(
            {"$and": [{"tag" : {"$in" : player_tags}}, {"townhall": th}, {"stars": 2}, {"defender_townhall": th}]})
        num_triples = await bot.warhits.count_documents(
            {"$and": [{"tag" : {"$in" : player_tags}}, {"townhall": th}, {"stars": 3}, {"defender_townhall": th}]})
        text += f"{bot.fetch_emoji(name=th)}`{custom_round((num_zeros / num_total) * 100):>4}% ☆☆☆` |" \
                f" `{custom_round((num_ones / num_total) * 100):>4}% ★☆☆`\n" \
                f"{bot.emoji.blank}`{custom_round((num_twos / num_total) * 100):>4}% ★★☆` |" \
                f" `{custom_round((num_triples / num_total) * 100):>4}% ★★★`\n"
    if not text:
        text = "No Results Found"
    embed = disnake.Embed(title=title, description=text, color=embed_color)
    embed.set_thumbnail(url=thumbnail)
    return embed


    pipeline = [
        {"$match": {"tag": {"$in": player_tags}}},
        {"$group": {"_id": "$data.townHallLevel", "count" : {"$sum" : 1}, "list_tags" : {"$push" : "$tag"}}},
        {"$sort" : {"_id" : -1}}
    ]
    results = await bot.player_cache.aggregate(pipeline=pipeline).to_list(length=None)

    th_count_dict = defaultdict(int)
    th_sum = 0
    for result in results:
        th_sum += (result["_id"] * result["count"])
        th_count_dict[result["_id"]] += result["count"]

    tags_found = []
    for t in results:
        tags_found += t["list_tags"]
    missing = set(player_tags) - set(tags_found)
    players = await bot.get_players(tags=list(missing), custom=False, use_cache=False)
    for player in players:
        th_sum += player.town_hall
        th_count_dict[player.town_hall] += 1

    embed_description = ""
    for th_level, th_count in sorted(th_count_dict.items(), reverse=True):
        if th_level <= 9:
            th_emoji = bot.fetch_emoji(th_level)
            embed_description += f"{th_emoji} `TH{th_level} ` {th_count}\n"

        else:
            th_emoji = bot.fetch_emoji(th_level)
            embed_description += f"{th_emoji} `TH{th_level}` {th_count}\n"

    th_average = round((th_sum / len(player_tags)), 2)

    embed = disnake.Embed(title=title, description=embed_description, color=embed_color)

    embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text=f"Average Th: {th_average}\nTotal: {len(player_tags)} accounts")

    return embed


async def activity_graph(bot: CustomClient, players: List[MyCustomPlayer], season: str, title: str, granularity: str, time_zone: str, tier: str, no_html:bool = False) -> (disnake.File, disnake.ActionRow):
    s = season
    if season is None:
        season = bot.gen_season_date()
    list_ = []
    days = defaultdict(int)
    for player in players:
        all_lo = player.season_last_online(season_date=season)
        for time in all_lo:
            if granularity == "day":
                time = datetime.fromtimestamp(time).replace(hour=0, minute=0, second=0)
            elif granularity == "hour":
                time = datetime.fromtimestamp(time).replace(minute=0, second=0)
            elif granularity == "quarterday":
                time = datetime.fromtimestamp(time)
                time = time.replace(hour=(time.hour // 6) * 6, minute=0, second=0)
            if player.clan is None:
                continue
            days[f"{int(time.timestamp())}_{player.clan.name}"] += 1
    for date_time, amount in days.items():
        list_.append([pd.to_datetime(int(date_time.split("_")[0]), unit="s", utc=True).tz_convert(time_zone), amount, date_time.split("_")[1]])
    df = pd.DataFrame(list_, columns=["Date", "Total Activity", "Clan"])
    df.sort_values(by="Date", inplace=True)
    file, buttons = (await graph_creator(bot=bot, df=df, x="Date", y="Total Activity", title=title, footer="Choose Granularity Below", no_html=no_html))
    if buttons:
        buttons.append_item(disnake.ui.Button(label="1d", style=disnake.ButtonStyle.grey, custom_id=f"{tier}_day_{s}_{time_zone}"))
        buttons.append_item(disnake.ui.Button(label="6h", style=disnake.ButtonStyle.grey, custom_id=f"{tier}_quarterday_{s}_{time_zone}"))
        buttons.append_item(disnake.ui.Button(label="1h", style=disnake.ButtonStyle.grey, custom_id=f"{tier}_hour_{s}_{time_zone}"))
    return file, buttons




async def capital_donation_board(bot: CustomClient, players: List[MyCustomPlayer], week: str, title_name: str, limit: int = 60,
                                 footer_icon: str = None, embed_color: disnake.Color = disnake.Color.green()):
    players.sort(key=lambda x: sum(x.clan_capital_stats(week=week).donated), reverse=True)
    total_donated = 0
    text = ""
    for count, player in enumerate(players, 1):
        tag = player.tag.strip("#")
        if count <= limit:
            text += f"[⌕]({SHORT_PLAYER_LINK}{tag})`{count:2} {sum(player.clan_capital_stats(week=week).donated):5} {player.clear_name[:13]:13}`\n"
        total_donated += sum(player.clan_capital_stats(week=week).donated)
    if text == "":
        text = "No Results Found"
    embed = disnake.Embed(description=f"{text}", color=embed_color)
    embed.set_author(name=f"{title_name} Clan Capital Donations",
                     icon_url=bot.emoji.capital_gold.partial_emoji.url)
    if footer_icon is None:
        footer_icon = bot.user.avatar.url
    embed.set_footer(icon_url=footer_icon, text=f"Donated: {'{:,}'.format(total_donated)} | {week}")
    embed.timestamp = datetime.now()
    return embed


async def capital_raided_board(bot: CustomClient, players: List[MyCustomPlayer], week: str, title_name: str, limit: int = 60,
                               footer_icon: str = None, embed_color: disnake.Color = disnake.Color.green()):
    players.sort(key=lambda x: sum(x.clan_capital_stats(week=week).raided), reverse=True)
    total_donated = 0
    text = ""
    for count, player in enumerate(players, 1):
        tag = player.tag.strip("#")
        if count <= limit:
            text += f"[⌕]({SHORT_PLAYER_LINK}{tag})`{count:2} {sum(player.clan_capital_stats(week=week).raided):5} {player.clear_name[:13]:13}`\n"
        total_donated += sum(player.clan_capital_stats(week=week).raided)
    if text == "":
        text = "No Results Found"
    embed = disnake.Embed(description=f"{text}", color=embed_color)
    embed.set_author(name=f"{title_name} Clan Capital Raid Totals",
                     icon_url=bot.emoji.capital_gold.partial_emoji.url)
    if footer_icon is None:
        footer_icon = bot.user.avatar.url
    embed.set_footer(icon_url=footer_icon, text=f"Raided: {'{:,}'.format(total_donated)} | {week}")
    embed.timestamp = datetime.now()
    return embed