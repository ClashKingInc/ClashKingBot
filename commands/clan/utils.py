import asyncio
import time

import aiohttp
import coc
import emoji
import re
import disnake
import pandas as pd
import re

from disnake import Embed, Color
from disnake.utils import get
from collections import defaultdict
from coc.raid import RaidLogEntry
from datetime import datetime
from CustomClasses.CustomPlayer import MyCustomPlayer, LegendRanking, ClanCapitalWeek
from CustomClasses.CustomBot import CustomClient
from typing import List
from ballpark import ballpark as B
from statistics import mean
from Utils.Clash.capital import gen_raid_weekend_datestrings, calc_raid_medals
from Utils.clash import cwl_league_emojis, clan_super_troop_comp, clan_th_comp
from Utils.discord_utils import fetch_emoji, register_button
from Utils.general import create_superscript, response_to_line, fetch, get_guild_icon
from Utils.constants import SUPER_SCRIPTS, MAX_NUM_SUPERS
from pytz import utc
from Utils.clash import league_to_emoji

@register_button("clan board detailed")
async def detailed_clan_board(bot: CustomClient, clan: coc.Clan, server: disnake.Guild, embed_color: disnake.Color = disnake.Color.green()):
    db_clan = await bot.clan_db.find_one({"$and": [
        {"tag": clan.tag},
        {"server": server.id}
    ]})

    clan_legend_ranking = await bot.clan_leaderboard_db.find_one({"tag": clan.tag})

    previous_season = bot.gen_previous_season_date()
    season = bot.gen_season_date()

    clan_leader = get(clan.members, role=coc.Role.leader)
    warwin = clan.war_wins
    winstreak = clan.war_win_streak
    if clan.public_war_log:
        warloss = clan.war_losses
        if warloss == 0:
            winrate = warwin
        else:
            winrate = round((warwin / warloss), 2)
    else:
        warloss = "Hidden Log"
        winrate = "Hidden Log"

    if str(clan.location) == "International":
        flag = "<a:earth:861321402909327370>"
    else:
        try:
            flag = f":flag_{clan.location.country_code.lower()}:"
        except:
            flag = "ðŸ�³ï¸�"

    ranking = LegendRanking(clan_legend_ranking)
    rank_text = f"<a:earth:861321402909327370> {ranking.global_ranking} | "

    try:
        location_name = clan.location.name
    except:
        location_name = "Not Set"

    if clan.location is not None:
        if clan.location.name == "International":
            rank_text += f"ðŸŒ� {ranking.local_ranking}"
        else:
            rank_text += f"{flag} {ranking.local_ranking}"
    else:
        rank_text += f"{flag} {ranking.local_ranking}"
    if not str(ranking.local_ranking).isdigit() and not str(ranking.global_ranking).isdigit():
        rank_text = ""
    else:
        rank_text = f"Rankings: {rank_text}\n"

    cwl_league_emoji = cwl_league_emojis(str(clan.war_league))
    capital_league_emoji = cwl_league_emojis(str(clan.capital_league))

    hall_level = 0 if coc.utils.get(clan.capital_districts, id=70000000) is None else coc.utils.get(clan.capital_districts, id=70000000).hall_level
    hall_level_emoji = 1 if hall_level == 0 else hall_level
    clan_capital_text = f"Capital League: {capital_league_emoji}{clan.capital_league}\n" \
                        f"Capital Points: {bot.emoji.capital_trophy}{clan.capital_points}\n" \
                        f"Capital Hall: {fetch_emoji(f'Capital_Hall{hall_level_emoji}')} Level {hall_level}\n"

    clan_type_converter = {"open": "Anyone Can Join", "inviteOnly": "Invite Only", "closed": "Closed"}
    embed = Embed(
        title=f"**{clan.name}**",
        description=(
            f"Tag: [{clan.tag}]({clan.share_link})\n"
            f"Trophies: <:trophy:825563829705637889> {clan.points} | "
            f"<:vstrophy:944839518824058880> {clan.versus_points}\n"
            f"Requirements: <:trophy:825563829705637889>{clan.required_trophies} | {fetch_emoji(clan.required_townhall)}{clan.required_townhall}\n"
            f"Type: {clan_type_converter[clan.type]}\n"
            f"Location: {flag} {location_name}\n"
            f"{rank_text}\n"
            f"Leader: {clan_leader.name}\n"
            f"Level: {clan.level} \n"
            f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
            f"CWL: {cwl_league_emoji}{str(clan.war_league)}\n"
            f"Wars Won: <:warwon:932212939899949176>{warwin}\n"
            f"Wars Lost: <:warlost:932212154164183081>{warloss}\n"
            f"War Streak: <:warstreak:932212939983847464>{winstreak}\n"
            f"Winratio: <:winrate:932212939908337705>{winrate}\n\n"
            f"{clan_capital_text}\n"
            f"Description: {clan.description}"),
        color=embed_color
    )

    clan_members: List[MyCustomPlayer] = await bot.get_players(tags=[member.tag for member in clan.members], custom=True)

    clan_stats = await bot.clan_stats.find_one({"tag" : clan.tag})
    clan_games_points = 0
    total_donated = 0
    total_received = 0
    if clan_stats:
        for s in [season, previous_season]:
            for tag, data in clan_stats.get(s, {}).items():
                clan_games_points += data.get("clan_games", 0)
            if clan_games_points != 0:
                break

        for tag, data in clan_stats.get(season, {}).items():
            total_donated += data.get("donated", 0)
            total_received += data.get("received", 0)


    raid_season_stats = [c.results for c in clan_members]
    donated_cc = 0
    for date in gen_raid_weekend_datestrings(number_of_weeks=4):
        donated_cc += sum([sum(player.get(f"capital_gold").get(f"{date}").get("donate")) for player in raid_season_stats
                           if player.get("capital_gold") is not None and player.get("capital_gold").get(f"{date}") is not None and
                           player.get("capital_gold").get(f"{date}").get("donate") is not None])

    now = datetime.utcnow()
    time_add = defaultdict(set)
    for player in clan_members:
        for t in player.season_last_online():
            time_to_date = datetime.fromtimestamp(t)
            if now.date() == time_to_date.date():
                continue
            time_add[str(time_to_date.date())].add(player.tag)

    num_players_day = []
    for date, players in time_add.items():
        num_players_day.append(len(players))

    try:
        avg_players = int(sum(num_players_day) / len(num_players_day))
    except:
        avg_players = 0

    embed.add_field(name="Season Stats", value=f"Clan Games: {'{:,}'.format(clan_games_points)} Points\n"
                                               f"Cap Gold: {'{:,}'.format(donated_cc)} Donated\n"
                                               f"Donos: {bot.emoji.up_green_arrow}{'{:,}'.format(total_donated)}, {bot.emoji.down_red_arrow}{'{:,}'.format(total_received)}\n"
                                               f"Active Daily: {avg_players} players/avg")
    th_comp = clan_th_comp(clan_members=clan_members)
    super_troop_comp = clan_super_troop_comp(clan_members=clan_members)

    embed.add_field(name="**Townhall Composition:**",
                    value=th_comp, inline=False)
    embed.add_field(name="**Boosted Super Troops:**",
                    value=super_troop_comp, inline=False)

    embed.set_thumbnail(url=clan.badge.large)
    if db_clan is not None:
        ctg = db_clan.get("category")
        if ctg is not None:
            category = f"Category: {ctg} Clans"
            embed.set_footer(text=category)
    embed.timestamp = datetime.now()
    return embed

