
from typing import List
import coc
import disnake
import plotly.io as pio
import io
import plotly.graph_objects as go
import plotly.express as px


from collections import defaultdict
from Utils.general import create_superscript
from CustomClasses.CustomBot import CustomClient
from datetime import datetime, timedelta
from pytz import utc
import pandas as pd

async def capital_stats_monthly_graph(clan_tags: List[str], bot: CustomClient, attribute: str, months: int = 6):
    dates = bot.gen_season_date(seasons_ago=months, as_text=False)

    season_stats = {}
    clan_to_name = {}

    for date in reversed(dates):
        year = date[:4]
        month = date[-2:]
        START_DATE = coc.utils.get_season_start(month=(int(month) - 1 if int(month) != 1 else month == 12), year=int(year) if int(month) != 1 else int(year) - 1).strftime('%Y%m%dT%H%M%S.000Z')
        END_DATE = coc.utils.get_season_end(month=(int(month) - 1 if int(month) != 1 else month == 12), year=int(year) if int(month) != 1 else int(year) - 1).strftime('%Y%m%dT%H%M%S.000Z')

        pipeline = [
            {"$match": {"$and": [{"clan_tag": {"$in": clan_tags}}, {"data.startTime": {"$gte": START_DATE}}, {"data.endTime": {"$lte": END_DATE}}]}},
        ]
        raids = await bot.raid_weekend_db.aggregate(pipeline, allowDiskUse=True).to_list(length=None)

        basic_clans = await bot.basic_clan.find({"tag": {"$in": clan_tags}}).to_list(length=None)
        for b_c in basic_clans:
            clan_to_name[b_c.get("tag")] = b_c.get("name")

        player_tags = set()
        for raid in raids:
            raid = raid.get("data")
            raid = coc.RaidLogEntry(data=raid, client=bot.coc_client)
            for raid_member in raid.members:
                player_tags.add(raid_member.tag)

        by_clan = defaultdict(lambda : defaultdict(int))

        player_stats = await bot.player_stats.find({"tag": {"$in": list(player_tags)}}, {"tag": 1, "capital_gold": 1}).to_list(length=None)
        donated_capital = {}
        for p in player_stats:
            donated_capital[p.get("tag")] = p.get("capital_gold", {})
        for raid in raids:
            clan_tag = raid.get("clan_tag")
            raid = raid.get("data")
            raid = coc.RaidLogEntry(data=raid, client=bot.coc_client)
            raid_date = str(raid.start_time.time.date())
            for raid_member in raid.members:
                tag = raid_member.tag
                by_clan[clan_tag]["raided"] += raid_member.capital_resources_looted
                by_clan[clan_tag]["donated"] += sum(donated_capital.get(tag, {}).get(raid_date, {}).get("donate", [0]))
                by_clan[clan_tag]["attacks"] += raid_member.attack_count
            by_clan[clan_tag]["medals"] += raid.offensive_reward * 6 + raid.defensive_reward

        by_clan_totals = []
        for k, v in by_clan.items():
            if clan_to_name.get(k) is None:
                continue
            by_clan_totals.append({"tag": k, "name": clan_to_name.get(k)} | dict(v))

        season_stats[date] = by_clan_totals


    for tag, name in clan_to_name.copy().items():
        if name is None:
            del clan_to_name[tag]
        clan_to_name[tag] = f"{name} ({tag})"

    data_by_clan = defaultdict(list)
    for date, season_data in season_stats.items():
        clans_to = clan_tags.copy()
        for clan_data in season_data:
            if clan_to_name.get(clan_data.get("tag")) is None:
                continue
            data_by_clan[clan_to_name.get(clan_data.get("tag"))].append(clan_data.get(attribute))
            clans_to.remove(clan_data.get("tag"))
        for c in clans_to:
            if clan_to_name.get(c) is None:
                continue
            data_by_clan[clan_to_name.get(c)].append(0)

    fig = go.Figure()

    for name, data in data_by_clan.items():
        fig.add_trace(go.Scatter(
            x=list(season_stats.keys()),
            y=data,
            name=name)
        )

    fig.update_layout(
        title=f"Capital {attribute.capitalize()} (last {months} months)",
        xaxis_title="Season",
        yaxis_title=attribute.capitalize(),
        legend_title="Clans",
        legend=dict(
            orientation="h",

        )
    )
    img = pio.to_image(fig, format="png", scale=3.0)
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")
    return file


async def clan_donation_monthly_graph(clan_tags: List[str], bot: CustomClient, attribute: str, months: int = 6):
    pass

async def clan_war_attack_monthly_graph(clan_tags: List[str], bot: CustomClient, attribute: str, months: int = 6):
    pass