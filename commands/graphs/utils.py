import asyncio
import coc
import disnake
import io
import pandas as pd
import pendulum as pend
import plotly.express as px
import plotly.io as pio
import statistics
import uuid

from classes.bot import CustomClient
from collections import defaultdict
from exceptions.CustomExceptions import MessageException
from typing import List
from utility.constants import leagues
from utility.clash.capital import get_season_raid_weeks
from utility.clash.other import (
    gen_season_start_end_as_timestamp,
    gen_season_start_end_as_iso,
)
from utility.cdn import upload_html_to_cdn


async def daily_graph(
    bot: CustomClient,
    clan_tags: List[str],
    attribute: str,
    months: int,
    limit: int = 20,
    html: bool = False,
) -> (disnake.File, str):
    clan_name_map = await bot.get_clan_name_mapping(clans=clan_tags)
    clan_member_map = await bot.get_mapped_clan_member_tags(clan_tags=clan_tags)
    member_map = {tag: f"{clan_name_map.get(clan_tag)}" for tag, clan_tag in clan_member_map.items()}

    def bucket_timestamps(timestamps: List[int], granularity):
        buckets = {}

        for timestamp in timestamps:
            dt_object = pend.from_timestamp(timestamp, tz=pend.UTC)
            if granularity == "day":
                key = dt_object.strftime("%Y-%m-%d")
            elif granularity == "hour":
                key = dt_object.strftime("%Y-%m-%d %H:00:00")
            else:
                continue
            if key not in buckets:
                buckets[key] = 0
            buckets[key] += 1
        return buckets

    data = {}
    if attribute == "activity":
        season = bot.gen_season_date(seasons_ago=24, as_text=False)[months - 1]
        data = await bot.player_stats.find(
            {"tag": {"$in": list(member_map.keys())}},
            projection={"tag": 1, f"last_online_times.{season}": 1},
        ).to_list(length=None)
        reformated_data = [
            {
                "tag": d.get("tag"),
                "times": d.get(f"last_online_times", {}).get(season, []),
            }
            for d in data
        ]
        holder = defaultdict(list)
        for data in reformated_data:
            holder[member_map.get(data.get("tag"))] += data.get("times")
        data = {}
        # data now looks like {clan : List[unix_timestamps]}
        for clan_name, times in holder.items():
            data[clan_name] = bucket_timestamps(timestamps=times, granularity="day")
    else:
        do_count = True
        if attribute == "troopupgrades":
            lookup = list(coc.enums.HOME_TROOP_ORDER + coc.enums.SPELL_ORDER + coc.enums.BUILDER_TROOPS_ORDER)
        elif attribute == "heroupgrades":
            lookup = list(coc.enums.HERO_ORDER + coc.enums.PETS_ORDER)
        elif attribute == "heroequipment":
            lookup = list(coc.enums.HERO_EQUIPMENT)
        else:
            if attribute in ["clanCapitalContributions", "bestTrophies"]:
                do_count = False
            lookup = [attribute]
        START_TIME = int(pend.now(tz=pend.UTC).subtract(months=months).timestamp())
        END_TIME = int(pend.now(tz=pend.UTC).timestamp())
        pipeline = [
            {
                "$match": {
                    "$and": [
                        {"tag": {"$in": list(member_map.keys())}},
                        {"type": {"$in": lookup}},
                        {"time": {"$gte": START_TIME}},
                        {"time": {"$lte": END_TIME}},
                    ]
                }
            },
            {"$group": {"_id": "$tag", "items": {"$push": "$$ROOT"}}},
        ]
        result = await bot.player_history.aggregate(pipeline=pipeline).to_list(length=None)
        holder = defaultdict(list)
        for data in result:
            for item in data.get("items", []):
                times = 1
                if do_count and str(item.get("p_value")).isdigit() and str(item.get("value")).isdigit():
                    times = item.get("value") - item.get("p_value")
                for x in range(0, times):
                    holder[member_map.get(data.get("_id"))] += [item.get("time")] * times
        data = {}
        for clan_name, times in holder.items():
            data[clan_name] = bucket_timestamps(timestamps=times, granularity="day")

    if not data:
        raise MessageException("No data found")
    data_list = []
    count_each_has = defaultdict(int)
    for clan, datetime_count_dict in data.items():
        for datetime, count in sorted(datetime_count_dict.items()):
            count_each_has[clan] += count
    top_20_clans = dict(sorted(count_each_has.items(), key=lambda x: x[1], reverse=True)[:limit])
    for clan, datetime_count_dict in data.items():
        if top_20_clans.get(clan) is None:
            continue
        for datetime, count in sorted(datetime_count_dict.items()):
            data_list.append({"Clan": clan, "Date": datetime, "Count": count})

    df = pd.DataFrame(data_list)
    # Create Plotly figure
    fig = px.line(df, x="Date", y="Count", color="Clan")
    fig.update_layout(
        title=dict(
            text=f"{attribute.replace('_', ' ').title()} ({months} months) | Made w/ ❤️ by ClashKing",
            xref="paper",  # Set xref to 'paper' for relative positioning
            automargin=False,
            x=0.5,
            y=0.985,
            xanchor="center",
            yanchor="top",
            font=dict(size=10),  # Set font size to make it small
        ),
        xaxis=dict(title=None),  # Remove x-axis label
        yaxis=dict(title=attribute),
        width=1000,  # Set the width of the plot
        height=500,  # Set the height of the plot
        margin=dict(l=20, r=20, t=20, b=25),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        showlegend=(len(clan_tags) >= 2),  # You can set this to False if you want to hide the legend initially
    )
    loop = asyncio.get_event_loop()

    def get_img(fig):
        return pio.to_image(fig, format="png", scale=1.0)

    img = await loop.run_in_executor(None, get_img, fig)
    web_version = None
    if html:
        html_content = pio.to_html(fig)
        buffer = io.BytesIO()
        buffer.write(bytes(html_content, "utf-8"))
        web_version = await upload_html_to_cdn(bytes_=buffer.getvalue(), id=str(uuid.uuid4()).replace("-", "")[:8])
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")
    return file, web_version


