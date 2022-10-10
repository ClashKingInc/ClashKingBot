import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from datetime import datetime
from utils.discord_utils import partial_emoji_gen
from utils.components import raid_buttons
from utils.clash import create_weekends
import asyncio
from CustomClasses.CustomPlayer import MyCustomPlayer
import pandas as pd

class clan_commands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="clan")
    async def clan(self, ctx):
        pass

    @clan.sub_command(name="search", description="lookup clan by tag")
    async def getclan(self, ctx: disnake.ApplicationCommandInteraction, clan: str):
        """
            Parameters
            ----------
            clan: Search by clan tag or select an option from the autocomplete
        """

        clan = await self.bot.getClan(clan)

        if clan is None or clan.member_count == 0:
            return await ctx.send("Not a valid clan tag.")

        await ctx.response.defer()
        embed = disnake.Embed(
            description=f"<a:loading:884400064313819146> Fetching clan...",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

        embed = await self.clan_overview(ctx, clan)

        emoji = partial_emoji_gen(self.bot, "<:discord:840749695466864650>")
        rx = partial_emoji_gen(self.bot, "<:redtick:601900691312607242>")
        trophy = partial_emoji_gen(self.bot, "<:trophy:825563829705637889>")
        clan_e = partial_emoji_gen(self.bot, "<:clan_castle:855688168816377857>")
        opt = partial_emoji_gen(self.bot, "<:opt_in:944905885367537685>")
        stroop = partial_emoji_gen(self.bot, "<:stroop:961818095930978314>")
        cwl_emoji = partial_emoji_gen(self.bot, "<:cwlmedal:793561011801948160>")

        main = embed
        options = [  # the options in your dropdown
            disnake.SelectOption(label="Clan Overview", emoji=clan_e, value="clan"),
            disnake.SelectOption(label="Linked Players", emoji=emoji, value="link"),
            disnake.SelectOption(label="Unlinked Players", emoji=rx, value="unlink"),
            disnake.SelectOption(label="Players, Sorted: Trophies", emoji=trophy, value="trophies"),
            disnake.SelectOption(label="Players, Sorted: TH", emoji=self.bot.partial_emoji_gen(self.bot.fetch_emoji(14)), value="townhalls"),
            disnake.SelectOption(label="War Opt Statuses", emoji=opt, value="opt"),
            disnake.SelectOption(label="Super Troops", emoji=stroop, value="stroop"),
            disnake.SelectOption(label="CWL History", emoji=cwl_emoji, value="cwl")
        ]

        if clan.public_war_log:
            options.append(disnake.SelectOption(label="Warlog", emoji="ℹ️", value="warlog"))
        select = disnake.ui.Select(
            options=options,
            placeholder="Choose a page",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        await ctx.edit_original_message(embed=embed, components=dropdown)
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

            await res.response.defer()

            if res.values[0] == "link":
                embed = await self.linked_players(ctx, clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "unlink":
                embed = await self.unlinked_players(ctx, clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "trophies":
                embed = await self.player_trophy_sort(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "townhalls":
                embed = await self.player_townhall_sort(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "clan":
                await res.edit_original_message(embed=main)
            elif res.values[0] == "opt":
                embed = await self.opt_status(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "warlog":
                embed = await self.war_log(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "stroop":
                embed = await self.stroop_list(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "cwl":
                embed = await self.cwl_performance(clan)
                await res.edit_original_message(embed=embed)

    @clan.sub_command(name="player-links", description="List of un/linked players in clan")
    async def linked_clans(self, ctx: disnake.ApplicationCommandInteraction, clan):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()
        clan = await self.bot.getClan(clan)
        if clan is None or clan.member_count == 0:
            embed = disnake.Embed(description="Not a valid clan tag.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        embed = await self.linked_players(ctx, clan)
        embed2 = await self.unlinked_players(ctx, clan)
        embed2.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"linked_{clan.tag}"))
        await ctx.edit_original_message(embeds=[embed, embed2], components=buttons)

    @clan.sub_command(name="sorted-trophies", description="List of clan members, sorted by trophies")
    async def player_trophy(self, ctx: disnake.ApplicationCommandInteraction, clan):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        clan = await self.bot.getClan(clan)
        if clan is None or clan.member_count == 0:
            embed = disnake.Embed(description="Not a valid clan tag.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await self.player_trophy_sort(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"trophies_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="sorted-townhall", description="List of clan members, sorted by trophies")
    async def player_th(self, ctx: disnake.ApplicationCommandInteraction, clan):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        clan = await self.bot.getClan(clan)
        if clan is None or clan.member_count == 0:
            embed = disnake.Embed(description="Not a valid clan tag.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await self.player_townhall_sort(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"townhall_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="war-preferences", description="List of player's war preferences")
    async def war_opt(self, ctx: disnake.ApplicationCommandInteraction, clan):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        clan = await self.bot.getClan(clan)
        if clan is None or clan.member_count == 0:
            embed = disnake.Embed(description="Not a valid clan tag.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await self.opt_status(clan)
        embed.description += f"Last Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"waropt_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="war-log", description="List of clan's last 25 war win & losses")
    async def clan_war_log(self, ctx: disnake.ApplicationCommandInteraction, clan):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        clan = await self.bot.getClan(clan)
        if clan is None or clan.member_count == 0:
            embed = disnake.Embed(description="Not a valid clan tag.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        if not clan.public_war_log:
            embed = disnake.Embed(description="Clan has a private war log.",
                                  color=disnake.Color.red())
            embed.set_thumbnail(url=clan.badge.url)
            return await ctx.edit_original_message(embed=embed)

        embed = await self.war_log(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"warlog_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="super-troops", description="List of clan member's boosted & unboosted troops")
    async def clan_super_troops(self, ctx: disnake.ApplicationCommandInteraction, clan):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        clan = await self.bot.getClan(clan)
        if clan is None or clan.member_count == 0:
            embed = disnake.Embed(description="Not a valid clan tag.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed: disnake.Embed = await self.stroop_list(clan)
        values = embed.fields[0].value + f"\nLast Refreshed: <t:{int(time)}:R>"
        embed.set_field_at(0, name="**Not Boosting:**",value=values, inline=False)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"stroops_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="board", description="Simple embed, with overview of a clan")
    async def clan_board(self, ctx: disnake.ApplicationCommandInteraction, clan, button_text: str = None, button_link: str = None):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            button_text: can add an extra button to this board, this is the text for it
            button_link:can add an extra button to this board, this is the link for it
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        clan = await self.bot.getClan(clan)
        if clan is None or clan.member_count == 0:
            embed = disnake.Embed(description="Not a valid clan tag.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await self.clan_overview(ctx, clan)
        values = embed.fields[-1].value + f"\nLast Refreshed: <t:{int(time)}:R>"
        embed.set_field_at(len(embed.fields) - 1, name="**Boosted Super Troops:**", value=values, inline=False)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"clanboard_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(label=f"Clan Link", emoji="🔗",url=clan.share_link))
        if button_text is not None and button_link is not None:
            buttons.append_item(disnake.ui.Button(label=button_text, emoji="🔗", url=button_link))

        try:
            await ctx.edit_original_message(embed=embed, components=buttons)
        except disnake.errors.HTTPException:
            embed = disnake.Embed(description="Not a valid button link.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

    Weekends = commands.option_enum(create_weekends())
    @clan.sub_command(name="capital", description="See clan capital stats for a week")
    async def clan_capital(self, ctx: disnake.ApplicationCommandInteraction, clan: str, show_zeros=commands.Param(default="False", choices=["True", "False"]), weekend: Weekends = None):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            show_missing: Show those with zero donations/raids
            weekend: weekend to show stats for
        """
        show_zeros = show_zeros == "True"
        if weekend is None:
            weekend = self.bot.gen_raid_date()
        await ctx.response.defer()
        clan = await self.bot.getClan(clan)
        if clan is None or clan.member_count == 0:
            return await ctx.send("Not a valid clan tag.")
        clan_member_tags = [player.tag for player in clan.members]
        other_tags = []
        results = self.bot.player_stats.find({f"capital_gold.{weekend}.raided_clan": clan.tag})

        for result in await results.to_list(length=100):
            tag = result.get("tag")
            other_tags.append(tag)
        all_tags = list(set(clan_member_tags + other_tags))
        tasks = []
        for tag in all_tags:
            results = await self.bot.player_stats.find_one({"tag": tag})
            task = asyncio.ensure_future(self.bot.coc_client.get_player(player_tag=tag, cls=MyCustomPlayer, bot=self.bot, results=results))

            tasks.append(task)
        responses = await asyncio.gather(*tasks)
        donation_list = []
        raid_list = []
        data = []
        columns = ["Donated", "Number of Donations", "Raided" , "Number of Raids"]
        index = []
        for player in responses:
            player: MyCustomPlayer
            cc_stats = player.clan_capital_stats(week=weekend)
            name: str = player.name
            p_data = []
            index.append(name)
            for char in ["`", "*", "_", "~"]:
                name = name.replace(char, "", 10)
            if not show_zeros and player.clan_tag() == clan.tag and sum(cc_stats.donated) != 0:
                donation_text = f"{sum(cc_stats.donated)}".ljust(5)
                donation_list.append([f"{self.bot.emoji.capital_gold.emoji_string}`{donation_text}`: {name}", sum(cc_stats.donated)])

            elif show_zeros and player.clan_tag() == clan.tag:
                p_data.append(sum(cc_stats.donated))
                p_data.append(len(cc_stats.donated))
                donation_text = f"{sum(cc_stats.donated)}".ljust(5)
                donation_list.append([f"{self.bot.emoji.capital_gold.emoji_string}`{donation_text}`: {name}", sum(cc_stats.donated)])

            if clan.tag == cc_stats.raid_clan:
                if player.clan_tag() == clan.tag:
                    raid_text = f"{sum(cc_stats.raided)}".ljust(5)
                    num_raided = len(cc_stats.raided)
                    if num_raided > 6:
                        num_raided = "6"
                    raid_list.append([f"{self.bot.emoji.capital_gold.emoji_string}`{num_raided}/6 {raid_text}`: {name}", sum(cc_stats.raided)])

                else:
                    raid_text = f"{sum(cc_stats.raided)}".ljust(5)
                    num_raided = len(cc_stats.raided)
                    if num_raided > 6:
                        num_raided = "6"
                    raid_list.append([f"<:deny_mark:892770746034704384>`{num_raided}/6 {raid_text}`: {name}", sum(cc_stats.raided)])
                p_data.append(sum(cc_stats.raided))
                p_data.append(len(cc_stats.raided))

            elif show_zeros and cc_stats.raid_clan is None:
                raid_text = f"{0}".ljust(5)
                p_data.append(0)
                p_data.append(0)
                raid_list.append([f"{self.bot.emoji.capital_gold.emoji_string}`{0}/6 {raid_text}`: {name}", 0])
            data.append(p_data)

        donation_ranked = sorted(donation_list, key=lambda l: l[1], reverse=True)
        raids_ranked = sorted(raid_list, key=lambda l: l[1], reverse=True)
        donated_lines = [line[0] for line in donation_ranked]
        raid_lines = [line[0] for line in raids_ranked]
        if donated_lines == []:
            donated_lines = ["No Capital Gold Donated"]
        if raid_lines == []:
            raid_lines = ["No Capital Gold Raided"]
        raid_embed = self.bot.create_embeds(line_lists=raid_lines, title=f"**{clan.name} Raid Totals**", max_lines=50, thumbnail_url=clan.badge.url, footer=f"Week of {weekend} | {len(raid_lines)}/50")

        donation_embed = self.bot.create_embeds(line_lists=donated_lines, title="**Clan Capital Donations**", max_lines=50, thumbnail_url=clan.badge.url, footer=f"Week of {weekend} | {len(donated_lines)}/50")

        buttons = raid_buttons(self.bot, data)
        await ctx.edit_original_message(embed=raid_embed[0], components=buttons)
        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)

            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break
            await res.response.defer()
            if res.data.custom_id == "cg_dono":
                await res.edit_original_message(embed=donation_embed[0])
            elif res.data.custom_id == "cg_raid":
                await res.edit_original_message(embed=raid_embed[0])
            elif res.data.custom_id == "capseason":
                await res.edit_original_message(file=self.create_excel(columns=columns, index=index, data=data, weekend=weekend))

    def create_excel(self, columns, index, data, weekend):
        df = pd.DataFrame(data, index=index, columns=columns)
        df.to_excel('ClanCapitalStats.xlsx', sheet_name=f'{weekend}')
        return disnake.File("Family_and_Clans/ClanCapitalStats.xlsx", filename=f"{weekend}_ccstats")

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        time = datetime.now().timestamp()
        if "linked_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed = await self.linked_players(ctx, clan)
            embed2 = await self.unlinked_players(ctx, clan)
            embed2.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                                  custom_id=f"linked_{clan.tag}"))
            await ctx.edit_original_message(embeds=[embed, embed2], components=buttons)
        elif "trophies_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.player_trophy_sort(clan)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "waropt_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.opt_status(clan)
            embed.description += f"Last Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "warlog_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.war_log(clan)
            embed.description += f"Last Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "stroops_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.stroop_list(clan)
            values = embed.fields[0].value + f"\nLast Refreshed: <t:{int(time)}:R>"
            embed.set_field_at(0, name="**Not Boosting:**",value=values, inline=False)
            await ctx.edit_original_message(embed=embed)
        elif "clanboard_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.clan_overview(ctx, clan)
            values = embed.fields[-1].value + f"\nLast Refreshed: <t:{int(time)}:R>"
            embed.set_field_at(len(embed.fields) - 1, name="**Boosted Super Troops:**", value=values, inline=False)
            await ctx.edit_original_message(embed=embed)
        elif "townhall_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.player_townhall_sort(clan)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)


    @linked_clans.autocomplete("clan")
    @player_trophy.autocomplete("clan")
    @war_opt.autocomplete("clan")
    @clan_war_log.autocomplete("clan")
    @clan_super_troops.autocomplete("clan")
    @clan_board.autocomplete("clan")
    @getclan.autocomplete("clan")
    @clan_capital.autocomplete("clan")
    @player_th.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
            tracked = self.bot.clan_db.find({"server": ctx.guild.id})
            limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
            clan_list = []
            for tClan in await tracked.to_list(length=limit):
                name = tClan.get("name")
                tag = tClan.get("tag")
                if query.lower() in name.lower():
                        clan_list.append(f"{name} | {tag}")

            if clan_list == [] and len(query) >= 3:
                clan = await self.bot.getClan(query)
                if clan is None:
                    results = await self.bot.coc_client.search_clans(name=query, limit=5)
                    for clan in results:
                        league = str(clan.war_league).replace("League ", "")
                        clan_list.append(f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
                else:
                    clan_list.append(f"{clan.name} | {clan.tag}")
                    return clan_list
            return clan_list[0:25]