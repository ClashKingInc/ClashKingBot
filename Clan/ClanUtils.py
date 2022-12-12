from CustomClasses.CustomPlayer import LegendRanking
from CustomClasses.CustomBot import CustomClient
from utils.discord_utils import fetch_emoji
import disnake
import coc
import pytz
import asyncio
import aiohttp
import calendar
import emoji
import statistics
import matplotlib.pyplot as plt
import datetime as dt
import numpy as np

from scipy.interpolate import make_interp_spline
from disnake.ext import commands
from Assets.emojiDictionary import emojiDictionary
from collections import defaultdict
from coc import utils
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


class ClanUtils(commands.Cog, name="Clan"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    def leagueAndTrophies(self, league):

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

    async def stroop_list(self, clan: coc.Clan):
        boosted = ""
        none_boosted = ""
        async for player in clan.get_detailed_members():
            troops = player.troop_cls
            troops = player.troops
            text = f"{player.name}"
            if player.town_hall < 11:
                continue
            num = 0
            for troop in troops:
                if troop.is_active:
                    try:
                        if troop.name in SUPER_TROOPS:
                            text = f"{emojiDictionary(troop.name)} " + text
                            num += 1
                    except:
                        pass
            if num == 1:
                text = "<:blanke:838574915095101470> " + text
            if text == player.name:
                none_boosted += f"{player.name}\n"
            else:
                boosted += f"{text}\n"
        if boosted == "":
            boosted = "None"
        embed = disnake.Embed(title=f"**{clan.name} Boosting Statuses**", description=f"\n**Boosting:**\n{boosted}",
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        if none_boosted == "":
            none_boosted = "None"
        #embed.add_field(name="Boosting", value=boosted)
        embed.add_field(name="Not Boosting:", value=none_boosted)
        return embed

    async def cwl_performance(self, clan: coc.Clan):

        async def fetch(url, session):
            async with session.get(url) as response:
                return await response.json()

        dates = await self.bot.coc_client.get_seasons(29000022)
        dates.append(self.bot.gen_season_date())
        dates = reversed(dates)

        tasks = []
        async with aiohttp.ClientSession() as session:
            tag = clan.tag.replace("#", "")
            for date in dates:
                url = f"https://api.clashofstats.com/clans/{tag}/cwl/seasons/{date}"
                task = asyncio.ensure_future(fetch(url, session))
                tasks.append(task)

            responses = await asyncio.gather(*tasks)
            await session.close()

        embed = disnake.Embed(title=f"**{clan.name} CWL History**",
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)

        old_year = "2015"
        year_text = ""
        not_empty = False
        for response in responses:
            try:
                text, year = self.response_to_line(response, clan)
            except:
                continue
            if year != old_year:
                if year_text != "":
                    not_empty = True
                    embed.add_field(
                        name=old_year, value=year_text, inline=False)
                    year_text = ""
                old_year = year
            year_text += text

        if year_text != "":
            not_empty = True
            embed.add_field(name=f"**{old_year}**",
                            value=year_text, inline=False)

        if not not_empty:
            embed.description = "No prior cwl data"
        return embed

    async def create_last_online(self, clan: coc.Clan):
        member_tags = [member.tag for member in clan.members]
        members = await self.bot.get_players(tags=member_tags, custom=True)
        text = []
        avg_time = []
        for member in members:
            last_online = member.last_online
            last_online_sort = last_online
            if last_online is None:
                last_online_sort = 0
                text.append([f"Not Seen `{member.name}`", last_online_sort])
            else:
                avg_time.append(last_online)
                text.append(
                    [f"<t:{last_online}:R> `{member.name}`", last_online_sort])

        text = sorted(text, key=lambda l: l[1], reverse=True)
        text = [line[0] for line in text]
        text = "\n".join(text)
        if avg_time != []:
            avg_time.sort()
            avg_time = statistics.median(avg_time)
            avg_time = f"\n\n**Median L.O.** <t:{int(avg_time)}:R>"
        else:
            avg_time = ""
        embed = disnake.Embed(title=f"**{clan.name} Last Online**",
                              description=text + avg_time,
                              color=disnake.Color.green())
        return embed

    async def create_activities(self, clan: coc.Clan):
        member_tags = [member.tag for member in clan.members]
        members = await self.bot.get_players(tags=member_tags, custom=True)
        text = []
        for member in members:
            member: MyCustomPlayer
            last_online = member.season_last_online()
            text.append(
                [f"{str(len(last_online)).ljust(4)} | {member.name}", len(last_online)])

        text = sorted(text, key=lambda l: l[1], reverse=True)
        text = [line[0] for line in text]
        text = "\n".join(text)

        embed = disnake.Embed(title=f"**{clan.name} Activity Count**",
                              description=f"```#     NAME\n{text}```",
                              color=disnake.Color.green())
        return embed

    async def create_clan_games(self, clan: coc.Clan, date=None):
        if date is None:
            date = self.bot.gen_season_date()
        member_tags = [member.tag for member in clan.members]

        tags = await self.bot.player_stats.distinct("tag", filter={f"clan_games.{date}.clan": clan.tag})
        all_tags = list(set(member_tags + tags))

        tasks = []
        for tag in all_tags:
            results = await self.bot.player_stats.find_one({"tag": tag})
            task = asyncio.ensure_future(
                self.bot.coc_client.get_player(player_tag=tag, cls=MyCustomPlayer, bot=self.bot, results=results))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        point_text = []
        total_points = sum(player.clan_games(date) for player in responses)
        for player in responses:
            player: MyCustomPlayer
            name = player.name
            for char in ["`", "*", "_", "~", "´"]:
                name = name.replace(char, "", len(player.name))
            points = player.clan_games(date)

            if player.tag in member_tags:
                point_text.append(
                    [f"{self.bot.emoji.clan_games}`{str(points).ljust(4)}`: {name}", points])
            else:
                point_text.append(
                    [f"{self.bot.emoji.deny_mark}`{str(points).ljust(4)}`: {name}", points])

        point_text = sorted(point_text, key=lambda l: l[1], reverse=True)
        point_text = [line[0] for line in point_text]
        point_text = "\n".join(point_text)
        cg_point_embed = disnake.Embed(title=f"**{clan.name} Clan Game Totals**", description=point_text,
                                       color=disnake.Color.green())
        cg_point_embed.set_footer(
            text=f"Total Points: {'{:,}'.format(total_points)}")
        return cg_point_embed

    async def create_donations(self, clan: coc.Clan, type: str, date=None):
        if date is None:
            date = self.bot.gen_season_date()
        tasks = []
        for member in clan.members:
            results = await self.bot.player_stats.find_one({"tag": member.tag})
            task = asyncio.ensure_future(
                self.bot.coc_client.get_player(player_tag=member.tag, cls=MyCustomPlayer, bot=self.bot, results=results))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        donated_text = []
        received_text = []
        ratio_text = []
        total_donated = sum(player.donos(date).donated for player in responses)
        total_received = sum(player.donos(
            date).received for player in responses)

        for player in responses:
            player: MyCustomPlayer
            name = player.name
            for char in ["`", "*", "_", "~", "´"]:
                name = name.replace(char, "", len(player.name))
            name = emoji.replace_emoji(name, "")
            name = name[:13]
            donated_text.append(
                [f"{str(player.donos(date).donated).ljust(5)} | {str(player.donos(date).received).ljust(5)} | {name}", player.donos(date).donated])
            received_text.append(
                [f"{str(player.donos(date).received).ljust(5)} | {str(player.donos(date).donated).ljust(5)} | {name}", player.donos(date).received])
            ratio_text.append(
                [f"{str(player.donation_ratio(date)).ljust(5)} | {name}", player.donation_ratio(date)])

        if type == "donated":
            donated_text = sorted(
                donated_text, key=lambda l: l[1], reverse=True)
            donated_text = [line[0] for line in donated_text]
            donated_text = "\n".join(donated_text)
            donated_text = "DON   | REC   | Name\n" + donated_text
            donation_embed = disnake.Embed(title=f"**{clan.name} Donations**", description=f"```{donated_text}```",
                                           color=disnake.Color.green())
            donation_embed.set_footer(
                icon_url=clan.badge.url, text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return donation_embed
        elif type == "received":
            received_text = sorted(
                received_text, key=lambda l: l[1], reverse=True)
            received_text = [line[0] for line in received_text]
            received_text = "\n".join(received_text)
            received_text = "REC   | DON   | Name\n" + received_text
            received_embed = disnake.Embed(title=f"**{clan.name} Received**", description=f"```{received_text}```",
                                           color=disnake.Color.green())
            received_embed.set_footer(icon_url=clan.badge.url,
                                      text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return received_embed
        else:
            ratio_text = sorted(ratio_text, key=lambda l: l[1], reverse=True)
            ratio_text = [line[0] for line in ratio_text]
            ratio_text = "\n".join(ratio_text)
            ratio_text = "Ratio | Name\n" + ratio_text
            ratio_embed = disnake.Embed(title=f"**{clan.name} Ratios**", description=f"```{ratio_text}```",
                                        color=disnake.Color.green())
            ratio_embed.set_footer(icon_url=clan.badge.url,
                                   text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return ratio_embed

    def response_to_line(self, response, clan):
        import json
        te = json.dumps(response)
        if "Not Found" in te:
            return ""

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
        stars = dict(
            sorted(stars.items(), key=lambda item: item[1], reverse=True))
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

        return [f"{emoji} {self.leagueAndTrophies(league_name)}{SUPER_SCRIPTS[tier]} `{place}{end}` | {date}\n", year]

    async def create_graph(self, clans: list, timezone):
        fig, ax = plt.subplots(figsize=(15, 10))
        biggest = 0
        for clan in clans:
            player_tags = [member.tag for member in clan.members]
            players = await self.bot.get_players(tags=player_tags, custom=True)
            times_by_day = {}
            for player in players:  # type: MyCustomPlayer
                times = player.season_last_online()
                previous_time = None
                for time in times:
                    time = dt.datetime.fromtimestamp(time, tz=timezone)
                    if f"{time.hour}-{time.day}" != previous_time:
                        previous_time = f"{time.hour}-{time.day}"
                        if f"{time.day}-{time.month}" not in list(times_by_day.keys()):
                            times_by_day[f"{time.day}-{time.month}"] = defaultdict(
                                int)
                        times_by_day[f"{time.day}-{time.month}"][time.hour] += 1

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