@register_button("clan board basic")
async def basic_clan_board(clan: coc.Clan, embed_color: disnake.Color = disnake.Color.green()):
    leader = coc.utils.get(clan.members, role=coc.Role.leader)

    if clan.public_war_log:
        warwin = clan.war_wins
        warloss = clan.war_losses
        if warloss == 0:
            warloss = 1
        winstreak = clan.war_win_streak
        winrate = round((warwin / warloss), 2)
    else:
        warwin = clan.war_wins
        warloss = "Hidden Log"
        winstreak = clan.war_win_streak
        winrate = "Hidden Log"

    if str(clan.location) == "International":
        flag = "<a:earth:861321402909327370>"
    else:
        try:
            flag = f":flag_{clan.location.country_code.lower()}:"
        except:
            flag = "<a:earth:861321402909327370>"

    embed = disnake.Embed(title=f"**{clan.name}**",
                          description=f"Tag: [{clan.tag}]({clan.share_link})\n"
                                      f"Trophies: <:trophy:825563829705637889> {clan.points} | <:vstrophy:944839518824058880> {clan.versus_points}\n"
                                      f"Required Trophies: <:trophy:825563829705637889> {clan.required_trophies}\n"
                                      f"Location: {flag} {clan.location}\n\n"
                                      f"Leader: {leader.name}\n"
                                      f"Level: {clan.level} \n"
                                      f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
                                      f"CWL: {cwl_league_emojis(str(clan.war_league))}{str(clan.war_league)}\n"
                                      f"Wars Won: <:warwon:932212939899949176>{warwin}\nWars Lost: <:warlost:932212154164183081>{warloss}\n"
                                      f"War Streak: <:warstreak:932212939983847464>{winstreak}\nWinratio: <:winrate:932212939908337705>{winrate}\n\n"
                                      f"Description: {clan.description}",
                          color=embed_color)

    embed.set_thumbnail(url=clan.badge.large)
    return embed


@register_button("clan compo")
async def clan_composition(bot: CustomClient, clan: coc.Clan, type: str, embed_color: disnake.Color = disnake.Color.green()):
    bucket = defaultdict(int)

    tag_to_location = {}
    location_name_to_code = {}
    if type == "Location":
        location_info = await bot.leaderboard_db.find({"tag" : {"$in" : [m.tag for m in clan.members]}}, {"tag" : 1, "country_name" : 1, "country_code" : 1}).to_list(length=None)
        tag_to_location = {d.get("tag") : d.get("country_name")for d in location_info}
        location_name_to_code = {d.get("country_name") : d.get("country_code") for d in location_info}


    for member in clan.members:
        if type == "Townhall":
            if member._raw_data.get("townHallLevel") == 0:
                continue
            bucket[str(member._raw_data.get("townHallLevel"))] += 1
        elif type == "Trophies":
            if member.trophies >= 1000:
                bucket[str(int(str(member.trophies)[0]) * 1000)] += 1
            else:
                bucket["100"] += 1
        elif type == "Location":
            location = tag_to_location.get(member.tag)
            if location is None:
                continue
            bucket[location] += 1
        elif type == "Role":
            bucket[member.role.in_game_name] += 1
        elif type == "League":
            bucket[member.league.name] += 1

    text = ""
    total = 0
    field_to_sort = 1
    if type == "Townhall":
        field_to_sort = 0
    for key, value in sorted(bucket.items(), key=lambda x:x[field_to_sort], reverse=True):
        icon = ""
        if type == "Townhall":
            icon = bot.fetch_emoji(int(key))
            total += (int(key) * value)
        elif type == "Location":
            icon = f":flag_{location_name_to_code.get(key).lower()}:"
        elif type == "League":
            icon = league_to_emoji(key)

        formats = {
            "Townhall" : "`{value:2}` {icon}`TH{key} `\n",
            "Trophies" : "`{value:2}` {icon}`{key}+ Trophies`\n",
            "Location": "`{value:2}` {icon}`{key}`\n",
            "Role" : "`{value:2}` {icon}`{key}`\n",
            "League": "`{value:2}` {icon}`{key}`\n",
        }
        text += f"{formats.get(type).format(key=key,value=value, icon=icon)}"

    footer_text = f"{clan.member_count} accounts"
    if type == "Townhall":
        footer_text += f" | Avg Townhall: {round((total / clan.member_count), 2)}"

    embed = disnake.Embed(title=f"{clan.name} {type}s",
                            description=text,
                            color=embed_color)
    embed.set_thumbnail(url=clan.badge.large)
    embed.set_footer(text=footer_text)
    embed.timestamp = datetime.now()
    return embed


async def hero_progress(bot: CustomClient, season: str, clan: coc.Clan = None, server: disnake.Guild = None, limit: int = 50, embed_color: disnake.Color = disnake.Color.green()):
    if not season:
        season = bot.gen_season_date()
    if clan:
        player_tags = [member.tag for member in clan.members]
    else:
        server_tags = await bot.get_guild_clans(guild_id=server.id)
        player_tags = await bot.player_stats.distinct("tag", filter={"$and" : [{"clan_tag": {"$in" : server_tags}}, {"paused" : {"$ne" : True}}]})

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
            self.name = data.get("name")[0] if data.get("name") else "unknown"
            self.king = next((item["count"] for item in data["hero_counts"] if item["hero_name"] == "Barbarian King"), 0)
            self.queen = next((item["count"] for item in data["hero_counts"] if item["hero_name"] == "Archer Queen"), 0)
            self.warden = next((item["count"] for item in data["hero_counts"] if item["hero_name"] == "Grand Warden"), 0)
            self.rc = next((item["count"] for item in data["hero_counts"] if item["hero_name"] == "Royal Champion"), 0)
            self.pets = sum(next((item["count"] for item in data["hero_counts"] if item["hero_name"] == pet), 0) for pet in coc.enums.PETS_ORDER
            )
            self.total_upgraded = self.king + self.queen + self.warden + self.rc + self.pets

    all_items = []
    for result in results:
        all_items.append(
            ItemHolder(data=result)
        )
    all_items = sorted(all_items, key=lambda x: x.total_upgraded, reverse=True)[:min(limit, len(all_items))]
    if not all_items:
        embed = disnake.Embed(description="**No Upgrades Yet**",colour=disnake.Color.red())
    else:
        text = f"BK AQ WD RC Pet Name          \n"
        for item in all_items:
            text +=  re.sub(r'\b0\b', "-", f"{item.king:<2} {item.queen:<2} {item.warden:<2} {item.rc:<2} {item.pets:<2}", count=6) + f"  {item.name[:13]}\n"
        embed = disnake.Embed(description=f"```{text}```", colour=embed_color)
    embed.set_author(name=f"{(clan or server).name} Hero & Pet Upgrades", icon_url=(clan.badge.url if not server else get_guild_icon(guild=server)))



    enums = coc.enums.HERO_ORDER + coc.enums.PETS_ORDER
    #enums = coc.enums.HOME_TROOP_ORDER + coc.enums.SPELL_ORDER
    pipeline = [
        {"$match": {"$and": [{"tag": {"$in": player_tags}},
                             {"type": {"$in": enums}},
                             {"time": {"$gte": season_start.timestamp()}},
                             {"time": {"$lte": season_end.timestamp()}}]}},
        {"$group": {"_id": {"type": "$type"}, "num": {"$sum": 1}}},
        {"$sort": {"num": -1}},
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)
    text = ""
    total_upgrades = 0
    for result in results:
        type = result.get("_id").get("type")
        emoji = bot.fetch_emoji(type)
        amount = result.get("num")
        total_upgrades += amount
        text += f"{emoji}`{type:15} {amount:3}`\n"

    totals_embed = disnake.Embed(description=f"{text}", colour=embed_color)
    totals_embed.timestamp = datetime.now()
    totals_embed.set_footer(text=f"{season} | {total_upgrades} Upgrades")


    return [embed, totals_embed]



