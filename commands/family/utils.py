import asyncio
import aiohttp
import coc
import emoji
import re
import disnake

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
from utility.clash.capital import gen_raid_weekend_datestrings, calc_raid_medals, get_season_raid_weeks
from utility.clash.other import cwl_league_emojis, clan_super_troop_comp, clan_th_comp, league_to_emoji, gen_season_start_end_as_iso
from utility.discord_utils import register_button
from utility.general import create_superscript, response_to_line, fetch, get_guild_icon
from utility.constants import leagues
from pytz import utc
import pendulum as pend
import countryflag


@register_button("familycompo", parser="_:server:type")
async def family_composition(bot: CustomClient, server: disnake.Guild, type: str, embed_color: disnake.Color = disnake.Color.green()):
    bucket = defaultdict(int)
    clan_tags = await bot.get_guild_clans(guild_id=server.id)
    clans = await bot.get_clans(tags=clan_tags)

    def process_member(member: coc.ClanMember, bucket):
        if type == "Townhall":
            if member._raw_data.get("townHallLevel") == 0:
                return
            bucket[str(member._raw_data.get("townHallLevel"))] += 1
        elif type == "Trophies":
            bucket[str(int(str(member.trophies)[0]) * 1000 if member.trophies >= 1000 else 100)] += 1
        elif type == "Location":
            location = tag_to_location.get(member.tag)
            if location:
                bucket[location] += 1
        elif type == "Role":
            bucket[member.role.in_game_name] += 1
        elif type == "League":
            bucket[member.league.name] += 1

    if type == "Location":
        location_info = await bot.leaderboard_db.find({"tag": {"$in": [m.tag for clan in clans for m in clan.members]}}, {"tag": 1, "country_name": 1, "country_code": 1}).to_list(length=None)
        tag_to_location = {d.get("tag"): d.get("country_name") for d in location_info}
        location_name_to_code = {d.get("country_name"): d.get("country_code") for d in location_info}

    total_count = 0
    for clan in clans:
        for member in clan.members:
            total_count += 1
            process_member(member, bucket)

    formats = {
        "Townhall": "`{value:2}` {icon}`TH{key} `\n",
        "Trophies": "`{value:2}` {icon}`{key}+ Trophies`\n",
        "Location": "`{value:2}` {icon}`{key}`\n",
        "Role": "`{value:2}` {icon}`{key}`\n",
        "League": "`{value:2}` {icon}`{key}`\n",
    }
    footer_text = f"{total_count} accounts"

    def get_icon(type, key):
        if type == "Townhall":
            return bot.fetch_emoji(int(key))
        elif type == "Location":
            return f":flag_{location_name_to_code.get(key).lower()}:"
        elif type == "League":
            return league_to_emoji(key)
        return ""

    text = ""
    field_to_sort = 1
    if type == "Townhall":
        field_to_sort = 0
    for key, value in sorted(bucket.items(), key=lambda x: int(x[field_to_sort]), reverse=True):
        icon = get_icon(type, key)
        text += formats[type].format(key=key, value=value, icon=icon)

    if type == "Townhall":
        total = sum(int(key) * value for key, value in bucket.items())
        footer_text += f" | Avg Townhall: {round((total / total_count), 2)}"

    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(name=f"{server.name} {type} Compo", icon_url=get_guild_icon(guild=server))
    embed.set_footer(text=footer_text)
    embed.timestamp = datetime.now()
    return embed



