
from typing import List
import coc
import disnake
import plotly.io as pio
import io
import plotly.graph_objects as go
import uuid
from exceptions.CustomExceptions import MessageException
from collections import defaultdict
from utility.general import create_superscript
from utility.cdn import upload_html_to_cdn
from CustomClasses.CustomBot import CustomClient
import pendulum as pend

import plotly.express as px
import pandas as pd

async def monthly_capital_stats_graph(clan_tags: List[str], bot: CustomClient, attribute: str, months: int = 6):
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



async def create_clan_donation_graph(bot: CustomClient, clans: List[coc.Clan], townhalls: List[int], season: str, type: str):
    pipeline = [
        {"$match": {"$and": [{"clan_tag": {"$in": [clan.tag for clan in clans]}}, {"townhall": {"$in": townhalls}}]}},
        {"$group": {"_id": "$clan_tag", "total_donated": {"$sum": f"$donations.{season}.donated"},
                    "total_received": {"$sum": f"$donations.{season}.received"}}},
        {"$sort": {f"total_{type}": 1}}
    ]
    results = await bot.player_stats.aggregate(pipeline).to_list(length=None)
    clan_tags = set([clan.tag for clan in clans])
    x = []
    y = []
    text = []
    sums = {"total_donated": sum([x["total_donated"] for x in results]),
            "total_received": sum([x["total_received"] for x in results])}
    names_plotted = defaultdict(int)
    nums_zero = 0
    for result in results:
        if result["_id"] in clan_tags:
            perc = int((result[f'total_{type}'] / sums[f"total_{type}"]) * 100)
            if perc == 0:
                nums_zero += 1
                if nums_zero > 5 or len(clan_tags) >= 15:
                    continue
            x.append(result[f'total_{type}'])
            name = f"{coc.utils.get(clans, tag=result['_id']).name}"
            if names_plotted[name] > 0:
                y.append(f"{name}{create_superscript(names_plotted[name] + 1)}")
            else:
                y.append(f"{name}")
            r = "{:,}".format(result[f'total_{type}'])
            text.append(f"{r} | {perc}%")
            names_plotted[name] += 1

    fig = go.Figure(go.Bar(
        x=x,
        y=y,
        text=text,
        textposition="inside",
        textfont=dict(color="white"),
        orientation='h'))
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    fig.update_layout(barmode="overlay", template="plotly_white", margin=dict(l=50, r=25, b=25, t=25, pad=4), width=750,
                      height=500)
    img = pio.to_image(fig, format="png", scale=3.0)
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")
    return file, sums["total_donated"], sums["total_received"]


async def create_capital_graph(bot: CustomClient, server_id: int, all_players: List[int], clans: List[coc.Clan], week: str, type: str):
    pipeline = [
        {"$match": {"$and": [{"clan_tag": {"$in": [clan.tag for clan in clans]}}, {"townhall": {"$in": townhalls}}]}},
        {"$group": {"_id": "$clan_tag", "total_donated": {"$sum": f"$donations.{season}.donated"},
                    "total_received": {"$sum": f"$donations.{season}.received"}}},
        {"$sort": {f"total_{type}": 1}}
    ]
    results = await bot.player_stats.aggregate(pipeline).to_list(length=None)
    clan_tags = set([clan.tag for clan in clans])
    x = []
    y = []
    text = []
    sums = {"total_donated": sum([x["total_donated"] for x in results]),
            "total_received": sum([x["total_received"] for x in results])}
    names_plotted = defaultdict(int)
    nums_zero = 0
    for result in results:
        if result["_id"] in clan_tags:
            perc = int((result[f'total_{type}'] / sums[f"total_{type}"]) * 100)
            if perc == 0:
                nums_zero += 1
                if nums_zero > 5 or len(clan_tags) >= 15:
                    continue
            x.append(result[f'total_{type}'])
            name = f"{coc.utils.get(clans, tag=result['_id']).name}"
            if names_plotted[name] > 0:
                y.append(f"{name}{create_superscript(names_plotted[name] + 1)}")
            else:
                y.append(f"{name}")
            r = "{:,}".format(result[f'total_{type}'])
            text.append(f"{r} | {perc}%")
            names_plotted[name] += 1

    fig = go.Figure(go.Bar(
        x=x,
        y=y,
        text=text,
        textposition="inside",
        textfont=dict(color="white"),
        orientation='h'))
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    fig.update_layout(barmode="overlay", template="plotly_white", margin=dict(l=50, r=25, b=25, t=25, pad=4), width=750,
                      height=500)
    img = pio.to_image(fig, format="png", scale=3.0)
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")
    return file, sums["total_donated"], sums["total_received"]



    clan_tags = set([clan.tag for clan in clans])
    dono_dict = defaultdict(int)
    rec_dict = defaultdict(int)
    clan_tag_to_name = {}
    for member in all_players:
        if member.clan is not None and member.clan_capital_stats(week=week).raid_clan in clan_tags:
            dono_dict[member.clan.tag] += sum(member.clan_capital_stats(week=week).donated)
            rec_dict[member.clan.tag] += sum(member.clan_capital_stats(week=week).raided)
            clan_tag_to_name[member.clan.tag] = member.clan.name

    list_ = []
    num = defaultdict(int)
    for tag, name in clan_tag_to_name.items():
        if dono_dict.get(tag, 0) == 0 and rec_dict.get(tag, 0) == 0:
            continue
        num[name] += 1
        if num[name] >= 2:
            list_.append([f"{name}{create_superscript(num[name])}", dono_dict.get(tag, 0), rec_dict.get(tag, 0)])
        else:
            list_.append([f"{name}", dono_dict.get(tag, 0), rec_dict.get(tag, 0)])

    df = pd.DataFrame(list_, columns=["Clan", "Donations", "Raided"])

    if type == "donations":
        df.sort_values(ascending=False, by="Donations", inplace=True)
    elif type == "raided":
        df.sort_values(ascending=False, by="Raided", inplace=True)

    metadata = {"describe": {"byline": "Created by ClashKing"}}

    return (await self.create_and_publish_chart(server_id=server_id, title="Capital Contributions",
                                                chart_type="d3-bars-split", data=df, metadata=metadata,
                                                gtype=f"familycapital_{type}", season=week))