async def troops_spell_siege_progress(bot: CustomClient, season: str, clan: coc.Clan = None, server: disnake.Guild = None, limit: int = 50, embed_color: disnake.Color = disnake.Color.green()):
    if not season:
        season = bot.gen_season_date()
    if clan:
        player_tags = [member.tag for member in clan.members]
    else:
        server_tags = await bot.get_guild_clans(guild_id=server.id)
        player_tags = await bot.player_stats.distinct("tag", filter={"$and" : [{"clan_tag": {"$in" : server_tags}}, {"paused" : {"$ne" : True}}]})

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
        embed = disnake.Embed(title=(clan or server).name, description="**No Upgrades Yet**",colour=disnake.Color.red())
    else:
        text = f"HT SP SG BT Name          \n"
        for item in all_items:
            '''if item.total_upgraded == 0:
                continue'''
            text += f"{item.troops:<2} {item.spells:<2} {item.sieges:<2} {item.builder_troops:<2} {item.name[:13]}\n"
        embed = disnake.Embed(description=f"```{text}```", colour=embed_color)

    embed.set_author(name=f"{(clan or server).name} Troop/Spell/Siege Upgrades", icon_url=(clan.badge.url if not server else get_guild_icon(guild=server)))
    embed.set_footer(text=f"HT=Home Troops, SP=Spells, SG=Sieges, BT=Builder Troops | {season}")
    embed.timestamp = datetime.now()
    return embed






async def donation_board(bot: CustomClient, db_clan, season= None, embed_color: disnake.Color = disnake.Color.green()):
    season = bot.gen_season_date() if season is None else season
    clan_season = await db_clan.get_season(season=season)
    players = clan_season.members
    players.sort(key=lambda x: x.donated, reverse=True)
    players = players[:55]
    text = "` #  DON   REC  NAME        `\n"
    total_donated = 0
    total_received = 0
    for count, member in enumerate(players, 1):
        text += f"`{count:2} {member.donated:5} {member.received:5} {member.player.clear_name[:13]:13}`[{create_superscript(member.player.town_hall)}]({member.share_link})\n"
        total_donated += member.donated
        total_received += member.received

    embed = disnake.Embed(description=f"{text}", color=embed_color)
    embed.set_author(name=f"{db_clan.clan.name} Top {len(players)} Donators", icon_url=db_clan.clan.badge.url)
    embed.set_footer(icon_url=bot.emoji.clan_castle.partial_emoji.url,
                     text=f"▲{total_donated:,} | ▼{total_received:,} | {season}")
    embed.timestamp = datetime.now()
    return embed


async def received_board(bot: CustomClient, db_clan, season= None, embed_color: disnake.Color = disnake.Color.green()):
    season = bot.gen_season_date() if season is None else season
    clan_season = await db_clan.get_season(season=season)
    players = clan_season.members
    players.sort(key=lambda x: x.received, reverse=True)
    players = players[:55]
    text = "` #  REC   DON  NAME        `\n"
    total_donated = 0
    total_received = 0
    for count, member in enumerate(players, 1):
        text += f"`{count:2} {member.received:5} {member.donated:5} {member.player.clear_name[:13]:13}`[{create_superscript(member.player.town_hall)}]({member.share_link})\n"
        total_donated += member.donated
        total_received += member.received

    embed = disnake.Embed(description=f"{text}", color=embed_color)
    embed.set_author(name=f"{db_clan.clan.name} Top {len(players)} Received", icon_url=db_clan.clan.badge.url)
    embed.set_footer(icon_url=bot.emoji.clan_castle.partial_emoji.url,
                     text=f"▲{total_donated:,} | ▼{total_received:,} | {season}")
    embed.timestamp = datetime.now()
    return embed


async def ratio_donations(bot: CustomClient, db_clan, season= None, embed_color: disnake.Color = disnake.Color.green()):
    season = bot.gen_season_date() if season is None else season
    clan_season = await db_clan.get_season(season=season)
    players = clan_season.members
    players.sort(key=lambda x: x.dono_ratio, reverse=True)
    players = players[:55]
    text = "` #  RATIO  NAME        `\n"
    total_donated = 0
    total_received = 0
    for count, member in enumerate(players, 1):
        text += f"`{count:2} {member.dono_ratio:5} {member.player.clear_name[:13]:13}`[{create_superscript(member.player.town_hall)}]({member.share_link})\n"
        total_donated += member.donated
        total_received += member.received

    embed = disnake.Embed(description=f"{text}", color=embed_color)
    embed.set_author(name=f"{db_clan.clan.name} Top {len(players)} Dono Ratio", icon_url=db_clan.clan.badge.url)
    embed.set_footer(icon_url=bot.emoji.clan_castle.partial_emoji.url,
                     text=f"▲{total_donated:,} | ▼{total_received:,} | {season}")
    embed.timestamp = datetime.now()
    return embed


