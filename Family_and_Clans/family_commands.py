import disnake
import coc
import pytz

from disnake.ext import commands
from coc import utils
from Dictionaries.emojiDictionary import emojiDictionary
from CustomClasses.CustomBot import CustomClient
from collections import defaultdict
from collections import Counter
from datetime import datetime

tiz = pytz.utc

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

        for tag in clan_tags:
            clan = await self.bot.getClan(tag)
            clan_list.append(clan)

        thcount = defaultdict(int)
        total = 0
        sumth = 0
        clan_members = []
        select_menu_options = []
        names = {}
        for count, clan in enumerate(clan_list):
            clan = await self.bot.getClan(clan.tag)
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
        embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
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

    @family.sub_command(name="wars", description="List of current wars by family clans")
    async def family_wars(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        if len(clan_tags) == 0:
            return await ctx.send("No clans linked to this server.")
        if ctx.guild.id == 923764211845312533:
            clan_tags.append("#29Q9809")
            clan_tags.append("#20VRYL99C")
            clan_tags.append("#88UUCRR9")
        war_list = []
        for tag in clan_tags:
            war = await self.bot.get_clanwar(tag)
            if war is not None:
                war_list.append(war)

        if len(war_list) == 0:
            return await ctx.send("No clans in war and/or have public war logs.")

        embed = disnake.Embed(description=f"**{ctx.guild.name} Current Wars**", color=disnake.Color.green())
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

            team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(7)
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
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.create_donations(ctx.guild, type="received")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "ratiofam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.create_donations(ctx.guild, type="ratio")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

def setup(bot: CustomClient):
    bot.add_cog(family_commands(bot))