async def season_line_graph(
    bot: CustomClient,
    clan_tags: List[str],
    attribute: str,
    months: int,
    limit: int = 20,
    html: bool = False,
) -> (disnake.File, str):
    clan_name_map = await bot.get_clan_name_mapping(clans=clan_tags)

    seasons = bot.gen_season_date(seasons_ago=months, as_text=False)
    # attributes: activity, clan games, attack wins, capital raided, wars spun, war stars, cwl league, raid league, donations, received
    data = {}
    y_axis_set = dict(title=None)
    x_axis_set = dict(title=None)
    countable = True
    if attribute in ["activity", "clan_games", "attack_wins", "donations", "received"]:
        if attribute == "donations":
            attribute = "donated"
        data = defaultdict(lambda: defaultdict(int))
        projection = {"_id": 0, "tag": 1} | {s: 1 for s in seasons}
        clan_stats = await bot.clan_stats.find({"tag": {"$in": clan_tags}}, projection=projection).to_list(length=None)
        for clan in clan_stats:
            clan_name = clan_name_map.get(clan.get("tag"))
            for season in seasons:
                for value_data in clan.get(season, {}).values():
                    data[clan_name][season] += value_data.get(attribute, 0)
    elif attribute == "cwl_leagues":
        reversed_leagues = list(reversed(leagues))
        countable = False
        basic_clan = (
            await bot.basic_clan.find(
                {"tag": {"$in": clan_tags}},
                projection={"_id": 0, "tag": 1, "changes.clanWarLeague": 1},
            )
            .sort("members", -1)
            .limit(limit)
            .to_list(length=None)
        )
        data = defaultdict(lambda: defaultdict(int))
        for clan in basic_clan:
            cwl_data = clan.get("changes", {}).get("clanWarLeague", {})
            clan_name = clan_name_map.get(clan.get("tag"))
            for season in seasons:
                data[clan_name][season] = reversed_leagues.index(cwl_data.get(season, {}).get("league", "Unranked"))
        y_axis_set = dict(
            tickmode="array",
            tickvals=list(range(len(leagues))),
            ticktext=reversed_leagues,
            title=None,  # Optional Y-axis title
        )
        x_axis_set = dict(
            tickmode="array",
            tickvals=seasons,
            ticktext=seasons,
            title=None,  # Optional Y-axis title
        )
    elif attribute == "capital_leagues":
        reversed_leagues = list(reversed(leagues))
        countable = False
        basic_clan = (
            await bot.basic_clan.find(
                {"tag": {"$in": clan_tags}},
                projection={"_id": 0, "tag": 1, "changes.clanCapital": 1},
            )
            .sort("members", -1)
            .limit(limit)
            .to_list(length=None)
        )
        data = defaultdict(lambda: defaultdict(int))
        raid_weeks = []
        for season in seasons:
            raid_weeks += get_season_raid_weeks(season=season)
        if raid_weeks.count("2023-11-10") == 1:
            raid_weeks.remove("2023-11-10")
        for clan in basic_clan:
            cwl_data = clan.get("changes", {}).get("clanCapital", {})
            clan_name = clan_name_map.get(clan.get("tag"))
            for week in raid_weeks:
                data[clan_name][week] = reversed_leagues.index(cwl_data.get(week, {}).get("league", "Unranked"))
        y_axis_set = dict(
            tickmode="array",
            tickvals=list(range(len(leagues))),
            ticktext=reversed_leagues,
            title=None,  # Optional Y-axis title
        )
    elif attribute == "capital_trophies":
        countable = False
        basic_clan = (
            await bot.basic_clan.find(
                {"tag": {"$in": clan_tags}},
                projection={"_id": 0, "tag": 1, "changes.clanCapital": 1},
            )
            .sort("members", -1)
            .limit(limit)
            .to_list(length=None)
        )
        data = defaultdict(lambda: defaultdict(int))
        raid_weeks = []
        for season in seasons:
            raid_weeks += get_season_raid_weeks(season=season)
        if raid_weeks.count("2023-11-10") == 1:
            raid_weeks.remove("2023-11-10")
        for clan in basic_clan:
            cwl_data = clan.get("changes", {}).get("clanCapital", {})
            clan_name = clan_name_map.get(clan.get("tag"))
            for week in raid_weeks:
                data[clan_name][week] = cwl_data.get(week, {}).get("trophies", 0)

    if not data:
        raise MessageException("No data found")
    data_list = []
    if countable:
        count_each_has = defaultdict(int)
        for clan, season_data in data.items():
            for season_id, season_count in sorted(season_data.items(), key=lambda x: x[0]):
                count_each_has[clan] += season_count
        top_20_clans = dict(sorted(count_each_has.items(), key=lambda x: x[1], reverse=True)[:limit])

    for clan, season_data in data.items():
        if countable and top_20_clans.get(clan) is None:
            continue
        for season_id, season_count in sorted(season_data.items(), key=lambda x: x[0]):
            data_list.append({"Clan": clan, "Date": season_id, "Count": season_count})

    df = pd.DataFrame(data_list)
    # Create Plotly figure
    fig = px.line(df, x="Date", y="Count", color="Clan")
    fig.update_layout(
        title=dict(
            text=f"{attribute.replace('_', ' ').title()} ({months} months) | Made w/ ❤️ by ClashKing",
            xref="paper",  # Set xref to 'paper' for relative positioning
            automargin=False,
            x=0.5,
            y=0.985,
            xanchor="center",
            yanchor="top",
            font=dict(size=10),  # Set font size to make it small
        ),
        xaxis=x_axis_set,  # Remove x-axis label
        yaxis=y_axis_set,
        width=1000,  # Set the width of the plot
        height=500,  # Set the height of the plot
        margin=dict(l=20, r=20, t=40, b=25),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        showlegend=(len(clan_tags) >= 2),  # You can set this to False if you want to hide the legend initially
    )
    loop = asyncio.get_event_loop()

    def get_img(fig):
        return pio.to_image(fig, format="png", scale=1.0)

    img = await loop.run_in_executor(None, get_img, fig)
    web_version = None
    if html:
        html_content = pio.to_html(fig)
        buffer = io.BytesIO()
        buffer.write(bytes(html_content, "utf-8"))
        web_version = await upload_html_to_cdn(bytes_=buffer.getvalue(), id=str(uuid.uuid4()).replace("-", "")[:8])
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")
    return file, web_version