async def clan_summary(bot: CustomClient, clan: coc.Clan, season: str):
    season = bot.gen_season_date() if season is None else season
    date = season

    results = await bot.player_stats.find({"tag": {"$in": [member.tag for member in clan.members]}}).to_list(length=None)

    def gold(elem):
        g = elem.get("gold_looted")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return sum(g)

    top_gold = sorted(results, key=gold, reverse=True)[:10]

    text = f"**{bot.emoji.gold} Gold Looted\n**"
    for count, result in enumerate(top_gold, 1):
        try:
            looted_gold = sum(result['gold_looted'][date])
        except:
            looted_gold = 0
        try:
            result['name']
        except:
            continue
        text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(looted_gold):11} \u200e{result['name']}`\n"

    def elixir(elem):
        g = elem.get("elixir_looted")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return sum(g)

    top_elixir = sorted(results, key=elixir, reverse=True)[:10]

    text += f"**{bot.emoji.elixir} Elixir Looted\n**"
    for count, result in enumerate(top_elixir, 1):
        try:
            looted_elixir = sum(result['elixir_looted'][date])
        except:
            looted_elixir = 0
        try:
            result['name']
        except:
            continue
        text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(looted_elixir):11} \u200e{result['name']}`\n"

    def dark_elixir(elem):
        g = elem.get("dark_elixir_looted")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return sum(g)

    top_dark_elixir = sorted(results, key=dark_elixir, reverse=True)[:10]

    text += f"**{bot.emoji.dark_elixir} Dark Elixir Looted\n**"
    for count, result in enumerate(top_dark_elixir, 1):
        try:
            looted_dark_elixir = sum(result['dark_elixir_looted'][date])
        except:
            looted_dark_elixir = 0
        try:
            result['name']
        except:
            continue
        text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(looted_dark_elixir):11} \u200e{result['name']}`\n"

    def activity_count(elem):
        g = elem.get("last_online_times")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return len(g)

    top_activity = sorted(results, key=activity_count, reverse=True)[:10]

    text += f"**{bot.emoji.clock} Top Activity\n**"
    for count, result in enumerate(top_activity, 1):
        try:
            activity = activity_count(result)
        except:
            activity = 0
        try:
            result['name']
        except:
            continue
        text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(activity):5} \u200e{result['name']}`\n"

    def donations(elem):
        g = elem.get("donations")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        g = g.get("donated")
        if g is None:
            return 0
        return g

    top_donations = sorted(results, key=donations, reverse=True)[:10]

    second_text = f"**{bot.emoji.up_green_arrow} Donations\n**"
    for count, result in enumerate(top_donations, 1):
        try:
            donated = result['donations'][date]['donated']
        except:
            donated = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(donated):7} \u200e{result['name']}`\n"

    def received(elem):
        g = elem.get("donations")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        g = g.get("received")
        if g is None:
            return 0
        return g

    top_received = sorted(results, key=received, reverse=True)[:10]

    second_text += f"**{bot.emoji.down_red_arrow} Received\n**"
    for count, result in enumerate(top_received, 1):
        try:
            received = result['donations'][date]['received']
        except:
            received = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(received):7} \u200e{result['name']}`\n"

    def attacks(elem):
        g = elem.get("attack_wins")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return g

    top_attacks = sorted(results, key=attacks, reverse=True)[:10]

    second_text += f"**{bot.emoji.sword_clash} Attack Wins\n**"
    for count, result in enumerate(top_attacks, 1):
        try:
            attack_num = result['attack_wins'][date]
        except:
            attack_num = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(attack_num):7} \u200e{result['name']}`\n"

    def capital_gold_donated(elem):
        weeks = gen_raid_weekend_datestrings(4)
        weeks = weeks[0:4]
        cc_results = []
        for week in weeks:
            if elem is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            clan_capital_result = elem.get("capital_gold")
            if clan_capital_result is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            week_result = clan_capital_result.get(week)
            if week_result is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            cc_results.append(ClanCapitalWeek(week_result))
        return sum([sum(cap.donated) for cap in cc_results])

    top_cg_donos = sorted(results, key=capital_gold_donated, reverse=True)[:10]

    second_text += f"**{bot.emoji.capital_gold} CG Donated (last 4 weeks)\n**"
    for count, result in enumerate(top_cg_donos, 1):
        try:
            cg_donated = capital_gold_donated(result)
        except:
            cg_donated = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(cg_donated):7} \u200e{result['name']}`\n"

    def capital_gold_raided(elem):
        weeks = gen_raid_weekend_datestrings(4)
        weeks = weeks[0:4]
        cc_results = []
        for week in weeks:
            if elem is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            clan_capital_result = elem.get("capital_gold")
            if clan_capital_result is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            week_result = clan_capital_result.get(week)
            if week_result is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            cc_results.append(ClanCapitalWeek(week_result))
        return sum([sum(cap.raided) for cap in cc_results])

    top_cg_raided = sorted(results, key=capital_gold_raided, reverse=True)[:10]

    second_text += f"**{bot.emoji.capital_gold} CG Raided (last 4 weeks)\n**"
    for count, result in enumerate(top_cg_raided, 1):
        try:
            cg_raided = capital_gold_raided(result)
        except:
            cg_raided = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(cg_raided):7} \u200e{result['name']}`\n"

    tags = [result.get("tag") for result in results]
    start = int(coc.utils.get_season_start().timestamp())
    now = (datetime.now().timestamp())
    hits = await bot.warhits.find(
        {"$and": [
            {"tag": {"$in": tags}},
            {"_time": {"$gte": start}},
            {"_time": {"$lte": now}}
        ]}).to_list(length=100000)

    names = {}
    group_hits = defaultdict(int)
    for hit in hits:
        if hit["war_type"] == "friendly":
            continue
        group_hits[hit["tag"]] += hit["stars"]
        names[hit["tag"]] = hit['name']

    top_war_stars = sorted(group_hits.items(), key=lambda x: x[1], reverse=True)[:10]

    second_text += f"**{bot.emoji.war_star} War Stars\n**"
    for count, result in enumerate(top_war_stars, 1):
        tag, war_star = result
        try:
            name = names[tag]
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(war_star):3} \u200e{name}`\n"

    embed = disnake.Embed(title=f"{clan.name} Season Summary", description=text)
    embed2 = disnake.Embed(description=second_text)
    print(len(embed.description) + len(embed2.description))
    return [embed, embed2]


async def linked_players(bot: CustomClient, clan: coc.Clan, guild: disnake.Guild):
    player_links = await bot.link_client.get_links(*[member.tag for member in clan.members])
    embeds = []
    embed_description = f"{bot.emoji.discord}`Name           ` **Discord**\n"

    db_clan = await bot.clan_db.find_one({"$and": [
        {"tag": clan.tag},
        {"server": guild.id}
    ]})

    player_link_count = 0
    player_link_dict = dict(player_links)
    for player in clan.members:
        player_link = player_link_dict[f"{player.tag}"]
        # user not linked to player
        if player_link is None:
            continue

        name = bot.clean_string(player.name)[:14]
        if len(name) <= 2:
            name = player.name

        player_link_count += 1
        member = await guild.getch_member(player_link)
        # member not found in server
        if member is None:
            member = ""

        embed_description += f'\u200e{bot.emoji.green_tick}`{name:14}` \u200e{member}\n'

    # no players were linked
    if player_link_count == 0:
        embed_description = "No players linked."

    embed = Embed(
        description=embed_description, color=Color.green())
    embed.set_author(name=f"{clan.name} (Un)Linked Players", icon_url=clan.badge.url)
    embeds.append(embed)

    embed_description = f"{bot.emoji.discord}`Name           ` **Player Tag**\n"
    unlinked_player_count = 0
    player_link_dict = dict(player_links)
    for player in clan.members:
        player_link = player_link_dict[f"{player.tag}"]
        # linked player found
        if player_link is not None:
            continue
        name = bot.clean_string(player.name)[:14]
        if len(name) <= 2:
            name = player.name
        unlinked_player_count += 1
        embed_description += f'\u200e{bot.emoji.red_tick}`{name:14}` \u200e{player.tag}\n'

    if unlinked_player_count == 0:
        embed_description = "No players unlinked."

    embed = Embed(
        description=embed_description,
        color=Color.green())
    embed.set_footer(text=f"{player_link_count}✓ | {unlinked_player_count}✘")
    embed.timestamp = datetime.now()
    embeds.append(embed)

    return embeds


