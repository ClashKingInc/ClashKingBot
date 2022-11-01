import json

import coc
import disnake
from disnake.ext import commands, tasks
from datetime import datetime
from utils.troop_methods import cwl_league_emojis
from utils.discord_utils import partial_emoji_gen
from Dictionaries.emojiDictionary import emojiDictionary
from Dictionaries.levelEmojis import levelEmojis
from collections import defaultdict
import operator
import aiohttp
from bs4 import BeautifulSoup
import asyncio

from CustomClasses.CustomBot import CustomClient

leagues = ["Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]

import pytz
tiz = pytz.utc


class Cwl(commands.Cog, name="CWL"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="cwl", description="Stats, stars, and more for a clan's cwl")
    async def cwl(self, ctx: disnake.ApplicationCommandInteraction, clan: str):
        await ctx.response.defer()
        clan = await self.bot.getClan(clan)

        if clan is None:
            return await ctx.send("Not a valid clan tag.")

        war = None
        next_war = None
        try:
            group = await self.bot.coc_client.get_league_group(clan.tag)
            rounds = group.number_of_rounds
            league_wars = []
            async for w in group.get_wars_for_clan(clan.tag):
                league_wars.append(w)
                if str(w.state) == "inWar":
                    war = w
                if str(w.state) == "preparation":
                    next_war = w
        except:
            embed = disnake.Embed(description=f"[**{clan.name}**]({clan.share_link}) is not in CWL.",
                                  color=disnake.Color.green())
            embed.set_thumbnail(url=clan.badge.large)
            return await ctx.send(embed=embed)

        if war is None and next_war is not None:
            war = next_war
            next_war= None

        if war is None and next_war is None:
            embed = disnake.Embed(description=f"[**{clan.name}**]({clan.share_link}) is not in CWL.",
                                  color=disnake.Color.green())
            embed.set_thumbnail(url=clan.badge.large)
            return await ctx.send(embed=embed)

        map = partial_emoji_gen(self.bot, "<:map:944913638500761600>")
        swords = partial_emoji_gen(self.bot, "<a:swords:944894455633297418>", animated=True)
        star = partial_emoji_gen(self.bot, "<:star:825571962699907152>")
        troop = partial_emoji_gen(self.bot, "<:troop:861797310224400434>")
        up = partial_emoji_gen(self.bot, "<:warwon:932212939899949176>")

        options= [  # the options in your dropdown
                disnake.SelectOption(label="Star Leaderboard", emoji=star, value="stars"),
                disnake.SelectOption(label="Clan Rankings", emoji=up, value="rankings"),
                disnake.SelectOption(label="All Rounds", emoji=map, value="allrounds"),
            ]

        #on first round - only next round
        #on last round - only current round

        if war is None:
            options.insert(0, disnake.SelectOption(label="Next Round", emoji='📍', value="nextround"))
            options.insert(1, disnake.SelectOption(label="Next Round Lineup", emoji=troop, value="lineup"))
        elif next_war is None:
            options.insert(0, disnake.SelectOption(label="Current Round", emoji=swords, value="round"))
        else:
            options.insert(0, disnake.SelectOption(label="Current Round", emoji=swords, value="round"))
            options.insert(1, disnake.SelectOption(label="Next Round", emoji="📍", value="nextround"))
            options.insert(2, disnake.SelectOption(label="Next Round Lineup", emoji=troop, value="lineup"))


        select = disnake.ui.Select(
            options=options,
            placeholder="Choose a page",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        main = await self.war_embed(war, clan)
        await ctx.send(embed=main, components=dropdown)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            if res.values[0] == "round":
                await res.response.edit_message(embed=main)
            elif res.values[0] == "nextround":
                embed = await self.war_embed(next_war, clan)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "lineup":
                embed1 = await self.roster_embed(next_war)
                embed2 = await self.opp_roster_embed(next_war)
                await res.response.edit_message(embeds=[embed1, embed2])
            elif res.values[0] == "stars":
                embed = await self.star_lb(league_wars, clan)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "rankings":
                embed = await self.ranking_lb(group, clan)
                await res.response.edit_message(embed=embed)
            elif res.values[0] == "allrounds":
                embed = await self.all_rounds(league_wars, clan)
                await res.response.edit_message(embed=embed)

    @cwl.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]

    async def war_embed(self, war: coc.ClanWar, clan: coc.Clan):

        war_time = war.start_time.seconds_until

        war_state = "In Prep"
        war_pos = "Starting"
        if war_time >= 0:
            war_time = war.start_time.time.replace(tzinfo=tiz).timestamp()
        else:
            war_time = war.end_time.seconds_until
            if war_time <= 0:
                war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                war_pos = "Ended"
                war_state = "War Over"
            else:
                war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                war_pos = "Ending"
                war_state = "In War"

        stats = await self.calculate_stars_percent(war)
        team_stars = str(stats[2]).ljust(7)
        opp_stars = str(stats[0]).rjust(7)
        team_per = (str(stats[3]) + "%").ljust(7)
        opp_per = (str(stats[1]) + "%").rjust(7)
        team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(7)
        opp_hits = f"{len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".rjust(7)

        th_comps = await self.war_th_comps(war)

        embed = disnake.Embed(description=f"[**{clan.name}**]({clan.share_link})",
                              color=disnake.Color.green())
        embed.add_field(name=f"**War Against**", value=f"[**{war.opponent.name}**]({war.opponent.share_link})\n­\n",
                        inline=False)
        embed.add_field(name=f"**War State**",
                        value=f"{cwl_league_emojis(str(clan.war_league))}{str(clan.war_league)}\n"
                              f"{war_state} ({war.team_size} vs {war.team_size})\n"
                              f"{war_pos}: <t:{int(war_time)}:R>\n­\n", inline=False)
        embed.add_field(name="**War Stats**",
                        value=f"`{team_hits}`<a:swords:944894455633297418>`{opp_hits}`\n"
                              f"`{team_stars}`<:star:825571962699907152>`{opp_stars}`\n"
                              f"`{team_per}`<:broken_sword:944896241429540915>`{opp_per}`\n­\n"
                        , inline=False)

        embed.add_field(name="War Composition", value=f"{war.clan.name}\n{th_comps[0]}\n"
                                                      f"{war.opponent.name}\n{th_comps[1]}", inline=False)

        embed.set_thumbnail(url=clan.badge.large)
        return embed

    async def roster_embed(self, war: coc.ClanWar):
        roster = ""
        tags = []
        lineup = []
        x =0
        for player in war.members:
            if player not in war.opponent.members:
                tags.append(player.tag)
                x+=1
                lineup.append(x)

        x = 0
        async for player in self.bot.coc_client.get_players(tags):
            th = player.town_hall
            th_emoji = emojiDictionary(th)
            place = str(lineup[x]) + "."
            place = place.ljust(3)
            hero_total = 0
            hero_names = ["Barbarian King", "Archer Queen", "Royal Champion", "Grand Warden"]
            heros = player.heroes
            for hero in heros:
                if hero.name in hero_names:
                    hero_total += hero.level
            if hero_total == 0:
                hero_total = ""
            roster += f"\u200e`{place}` {th_emoji} \u200e{player.name}\u200e | {hero_total}\n"
            x += 1

        embed = disnake.Embed(title=f"{war.clan.name} War Roster", description=roster,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=war.clan.badge.large)
        return embed

    async def opp_roster_embed(self, war):
        roster = ""
        tags = []
        lineup = []
        x = 0
        for player in war.opponent.members:
            tags.append(player.tag)
            x += 1
            lineup.append(x)

        x = 0
        async for player in self.bot.coc_client.get_players(tags):
            th = player.town_hall
            th_emoji = emojiDictionary(th)
            place = str(lineup[x]) + "."
            place = place.ljust(3)
            heros = player.heroes
            hero_total = 0
            hero_names = ["Barbarian King", "Archer Queen", "Royal Champion", "Grand Warden"]
            for hero in heros:
                if hero.name in hero_names:
                    hero_total += hero.level
            if hero_total == 0:
                hero_total = ""
            roster += f"\u200e`{place}` {th_emoji} \u200e{player.name}\u200e | {hero_total}\n"
            x += 1

        embed = disnake.Embed(title=f"{war.opponent.name} War Roster", description=roster,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=war.opponent.badge.large)
        return embed

    async def star_lb(self, league_wars, clan):
        star_dict = defaultdict(int)
        dest_dict = defaultdict(int)
        tag_to_name = defaultdict(str)
        for war in league_wars:
            war: coc.ClanWar
            for player in war.members:
                if player not in war.opponent.members:
                    attacks = player.attacks
                    tag_to_name[player.tag] = player.name
                    for attack in attacks:
                        stars = attack.stars
                        destruction = attack.destruction
                        star_dict[player.tag] += stars
                        dest_dict[player.tag] += destruction

        star_list = []
        for tag, stars in star_dict.items():
            destruction = dest_dict[tag]
            name = tag_to_name[tag]
            star_list.append([name, stars, destruction])

        sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)
        text = ""
        text += f"` # ST DSTR NAME           `\n"
        x = 1
        for item in sorted_list:
            name = item[0]
            stars = str(item[1])
            dest = str(item[2])
            rank = str(x)
            rank = rank.rjust(2)
            stars = stars.rjust(2)
            name = name.ljust(15)
            dest = dest.rjust(3) + "%"
            text += f"`\u200e{rank} {stars} {dest} \u200e{name}`\n"
            x+=1

        embed = disnake.Embed(title=f"{clan.name} Star Leaderboard", description=text,
                              color=disnake.Color.green())
        return embed

    async def all_rounds(self, league_wars, clan):
        embed = disnake.Embed(title=f"{clan.name} CWL | All Rounds",
                              color=disnake.Color.green())

        round = 1
        for war in league_wars:
            war: coc.ClanWar
            war_time = war.start_time.seconds_until
            war_state = "In Prep"
            war_pos = "Starting"
            if war_time >= 0:
                war_time = war.start_time.time.replace(tzinfo=tiz).timestamp()
            else:
                war_time = war.end_time.seconds_until
                if war_time <= 0:
                    war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                    war_pos = "Ended"
                    war_state = "War Over | "
                else:
                    war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                    war_pos = "Ending"
                    war_state = "In War |"
            stats = await self.calculate_stars_percent(war)
            team_stars = str(stats[2]).ljust(7)
            opp_stars = str(stats[0]).rjust(7)
            team_per = (str(stats[3]) + "%").ljust(7)
            opp_per = (str(stats[1]) + "%").rjust(7)
            team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(
                7)
            opp_hits = f"{len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".rjust(7)
            emoji=""
            if str(war.status) == "won":
                emoji = "<:greentick:601900670823694357>"
            elif str(war.status) == "lost":
                emoji = "<:redtick:601900691312607242>"
            embed.add_field(name=f"**{war.clan.name}** vs **{war.opponent.name}**\n"
                                 f"{emoji}Round {round} | {war_state} {str(war.status).capitalize()}",
                            value=f"`{team_hits}`<a:swords:944894455633297418>`{opp_hits}`\n"
                                  f"`{team_stars}`<:star:825571962699907152>`{opp_stars}`\n"
                                  f"`{team_per}`<:broken_sword:944896241429540915>`{opp_per}`\n"
                                  f"{war_pos} <t:{int(war_time)}:R>\n­\n"
                            , inline=False)
            round+=1
        return embed

    async def ranking_lb(self, group: coc.ClanWarLeagueGroup, clan):
        star_dict = defaultdict(int)
        dest_dict = defaultdict(int)
        tag_to_name = defaultdict(str)

        rounds = group.rounds
        for round in rounds:
            for war_tag in round:
                war = await self.bot.coc_client.get_league_war(war_tag)
                if str(war.status) == "won":
                    star_dict[war.clan.tag] += 10
                elif str(war.status) == "lost":
                    star_dict[war.opponent.tag] += 10
                tag_to_name[war.clan.tag] = war.clan.name
                tag_to_name[war.opponent.tag] = war.opponent.name
                for player in war.members:
                    attacks = player.attacks
                    for attack in attacks:
                        star_dict[player.clan.tag] += attack.stars
                        dest_dict[player.clan.tag] += attack.destruction

        star_list = []
        for tag, stars in star_dict.items():
            destruction = dest_dict[tag]
            name = tag_to_name[tag]
            star_list.append([name, stars, destruction])

        sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)
        text = ""
        text += f"`# STR DSTR   NAME           `"
        x = 1
        for item in sorted_list:
            name = item[0]
            stars = str(item[1])
            dest = str(item[2])
            rank = str(x)
            rank = rank.rjust(1)
            stars = stars.rjust(2)
            name = name.ljust(15)
            dest = dest.rjust(5) + "%"
            text += f"\n`\u200e{rank} \u200e{stars} {dest} \u200e{name}`"
            x += 1

        embed = disnake.Embed(title=f"Clan Ranking Leaderboard", description=text,
                              color=disnake.Color.green())
        return embed

    async def calculate_stars_percent(self, war: coc.ClanWar):
        stars = 0
        destr = 0
        num_def = 0

        opp_stars = 0
        opp_destr = 0
        opp_num_def = 0

        for member in war.members:
            if member not in war.opponent.members:
                defenses = member.defenses
                num_def += 1
                largest_star = 0
                largest_per = 0
                for defense in defenses:
                    star = defense.stars
                    if star >= largest_star:
                        if defense.destruction > largest_per:
                            largest_star = star
                            largest_per = defense.destruction
                stars += largest_star
                destr += largest_per
            else:
                defenses = member.defenses
                opp_num_def += 1
                largest_star = 0
                largest_per = 0
                for defense in defenses:
                    star = defense.stars
                    if star >= largest_star:
                        if defense.destruction > largest_per:
                            largest_star = star
                            largest_per = defense.destruction
                opp_stars += largest_star
                opp_destr += largest_per

        avg_destr = round(destr / num_def, 2)
        avg_destr_opp = round(opp_destr / opp_num_def, 2)
        return [stars, avg_destr, opp_stars, avg_destr_opp]

    async def war_th_comps(self, war: coc.ClanWar):
        thcount = defaultdict(int)
        opp_thcount = defaultdict(int)

        for player in war.members:
            if player not in war.opponent.members:
                thcount[player.town_hall] += 1
            else:
                opp_thcount[player.town_hall] += 1

        stats = ""
        for th_level, th_count in sorted(thcount.items(), reverse=True):
            th_emoji = self.bot.fetch_emoji(th_level)
            stats += f"{th_emoji}`{th_count}` "
        opp_stats = ""
        for th_level, th_count in sorted(opp_thcount.items(), reverse=True):
            th_emoji = self.bot.fetch_emoji(th_level)
            opp_stats += f"{th_emoji}`{th_count}` "

        return [stats, opp_stats]

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

    @commands.slash_command(name="cwl-leagues", description="List of clans in family, sorted by cwl league")
    async def cwl_co(self, ctx: disnake.ApplicationCommandInteraction):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("No clans linked to this server.")

        same = "<:dash:933150462818021437>"
        up = "<:warwon:932212939899949176>"
        down = "<:warlost:932212154164183081>"
        cwl_list = []
        for tClan in await tracked.to_list(length=limit):
            c = []
            tag = tClan.get("tag")
            clan = await self.bot.getClan(tag)
            c.append(clan.name)
            c.append(clan.war_league.name)
            cwl_list.append(c)

        clans_list = sorted(cwl_list, key=lambda l: l[0], reverse=False)

        main_embed = disnake.Embed(title=f"__**{ctx.guild.name} CWL Leagues**__",
                                     color=disnake.Color.green())
        if ctx.guild.icon is not None:
            main_embed.set_thumbnail(url=ctx.guild.icon.url)


        embeds = []
        leagues_present = ["All"]
        for league in leagues:
            #print(league)
            text = ""
            for clan in clans_list:
                #print(clan)
                if clan[1] == league:
                    text += clan[0] + "\n"
                if (clan[0] == clans_list[len(clans_list)-1][0]) and (text !=""):
                    leagues_present.append(league)
                    league_emoji = cwl_league_emojis(league)
                    main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                    embed = disnake.Embed(title=f"__**{ctx.guild.name} {league} Clans**__", description=text,
                                               color=disnake.Color.green())
                    if ctx.guild.icon is not None:
                        embed.set_thumbnail(url=ctx.guild.icon.url)
                    embeds.append(embed)

        embeds.append(main_embed)

        await ctx.send(embed=main_embed)
        '''
        options = []
        for league in leagues_present:
            if league == "All":
                league_emoji = "<:LeagueMedal:858424820857307176>"
            else:
                league_emoji = cwl_league_emojis(league)
            emoji = league_emoji.split(":", 2)
            emoji = emoji[2]
            emoji = emoji[0:len(emoji) - 1]
            emoji = self.bot.get_emoji(int(emoji))
            emoji = disnake.PartialEmoji(name=emoji.name, id=emoji.id)
            options.append(create_select_option(f"{league}", value=f"{league}", emoji=emoji))

        select1 = create_select(
            options=options,
            placeholder="Choose clan category",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = create_actionrow(select1)

        msg = await ctx.reply(embed=embeds[len(embeds) - 1], components=[action_row],
                              mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=action_row,
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()
            value = res.values[0]

            current_page = leagues_present.index(value) - 1

            await msg.edit(embed=embeds[current_page],
                           components=[action_row])
            '''

    @commands.slash_command(name="cwl-status", description="CWL spin status of clans in family")
    async def cwl_status(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        now = datetime.utcnow()
        year = now.year
        month = now.month
        if month <= 9:
            month = f"0{month}"
        dt = f"{year}-{month}"
        #print(dt)
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.edit_original_message(content="No clans linked to this server.")

        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Loading Family CWL Status...",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

        spin_list = []
        for tClan in await tracked.to_list(length=limit):
            c = []
            tag = tClan.get("tag")
            name = tClan.get("name")
            c.append(name)
            clan = await self.bot.getClan(tag)
            c.append(clan.war_league.name)
            c.append(clan.tag)
            try:
                league = await self.bot.coc_client.get_league_group(tag)
                state = league.state
                if str(state) == "preparation":
                    c.append("<a:CheckAccept:992611802561134662>")
                    c.append(1)
                elif str(state) == "ended":
                    c.append("<:dash:933150462818021437>")
                    c.append(3)
                elif str(state) == "inWar":
                    c.append("<a:swords:944894455633297418>")
                    c.append(0)
            except coc.errors.NotFound:
                c.append("<:dash:933150462818021437>")
                c.append(3)
            except:
                c.append("<a:spinning:992612297048588338>")
                c.append(2)
            spin_list.append(c)

        #print(spin_list)
        clans_list = sorted(spin_list, key=lambda x: (x[1], x[4]), reverse=False)

        main_embed = disnake.Embed(title=f"__**{ctx.guild.name} CWL Status**__",
                                   color=disnake.Color.green())
        if ctx.guild.icon is not None:
            main_embed.set_thumbnail(url=ctx.guild.icon.url)

        embeds = []
        leagues_present = ["All"]
        for league in leagues:
            text = ""
            for clan in clans_list:
                if clan[1] == league:
                    text += f"{clan[3]} {clan[0]}\n"
                if (clan[2] == clans_list[len(clans_list) - 1][2]) and (text != ""):
                    leagues_present.append(league)
                    main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                    embed = disnake.Embed(title=f"__**{ctx.guild.name} {league} Clans**__", description=text,
                                          color=disnake.Color.green())
                    if ctx.guild.icon is not None:
                        embed.set_thumbnail(url=ctx.guild.icon.url)
                    embeds.append(embed)

        main_embed.add_field(name="Legend", value=f"<a:spinning:992612297048588338> Spinning | <:dash:933150462818021437> Not Spun | <a:CheckAccept:992611802561134662> Prep |  <a:swords:944894455633297418> War")
        embeds.append(main_embed)
        await ctx.edit_original_message(embed=main_embed)



def setup(bot: CustomClient):
    bot.add_cog(Cwl(bot))