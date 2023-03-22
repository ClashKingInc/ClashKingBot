import disnake
import coc
import pytz
import operator
import json
import asyncio

from disnake.ext import commands
from coc import utils
from Assets.emojiDictionary import emojiDictionary
from CustomClasses.CustomBot import CustomClient
from collections import defaultdict
from collections import Counter
from datetime import datetime
from CustomClasses.Enums import TrophySort
from utils.constants import item_to_name

SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]
tiz = pytz.utc
leagues = ["Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]

class family_commands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="family")
    async def family(self, ctx):
        pass

    @family.sub_command(name="clans", description="List of family clans")
    async def family_clan(self, ctx: disnake.ApplicationCommandInteraction):
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("No clans linked to this server.")
        categoryTypesList = []
        categoryTypesList.append("All Clans")

        categories = await self.bot.clan_db.distinct("category", filter={"server": ctx.guild.id})
        server_db = await self.bot.server_db.find_one({"server": ctx.guild.id})
        sorted_categories = server_db.get("category_order")
        if sorted_categories is not None:
            missing_cats = list(set(categories).difference(sorted_categories))
            categories = sorted_categories + missing_cats
        categoryTypesList += categories

        embeds = []
        master_embed = disnake.Embed(description=f"__**{ctx.guild.name} Clans**__",
                                     color=disnake.Color.green())
        if ctx.guild.icon is not None:
            master_embed.set_thumbnail(url=ctx.guild.icon.url)
        for category in categoryTypesList:
            if category == "All Clans":
                continue
            text = ""
            other_text = ""

            results = self.bot.clan_db.find({"$and": [
                {"category": category},
                {"server": ctx.guild.id}
            ]}).sort("name", 1)
            if results is None:
                continue
            limit = await self.bot.clan_db.count_documents(filter={"$and": [
                {"category": category},
                {"server": ctx.guild.id}
            ]})
            for result in await results.to_list(length=limit):
                tag = result.get("tag")
                clan = await self.bot.getClan(tag)
                try:
                    leader = utils.get(clan.members, role=coc.Role.leader)
                except:
                    continue
                if clan is None:
                    continue
                if clan.member_count == 0:
                    continue
                text += f"[{clan.name}]({clan.share_link}) | ({clan.member_count}/50)\n" \
                        f"**Leader:** {leader.name}\n\n"
                other_text += f"{clan.name} | ({clan.member_count}/50)\n"

            embed = disnake.Embed(title=f"__**{category} Clans**__",
                                  description=text,
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            master_embed.add_field(name=f"__**{category} Clans**__", value=other_text, inline=False)
            embeds.append(embed)

        embeds.append(master_embed)


        options = []
        for category in categoryTypesList:
            options.append(disnake.SelectOption(label=f"{category}", value=f"{category}"))

        select1 = disnake.ui.Select(
            options=options,
            placeholder="Choose clan category",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = disnake.ui.ActionRow()
        action_row.append_item(select1)

        await ctx.send(embed=embeds[len(embeds)-1], components=[action_row])

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author.id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", ephemeral=True)
                continue

            value = res.values[0]

            current_page = categoryTypesList.index(value)-1

            await res.response.edit_message(embed=embeds[current_page])

    @family.sub_command(name='compo', description="Compo of an all clans in server")
    async def family_compo(self, ctx: disnake.ApplicationCommandInteraction):
        clan_list = []
        await ctx.response.defer()
        embed = disnake.Embed(description=f"<a:loading:884400064313819146> Calculating TH Composition for {ctx.guild.name}.", color=disnake.Color.green())

        await ctx.edit_original_message(embed=embed)
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        if len(clan_tags) == 0:
            return await ctx.edit_original_message(content="No clans linked to this server.", embed=None)

        clan_list = await self.bot.get_clans(tags=clan_tags)


        thcount = defaultdict(int)
        total = 0
        sumth = 0
        clan_members = []
        select_menu_options = []
        names = {}
        for count, clan in enumerate(clan_list):
            names[clan.tag] = clan.name
            clan_members += [member.tag for member in clan.members]
            url = clan.badge.url.replace(".png", "")
            emoji = disnake.utils.get(self.bot.emojis, name=url[-15:].replace("-", ""))
            if emoji is None:
                emoji = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            else:
                emoji = f"<:{emoji.name}:{emoji.id}>"

            if count < 25:
                select_menu_options.append(disnake.SelectOption(label=clan.name, emoji=self.bot.partial_emoji_gen(emoji_string=emoji), value=clan.tag))

        select = disnake.ui.Select(
            options=select_menu_options,
            placeholder="Mix & Match Compo",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(select_menu_options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        list_members = await self.bot.get_players(tags=clan_members, custom=False)

        compos = {}
        for player in list_members:
            if player is None:
                continue
            if player.clan is not None:
                if player.clan.tag not in compos.keys():
                    compos[player.clan.tag] = {}
                if player.town_hall not in compos[player.clan.tag].keys():
                    compos[player.clan.tag][player.town_hall] = 0
                compos[player.clan.tag][player.town_hall] += 1
            th = player.town_hall
            sumth += th
            total += 1
            thcount[th] += 1

        stats = ""
        for th_level, th_count in sorted(thcount.items(), reverse=True):
            if th_level <= 9:
                th_emoji = emojiDictionary(th_level)
                stats += f"{th_emoji} `TH{th_level} `: {th_count}\n"
            else:
                th_emoji = emojiDictionary(th_level)
                stats += f"{th_emoji} `TH{th_level}` : {th_count}\n"
        average = round(sumth / total, 2)
        embed = disnake.Embed(title=f"{ctx.guild.name} Townhall Composition", description=stats, color=disnake.Color.green())

        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        #embed2 = await self.generate_townhall_lines(master_compo_dict=compos, names=names)
        #embed2.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
        await ctx.edit_original_message(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            all_added = Counter(compos[res.values[0]])
            name_clans = [names[res.values[0]]]
            for value in res.values[1:]:
                all_added += Counter(compos[value])
                name_clans.append(names[value])

            stats = ""
            total = sum(all_added.values())
            sumth = 0
            for th_level, th_count in sorted(dict(all_added).items(), reverse=True):
                sumth += (th_level * th_count)
                if th_level <= 9:
                    th_emoji = emojiDictionary(th_level)
                    stats += f"{th_emoji} `TH{th_level} `: {th_count}\n"
                else:
                    th_emoji = emojiDictionary(th_level)
                    stats += f"{th_emoji} `TH{th_level}` : {th_count}\n"
            average = round(sumth / total, 2)
            embed = disnake.Embed(title=f"Selected Clans Townhall Composition", description=stats,
                                  color=disnake.Color.green())

            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)

            embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts\nClans: {', '.join(name_clans)}")
            await res.response.edit_message(embed=embed)

    async def generate_townhall_lines(self, master_compo_dict: dict, names: dict):
        master_string = "".join(f"{x:2} " for x in reversed(range(10, 16))) + "\n"
        for clan_tag, compo_dict in master_compo_dict.items():
            try:
                name = names[clan_tag]
            except:
                pass
            for x in reversed(range(10, 16)):
                #number = compo_dict.get(x, 0)
                master_string += f"{compo_dict.get(x, 0):2} "
                '''if number >= 1:
                    master_string += f"{self.bot.get_number_emoji(color='white', number=number)}"
                else:
                    master_string += f"<:blanke:838574915095101470>"'''
            master_string += f"{name[:13]:13}\n"
        master_string = f"```{master_string}```"
        embed = disnake.Embed(description=master_string, color=disnake.Color.green())
        return embed


    @family.sub_command(name="wars", description="List of current wars by family clans")
    async def family_wars(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        time = datetime.now()
        embed: disnake.Embed = await self.create_wars(guild=ctx.guild)
        embed.timestamp = time
        embed.set_footer(text="Last Refreshed:")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"warsfam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)
        await ctx.edit_original_message(embed=embed)

    @family.sub_command(name="donations", description="List of top 50 donators in family")
    async def family_donos(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        time = datetime.now().timestamp()
        embed = await self.create_donations(guild=ctx.guild, type="donated")
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"donationfam_"))
        buttons.append_item(disnake.ui.Button(label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,
                                              style=disnake.ButtonStyle.green, custom_id=f"receivedfam_"))
        buttons.append_item(
            disnake.ui.Button(label="Ratio", emoji=self.bot.emoji.ratio.partial_emoji, style=disnake.ButtonStyle.green,
                              custom_id=f"ratiofam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @family.sub_command(name="cwl-rankings", description="Get rankings of family clans in current cwl")
    async def cwl_rankings(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        if len(clan_tags) == 0:
            return await ctx.send("No clans linked to this server.")

        clans =await self.bot.get_clans(tags=clan_tags)
        cwl_list = []
        tasks = []
        for clan in clans:
            cwl_list.append([clan.name, clan.tag, clan.war_league.name, clan])
            task = asyncio.ensure_future(self.cwl_ranking_create(clan))
            tasks.append(task)
        rankings = await asyncio.gather(*tasks)
        new_rankings = {}
        print(rankings)
        for item in rankings:
            new_rankings[list(item.keys())[0]] = list(item.values())[0]

        clans_list = sorted(cwl_list, key=lambda l: l[2], reverse=False)

        main_embed = disnake.Embed(title=f"__**{ctx.guild.name} CWL Rankings**__",
                                   color=disnake.Color.green())
        if ctx.guild.icon is not None:
            main_embed.set_thumbnail(url=ctx.guild.icon.url)

        embeds = []
        leagues_present = ["All"]
        for league in leagues:
            text = ""
            for clan in clans_list:
                # print(clan)
                if clan[2] == league:
                    tag = clan[1]
                    placement = new_rankings[tag]
                    if placement is None:
                        continue
                    if len(text) + len(f"{placement}{clan[0]}\n") >= 1020:
                        main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                        text = ""
                    text += f"{placement}{clan[0]}\n"
                if (clan[0] == clans_list[len(clans_list) - 1][0]) and (text != ""):
                    leagues_present.append(league)
                    main_embed.add_field(name=f"**{league}**", value=text, inline=False)
                    embed = disnake.Embed(title=f"__**{ctx.guild.name} {league} Clans**__", description=text,
                                          color=disnake.Color.green())
                    if ctx.guild.icon is not None:
                        embed.set_thumbnail(url=ctx.guild.icon.url)
                    embeds.append(embed)

        embeds.append(main_embed)
        await ctx.send(embed=main_embed)

    @family.sub_command(name="last-online", description="Last 50 online in family")
    async def last_online(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        time = datetime.now().timestamp()
        embed = await self.create_last_online(guild=ctx.guild)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"lastonlinefam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @family.sub_command(name="activities", description="Activity count leaderboard of how often players have been seen online")
    async def activities(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        time = datetime.now().timestamp()
        embed = await self.create_activities(guild=ctx.guild)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"activitiesfam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @family.sub_command(name="leagues", description="List of clans by cwl or capital league")
    async def league(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        embed = await self.create_cwl_leagues(guild=ctx.guild)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="CWL", emoji=self.bot.emoji.cwl_medal.partial_emoji, style=disnake.ButtonStyle.green,
                              custom_id=f"cwlleaguesfam_"))
        buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.grey, custom_id=f"capitalleaguesfam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @family.sub_command(name="raids", description="Show list of raids in family")
    async def family_raids(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        time = datetime.now()
        embed: disnake.Embed = await self.create_raids(guild=ctx.guild)
        embed.timestamp = time
        embed.set_footer(text="Last Refreshed:")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"raidsfam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @family.sub_command(name="trophies", description="List of clans by home, builder, or capital trophy points")
    async def trophies(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        embed = await self.create_trophies(guild=ctx.guild, sort_type=TrophySort.home)
        buttons = disnake.ui.ActionRow()
        sort_type = TrophySort.home
        buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,custom_id=f"hometrophiesfam_"))
        buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey, custom_id=f"versustrophiesfam_"))
        buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                              custom_id=f"capitaltrophiesfam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @family.sub_command(name="summary", description="Summary of family stats")
    async def family_summary(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        time = datetime.now()
        embeds = await self.create_summary(guild=ctx.guild)
        embeds[-1].timestamp = time
        embeds[-1].set_footer(text="Last Refreshed:")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"summaryfam_"))
        await ctx.edit_original_message(embeds=embeds, components=buttons)

    @family.sub_command(name="join-history", description="Summary of join/leave stats")
    async def family_history(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        time = datetime.now()
        embed: disnake.Embed = await self.create_joinhistory(guild=ctx.guild)
        embed.timestamp = time
        embed.set_footer(text="Last Refreshed:")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"joinhistoryfam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @family.sub_command(name="sorted", description="Sort family members in different ways")
    async def family_sorted(self, ctx: disnake.ApplicationCommandInteraction, sort_by: str = commands.Param(choices=sorted(item_to_name.keys()))):
        await ctx.response.defer()
        time = datetime.now()
        embed: disnake.Embed = await self.create_sorted(guild=ctx.guild, sort_by=sort_by)
        embed.timestamp = time
        embed.set_footer(text="Last Refreshed:")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"sortfam_"))
        await ctx.edit_original_message(embed=embed, components=[])

    @family.sub_command(name="clan-games", description="Show top clan games points in family")
    async def family_clan_games(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        time = datetime.now()
        embed: disnake.Embed = await self.create_clan_games(guild=ctx.guild)
        embed.timestamp = time
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"clangamesfam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)


    async def cwl_ranking_create(self, clan: coc.Clan):
        try:
            group = await self.bot.coc_client.get_league_group(clan.tag)
            state = group.state
            if str(state) == "preparation" and len(group.rounds) == 1:
                return {clan.tag: None}
            if str(group.season) != self.bot.gen_season_date():
                return {clan.tag: None}
        except:
            return {clan.tag: None}

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
            star_list.append([tag, stars, destruction])

        sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)
        place= 1
        for item in sorted_list:
            war_leagues = open(f"Assets/war_leagues.json")
            war_leagues = json.load(war_leagues)
            promo = [x["promo"] for x in war_leagues["items"] if x["name"] == clan.war_league.name][0]
            demo = [x["demote"] for x in war_leagues["items"] if x["name"] == clan.war_league.name][0]
            if place <= promo:
                emoji = "<:warwon:932212939899949176>"
            elif place >= demo:
                emoji = "<:warlost:932212154164183081>"
            else:
                emoji = "<:dash:933150462818021437>"
            tag = item[0]
            stars = str(item[1])
            dest = str(item[2])
            if place == 1:
                rank = f"{place}st"
            elif place == 2:
                rank = f"{place}nd"
            elif place == 3:
                rank = f"{place}rd"
            else:
                rank = f"{place}th"
            if tag == clan.tag:
                tier = str(clan.war_league.name).count("I")
                return {clan.tag : f"{emoji}`{rank}` {self.leagueAndTrophies(clan.war_league.name)}{SUPER_SCRIPTS[tier]}"}
            place += 1

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


    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        time = datetime.now().timestamp()
        if "donationfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_donations(ctx.guild, type="donated")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "receivedfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_donations(ctx.guild, type="received")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "ratiofam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_donations(ctx.guild, type="ratio")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "lastonlinefam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_last_online(ctx.guild)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "activitiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_activities(ctx.guild)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "summaryfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            time = datetime.now()
            embeds = await self.create_summary(guild=ctx.guild)
            embeds[-1].timestamp = time
            embeds[-1].set_footer(text="Last Refreshed:")
            await ctx.edit_original_message(embeds=embeds)

        elif "cwlleaguesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_cwl_leagues(guild=ctx.guild)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                     disnake.ui.Button(label="CWL", emoji=self.bot.emoji.cwl_medal.partial_emoji, style=disnake.ButtonStyle.green,
                              custom_id=f"cwlleaguesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.grey, custom_id=f"capitalleaguesfam_"))

            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "capitalleaguesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_capital_leagues(guild=ctx.guild)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                    disnake.ui.Button(label="CWL", emoji=self.bot.emoji.cwl_medal.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"cwlleaguesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green, custom_id=f"capitalleaguesfam_"))

            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "raidsfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_raids(guild=ctx.guild)
            embed.set_footer(text="Last Refreshed:")
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "clangamesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_clan_games(guild=ctx.guild)
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "joinhistoryfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_joinhistory(guild=ctx.guild)
            embed.set_footer(text="Last Refreshed:")
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "warsfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_wars(guild=ctx.guild)
            embed.set_footer(text="Last Refreshed:")
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "hometrophiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            sort_type = TrophySort.home
            embed = await self.create_trophies(guild=ctx.guild, sort_type=sort_type)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                                  custom_id=f"hometrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                                  custom_id=f"versustrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                                  custom_id=f"capitaltrophiesfam_"))
            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "versustrophiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            sort_type = TrophySort.versus
            embed = await self.create_trophies(guild=ctx.guild, sort_type=sort_type)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                                  custom_id=f"hometrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                                  custom_id=f"versustrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                                  custom_id=f"capitaltrophiesfam_"))
            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "capitaltrophiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            sort_type = TrophySort.capital
            embed = await self.create_trophies(guild=ctx.guild, sort_type=sort_type)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                                  custom_id=f"hometrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                                  custom_id=f"versustrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                                  custom_id=f"capitaltrophiesfam_"))
            await ctx.edit_original_message(embed=embed, components=buttons)


def setup(bot: CustomClient):
    bot.add_cog(family_commands(bot))