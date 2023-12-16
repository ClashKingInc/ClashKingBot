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
from utils.ClanCapital import gen_raid_weekend_datestrings, calc_raid_medals
from utils.clash import cwl_league_emojis, clan_super_troop_comp, clan_th_comp
from utils.discord_utils import fetch_emoji
from utils.general import create_superscript, response_to_line, fetch, get_guild_icon
from utils.constants import SUPER_SCRIPTS, MAX_NUM_SUPERS, TOWNHALL_LEVELS
from pytz import utc
from CustomClasses.DatabaseClasses import StatsClan
from utils.clash import league_to_emoji


async def family_composition(bot: CustomClient, server: disnake.Guild, type: str, embed_color: disnake.Color = disnake.Color.green()):
    bucket = defaultdict(int)
    clan_tags = await bot.get_guild_clans(guild_id=server.id)
    clans = await bot.get_clans(tags=clan_tags)

    def process_member(member: coc.ClanMember, bucket):
        if type == "Townhall":
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
    for key, value in sorted(bucket.items(), key=lambda x: x[1], reverse=True):
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