@register_button("familysummary", parser="_:server:season:limit")
async def family_summary(bot: CustomClient, server: disnake.Guild, season: str, limit: int, embed_color: disnake.Color):
    season = bot.gen_season_date() if season is None else season
    member_tags = await bot.get_family_member_tags(guild_id=server.id)
    #we dont want results w/ no name
    results = await bot.player_stats.find({"$and" : [
                                            {"tag" : {"$in": member_tags}},
                                            {"name" : {"$ne" : None}}]}
                                          ).to_list(length=None)
    text = ""
    for option, emoji in zip(["gold", "elixir", "dark_elixir"], [bot.emoji.gold, bot.emoji.elixir, bot.emoji.dark_elixir]):
        top_results = sorted(results, key=lambda x: x.get(option, {}).get(season, 0), reverse=True)[:limit]
        if top_results[0] == 0:
            continue
        for count, result in enumerate(top_results, 1):
            looted = result.get(option, {}).get(season, 0)
            if looted == 0:
                continue
            if count == 1:
                text += f"**{emoji} {option.replace('_', ' ').title()}\n**"
            text += f"`{count:<2} {'{:,}'.format(looted):11} \u200e{result['name']}`\n"
        text += "\n"


    for option, emoji in zip(["activity", "attack_wins", "season_trophies"], [bot.emoji.clock, bot.emoji.wood_swords, bot.emoji.trophy]):
        top_results = sorted(results, key=lambda x: x.get(option, {}).get(season, 0), reverse=True)[:limit]
        if top_results[0] == 0:
            continue
        for count, result in enumerate(top_results, 1):
            looted = result.get(option, {}).get(season, 0)
            if looted == 0:
                continue
            if count == 1:
                text += f"**{emoji} {option.replace('_', ' ').title()}\n**"
            text += f"`{count:<2} {'{:,}'.format(looted):4} \u200e{result['name']}`\n"
        text += "\n"

    first_embed = disnake.Embed(description=text, color=embed_color)
    first_embed.set_author(name=f"{server.name} Season Summary ({season})", icon_url=get_guild_icon(server))
    text = ""

    top_results = sorted(results, key=lambda x: x.get("donations", {}).get(season, {}).get("donated", 0), reverse=True)[:limit]
    text += f"**{bot.emoji.up_green_arrow} Donations\n**"
    for count, result in enumerate(top_results, 1):
        looted = result.get("donations", {}).get(season, {}).get("donated", 0)
        text += f"`{count:<2} {'{:,}'.format(looted):7} \u200e{result['name']}`\n"
    text += "\n"

    top_results = sorted(results, key=lambda x: x.get("donations", {}).get(season, {}).get("received", 0), reverse=True)[:limit]
    text += f"**{bot.emoji.down_red_arrow} Received\n**"
    for count, result in enumerate(top_results, 1):
        looted = result.get("donations", {}).get(season, {}).get("received", 0)
        text += f"`{count:<2} {'{:,}'.format(looted):7} \u200e{result['name']}`\n"
    text += "\n"

    season_raid_weeks = get_season_raid_weeks(season=season)
    def capital_gold_donated(elem):
        cc_results = []
        for week in season_raid_weeks:
            week_result = elem.get("capital_gold", {}).get(week)
            cc_results.append(ClanCapitalWeek(week_result))
        return sum([sum(cap.donated) for cap in cc_results])
    top_capital_donos = sorted(results, key=capital_gold_donated, reverse=True)[:limit]
    text += f"**{bot.emoji.capital_gold} CG Donated\n**"
    for count, result in enumerate(top_capital_donos, 1):
        cg_donated = capital_gold_donated(result)
        text += f"`{count:<2} {'{:,}'.format(cg_donated):7} \u200e{result['name']}`\n"
    text += "\n"

    def capital_gold_raided(elem):
        cc_results = []
        for week in season_raid_weeks:
            week_result = elem.get("capital_gold", {}).get(week)
            cc_results.append(ClanCapitalWeek(week_result))
        return sum([sum(cap.raided) for cap in cc_results])
    top_capital_raided = sorted(results, key=capital_gold_raided, reverse=True)[:limit]
    text += f"**{bot.emoji.capital_gold} CG Raided\n**"
    for count, result in enumerate(top_capital_raided, 1):
        cg_raided = capital_gold_raided(result)
        text += f"`{count:<2} {'{:,}'.format(cg_raided):7} \u200e{result['name']}`\n"
    text += "\n"

    SEASON_START, SEASON_END = gen_season_start_end_as_iso(season=season)
    pipeline = [
        {'$match': {
            "$and" : [
                {'$or': [{'data.clan.members.tag': {'$in': member_tags}},
                        {'data.opponent.members.tag': {'$in': member_tags}}]},
                {"data.preparationStartTime": {"$gte": SEASON_START}}, {"data.preparationStartTime": {"$lte": SEASON_END}},
                {"type" : {"$ne" : "friendly"}}
                ]
            }
        },
        {'$project': {'_id': 0,'uniqueKey': {'$concat': [
                        {'$cond': {
                            'if': {'$lt': ['$data.clan.tag', '$data.opponent.tag']},
                            'then': '$data.clan.tag',
                            'else': '$data.opponent.tag'}},
                        {'$cond': {
                            'if': {'$lt': ['$data.opponent.tag', '$data.clan.tag']},
                            'then': '$data.opponent.tag',
                            'else': '$data.clan.tag'}},
                        '$data.preparationStartTime']},
                      'data': 1}},
        {'$group': {'_id': '$uniqueKey', 'data': {'$first': '$data'}}},
        {'$project': {'members': {'$concatArrays': ['$data.clan.members', '$data.opponent.members']}}},
        {'$unwind': '$members'},
        {"$match" : {"members.tag" : {"$in" : member_tags}}},
        {'$project': {
            '_id': 0,
            'tag': '$members.tag',
            "name" : "$members.name",
            'stars': {
                '$sum': '$members.attacks.stars'}
            }
        },
        {'$group': {
            '_id': '$tag',
            "name" : {"$last" : "$name"},
            'totalStars': {
                '$sum': '$stars'}
            }
        },
        {"$sort" : {"totalStars" : -1}},
        {"$limit" : limit}
    ]
    war_star_results = await bot.clan_war.aggregate(pipeline=pipeline).to_list(length=None)

    if war_star_results:
        text += f"**{bot.emoji.war_star} War Stars\n**"
        for count, result in enumerate(war_star_results, 1):
            text += f"`{count:<2} {'{:,}'.format(result.get('totalStars')):3} \u200e{result.get('name')}`\n"

    second_embed = disnake.Embed(description=text, color=embed_color)
    second_embed.timestamp = pend.now(tz=pend.UTC)
    return [first_embed, second_embed]