async def opt_status(bot: CustomClient, clan: coc.Clan, embed_color: disnake.Color = disnake.Color.green()):
    in_count = 0
    out_count = 0
    thcount = defaultdict(int)
    out_thcount = defaultdict(int)
    pipeline = [
        {"$match" : {"$and" : [{"tag": {"$in": [member.tag for member in clan.members]}}, {"type" : "warPreference"}]}},
        {"$group" : {"_id": "$tag", "last_change": {"$last": "$time"}}}
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)
    member_stats = {result["_id"] : f"`<t:{result['last_change']}:R>" for result in results}

    players: List[MyCustomPlayer] = await bot.get_players(tags=[member.tag for member in clan.members], custom=True, use_cache=False, fake_results=True)
    players.sort(key=lambda x: (-x.town_hall, x.name), reverse=False)
    opted_in_text = ""
    opted_out_text = ""
    for player in players:
        war_opt_time = member_stats.get(player.tag, "N/A`")
        if player.war_opted_in:
            opted_in_text += f"<:opt_in:944905885367537685>{player.town_hall_cls.emoji}\u200e`{emoji.replace_emoji(player.name)[:15]:15}{war_opt_time}\n"
            thcount[player.town_hall] += 1
            in_count += 1
        else:
            opted_out_text += f"<:opt_out:944905931265810432>{player.town_hall_cls.emoji}\u200e`{emoji.replace_emoji(player.name)[:15]:15}{war_opt_time}\n"
            out_thcount[player.town_hall] += 1
            out_count += 1

    if opted_in_text == "":
        opted_in_text = "None"
    if opted_out_text == "":
        opted_out_text = "None"

    in_string = ", ".join(f"Th{index}: {th} " for index, th in sorted(thcount.items(), reverse=True) if th != 0)
    out_string = ", ".join(f"Th{index}: {th} " for index, th in sorted(out_thcount.items(), reverse=True) if th != 0)

    embed = Embed(description=f"**Opted In - {in_count}:**\n{opted_in_text}\n", color=embed_color)

    embed2 = Embed(description=f"**Opted Out - {out_count}:**\n{opted_out_text}\n", color=embed_color)

    embed.set_author(name=f"{clan.name} War Preferences", icon_url=clan.badge.url)
    embed2.set_footer(text=f"In: {in_string}\nOut: {out_string}")
    embed2.timestamp = datetime.now()
    return [embed, embed2]


async def war_log(bot: CustomClient, clan: coc.Clan, limit=25):
    embed_description = ""
    wars_counted = 0
    try:
        war_log = await bot.coc_client.get_warlog(clan.tag, limit=limit)
    except coc.errors.PrivateWarLog:
        return disnake.Embed(description=f"{clan.name} has a private war log", color=disnake.Color.red())
    for war in war_log:
        if war.is_league_entry:
            continue
        clan_attack_count = war.clan.attacks_used

        if war.result == "win":
            status = "<:warwon:932212939899949176>"
            op_status = "Win"

        elif ((war.opponent.stars == war.clan.stars) and
              (war.clan.destruction == war.opponent.destruction)):
            status = "<:dash:933150462818021437>"
            op_status = "Draw"

        else:
            status = "<:warlost:932212154164183081>"
            op_status = "Loss"

        time = f"<t:{int(war.end_time.time.replace(tzinfo=utc).timestamp())}:R>"
        war: coc.ClanWarLogEntry

        try:
            total = war.team_size * war.attacks_per_member
            num_hit = SUPER_SCRIPTS[war.attacks_per_member]
        except:
            total = war.team_size
            num_hit = SUPER_SCRIPTS[1]

        embed_description += (
            f"{status}**{op_status} vs "
            f"\u200e{war.opponent.name}**\n"
            f"({war.team_size} vs {war.team_size}){num_hit} | {time}\n"
            f"{war.clan.stars} <:star:825571962699907152> {war.opponent.stars} | "
            f"{clan_attack_count}/{total} | {round(war.clan.destruction, 1)}% | "
            f"+{war.clan.exp_earned}xp\n")

        wars_counted += 1

    if wars_counted == 0:
        embed_description = "Empty War Log"

    embed = Embed(
        description=embed_description,
        color=Color.green())
    embed.set_author(icon_url=clan.badge.large, name=f"{clan.name} WarLog (last {wars_counted})")
    return embed


async def super_troop_list(bot: CustomClient, clan: coc.Clan):
    boosted = ""
    none_boosted = ""

    async for player in clan.get_detailed_members():
        text = ""
        if player.town_hall < 11:
            continue

        num_super_troops = 0
        for troop in player.troops:
            if troop.is_active:
                text = f"{fetch_emoji(troop.name)} {text}"
                num_super_troops += 1
            if num_super_troops == MAX_NUM_SUPERS:
                break

        if num_super_troops == 1:
            text = f"{bot.emoji.blank} {text}"

        if text == "":
            none_boosted += f"{player.name}\n"
        else:
            boosted += f"{text} {player.name}\n"

    if boosted == "":
        boosted = "None"

    embed = Embed(
        description=f"\n**Boosting:**\n{boosted}",
        color=Color.green())

    if none_boosted == "":
        none_boosted = "None"

    embed.set_author(name=f"{clan.name} Super Troops", icon_url=clan.badge.url)
    embed.add_field(name="Not Boosting:", value=none_boosted)
    embed.set_footer(text="Last Refreshed")
    embed.timestamp = datetime.now()
    return embed


