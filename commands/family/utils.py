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
from utility.clash.capital import gen_raid_weekend_datestrings, calc_raid_medals
from utility.clash.other import cwl_league_emojis, clan_super_troop_comp, clan_th_comp, league_to_emoji
from utility.discord_utils import register_button
from utility.general import create_superscript, response_to_line, fetch, get_guild_icon
from utility.constants import SUPER_SCRIPTS, MAX_NUM_SUPERS, TOWNHALL_LEVELS
from pytz import utc


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




@register_button("clanhero", parser="_:clan:season:")
async def clan_hero_progress(bot: CustomClient, season: str, clan: coc.Clan = None, server: disnake.Guild = None, limit: int = 50, embed_color: disnake.Color = disnake.Color.green()):
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