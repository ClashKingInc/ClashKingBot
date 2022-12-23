from utils.discord_utils import fetch_emoji
import disnake
import coc
import pytz
import calendar
import emoji
import json
import matplotlib.pyplot as plt
import datetime as dt
import numpy as np
import dateutil.relativedelta
from CustomClasses.emoji_class import Emojis
import pandas as pd

from scipy.interpolate import make_interp_spline
from collections import defaultdict
from CustomClasses.CustomPlayer import MyCustomPlayer

SUPER_TROOPS = [
    "Super Barbarian",
    "Super Archer",
    "Super Giant",
    "Sneaky Goblin",
    "Super Wall Breaker",
    "Rocket Balloon",
    "Super Wizard",
    "Inferno Dragon",
    "Super Minion",
    "Super Valkyrie",
    "Super Witch",
    "Ice Hound",
    "Super Bowler",
    "Super Dragon"
]
SUPER_SCRIPTS = [
    "⁰",
    "¹",
    "²",
    "³",
    "⁴",
    "⁵",
    "⁶",
    "⁷",
    "⁸",
    "⁹"
]
tiz = pytz.utc


def clan_th_comp(clan_members):
    thcount = defaultdict(int)

    for player in clan_members:
        thcount[player.town_hall] += 1

    th_comp_string = ""
    for th_level, th_count in sorted(thcount.items(), reverse=True):
        th_emoji = fetch_emoji(th_level)
        th_comp_string += f"{th_emoji}`{th_count}` "

    return th_comp_string


def clan_super_troop_comp(clan_members):

    # initializing the super troop dict to count active super troops
    super_troop_comp_dict = {}
    for super_troop in SUPER_TROOPS:
        super_troop_comp_dict[super_troop] = 0

    for player in clan_members:
        for troop in player.troops:
            if troop.is_active:
                try:
                    super_troop_comp_dict[troop.name] += 1
                except:
                    pass

    return_string = ""

    for troop in SUPER_TROOPS:
        nu = super_troop_comp_dict[troop]
        super_troop_emoji = fetch_emoji(emoji_name=troop)
        if nu != 0:
            return_string += f"{super_troop_emoji}`x{nu} `"

    if return_string == "":
        return_string = "None"

    return return_string


def league_and_trophies_emoji(league):

    if (league == "Bronze League III"):
        emoji = "<:BronzeLeagueIII:601611929311510528>"
    elif (league == "Bronze League II"):
        emoji = "<:BronzeLeagueII:601611942850986014>"
    elif (league == "Bronze League I"):
        emoji = "<:BronzeLeagueI:601611950228635648>"
    elif (league == "Silver League III"):
        emoji = "<:SilverLeagueIII:601611958067920906>"
    elif (league == "Silver League II"):
        emoji = "<:SilverLeagueII:601611965550428160>"
    elif (league == "Silver League I"):
        emoji = "<:SilverLeagueI:601611974849331222>"
    elif (league == "Gold League III"):
        emoji = "<:GoldLeagueIII:601611988992262144>"
    elif (league == "Gold League II"):
        emoji = "<:GoldLeagueII:601611996290613249>"
    elif (league == "Gold League I"):
        emoji = "<:GoldLeagueI:601612010492526592>"
    elif (league == "Crystal League III"):
        emoji = "<:CrystalLeagueIII:601612021472952330>"
    elif (league == "Crystal League II"):
        emoji = "<:CrystalLeagueII:601612033976434698>"
    elif (league == "Crystal League I"):
        emoji = "<:CrystalLeagueI:601612045359775746>"
    elif (league == "Master League III"):
        emoji = "<:MasterLeagueIII:601612064913621002>"
    elif (league == "Master League II"):
        emoji = "<:MasterLeagueII:601612075474616399>"
    elif (league == "Master League I"):
        emoji = "<:MasterLeagueI:601612085327036436>"
    elif (league == "Champion League III"):
        emoji = "<:ChampionLeagueIII:601612099226959892>"
    elif (league == "Champion League II"):
        emoji = "<:ChampionLeagueII:601612113345249290>"
    elif (league == "Champion League I"):
        emoji = "<:ChampionLeagueI:601612124447440912>"
    elif (league == "Titan League III"):
        emoji = "<:TitanLeagueIII:601612137491726374>"
    elif (league == "Titan League II"):
        emoji = "<:TitanLeagueII:601612148325744640>"
    elif (league == "Titan League I"):
        emoji = "<:TitanLeagueI:601612159327141888>"
    elif (league == "Legend League"):
        emoji = "<:LegendLeague:601612163169255436>"
    else:
        emoji = "<:Unranked:601618883853680653>"

    return emoji