async def clan_capital_overview(bot: CustomClient, clan: coc.Clan, raid_log_entry: RaidLogEntry):
    if raid_log_entry is None:
        return Embed(description="No Raid Weekend Entry Found. Donation info may be available.", color=disnake.Color.green())
    attack_count = 0
    for member in raid_log_entry.members:
        attack_count += member.attack_count
    embed = disnake.Embed(title=f"{clan.name} Raid Weekend Overview", color=disnake.Color.green())
    embed.set_footer(
        text=f"{str(raid_log_entry.start_time.time.date()).replace('-', '/')}-{str(raid_log_entry.end_time.time.date()).replace('-', '/')}", icon_url=clan.badge.url)
    embed.add_field(name="Overview",
                    value=f"- {bot.emoji.capital_gold}{'{:,}'.format(raid_log_entry.total_loot)} Looted\n"
                          f"- {bot.fetch_emoji('District_Hall5')}{raid_log_entry.destroyed_district_count} Districts Destroyed\n"
                          f"- {bot.emoji.thick_sword}{attack_count}/300 Attacks Complete\n"
                          f"- {bot.emoji.person}{len(raid_log_entry.members)}/50 Participants\n"
                          f"- Start {bot.timestamper(raid_log_entry.start_time.time.timestamp()).relative}, End {bot.timestamper(raid_log_entry.end_time.time.timestamp()).relative}\n",
                    inline=False)
    atk_stats_by_district = defaultdict(list)
    for clan in raid_log_entry.attack_log:
        for district in clan.districts:
            atk_stats_by_district[district.name].append(len(district.attacks))

    offense_district_stats = "```"
    for district, list_atks in atk_stats_by_district.items():
        offense_district_stats += f"{round(mean(list_atks), 2):4} {district}\n"
    offense_district_stats += "```"

    def_stats_by_district = defaultdict(list)
    for clan in raid_log_entry.defense_log:
        for district in clan.districts:
            def_stats_by_district[district.name].append(len(district.attacks))

    def_district_stats = "```"
    for district, list_atks in def_stats_by_district.items():
        def_district_stats += f"{round(mean(list_atks), 2):4} {district}\n"
    def_district_stats += "```"

    embed.add_field("Detailed Stats (Offense)",
                    value=f"- Avg Loot/Raid : {B(int(raid_log_entry.total_loot / len(raid_log_entry.attack_log)))}\n"
                          f"- Avg Loot/Player: {B(int(raid_log_entry.total_loot / len(raid_log_entry.members)))}\n"
                          f"- Avg Hits/Clan: {round(raid_log_entry.attack_count / len(raid_log_entry.attack_log), 2)}\n",
                    inline=False)
    embed.add_field(name="(Avg Atks By District, Off)", value=offense_district_stats)
    embed.add_field(name="(Avg Atks By District, Def)", value=def_district_stats)

    attack_summary_text = f"```a=atks, d=districts, l=loot\n"
    for clan in raid_log_entry.attack_log:
        # badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
        attack_summary_text += f"- {clan.name[:12]:12} {clan.attack_count:2}a {clan.destroyed_district_count:1}d {B(sum([d.looted for d in clan.districts])):3}l\n"

    defense_summary_text = "```"
    for clan in raid_log_entry.defense_log:
        # badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
        defense_summary_text += f"- {clan.name[:12]:12} {clan.attack_count:2}a {clan.destroyed_district_count:1}d {B(sum([d.looted for d in clan.districts])):3}l\n"

    attack_summary_text += "```"
    defense_summary_text += "```"
    embed.add_field(name=f"Attack Summary", value=attack_summary_text, inline=False)
    embed.add_field(name="Defense Summary", value=defense_summary_text, inline=False)

    members = sorted(list(raid_log_entry.members), key=lambda x: x.capital_resources_looted, reverse=True)
    top_text = ""
    for count, member in enumerate(members[:3], 1):
        member: coc.raid.RaidMember
        count_conv = {1: "gold",
                      2: "white",
                      3: "blue"}
        top_text += f"{bot.get_number_emoji(color=count_conv[count], number=count)}{bot.clean_string(member.name)} {bot.emoji.capital_gold}{member.capital_resources_looted}{create_superscript(member.attack_count)}\n"
    embed.add_field(name="Top 3 Raiders", value=top_text, inline=False)
    return embed


async def clan_raid_weekend_donation_stats(bot: CustomClient, clan: coc.Clan, weekend: str):
    member_tags = [member.tag for member in clan.members]
    capital_raiders = await bot.player_stats.distinct("tag", filter={
        "$or": [{f"capital_gold.{weekend}.raided_clan": clan.tag}, {"tag": {"$in": member_tags}}]})
    players = await bot.get_players(tags=capital_raiders)

    donated_data = {}
    number_donated_data = {}
    donation_text = ""

    players.sort(key=lambda x: sum(x.clan_capital_stats(week=weekend).donated), reverse=True)
    for player in players[:60]:  # type: MyCustomPlayer
        sum_donated = 0
        len_donated = 0
        cc_stats = player.clan_capital_stats(week=weekend)
        sum_donated += sum(cc_stats.donated)
        len_donated += len(cc_stats.donated)

        donated_data[player.tag] = sum_donated
        number_donated_data[player.tag] = len_donated

        if player.tag in member_tags:
            donation_text += f"{bot.emoji.capital_gold}`{sum_donated:6} {player.clear_name[:15]:15}`\n"
        else:
            donation_text += f"{bot.emoji.deny_mark}`{sum_donated:6} {player.clear_name[:15]:15}`\n"

    donation_embed = Embed(
        title=f"**{clan.name} Donation Totals**",
        description=donation_text[:4075], color=Color.green())

    donation_embed.set_footer(text=f"Donated: {'{:,}'.format(sum(donated_data.values()))} | Week: {weekend}")
    return donation_embed


async def clan_raid_weekend_raid_stats(bot: CustomClient, clan: coc.Clan, raid_log_entry: RaidLogEntry):
    if raid_log_entry is None:
        embed = Embed(
            title=f"**{clan.name} Raid Totals**",
            description="No raid found! Donation info may be available.", color=Color.green())
        return embed

    total_medals = 0
    total_attacks = defaultdict(int)
    total_looted = defaultdict(int)
    attack_limit = defaultdict(int)
    name_list = {}
    member_tags = [member.tag for member in clan.members]
    members_not_looted = member_tags.copy()

    for member in raid_log_entry.members:
        name_list[member.tag] = member.name
        total_attacks[member.tag] += member.attack_count
        total_looted[member.tag] += member.capital_resources_looted
        attack_limit[member.tag] += (
                member.attack_limit +
                member.bonus_attack_limit)
        try:
            members_not_looted.remove(member.tag)
        except:
            pass

    attacks_done = sum(list(total_attacks.values()))
    attacks_done = max(1, attacks_done)

    total_medals = calc_raid_medals(raid_log_entry.attack_log)

    raid_text = []
    for tag, amount in total_looted.items():
        name = name_list[tag]
        name = bot.clean_string(name)[:13]
        if tag in member_tags:
            raid_text.append([
                f"\u200e{bot.emoji.capital_gold}`"
                f"{total_attacks[tag]}/{attack_limit[tag]} "
                f"{amount:5} {name[:15]:15}`", amount])
        else:
            raid_text.append([
                f"\u200e{bot.emoji.deny_mark}`"
                f"{total_attacks[tag]}/{attack_limit[tag]} "
                f"{amount} {name[:15]:15}`", amount])

    more_to_show = 55 - len(total_attacks.values())
    for member in members_not_looted[:more_to_show]:
        member = coc.utils.get(clan.members, tag=member)
        name = bot.clean_string(member.name)
        raid_text.append([
            f"{bot.emoji.capital_gold}`{0}"
            f"/{6} {0:5} {name[:15]:15}`",
            0])

    raid_text = sorted(raid_text, key=lambda l: l[1], reverse=True)
    raid_text = [line[0] for line in raid_text]
    raid_text = "\n".join(raid_text)

    raid_embed = Embed(
        title=f"**{clan.name} Raid Totals**",
        description=raid_text,
        color=Color.green())

    raid_embed.set_footer(text=(
        f"Spots: {len(total_attacks.values())}/50 | "
        f"Attacks: {sum(total_attacks.values())}/300 | "
        f"Looted: {'{:,}'.format(sum(total_looted.values()))} | {raid_log_entry.start_time.time.date()}"))

    return raid_embed