async def daily_graph(bot: CustomClient, clans: List[coc.Clan], attribute: str, months: int, html: bool = False) -> (disnake.File, str):

    member_map = {m.tag : f"{clan.name} ({clan.tag})" for clan in clans for m in clan.members}

    def bucket_timestamps(timestamps: List[int], granularity):
        buckets = {}

        for timestamp in timestamps:
            dt_object = pend.from_timestamp(timestamp, tz=pend.UTC)
            if granularity == 'day':
                key = dt_object.strftime('%Y-%m-%d')
            elif granularity == 'hour':
                key = dt_object.strftime('%Y-%m-%d %H:00:00')
            else:
                continue
            if key not in buckets:
                buckets[key] = 0
            buckets[key] += 1
        return buckets


    data = {}
    if attribute == "activity":
        season = bot.gen_season_date(seasons_ago=24, as_text=False)[months - 1]
        data = await bot.player_stats.find({"tag" : {"$in" : list(member_map.keys())}}, projection={"tag" : 1, f"last_online_times.{season}" : 1}).to_list(length=None)
        reformated_data = [{"tag" : d.get("tag"), "times" : d.get(f"last_online_times", {}).get(season, [])} for d in data]
        holder = defaultdict(list)
        for data in reformated_data:
            holder[member_map.get(data.get("tag"))] += data.get("times")
        data = {}
        #data now looks like {clan : List[unix_timestamps]}
        for clan_name, times in holder.items():
            data[clan_name] = bucket_timestamps(timestamps=times, granularity="day")
    else:
        do_count = True
        if attribute == "troopupgrades":
            attribute = list(coc.enums.HOME_TROOP_ORDER + coc.enums.SPELL_ORDER + coc.enums.BUILDER_TROOPS_ORDER)
        elif attribute == "heroupgrades":
            attribute = list(coc.enums.HERO_ORDER + coc.enums.PETS_ORDER)
        elif attribute == "heroequipment":
            attribute = list(coc.enums.HERO_EQUIPMENT)
        else:
            if attribute in ["clanCapitalContributions", "bestTrophies"]:
                do_count = False
            attribute = [attribute]
        START_TIME = int(pend.now(tz=pend.UTC).subtract(months=months).timestamp())
        END_TIME = int(pend.now(tz=pend.UTC).timestamp())
        pipeline = [{"$match" : {"$and" : [{"tag" : {"$in" : list(member_map.keys())}}, {"type" : {"$in" : attribute}}, {"time" : {"$gte" : START_TIME}}, {"time" : {"$lte" : END_TIME}}]}},
                    {"$group" : {"_id" : "$tag", "items" : {"$push" : "$$ROOT"}}}]
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
    for clan, datetime_count_dict in data.items():
        for datetime, count in sorted(datetime_count_dict.items()):
            data_list.append({'Clan': clan, 'Date': datetime, 'Count': count})

    df = pd.DataFrame(data_list)
    # Create Plotly figure
    fig = px.line(df, x='Date', y='Count', color='Clan')
    fig.update_layout(
        xaxis=dict(title=None),  # Remove x-axis label
        yaxis=dict(title=None),
        width=1000,  # Set the width of the plot
        height=500,  # Set the height of the plot
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        showlegend=(len(clans) >= 2),  # You can set this to False if you want to hide the legend initially
    )
    img = pio.to_image(fig, format="png", scale=1.0)
    web_version = None
    if html:
        html_content = pio.to_html(fig)
        buffer = io.BytesIO()
        buffer.write(bytes(html_content, 'utf-8'))
        web_version = await upload_html_to_cdn(bytes_=buffer.getvalue(), id=str(uuid.uuid4()).replace('-', '')[:8])
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")
    return file, web_version




async def activity_graph(bot: CustomClient, players: List[int], season: str, title: str, granularity: str, time_zone: str, tier: str, no_html:bool = False) -> (disnake.File, disnake.ActionRow):
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