def get_raid(raid_log, after, before):
    for raid in raid_log:
        time_start = int(raid.start_time.time.timestamp())
        if before > time_start > after:
            return raid
    return None


def gen_season_date(seasons_ago=None):
    if seasons_ago is None:
        end = coc.utils.get_season_end().replace(tzinfo=pytz.utc).date()
        return f"{end.year}-{end.month}"
    else:
        dates = []
        for x in range(0, seasons_ago + 1):
            end = coc.utils.get_season_end().replace(tzinfo=pytz.utc) - \
                dateutil.relativedelta.relativedelta(months=x)
            dates.append(
                f"{calendar.month_name[end.date().month]} {end.date().year}")
        return dates


async def create_graph(clans: list, timezone, bot):

    fig, ax = plt.subplots(figsize=(15, 10))
    biggest = 0

    for clan in clans:
        times_by_day = {}

        last_online_stats = await bot.player_stats.find({f"tag": {"$in": [member.tag for member in clan.members]}}).to_list(length=100)

        for player in last_online_stats:
            times = player.get("last_online_times")
            if times is None:
                times = []
            season_date = bot.gen_season_date()
            times = times.get(season_date)
            if times is None:
                times = []
            previous_time = None

            for time in times:
                time = dt.datetime.fromtimestamp(time, tz=timezone)

                if f"{time.hour}-{time.day}" != previous_time:
                    previous_time = f"{time.hour}-{time.day}"

                    if (f"{time.day}-{time.month}" not in
                            list(times_by_day.keys())):
                        times_by_day[
                            f"{time.day}-{time.month}"] = defaultdict(int)

                    times_by_day[
                        f"{time.day}-{time.month}"][time.hour] += 1

        hour_totals = defaultdict(int)
        hour_days = defaultdict(int)

        for day, day_details in times_by_day.items():
            for hour, members_online in sorted(day_details.items(), reverse=False):
                hour_days[hour] += 1
                hour_totals[hour] += members_online

        for x in range(24):
            if x not in list(hour_totals.keys()):
                hour_totals[x] = 0

        dates = []
        activity_list = []
        for hour, members_online in sorted(hour_totals.items(), reverse=False):
            dates.append(hour)

            if hour_days[hour] == 0:
                activity_list.append(0)
                continue

            if int(round((members_online / hour_days[hour]))) > biggest:
                biggest = int(round((members_online / hour_days[hour])))

            activity_list.append(
                int(round((members_online / hour_days[hour]))))

        dates = np.array(dates)
        activity_list = np.array(activity_list)
        X_Y_Spline = make_interp_spline(dates, activity_list)
        X_ = np.linspace(dates.min(initial=0), dates.max(initial=0), 500)
        Y_ = X_Y_Spline(X_)

        ax.plot(X_, Y_, label=clan.name, linewidth=5)

        ax.yaxis.grid(color='gray', linestyle='dashed')
        ax.xaxis.grid(color='gray', linestyle='dashed')

    x_ticks = [f"{x}:00" for x in range(24)]

    # plt.style.use('seaborn-darkgrid')
    plt.title(f"Average People on Per an Hour | Timezone: {timezone}",
              loc='center', fontsize=20, fontweight=0, color='black')
    plt.xlabel("Time")
    plt.legend(loc="upper left")
    plt.yticks(range(0, biggest + 5, 2))
    plt.xticks(ticks=range(24), labels=x_ticks)
    plt.ylabel("Avg People On Per Hour")

    import io

    temp = io.BytesIO()

    plt.tight_layout()
    plt.savefig(temp, format="png")
    temp.seek(0)

    file = disnake.File(fp=temp, filename="filename.png")

    return file