async def create_last_online(bot: CustomClient, clan: coc.Clan):
    players = await bot.get_players(tags=[member.tag for member in clan.members])
    embed_description_list = []
    last_online_sum = 0
    last_online_count = 0
    for member in players:
        if member.last_online is None:
            last_online_sort = 0
            embed_description_list.append([
                f"Not Seen `{member.name}`",
                last_online_sort])

        else:
            last_online_sort = member.last_online
            last_online_count += 1
            last_online_sum += member.last_online

            embed_description_list.append([
                f"<t:{member.last_online}:R> `{member.name}`",
                last_online_sort])

    embed_description = sorted(
        embed_description_list, key=lambda l: l[1], reverse=True)
    embed_description = [line[0] for line in embed_description]
    embed_description = "\n".join(embed_description)

    if last_online_sum != 0:
        avg_last_online = last_online_sum / last_online_count
        embed_description += (
            f"\n\n**Median:** <t:{int(avg_last_online)}:R>")

    embed = Embed(
        description=embed_description,
        color=Color.green())
    embed.set_author(name=f"{clan.name} Last Online", icon_url=clan.badge.url)
    embed.timestamp = datetime.now()
    return embed


async def create_activities(bot: CustomClient, db_clan, season: str):
    season = bot.gen_games_season() if season is None else season
    db_season = await db_clan.get_season(season=season)
    members = sorted(db_season.members, key=lambda x: x.activity, reverse=True)
    text = "`  #  ACT NAME      `\n"
    total_activities = 0
    for count, member in enumerate(members, 1):
        if count <= 55:
            text += f"`{count:2} {member.activity:4} {member.player.clear_name[:15]:15}`[{create_superscript(member.player.town_hall)}]({member.share_link})\n"
        total_activities += member.activity

    embed = disnake.Embed(description=f"{text}")
    embed.set_author(name=f"{db_clan.clan.name} Top {len(members)} Activities", icon_url=db_clan.clan.badge.url)
    embed.set_footer(icon_url=bot.emoji.clock.partial_emoji.url, text=f"Activities: {total_activities:,} | {season}")
    embed.timestamp = datetime.now()
    return embed


async def create_clan_games(bot: CustomClient, db_clan, season: str, embed_color: disnake.Color = disnake.Color.green()):
    season = bot.gen_games_season() if season is None else season
    db_season = await db_clan.get_season(season=season)

    year = int(season[:4])
    month = int(season[-2:])

    next_month = month + 1
    if month == 12:
        next_month = 1
        year += 1

    start = datetime(year, month, 1)
    end = datetime(year, next_month, 1)

    pipeline = [
        {"$match": {"$and": [{"tag": {"$in": [member.tag for member in db_season.members]}}, {"type": "Games Champion"},
                             {"time": {"$gte": start.timestamp()}},
                             {"time": {"$lte": end.timestamp()}}]}},
        {"$sort": {"tag": 1, "time": 1}},
        {"$group": {"_id": "$tag", "first": {"$first": "$time"}, "last": {"$last": "$time"}}}
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)

    member_stat_dict = {}
    for m in results:
        member_stat_dict[m["_id"]] = {"first" : m["first"], "last" : m["last"]}

    total_points = sum(member.clan_games for member in db_season.members)
    player_list = sorted(db_season.members, key=lambda l: l.clan_games, reverse=True)

    point_text_list = []
    for player in player_list:
        name = player.player.name
        name = re.sub('[*_`~/]', '', name)
        points = player.clan_games
        time = ""
        stats = member_stat_dict.get(player.tag)
        if stats is not None:
            if points < 4000 and bot.is_games():
                stats["last"] = int(datetime.now().timestamp())
            first_time = datetime.fromtimestamp(stats["first"])
            last_time = datetime.fromtimestamp(stats["last"])
            diff = (last_time - first_time)
            m, s = divmod(diff.total_seconds(), 60)
            h, m = divmod(m, 60)
            time = f"{int(h)}h {int(m)}m"

        if player.player.clan is not None and player.player.clan.tag == db_clan.clan.tag:
            point_text_list.append([f"{bot.emoji.clan_games}`{str(points).rjust(4)} {time:7}` {name}"])
        else:
            point_text_list.append([f"{bot.emoji.deny_mark}`{str(points).rjust(4)} {time:7}` {name}"])


    point_text = [line[0] for line in point_text_list]
    point_text = "\n".join(point_text)

    if point_text == "":
        point_text = "No Stats Found"
    cg_point_embed = disnake.Embed(description=point_text, color=embed_color)
    cg_point_embed.set_author(name=f"{db_clan.clan.name} Clan Games", icon_url=db_clan.clan.badge.url)
    cg_point_embed.set_footer(text=f"Total Points: {'{:,}'.format(total_points)} | {season}", icon_url=bot.emoji.clan_games.partial_emoji.url)
    return cg_point_embed


def stat_components(bot: CustomClient):
    options = []
    for townhall in reversed(range(6, 16)):
        options.append(disnake.SelectOption(
            label=f"Townhall {townhall}", emoji=str(bot.fetch_emoji(name=townhall)), value=str(townhall)))
    th_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder="Select Townhalls",
        min_values=1,  # the minimum number of options a user must select
        # the maximum number of options a user can select
        max_values=len(options),
    )
    options = []
    real_types = ["Fresh Hits", "Non-Fresh", "random", "cwl", "friendly"]
    for count, filter in enumerate(["Fresh Hits", "Non-Fresh", "Random Wars", "CWL", "Friendly Wars"]):
        options.append(disnake.SelectOption(
            label=f"{filter}", value=real_types[count]))
    filter_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder="Select Filters",
        min_values=1,  # the minimum number of options a user must select
        # the maximum number of options a user can select
        max_values=len(options),
    )
    options = []
    emojis = [bot.emoji.sword_clash.partial_emoji,
              bot.emoji.shield.partial_emoji, bot.emoji.war_star.partial_emoji]
    for count, type in enumerate(["Offensive Hitrate", "Defensive Rate", "Stars Leaderboard"]):
        options.append(disnake.SelectOption(
            label=f"{type}", emoji=emojis[count], value=type))
    stat_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder="Select Stat Type",
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(th_select), disnake.ui.ActionRow(
        filter_select), disnake.ui.ActionRow(stat_select)]
    return dropdown


