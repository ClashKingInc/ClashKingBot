import datetime
import disnake
import coc
import pytz
import emoji
import asyncio
import statistics
import re

from coc.raid import RaidLogEntry
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer, ClanCapitalWeek
from utils.General import create_superscript
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry, calc_raid_medals
from utils.constants import item_to_name
from CustomClasses.Enums import TrophySort
from collections import defaultdict

tiz = pytz.utc
leagues = [ "Titan League I" , "Titan League II" , "Titan League III" ,"Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]

class getFamily(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def create_donations(self, guild: disnake.Guild, type: str):
        date = self.bot.gen_season_date()
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        tasks = []
        members = []
        clans = await self.bot.get_clans(tags=clan_tags)
        for clan in clans:
            members += [member.tag for member in clan.members]

        responses = await self.bot.get_players(tags=members, custom=True)

        donated_text = []
        received_text = []
        ratio_text = []
        total_donated = sum(player.donos().donated for player in responses if not isinstance(player, coc.errors.NotFound))
        total_received = sum(player.donos().received for player in responses if not isinstance(player, coc.errors.NotFound))

        for player in responses:
            if isinstance(player, coc.errors.NotFound):
                continue
            player: MyCustomPlayer
            if player is None:
                continue
            if player.clan is None:
                continue
            for char in ["`", "*", "_", "~"]:
                name = player.name.replace(char, "", 10)
            name = emoji.replace_emoji(name, "")
            name = name[:13]
            name = name.ljust(13)
            donated_text.append(
                [f"`{str(player.donos().donated).ljust(5)} | {str(player.donos().received).ljust(5)} | \u200e{name}`",
                 player.donos().donated])
            received_text.append(
                [f"`{str(player.donos().received).ljust(5)} | {str(player.donos().donated).ljust(5)} | \u200e{name}`",
                 player.donos().received])
            ratio_text.append([f"`{str(player.donation_ratio()).ljust(5)} | \u200e{name}`", player.donation_ratio()])

        if type == "donated":
            donated_text = sorted(donated_text, key=lambda l: l[1], reverse=True)
            donated_text = [f"{self.bot.get_number_emoji(color='gold', number=count)} {line[0]}" for count, line in enumerate(donated_text[:50], 1)]
            donated_text = "\n".join(donated_text)
            donated_text = "<:un:1036115340360429628>` DON   | REC   | Name` \n" + donated_text
            donation_embed = disnake.Embed(title=f"**{guild.name} Top 50 Donated**", description=f"{donated_text}",
                                           color=disnake.Color.green())
            if guild.icon is not None:
                icon = guild.icon.url
            else:
                icon = self.bot.user.avatar.url
            donation_embed.set_footer(icon_url=icon,
                                      text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return donation_embed
        elif type == "received":
            received_text = sorted(received_text, key=lambda l: l[1], reverse=True)
            received_text = [f"{self.bot.get_number_emoji(color='gold', number=count)} {line[0]}" for count, line in enumerate(received_text[:50], 1)]
            received_text = "\n".join(received_text)
            received_text = "<:un:1036115340360429628>` REC   | DON   | Name`\n" + received_text
            received_embed = disnake.Embed(title=f"**{guild.name} Top 50 Received**", description=f"{received_text}",
                                           color=disnake.Color.green())
            if guild.icon is not None:
                icon = guild.icon.url
            else:
                icon = self.bot.user.avatar.url
            received_embed.set_footer(icon_url=icon,
                                      text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return received_embed
        else:
            ratio_text = sorted(ratio_text, key=lambda l: l[1], reverse=True)
            ratio_text = [f"{self.bot.get_number_emoji(color='gold', number=count)} {line[0]}" for count, line in enumerate(ratio_text[:50], 1)]
            ratio_text = "\n".join(ratio_text)
            ratio_text = "<:un:1036115340360429628>` Ratio | Name`\n" + ratio_text
            ratio_embed = disnake.Embed(title=f"**{guild.name} Top 50 Ratios**", description=f"{ratio_text}",
                                        color=disnake.Color.green())
            if guild.icon is not None:
                icon = guild.icon.url
            else:
                icon = self.bot.user.avatar.url
            ratio_embed.set_footer(icon_url=icon,
                                   text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {date}")
            return ratio_embed

    async def create_last_online(self, guild: disnake.Guild):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        member_tags = [r["tag"] for r in (await self.bot.player_stats.find({"clan_tag": {"$in": clan_tags}}).sort("last_online", -1).to_list(length=50))]

        players = await self.bot.get_players(tags=member_tags, custom=True)
        text = []
        avg_time = []
        for member in players:
            last_online = member.last_online
            last_online_sort = last_online
            if last_online is None:
                last_online_sort = 0
                text.append([f"Not Seen `{member.name}`", last_online_sort])
            else:
                avg_time.append(last_online)
                text.append([f"<t:{last_online}:R> `{member.name}`", last_online_sort])

        text = sorted(text, key=lambda l: l[1], reverse=True)
        text = text[0:50]
        text = [line[0] for line in text]
        text = "\n".join(text)
        if avg_time != []:
            avg_time.sort()
            avg_time = statistics.median(avg_time)
            avg_time = f"\n\n**Median L.O.** <t:{int(avg_time)}:R>"
        else:
            avg_time = ""
        embed = disnake.Embed(title=f"**{guild.name} Last 50 Online**",
                              description=text + avg_time,
                              color=disnake.Color.green())
        return embed

    async def create_activities(self, guild: disnake.Guild):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans = await self.bot.get_clans(tags=clan_tags)
        member_tags = []
        for clan in clans:
            member_tags.extend(member.tag for member in clan.members)
        clan_members = await self.bot.get_players(tags=member_tags, custom=True)

        embed_description_list = []
        for member in clan_members:
            member: MyCustomPlayer
            last_online = member.season_last_online()
            embed_description_list.append([f"{str(len(last_online)).ljust(4)} | {member.name}", len(last_online)])

        embed_description_list_sorted = sorted(embed_description_list, key=lambda l: l[1], reverse=True)
        embed_description = [line[0] for line in embed_description_list_sorted[:50]]
        embed_description = "\n".join(embed_description)

        embed = disnake.Embed(
            title=f"**{guild.name} Activity Leaderboard**",
            description=f"```#     NAME\n{embed_description}```",
            color=disnake.Color.green())
        return embed

    async def create_capital_leagues(self, guild: disnake.Guild):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        if not clan_tags:
            embed = disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())
            return embed

        clans = await self.bot.get_clans(tags=clan_tags)
        clan_list = []
        for clan in clans:
            if clan is None:
                continue
            clan: coc.Clan
            clan_list.append([clan.name, clan.capital_league.name])

        clans_list = sorted(clan_list, key=lambda l: l[0], reverse=False)

        main_embed = disnake.Embed(title=f"__**{guild.name} Capital Leagues**__",
                                   color=disnake.Color.green())
        if guild.icon is not None:
            main_embed.set_thumbnail(url=guild.icon.url)

        leagues_present = ["All"]
        for league in leagues:
            text = ""
            for clan in clans_list:
                if clan[1] == league:
                    text += clan[0] + "\n"
                if (clan[0] == clans_list[len(clans_list) - 1][0]) and (text != ""):
                    leagues_present.append(league)
                    main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                    text = ""

        return main_embed

    async def create_cwl_leagues(self, guild: disnake.Guild):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server" : guild.id})
        if not clan_tags:
            embed = disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())
            return embed

        clans = await self.bot.get_clans(tags=clan_tags)
        cwl_list = []
        for clan in clans:
            if clan is None:
                continue
            cwl_list.append([clan.name, clan.war_league.name])

        clans_list = sorted(cwl_list, key=lambda l: l[0], reverse=False)

        main_embed = disnake.Embed(title=f"__**{guild.name} CWL Leagues**__",
                                   color=disnake.Color.green())
        if guild.icon is not None:
            main_embed.set_thumbnail(url=guild.icon.url)

        leagues_present = ["All"]
        for league in leagues:
            text = ""
            for clan in clans_list:
                if clan[1] == league:
                    text += clan[0] + "\n"
                if (clan[0] == clans_list[len(clans_list) - 1][0]) and (text != ""):
                    leagues_present.append(league)
                    main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                    text = ""

        return main_embed

    async def create_clan_games(self, guild: disnake.Guild):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})

        season_date = self.bot.gen_games_season()
        members = await self.bot.player_stats.distinct("tag", filter={f"clan_tag": {"$in" : clan_tags}})
        tags = await self.bot.player_stats.distinct("tag", filter={f"clan_games.{season_date}.clan": {"$in" : clan_tags}})
        all_tags = (members + tags)
        all_tags = [r["tag"] for r in (await self.bot.player_stats.find({"tag" : {"$in" : all_tags}}).sort(f"clan_games.{season_date}.clan", -1).to_list(length=50))]

        members = set(members)
        player_list = await self.bot.get_players(tags=list(set(all_tags)))

        member_stats = await self.bot.new_looper[f"{self.bot.gen_season_date()}-history"].find({"tag": {"$in" : all_tags}}).to_list(length=100)
        member_stat_dict = {}
        for m in member_stats:
            member_stat_dict[m["tag"]] = m

        total_points = sum(player.clan_games(season_date) for player in player_list)
        player_list = sorted(player_list, key=lambda l: l.clan_games(season_date), reverse=True)[:50]

        point_text_list = []
        for player in player_list:
            name = player.name
            name = re.sub('[*_`~/]', '', name)
            points = player.clan_games(season_date)

            time = ""
            stats = member_stat_dict.get(player.tag)
            if stats is not None:
                stats = stats.get("Games Champion", [])
                if points < 4000:
                    stats.append({"time" : int(datetime.datetime.now().timestamp())})
                if len(stats) >= 2:
                    first_time = datetime.datetime.fromtimestamp(stats[0].get("time"))
                    last_time = datetime.datetime.fromtimestamp(stats[-1].get("time"))
                    diff = (last_time - first_time)
                    m, s = divmod(diff.total_seconds(), 60)
                    h, m = divmod(m, 60)
                    time = f"{int(h)}h {int(m)}m"

            if player.tag in members:
                point_text_list.append([f"{self.bot.emoji.clan_games}`{str(points).ljust(4)} {time:7}` {name}"])
            else:
                point_text_list.append([f"{self.bot.emoji.deny_mark}`{str(points).ljust(4)} {time:7}` {name}"])

        point_text = [line[0] for line in point_text_list]
        point_text = "\n".join(point_text)

        cg_point_embed = disnake.Embed(title=f"**{guild.name} Clan Game Totals**",description=point_text,color=disnake.Color.green())

        cg_point_embed.set_footer(text=f"Total Points: {'{:,}'.format(total_points)}")
        return cg_point_embed

    async def create_raids(self, guild: disnake.Guild):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        if not clan_tags:
            embed = disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())
            return embed

        clans = await self.bot.get_clans(tags=clan_tags)

        tasks = []
        async def get_raid_stuff(clan):
            weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
            weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot, limit=2)
            return [clan, weekend_raid_entry]

        for clan in clans:
            if clan is None:
                continue
            task = asyncio.ensure_future(get_raid_stuff(clan))
            tasks.append(task)

        raid_list = await asyncio.gather(*tasks)
        raid_list = [r for r in raid_list if r[1] is not None]

        if len(raid_list) == 0:
            embed = disnake.Embed(description="No clans currently in raid weekend", color=disnake.Color.red())
            return embed

        embed = disnake.Embed(description=f"**{guild.name} Current Raids**", color=disnake.Color.green())

        raid_list = sorted(raid_list, key=lambda l: l[0].name, reverse=False)
        for raid_item in raid_list:
            clan: coc.Clan = raid_item[0]
            raid: RaidLogEntry = raid_item[1]

            medals = calc_raid_medals(raid.attack_log)
            emoji = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            hall_level = 0 if coc.utils.get(clan.capital_districts, id=70000000) is None else coc.utils.get(clan.capital_districts, id=70000000).hall_level
            embed.add_field(name=f"{emoji}{clan.name} | CH{hall_level}",
                            value=f"> {self.bot.emoji.thick_sword} {raid.attack_count}/300 | "
                                  f"{self.bot.emoji.person} {len(raid.members)}/50\n"
                                  f"> {self.bot.emoji.capital_gold} {'{:,}'.format(raid.total_loot)} | "
                                  f"{self.bot.emoji.raid_medal} {medals}", inline=False)

        return embed

    async def create_wars(self, guild: disnake.Guild):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        if len(clan_tags) == 0:
            embed = disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())
            return embed

        war_list = await self.bot.get_clan_wars(tags=clan_tags)
        war_list = [w for w in war_list if w is not None and w.start_time is not None]
        if len(war_list) == 0:
            embed = disnake.Embed(description="No clans in war and/or have public war logs.", color=disnake.Color.red())
            return embed

        war_list = sorted(war_list, key=lambda l: (str(l.state), int(l.start_time.time.timestamp())), reverse=False)
        embed = disnake.Embed(description=f"**{guild.name} Current Wars**", color=disnake.Color.green())
        for war in war_list:
            if war.clan.name is None:
                continue
            emoji = await self.bot.create_new_badge_emoji(url=war.clan.badge.url)
            war_cog = self.bot.get_cog(name="War")
            stars_percent = await war_cog.calculate_stars_percent(war)

            war_time = war.start_time.seconds_until
            if war_time < -172800:
                continue
            war_pos = "Starting"
            if war_time >= 0:
                war_time = war.start_time.time.replace(tzinfo=tiz).timestamp()
            else:
                war_time = war.end_time.seconds_until
                if war_time <= 0:
                    war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                    war_pos = "Ended"
                else:
                    war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                    war_pos = "Ending"

            team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(
                7)
            opp_hits = f"{len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".rjust(7)
            team_stars = str(stars_percent[2]).ljust(7)
            opp_stars = str(stars_percent[0]).rjust(7)
            team_per = (str(stars_percent[3]) + "%").ljust(7)
            opp_per = (str(stars_percent[1]) + "%").rjust(7)

            embed.add_field(name=f"{emoji}{war.clan.name} vs {war.opponent.name}",
                            value=f"> `{team_hits}`<a:swords:944894455633297418>`{opp_hits}`\n"
                                  f"> `{team_stars}`<:star:825571962699907152>`{opp_stars}`\n"
                                  f"> `{team_per}`<:broken_sword:944896241429540915>`{opp_per}`\n"
                                  f"> {war_pos}: <t:{int(war_time)}:R>", inline=False)
        return embed

    async def create_trophies(self, guild: disnake.Guild, sort_type: TrophySort):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans = await self.bot.get_clans(tags=clan_tags)
        clans = [clan for clan in clans if clan is not None]
        if not clans:
            return disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())

        if sort_type is TrophySort.home:
            point_type = "Trophies"
            clans = sorted(clans, key=lambda l: l.points, reverse=True)
            clan_text = [f"{self.bot.emoji.trophy}`{clan.points:5} {clan.name}`{create_superscript(clan.member_count)}" for clan in clans]
        elif sort_type is TrophySort.versus:
            point_type = "Versus Trophies"
            clans = sorted(clans, key=lambda l: l.versus_points, reverse=True)
            clan_text = [f"{self.bot.emoji.versus_trophy}`{clan.versus_points:5} {clan.name}`" for clan in clans]
        elif sort_type is TrophySort.capital:
            point_type = "Capital Trophies"
            clans = sorted(clans, key=lambda l: l.capital_points, reverse=True)
            clan_text = [f"{self.bot.emoji.capital_trophy}`{clan.capital_points:5} {clan.name}`" for clan in clans]

        clan_text = "\n".join(clan_text)

        embed = disnake.Embed(title=f"**{guild.name} {point_type}**", description=clan_text, color=disnake.Color.green())
        if guild.icon is not None:
            embed.set_footer(text="Last Refreshed", icon_url=guild.icon.url)
        embed.timestamp = datetime.datetime.now()
        return embed

    async def create_summary(self, guild: disnake.Guild):
        date = self.bot.gen_season_date()
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})

        results = await self.bot.player_stats.find({"clan_tag": {"$in": clan_tags}}).to_list(length=2000)
        def gold(elem):
            g = elem.get("gold_looted")
            if g is None:
                return 0
            g = g.get(date)
            if g is None:
                return 0
            return sum(g)
        top_gold = sorted(results, key=gold, reverse=True)[:10]


        text = f"**{self.bot.emoji.gold} Gold Looted\n**"
        for count, result in enumerate(top_gold, 1):
            try:
                looted_gold = sum(result['gold_looted'][date])
            except:
                looted_gold = 0
            try:
                result['name']
            except:
                continue
            text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(looted_gold):11} \u200e{result['name']}`\n"

        def elixir(elem):
            g = elem.get("elixir_looted")
            if g is None:
                return 0
            g = g.get(date)
            if g is None:
                return 0
            return sum(g)
        top_elixir = sorted(results, key=elixir, reverse=True)[:10]

        text += f"**{self.bot.emoji.elixir} Elixir Looted\n**"
        for count, result in enumerate(top_elixir, 1):
            try:
                looted_elixir = sum(result['elixir_looted'][date])
            except:
                looted_elixir = 0
            try:
                result['name']
            except:
                continue
            text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(looted_elixir):11} \u200e{result['name']}`\n"

        def dark_elixir(elem):
            g = elem.get("dark_elixir_looted")
            if g is None:
                return 0
            g = g.get(date)
            if g is None:
                return 0
            return sum(g)
        top_dark_elixir = sorted(results, key=dark_elixir, reverse=True)[:10]

        text += f"**{self.bot.emoji.dark_elixir} Dark Elixir Looted\n**"
        for count, result in enumerate(top_dark_elixir, 1):
            try:
                looted_dark_elixir = sum(result['dark_elixir_looted'][date])
            except:
                looted_dark_elixir = 0
            try:
                result['name']
            except:
                continue
            text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(looted_dark_elixir):11} \u200e{result['name']}`\n"


        def activity_count(elem):
            g = elem.get("last_online_times")
            if g is None:
                return 0
            g = g.get(date)
            if g is None:
                return 0
            return len(g)
        top_activity = sorted(results, key=activity_count, reverse=True)[:10]

        text += f"**{self.bot.emoji.clock} Top Activity\n**"
        for count, result in enumerate(top_activity, 1):
            try:
                activity = activity_count(result)
            except:
                activity = 0
            try:
                result['name']
            except:
                continue
            text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(activity):5} \u200e{result['name']}`\n"

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

        second_text = f"**{self.bot.emoji.up_green_arrow} Donations\n**"
        for count, result in enumerate(top_donations, 1):
            try:
                donated = result['donations'][date]['donated']
            except:
                donated = 0
            try:
                result['name']
            except:
                continue
            second_text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(donated):7} \u200e{result['name']}`\n"

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

        second_text += f"**{self.bot.emoji.down_red_arrow} Received\n**"
        for count, result in enumerate(top_received, 1):
            try:
                received = result['donations'][date]['received']
            except:
                received = 0
            try:
                result['name']
            except:
                continue
            second_text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(received):7} \u200e{result['name']}`\n"

        def attacks(elem):
            g = elem.get("attack_wins")
            if g is None:
                return 0
            g = g.get(date)
            if g is None:
                return 0
            return g
        top_attacks = sorted(results, key=attacks, reverse=True)[:10]

        second_text += f"**{self.bot.emoji.sword_clash} Attack Wins\n**"
        for count, result in enumerate(top_attacks, 1):
            try:
                attack_num = result['attack_wins'][date]
            except:
                attack_num = 0
            try:
                result['name']
            except:
                continue
            second_text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(attack_num):7} \u200e{result['name']}`\n"


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

        second_text += f"**{self.bot.emoji.capital_gold} CG Donated (last 4 weeks)\n**"
        for count, result in enumerate(top_cg_donos, 1):
            try:
                cg_donated = capital_gold_donated(result)
            except:
                cg_donated = 0
            try:
                result['name']
            except:
                continue
            second_text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(cg_donated):7} \u200e{result['name']}`\n"


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

        second_text += f"**{self.bot.emoji.capital_gold} CG Raided (last 4 weeks)\n**"
        for count, result in enumerate(top_cg_raided, 1):
            try:
                cg_raided = capital_gold_raided(result)
            except:
                cg_raided = 0
            try:
                result['name']
            except:
                continue
            second_text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(cg_raided):7} \u200e{result['name']}`\n"

        tags = [result.get("tag") for result in results]
        start = int(coc.utils.get_season_start().timestamp())
        now = (datetime.datetime.now().timestamp())
        hits = await self.bot.warhits.find(
            {"$and": [
                {"tag": {"$in" : tags}},
                {"_time": {"$gte": start}},
                {"_time": {"$lte": now}}
            ]}).to_list(length=100000)

        names = {}
        group_hits = defaultdict(int)
        for hit in hits:
            if hit["war_type"] == "friendly":
                continue
            group_hits[hit["tag"]]+= hit["stars"]
            names[hit["tag"]] = hit['name']

        top_war_stars = sorted(group_hits.items(), key=lambda x:x[1], reverse=True)[:10]

        second_text += f"**{self.bot.emoji.war_star} War Stars\n**"
        for count, result in enumerate(top_war_stars, 1):
            tag, war_star = result
            try:
                name = names[tag]
            except:
                continue
            second_text += f"{self.bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(war_star):3} \u200e{name}`\n"

        embed = disnake.Embed(title=f"{guild.name} Season Summary", description=text)
        embed2 = disnake.Embed(description=second_text)
        print(len(embed.description) + len(embed2.description))
        return [embed, embed2]

    async def create_joinhistory(self, guild: disnake.Guild):
        field = "clan"
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans = await self.bot.get_clans(tags=clan_tags)
        text = ""

        class ItemHolder():
            def __init__(self, tag: str, value: int, time: int, joined: bool):
                self.tag = tag
                self.value = value
                self.time = time
                self.joined = joined

        clans.sort(key= lambda x : x.name.upper())
        for clan in clans:
            member_stats = await self.bot.new_looper[f"{self.bot.gen_season_date()}-history"].find({"clan.value.tag": clan.tag}).to_list(length=100)
            all_items = []

            for member in member_stats:
                field_fetch = member.get(field)
                if field_fetch is None:
                    continue
                tag = member["tag"]
                if len(field_fetch) == 0:
                    continue
                freeze = False
                for count, item in enumerate(field_fetch):
                    if freeze and item["value"]["tag"] != clan.tag:
                        continue
                    all_items.append(ItemHolder(tag=tag, value=item["value"], time=item["time"],
                                                joined=item["value"]["tag"] == clan.tag))
                    if item["value"]["tag"] != clan.tag:
                        freeze = True
                    else:
                        freeze = False

            all_items = sorted(all_items, key=lambda x: x.time, reverse=True)

            join_len = {}
            for item in all_items:
                if item.joined:
                    join_text = "Joined"
                else:
                    join_text = "Left"
                join_len[item.tag] = join_text

            num_joined = len([i for i in join_len.values() if i == "Joined"])
            num_left = len([i for i in join_len.values() if i == "Left"])
            text += f"{num_joined:2} Join {num_left:2} Left | {clan.name[:13]}\n"

        embed = disnake.Embed(title=f"{guild.name} Clan History", description=f"```{text}```", colour=disnake.Color.green())
        return embed

    async def create_sorted(self, guild: disnake.Guild, sort_by: str):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        results = await self.bot.player_stats.distinct("tag", filter = {"clan_tag": {"$in": clan_tags}})

        def get_longest(players, attribute):
            longest = 0
            for player in players:
                if "ach_" not in attribute and attribute not in ["season_rank", "heroes"]:
                    spot = len(str(player.__getattribute__(sort_by)))
                elif "ach_" in sort_by:
                    spot = len(str(player.get_achievement(name=sort_by.split('_')[-1], default_value=0).value))
                elif sort_by == "season_rank":
                    def sort_func(a_player):
                        try:
                            a_rank = a_player.legend_statistics.best_season.rank
                        except:
                            return 0

                    spot = len(str(sort_func(player))) + 1
                else:
                    spot = len(str(sum([hero.level for hero in player.heroes if hero.is_home_base])))
                if spot > longest:
                    longest = spot
            return longest

        og_sort = sort_by
        sort_by = item_to_name[sort_by]
        players: list[coc.Player] = await self.bot.get_players(tags=results, custom=False)
        if "ach_" not in sort_by and sort_by not in ["season_rank", "heroes"]:
            attr = players[0].__getattribute__(sort_by)
            if isinstance(attr, str) or isinstance(attr, coc.Role) or isinstance(attr, coc.League):
                players = sorted(players, key=lambda x: str(x.__getattribute__(sort_by)))
            else:
                players = sorted(players, key=lambda x: x.__getattribute__(sort_by), reverse=True)
        elif "ach_" in sort_by:
            players = sorted(players, key=lambda x: x.get_achievement(name=sort_by.split('_')[-1], default_value=0).value,
                             reverse=True)
        elif sort_by == "season_rank":
            def sort_func(a_player):
                try:
                    a_rank = a_player.legend_statistics.best_season.rank
                    return a_rank
                except:
                    return 10000000

            players = sorted(players, key=sort_func, reverse=False)
        else:
            longest = 3

            def sort_func(a_player):
                a_rank = sum([hero.level for hero in a_player.heroes if hero.is_home_base])
                return a_rank

            players = sorted(players, key=sort_func, reverse=True)

        players = players[:50]
        longest = get_longest(players=players, attribute=sort_by)

        text = ""
        for count, player in enumerate(players, 1):
            if sort_by in ["role", "tag", "heroes", "ach_Friend in Need"]:
                emoji = self.bot.fetch_emoji(player.town_hall)
            elif sort_by in ["versus_trophies", "versus_attack_wins", "ach_Champion Builder"]:
                emoji = self.bot.emoji.versus_trophy
            elif sort_by in ["trophies", "ach_Sweet Victory!"]:
                emoji = self.bot.emoji.trophy
            elif sort_by in ["season_rank"]:
                emoji = self.bot.emoji.legends_shield
            elif sort_by in ["clan_capital_contributions", "ach_Aggressive Capitalism"]:
                emoji = self.bot.emoji.capital_gold
            elif sort_by in ["exp_level"]:
                emoji = self.bot.emoji.xp
            elif sort_by in ["ach_Nice and Tidy"]:
                emoji = self.bot.emoji.clock
            elif sort_by in ["ach_Heroic Heist"]:
                emoji = self.bot.emoji.dark_elixir
            elif sort_by in ["ach_War League Legend", "war_stars"]:
                emoji = self.bot.emoji.war_star
            elif sort_by in ["ach_Conqueror", "attack_wins"]:
                emoji = self.bot.emoji.thick_sword
            elif sort_by in ["ach_Unbreakable"]:
                emoji = self.bot.emoji.shield
            elif sort_by in ["ach_Games Champion"]:
                emoji = self.bot.emoji.clan_games

            spot = f"{count}."
            if "ach_" not in sort_by and sort_by not in ["season_rank", "heroes"]:
                text += f"`{spot:3}`{emoji}`{player.__getattribute__(sort_by):{longest}} {player.name[:15]}`\n"
            elif "ach_" in sort_by:
                text += f"`{spot:3}`{emoji}`{player.get_achievement(name=sort_by.split('_')[-1], default_value=0).value:{longest}} {player.name[:13]}`\n"
            elif sort_by == "season_rank":
                try:
                    rank = player.legend_statistics.best_season.rank
                except:
                    rank = " N/A"
                text += f"`{spot:3}`{emoji}`#{rank:<{longest}} {player.name[:15]}`\n"
            else:
                cum_heroes = sum([hero.level for hero in player.heroes if hero.is_home_base])
                text += f"`{spot:3}`{emoji}`{cum_heroes:3} {player.name[:15]}`\n"

        embed = disnake.Embed(title=f"{guild.name} sorted by {og_sort}", description=text, color=disnake.Color.green())

        return embed

def setup(bot: CustomClient):
    bot.add_cog(getFamily(bot))