def stat_components():
    options = []
    for townhall in reversed(range(6, 16)):
        options.append(disnake.SelectOption(
            label=f"Townhall {townhall}",
            emoji=fetch_emoji(townhall),
            value=str(townhall)))

    th_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder="Select Townhalls",
        min_values=1,  # the minimum number of options a user must select
        # the maximum number of options a user can select
        max_values=len(options),
    )

    options = []
    real_types = [
        "Fresh Hits",
        "Non-Fresh",
        "random", "cwl",
        "friendly"]

    for count, filter in enumerate([
        "Fresh Hits",
        "Non-Fresh",
        "Random Wars",
        "CWL",
            "Friendly Wars"]):
        options.append(disnake.SelectOption(
            label=f"{filter}",
            value=real_types[count]))

    filter_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder="Select Filters",
        min_values=1,  # the minimum number of options a user must select
        # the maximum number of options a user can select
        max_values=len(options),
    )

    options = []
    emojis = [
        Emojis().sword_clash.partial_emoji,
        Emojis().shield.partial_emoji,
        Emojis().war_star.partial_emoji]

    for count, type in enumerate([
        "Offensive Hitrate",
        "Defensive Rate",
            "Stars Leaderboard"]):
        options.append(disnake.SelectOption(
            label=f"{type}",
            emoji=emojis[count],
            value=type))

    stat_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder="Select Stat Type",
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )

    dropdown = [
        disnake.ui.ActionRow(th_select),
        disnake.ui.ActionRow(filter_select),
        disnake.ui.ActionRow(stat_select)]

    return dropdown


async def fetch_n_rank_hit_rate(
        player: MyCustomPlayer,
        townhall_level: list = [],
        fresh_type: list = [False, True],
        start_timestamp: int = 0,
        end_timestamp: int = 9999999999,
        war_types: list = ["random", "cwl", "friendly"],
        war_statuses=["lost", "losing", "winning", "won"]):

    if not townhall_level:
        townhall_level = list(range(1, 17))

    hitrate = await player.hit_rate(
        townhall_level=townhall_level,
        fresh_type=fresh_type,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        war_types=war_types, war_statuses=war_statuses)

    hr = hitrate[0]

    if hr.num_attacks == 0:
        return None

    hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
    name = emoji.replace_emoji(player.name, "")
    name = str(name)[0:12]
    name = f"{name}".ljust(12)
    destr = f"{round(hr.average_triples * 100, 1)}%".rjust(6)

    return [
        f"{player.town_hall_cls.emoji} `{hr_nums} {destr} {name}`\n",
        round(hr.average_triples * 100, 3),
        name, hr.num_attacks,
        player.town_hall]


async def fetch_n_rank_defensive_rate(
        player: MyCustomPlayer,
        townhall_level: list = [],
        fresh_type: list = [False, True],
        start_timestamp: int = 0,
        end_timestamp: int = 9999999999,
        war_types: list = ["random", "cwl", "friendly"],
        war_statuses=["lost", "losing", "winning", "won"]):

    hitrate = await player.defense_rate(
        townhall_level=townhall_level,
        fresh_type=fresh_type,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        war_types=war_types, war_statuses=war_statuses)

    hr = hitrate[0]

    if hr.num_attacks == 0:
        return None

    hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
    name = emoji.replace_emoji(player.name, "")
    name = str(name)[0:12]
    name = f"{name}".ljust(12)
    destr = f"{round(hr.average_triples * 100, 1)}%".rjust(6)

    return [
        f"{player.town_hall_cls.emoji} `{hr_nums} {destr} {name}`\n",
        round(hr.average_triples * 100, 3),
        name, hr.num_attacks,
        player.town_hall]