async def create_offensive_hitrate(bot: CustomClient, clan: coc.Clan, players,
                                   townhall_level: list = [], fresh_type: list = [False, True],
                                   start_timestamp: int = 0, end_timestamp: int = 9999999999,
                                   war_types: list = ["random", "cwl", "friendly"],
                                   war_statuses=["lost", "losing", "winning", "won"]):
    if not townhall_level:
        townhall_level = list(range(1, 17))
    tasks = []

    async def fetch_n_rank(player: MyCustomPlayer):
        hitrate = await player.hit_rate(townhall_level=townhall_level, fresh_type=fresh_type,
                                        start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                        war_types=war_types, war_statuses=war_statuses)
        hr = hitrate[0]
        if hr.num_attacks == 0:
            return None
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        name = emoji.replace_emoji(player.name, "")
        name = str(name)[0:12]
        name = f"{name}".ljust(12)
        destr = f"{round(hr.average_triples * 100, 1)}%".rjust(6)
        return [f"{player.town_hall_cls.emoji}` {hr_nums} {destr} {name}`\n", round(hr.average_triples * 100, 3), name,
                hr.num_attacks, player.town_hall]

    for player in players:
        task = asyncio.ensure_future(fetch_n_rank(player=player))
        tasks.append(task)
    responses = await asyncio.gather(*tasks)
    ranked = [response for response in responses if response is not None]
    ranked = sorted(
        ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
    text = "`# TH  NUM    HR%    NAME       `\n"
    for count, rank in enumerate(ranked, 1):
        spot_emoji = bot.get_number_emoji(color="gold", number=count)
        text += f"{spot_emoji}{rank[0]}"
    if len(ranked) == 0:
        text = "No War Attacks Tracked Yet."
    embed = disnake.Embed(title=f"Offensive Hit Rates",
                          description=text, colour=disnake.Color.green())
    filter_types = []
    if True in fresh_type:
        filter_types.append("Fresh")
    if False in fresh_type:
        filter_types.append("Non-Fresh")
    for type in war_types:
        filter_types.append(str(type).capitalize())
    filter_types = ", ".join(filter_types)
    time_range = "This Season"
    if start_timestamp != 0 and end_timestamp != 9999999999:
        time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
    embed.set_footer(icon_url=clan.badge.url,
                     text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
    return embed


async def create_defensive_hitrate(bot: CustomClient, clan: coc.Clan, players,
                                   townhall_level: list = [], fresh_type: list = [False, True],
                                   start_timestamp: int = 0, end_timestamp: int = 9999999999,
                                   war_types: list = ["random", "cwl", "friendly"],
                                   war_statuses=["lost", "losing", "winning", "won"]):
    if not townhall_level:
        townhall_level = list(range(1, 17))
    tasks = []

    async def fetch_n_rank(player: MyCustomPlayer):
        hitrate = await player.defense_rate(townhall_level=townhall_level, fresh_type=fresh_type,
                                            start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                            war_types=war_types, war_statuses=war_statuses)
        hr = hitrate[0]
        if hr.num_attacks == 0:
            return None
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        name = emoji.replace_emoji(player.name, "")
        name = str(name)[0:12]
        name = f"{name}".ljust(12)
        destr = f"{round(hr.average_triples * 100, 1)}%".rjust(6)
        return [f"{player.town_hall_cls.emoji} `{hr_nums} {destr} {name}`\n", round(hr.average_triples * 100, 3), name,
                hr.num_attacks, player.town_hall]

    for player in players:  # type: MyCustomPlayer
        task = asyncio.ensure_future(fetch_n_rank(player=player))
        tasks.append(task)
    responses = await asyncio.gather(*tasks)
    ranked = [response for response in responses if response is not None]
    ranked = sorted(
        ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
    text = "`# TH  NUM    DR%    NAME       `\n"
    for count, rank in enumerate(ranked, 1):
        spot_emoji = bot.get_number_emoji(color="gold", number=count)
        text += f"{spot_emoji}{rank[0]}"
    if len(ranked) == 0:
        text = "No War Attacks Tracked Yet."
    embed = disnake.Embed(title=f"Defensive Rates",
                          description=text, colour=disnake.Color.green())
    filter_types = []
    if True in fresh_type:
        filter_types.append("Fresh")
    if False in fresh_type:
        filter_types.append("Non-Fresh")
    for type in war_types:
        filter_types.append(str(type).capitalize())
    filter_types = ", ".join(filter_types)
    time_range = "This Season"
    if start_timestamp != 0 and end_timestamp != 9999999999:
        time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
    embed.set_footer(icon_url=clan.badge.url,
                     text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
    return embed


async def create_stars_leaderboard(bot: CustomClient,   clan: coc.Clan, players,
                                   townhall_level: list = [], fresh_type: list = [False, True],
                                   start_timestamp: int = 0, end_timestamp: int = 9999999999,
                                   war_types: list = ["random", "cwl", "friendly"],
                                   war_statuses=["lost", "losing", "winning", "won"]):
    if not townhall_level:
        townhall_level = list(range(1, 17))
    tasks = []

    async def fetch_n_rank(player: MyCustomPlayer):
        hitrate = await player.hit_rate(townhall_level=townhall_level, fresh_type=fresh_type,
                                        start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                        war_types=war_types, war_statuses=war_statuses)
        hr = hitrate[0]
        if hr.num_attacks == 0:
            return None
        name = str(player.name)[0:12]
        name = f"{name}".ljust(12)
        stars = f"{hr.total_stars}/{hr.num_attacks}".center(5)
        destruction = f"{int(hr.total_destruction)}%".ljust(5)
        return [f"{stars} {destruction} {name}\n", round(hr.average_triples * 100, 3), name, hr.total_stars,
                player.town_hall]

    for player in players:  # type: MyCustomPlayer
        task = asyncio.ensure_future(fetch_n_rank(player=player))
        tasks.append(task)
    responses = await asyncio.gather(*tasks)
    ranked = [response for response in responses if response is not None]
    ranked = sorted(
        ranked, key=lambda l: (-l[-2], -l[1], l[2]), reverse=False)
    text = "```#   â˜…     DSTR%  NAME       \n"
    for count, rank in enumerate(ranked, 1):
        # spot_emoji = self.bot.get_number_emoji(color="gold", number=count)
        count = f"{count}.".ljust(3)
        text += f"{count} {rank[0]}"
    text += "```"
    if len(ranked) == 0:
        text = "No War Attacks Tracked Yet."
    embed = disnake.Embed(title=f"Star Leaderboard",
                          description=text, colour=disnake.Color.green())
    filter_types = []
    if True in fresh_type:
        filter_types.append("Fresh")
    if False in fresh_type:
        filter_types.append("Non-Fresh")
    for type in war_types:
        filter_types.append(str(type).capitalize())
    filter_types = ", ".join(filter_types)
    time_range = "This Season"
    if start_timestamp != 0 and end_timestamp != 9999999999:
        time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
    embed.set_footer(icon_url=clan.badge.url,
                     text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
    return embed


async def cwl_performance(bot: CustomClient, clan: coc.Clan):
    responses = await bot.cwl_db.find({"$and" : [{"clan_tag": clan.tag}, {"data" : {"$ne" : None}}]}).sort("season", -1).to_list(length=None)
    embed = Embed(
        title=f"**{clan.name} CWL History**",
        color=Color.green())

    embed.set_thumbnail(url=clan.badge.large)

    old_year = "2015"
    year_text = ""
    not_empty = False
    for response in responses:
        text, year = response_to_line(response.get("data"), clan)
        if year != old_year:
            if year_text != "":
                not_empty = True
                embed.add_field(
                    name=old_year,
                    value=year_text,
                    inline=False)

                year_text = ""
            old_year = year
        year_text += text

    if year_text != "":
        not_empty = True
        embed.add_field(
            name=f"**{old_year}**",
            value=year_text,
            inline=False)

    if not not_empty:
        embed.description = "No prior cwl data"

    return embed