@register_button("familyoverview", parser="_:server")
async def family_overview(bot: CustomClient, server: disnake.Guild, embed_color: disnake.Color):
    season = bot.gen_season_date()
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": server.id})
    basic_clans = await bot.basic_clan.find({"tag": {"$in": clan_tags}}).to_list(length=None)

    member_count = sum([c.get("members", 0) for c in basic_clans])
    member_tags = [m.get("tag") for clan in basic_clans for m in clan.get("memberList", [])]
    sixty_mins = pend.now(tz=pend.UTC).subtract(minutes=60)
    last_online_sixty_mins = await bot.player_stats.count_documents({"$and" : [{"tag" : {"$in" : member_tags}}, {"last_online" : {"$gte" : int(sixty_mins.timestamp())}}]})
    description_text = (f"- {server.member_count} Members\n"
                        f"- {len(basic_clans)} Clans, {member_count} Members\n"
                        f"- {last_online_sixty_mins} Online (last hour)\n"
                        f"- Created: {bot.timestamper(unix_time=int(server.created_at.timestamp())).text_date}\n"
                        f"- Owner: {server.owner.display_name}")
    first_embed = disnake.Embed(description=description_text, color=embed_color)
    first_embed.set_author(name=f"{server.name} Overview", icon_url=get_guild_icon(server))

    th_compo_bucket = defaultdict(int)
    total_trophies = 0
    legend_player_count = 0
    for clan in basic_clans:
        for member in clan.get("memberList"):
            if member.get('townhall') != 0:
                th_compo_bucket[member.get("townhall")] += 1
            total_trophies += member.get("trophies")
            if member.get("league") == "Legend League":
                legend_player_count += 1

    clan_stats = await bot.clan_stats.find({"tag" : {"$in" : clan_tags}}, projection={"_id" : 0, "tag" : 1, f"{season}" : 1}).to_list(length=None)
    total_donations = 0
    total_received = 0
    total_de_looted = 0
    total_gold_looted = 0
    total_elix_looted = 0
    total_attack_wins = 0
    total_activity = 0
    for c_stat in clan_stats:
        season_stats = c_stat.get(season, {})
        for _, value in season_stats.items():
            total_donations += value.get("donated", 0)
            total_received += value.get("received", 0)
            total_de_looted += value.get("dark_elixir_looted", 0)
            total_gold_looted += value.get("gold_looted", 0)
            total_elix_looted += value.get("elixir_looted", 0)
            total_attack_wins += value.get("attack_wins", 0)
            total_activity += value.get("activity", 0)

    SEASON_START, SEASON_END = gen_season_start_end_as_iso(season=season)
    wars = await bot.clan_wars.find({"$and" : [
                {'$or': [{'data.clan.tag': {'$in': clan_tags}},
                        {'data.opponent.tag': {'$in': clan_tags}}]},
                {"data.preparationStartTime": {"$gte": SEASON_START}}, {"data.preparationStartTime": {"$lte": SEASON_END}},
                {"type" : {"$ne" : "friendly"}}
                ]
            }, projection={"data.clan.tag" : 1, "data.clan.stars" : 1, "data.opponent.stars" : 1, "data.opponent.tag" : 1}).to_list(length=None)
    total_war_stars = 0
    for war in wars:
        if war.get("data").get("clan").get("tag") in clan_tags:
            total_war_stars += war.get("data").get("clan").get("stars")
        else:
            total_war_stars += war.get("data").get("opponent").get("stars")

    stats_text = (f"```Donations: {total_donations:,}\n"
                  f"Received : {total_received:,}\n"
                  f"War Stars: {total_war_stars:,}\n"
                  #f"Gold: {total_gold_looted:,}\n"
                  #f"Elixir: {total_elix_looted:,}\n"
                  #f"Dark Elixir: {total_de_looted:,}\n"
                  f"Activity: {total_activity:,}\n"
                  f"Attack Wins: {total_attack_wins:,}\n```")
    first_embed.add_field(name="Season Stats", value=stats_text, inline=False)

    top_ten_clans = sorted(basic_clans, key=lambda x: leagues.index(x.get("warLeague", "Unranked")))[:10]
    clan_text = ""
    for clan in top_ten_clans:
        clan_text += f'{cwl_league_emojis(clan.get("warLeague", "Unranked"))}`{clan.get("name"):<15} ({clan.get("members")}/50)`\n'
    first_embed.add_field(name="Top 10 Clans", value=clan_text, inline=False)

    th_comp_string = ""
    count = 0
    for th_level, th_count in sorted(th_compo_bucket.items(), reverse=True):
        th_emoji = bot.fetch_emoji(th_level)
        th_comp_string += f"{th_emoji}`{th_count}` "
        count += 1
        if count % 5 == 0:
            th_comp_string += "\n"
    first_embed.add_field(name="Townhall Compo", value=th_comp_string, inline=False)
    return first_embed