async def monthly_bar_graph(
    bot: CustomClient,
    clan_tags: List[str],
    attribute: str,
    season: str,
    html: bool = False,
) -> (disnake.File, str):
    name_mapping = await bot.get_clan_name_mapping(clans=clan_tags)
    mapped_member_tags = await bot.get_mapped_clan_member_tags(clan_tags=clan_tags)
    # {member_tag: clan_tag}
    member_tags = list(mapped_member_tags.keys())
    if attribute in ["gold_looted", "elixir_looted", "de_looted"]:
        data = defaultdict(int)
        player_stats = await bot.player_stats.find(
            {"tag": {"$in": member_tags}},
            projection={
                "_id": 0,
                f"gold.{season}": 1,
                f"elixir.{season}": 1,
                f"dark_elixir.{season}": 1,
                "tag": 1,
            },
        ).to_list(length=None)
        attribute_map = {
            "gold_looted": "gold",
            "elixir_looted": "elixir",
            "de_looted": "dark_elixir",
        }
        for player in player_stats:
            player_clan_tag = mapped_member_tags.get(player.get("tag"))
            clan_name = name_mapping.get(player_clan_tag)
            data[f"{clan_name}"] += player.get(attribute_map.get(attribute), {}).get(season, 0)

    elif attribute in ["donations", "received", "activity", "attack_wins"]:
        attribute_map = {
            "donations": "donated",
            "received": "received",
            "activity": "activity",
            "attack_wins": "attack_wins",
        }
        data = defaultdict(int)
        clan_stats = await bot.clan_stats.find(
            {"tag": {"$in": clan_tags}}, projection={"_id": 0, f"{season}": 1, "tag": 1}
        ).to_list(length=None)
        for clan in clan_stats:
            clan_name = name_mapping.get(clan.get("tag"))
            for value_data in clan.get(season, {}).values():
                data[clan_name] += value_data.get(attribute_map.get(attribute), 0)

    elif attribute == "capital_gold_donated":
        data = defaultdict(int)
        player_stats = await bot.player_stats.find(
            {"tag": {"$in": member_tags}},
            projection={"_id": 0, f"capital_gold": 1, "tag": 1},
        ).to_list(length=None)
        season_raid_weeks = get_season_raid_weeks(season=season)
        for player in player_stats:
            player_clan_tag = mapped_member_tags.get(player.get("tag"))
            clan_name = name_mapping.get(player_clan_tag)
            for week in season_raid_weeks:
                data[f"{clan_name}"] += sum(player.get("capital_gold", {}).get(week, {}).get("donate", []))

    elif attribute == "capital_gold_raided":
        data = defaultdict(int)
        season_raid_weeks = get_season_raid_weeks(season=season)
        times_to_pull = []
        for week in season_raid_weeks:
            weekend_to_iso = pend.parse(week)
            weekend_to_iso = weekend_to_iso.replace(hour=7)
            times_to_pull.append(weekend_to_iso.strftime("%Y%m%dT%H%M%S.000Z"))
        raid_stats = await bot.raid_weekend_db.find(
            {
                "$and": [
                    {"clan_tag": {"$in": clan_tags}},
                    {"data.startTime": {"$in": times_to_pull}},
                ]
            },
            projection={"clan_tag": 1, "_id": 0, "data.capitalTotalLoot": 1},
        ).to_list(length=None)
        for raid in raid_stats:
            clan_name = name_mapping.get(raid.get("clan_tag"))
            data[clan_name] += raid.get("data", {}).get("capitalTotalLoot", 0)

    elif attribute == "average_raid_participants":
        data = defaultdict(int)
        season_raid_weeks = get_season_raid_weeks(season=season)
        times_to_pull = []
        for week in season_raid_weeks:
            weekend_to_iso = pend.parse(week)
            weekend_to_iso = weekend_to_iso.replace(hour=7)
            times_to_pull.append(weekend_to_iso.strftime("%Y%m%dT%H%M%S.000Z"))
        raid_stats = await bot.raid_weekend_db.find(
            {
                "$and": [
                    {"clan_tag": {"$in": clan_tags}},
                    {"data.startTime": {"$in": times_to_pull}},
                ]
            },
            projection={"clan_tag": 1, "_id": 0, "data.members": 1},
        ).to_list(length=None)
        holder = defaultdict(list)
        for raid in raid_stats:
            clan_name = name_mapping.get(raid.get("clan_tag"))
            holder[clan_name].append(len(raid.get("data", {}).get("members", [])))

        for name, list_members in holder.items():
            data[name] = int(statistics.mean(list_members))

    elif attribute in ["troops_upgraded", "heroes_upgraded"]:
        enum_map = {
            "troops_upgraded": coc.enums.HOME_TROOP_ORDER + coc.enums.SPELL_ORDER + coc.enums.BUILDER_TROOPS_ORDER,
            "heroes_upgraded": coc.enums.HERO_ORDER + coc.enums.PETS_ORDER,
        }
        SEASON_START, SEASON_END = gen_season_start_end_as_timestamp(season=season)
        pipeline = [
            {
                "$match": {
                    "$and": [
                        {"clan": {"$in": clan_tags}},
                        {"type": {"$in": enum_map.get(attribute)}},
                        {"time": {"$gte": SEASON_START}},
                        {"time": {"$lte": SEASON_END}},
                    ]
                }
            },
            {"$group": {"_id": "$clan", "num": {"$sum": 1}}},
        ]
        results = await bot.player_history.aggregate(pipeline=pipeline).to_list(length=None)
        data = defaultdict(int)
        for result in results:
            clan_name = name_mapping.get(result.get("_id"))
            data[clan_name] = result.get("num")

    elif attribute in ["war_stars", "wars_won", "wars_spun"]:
        SEASON_START, SEASON_END = gen_season_start_end_as_iso(season=season)

        clan_wars = await bot.clan_wars.find(
            {
                "$and": [
                    {
                        "$or": [
                            {"data.clan.tag": {"$in": clan_tags}},
                            {"data.opponent.tag": {"$in": clan_tags}},
                        ]
                    },
                    {"data.preparationStartTime": {"$gte": SEASON_START}},
                    {"data.preparationStartTime": {"$lte": SEASON_END}},
                ]
            },
            projection={"data": 1, "_id": 0},
        ).to_list(length=None)
        data = defaultdict(int)
        for war in clan_wars:
            main_clan = war.get("data").get("clan").get("tag")
            if war.get("data").get("opponent").get("tag") in clan_tags:
                main_clan = war.get("data").get("opponent").get("tag")
            coc_war = coc.ClanWar(data=war.get("data"), client=None, clan_tag=main_clan)
            clan_name = name_mapping.get(main_clan)
            if attribute == "war_stars":
                data[clan_name] += coc_war.clan.stars
            elif attribute == "wars_won":
                if coc_war.status == "won":
                    data[clan_name] += 1
            else:
                if str(coc_war.type) != "cwl":
                    data[clan_name] += 1

    total = sum(data.values())
    if total == 0:
        raise MessageException("No data at this time")
    clans = []
    bar_text = []
    attributes = []
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)[:20]
    for clan, attribute_value in reversed(sorted_data):
        perc = int((attribute_value / total) * 100)
        clans.append(clan)
        bar_text.append(f"{attribute_value:,} | {perc}%")
        attributes.append(attribute_value)

    # Create a horizontal bar chart
    fig = px.bar(
        x=attributes,
        y=clans,
        orientation="h",
        text=bar_text,  # Display attribute value on the bar
        labels={"x": f"{attribute.replace('_', ' ').title()} ({season})"},
    )

    fig.update_layout(
        yaxis=dict(title=None),
        width=1000,  # Set the width of the plot
        height=750,  # Set the height of the plot
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,  # You can set this to False if you want to hide the legend initially
    )
    # Customize the layout if needed
    loop = asyncio.get_event_loop()

    def get_img(fig):
        return pio.to_image(fig, format="png", scale=1.0)

    img = await loop.run_in_executor(None, get_img, fig)
    web_version = None
    if html:
        html_content = pio.to_html(fig)
        buffer = io.BytesIO()
        buffer.write(bytes(html_content, "utf-8"))
        web_version = await upload_html_to_cdn(bytes_=buffer.getvalue(), id=str(uuid.uuid4()).replace("-", "")[:8])
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")
    return file, web_version
