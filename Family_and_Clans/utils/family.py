import disnake
import coc
import pytz
import emoji
import asyncio
import statistics

from coc.raid import RaidLogEntry
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from utils.troop_methods import cwl_league_emojis
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry, calc_raid_medals


tiz = pytz.utc

leagues = ["Champion League I", "Champion League II", "Champion League III",
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
        async for clan in self.bot.coc_client.get_clans(tags=clan_tags):
            members += [member.tag for member in clan.members]

        for tag in members:
            results = await self.bot.player_stats.find_one({"tag": tag})
            task = asyncio.ensure_future(
                self.bot.coc_client.get_player(player_tag=tag, cls=MyCustomPlayer, bot=self.bot,
                                               results=results))
            tasks.append(task)
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        donated_text = []
        received_text = []
        ratio_text = []
        total_donated = sum(player.donos().donated for player in responses if not isinstance(player, coc.errors.NotFound))
        total_received = sum(player.donos().received for player in responses if not isinstance(player, coc.errors.NotFound))

        for player in responses:
            if isinstance(player, coc.errors.NotFound):
                print()
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
        clans = await self.bot.get_clans(tags=clan_tags)
        member_tags = []
        for clan in clans:
            member_tags.extend(member.tag for member in clan.members)

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
        pass

    async def create_raids(self, guild: disnake.Guild):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": 810466565744230410})
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

        if guild.id == 923764211845312533:
            clan_tags.append("#29Q9809")
            clan_tags.append("#20VRYL99C")
            clan_tags.append("#88UUCRR9")
        war_list = await self.bot.get_clan_wars(tags=clan_tags)
        war_list = [w for w in war_list if w is not None and w.start_time is not None]
        if len(war_list) == 0:
            embed = disnake.Embed(description="No clans in war and/or have public war logs.", color=disnake.Color.red())
            return embed

        war_list = sorted(war_list, key=lambda l: l.start_time.seconds_until, reverse=True)
        embed = disnake.Embed(description=f"**{guild.name} Current Wars**", color=disnake.Color.green())
        for war in war_list:
            if war.clan.name is None:
                continue
            emoji = await self.bot.create_new_badge_emoji(url=war.clan.badge.url)
            war_cog = self.bot.get_cog(name="War")
            stars_percent = await war_cog.calculate_stars_percent(war)

            war_time = war.start_time.seconds_until
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


def setup(bot: CustomClient):
    bot.add_cog(getFamily(bot))