async def fetch_n_rank_star_leaderboard(
        player: MyCustomPlayer,
        townhall_level: list = [],
        fresh_type: list = [False, True],
        start_timestamp: int = 0,
        end_timestamp: int = 9999999999,
        war_types: list = ["random", "cwl", "friendly"],
        war_statuses=["lost", "losing", "winning", "won"]):

    if not townhall_level:
        townhall_level = list(range(1, 17))

    hitrate = await player.hit_rate(
        townhall_level=townhall_level,
        fresh_type=fresh_type,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        war_types=war_types,
        war_statuses=war_statuses)

    hr = hitrate[0]
    if hr.num_attacks == 0:
        return None

    name = str(player.name)[0:12]
    name = f"{name}".ljust(12)
    stars = f"{hr.total_stars}/{hr.num_attacks}".center(5)
    destruction = f"{int(hr.total_destruction)}%".ljust(5)

    return [
        f"{stars} {destruction} {name}\n",
        round(hr.average_triples * 100, 3),
        name, hr.total_stars,
        player.town_hall]


def response_to_line(response, clan):
    te = json.dumps(response)
    clans = response["clans"]
    season = response["season"]
    tags = [x["tag"] for x in clans]
    stars = {}
    for tag in tags:
        stars[tag] = 0
    rounds = response["rounds"]
    for round in rounds:
        wars = round["wars"]
        for war in wars:
            main_stars = war["clan"]["stars"]
            main_destruction = war["clan"]["destructionPercentage"]
            stars[war["clan"]["tag"]] += main_stars

            opp_stars = war["opponent"]["stars"]
            opp_destruction = war["opponent"]["destructionPercentage"]
            stars[war["opponent"]["tag"]] += opp_stars

            if main_stars > opp_stars:
                stars[war["clan"]["tag"]] += 10
            elif opp_stars > main_stars:
                stars[war["opponent"]["tag"]] += 10
            elif main_destruction > opp_destruction:
                stars[war["clan"]["tag"]] += 10
            elif opp_destruction > main_destruction:
                stars[war["opponent"]["tag"]] += 10
    stars = dict(sorted(stars.items(), key=lambda item: item[1], reverse=True))
    place = list(stars.keys()).index(clan.tag) + 1
    league = response["leagueId"]
    war_leagues = open(f"Assets/war_leagues.json")
    war_leagues = json.load(war_leagues)
    league_name = [x["name"]
                   for x in war_leagues["items"] if x["id"] == league][0]
    promo = [x["promo"]
             for x in war_leagues["items"] if x["id"] == league][0]
    demo = [x["demote"]
            for x in war_leagues["items"] if x["id"] == league][0]

    if place <= promo:
        emoji = "<:warwon:932212939899949176>"
    elif place >= demo:
        emoji = "<:warlost:932212154164183081>"
    else:
        emoji = "<:dash:933150462818021437>"

    end = "th"
    ends = {1: "st", 2: "nd", 3: "rd"}
    if place <= 3:
        end = ends[place]

    year = season[0:4]
    month = season[5:]
    month = calendar.month_name[int(month)]
    #month = month.ljust(9)
    date = f"`{month}`"
    league = str(league_name).replace('League ', '')
    league = league.ljust(14)
    league = f"{league}"

    tier = str(league_name).count("I")

    return (f"{emoji} {league_and_trophies_emoji(league_name)}{SUPER_SCRIPTS[tier]} `{place}{end}` | {date}\n", year)


def create_excel(columns, index, data, weekend):
    df = pd.DataFrame(data, index=index, columns=columns)
    df.to_excel('ClanCapitalStats.xlsx', sheet_name=f'{weekend}')
    return disnake.File("ClanCapitalStats.xlsx", filename=f"{weekend}_clancapital.xlsx")

