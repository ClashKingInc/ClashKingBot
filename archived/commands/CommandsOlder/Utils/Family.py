import disnake
import coc
import asyncio

from coc.raid import RaidLogEntry
from datetime import datetime
from classes.bot import CustomClient
from classes.player.stats import StatsPlayer, ClanCapitalWeek
from utility.general import create_superscript
from utility.ClanCapital import (
    gen_raid_weekend_datestrings,
    get_raidlog_entry,
    calc_raid_medals,
)
from utility.constants import item_to_name, SHORT_PLAYER_LINK, leagues
from utility.clash import cwl_league_emojis
from classes.enums import TrophySort
from collections import defaultdict
from typing import List
from pytz import utc


async def create_trophies(bot: CustomClient, guild: disnake.Guild, sort_type: TrophySort):
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
    clans = await bot.get_clans(tags=clan_tags)
    clans = [clan for clan in clans if clan is not None]
    if not clans:
        return disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())

    if sort_type is TrophySort.home:
        point_type = "Trophies"
        clans = sorted(clans, key=lambda l: l.points, reverse=True)
        clan_text = [
            f"{bot.emoji.trophy}`{clan.points:5} {clan.name}`{create_superscript(clan.member_count)}" for clan in clans
        ]
    elif sort_type is TrophySort.versus:
        point_type = "Versus Trophies"
        clans = sorted(clans, key=lambda l: l.builder_base_points, reverse=True)
        clan_text = [f"{bot.emoji.versus_trophy}`{clan.builder_base_points:5} {clan.name}`" for clan in clans]
    elif sort_type is TrophySort.capital:
        point_type = "Capital Trophies"
        clans = sorted(clans, key=lambda l: l.capital_points, reverse=True)
        clan_text = [f"{bot.emoji.capital_trophy}`{clan.capital_points:5} {clan.name}`" for clan in clans]

    clan_text = "\n".join(clan_text)

    embed = disnake.Embed(
        title=f"**{guild.name} {point_type}**",
        description=clan_text,
        color=disnake.Color.green(),
    )
    if guild.icon is not None:
        embed.set_footer(text="Last Refreshed", icon_url=guild.icon.url)
    embed.timestamp = datetime.now()
    return embed


async def create_joinhistory(
    bot: CustomClient,
    guild: disnake.Guild,
    season: str,
    embed_color=disnake.Color.green(),
):
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
    text = ""

    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))

    pipeline = [
        {
            "$match": {
                "$and": [
                    {"tag": {"$in": clan_tags}},
                    {"type": "members"},
                    {"time": {"$gte": season_start.timestamp()}},
                    {"time": {"$lte": season_end.timestamp()}},
                ]
            }
        },
        {"$sort": {"tag": 1, "time": 1}},
        {"$group": {"_id": "$tag", "changes": {"$push": "$$ROOT"}}},
        {
            "$lookup": {
                "from": "clan_cache",
                "localField": "_id",
                "foreignField": "tag",
                "as": "name",
            }
        },
        {"$set": {"name": "$name.data.name"}},
    ]
    results: List[dict] = await bot.clan_history.aggregate(pipeline).to_list(length=None)

    class ItemHolder:
        def __init__(self, data):
            self.tag = data.get("tag")
            self.value = data.get("value")
            self.time = data.get("time")

    results = [r for r in results if r.get("name")]
    results.sort(key=lambda x: (x.get("name"))[0].upper())
    for clan in results:
        changes = clan.get("changes", [])
        name = clan.get("name")[0]
        if len(changes) <= 1:
            text += f"  0 Join   0 Left | {name[:13]}\n"

        joined = 0
        left = 0
        for count, change in enumerate(changes[1:]):
            previous_change = ItemHolder(data=changes[count])
            change = ItemHolder(data=change)
            if change.value - previous_change.value >= 0:
                joined += change.value - previous_change.value
            else:
                left += previous_change.value - change.value

        text += f"{joined:>4} J {left:>4} L {name[:13]}\n"

    embed = disnake.Embed(
        title=f"{guild.name} Join/Leave History",
        description=f"```{text}```",
        colour=embed_color,
    )
    embed.set_footer(text="J = Join, L = Left")
    return embed
