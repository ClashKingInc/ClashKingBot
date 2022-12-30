from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from utils.components import raid_buttons
from utils.discord_utils import partial_emoji_gen
from CustomClasses.CustomPlayer import MyCustomPlayer
from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands
from coc import utils

import Clan.ClanResponder as clan_responder
import Clan.ClanUtils as clan_utils
import coc
import disnake
import asyncio
import pytz
import calendar
tiz = pytz.utc
#import excel2img
import xlsxwriter
from ImageGen import ClanCapitalResult as capital_gen

#TODO- FIX CLAN GAMES SEASON CHOOSING

class ClanCommands(commands.Cog, name="Clan Commands"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    @commands.slash_command(name="clan")
    async def clan(self, ctx):
        await ctx.response.defer()

    @clan.sub_command(name="search", description="lookup clan by tag")
    async def get_clan(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Search by clan tag or select an option from the autocomplete
        """

        embed = disnake.Embed(
            description=f"<a:loading:884400064313819146> Fetching clan...",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

        db_clan = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})

        clan_legend_ranking = await self.bot.clan_leaderboard_db.find_one(
            {"tag": clan.tag})

        embed = await clan_responder.clan_overview(
            clan=clan, db_clan=db_clan,
            clan_legend_ranking=clan_legend_ranking, previous_season = self.bot.gen_previous_season_date(),
            season=self.bot.gen_season_date(), bot=self.bot)

        emoji = partial_emoji_gen(self.bot, "<:discord:840749695466864650>")
        rx = partial_emoji_gen(self.bot, "<:redtick:601900691312607242>")
        trophy = partial_emoji_gen(self.bot, "<:trophy:825563829705637889>")
        clan_e = partial_emoji_gen(
            self.bot, "<:clan_castle:855688168816377857>")
        opt = partial_emoji_gen(self.bot, "<:opt_in:944905885367537685>")
        stroop = partial_emoji_gen(self.bot, "<:stroop:961818095930978314>")
        cwl_emoji = partial_emoji_gen(
            self.bot, "<:cwlmedal:1037126610962362370>")

        main = embed

        # the options in your dropdown
        options = [
            disnake.SelectOption(
                label="Clan Overview",
                emoji=clan_e, value="clan"),
            disnake.SelectOption(
                label="Linked Players",
                emoji=emoji, value="link"),
            disnake.SelectOption(
                label="Unlinked Players",
                emoji=rx, value="unlink"),
            disnake.SelectOption(
                label="Players, Sorted: Trophies",
                emoji=trophy, value="trophies"),
            disnake.SelectOption(
                label="Players, Sorted: TH",
                emoji=self.bot.partial_emoji_gen(
                    self.bot.fetch_emoji(14)), value="townhalls"),
            disnake.SelectOption(
                label="War Opt Statuses",
                emoji=opt, value="opt"),
            disnake.SelectOption(
                label="Super Troops",
                emoji=stroop, value="stroop"),
            disnake.SelectOption(
                label="CWL History",
                emoji=cwl_emoji, value="cwl")
        ]

        if clan.public_war_log:
            options.append(disnake.SelectOption(
                label="Warlog", emoji="ℹ️", value="warlog"))
        select = disnake.ui.Select(
            options=options,
            # the placeholder text to show when no options have been chosen
            placeholder="Choose a page",
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
                res: disnake.MessageInteraction = await self.bot.wait_for(
                    "message_interaction", check=check, timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            await res.response.defer()

            if res.values[0] == "link":
                # initializing player link list
                clan_member_tags = [player.tag for player in clan.members]
                player_links = await self.bot.link_client.get_links(*clan_member_tags)
                linked_players_embed = clan_responder.linked_players(ctx.guild.members, clan, player_links)
                await res.edit_original_message(embed=linked_players_embed)

            elif res.values[0] == "unlink":
                # initializing player link list
                clan_member_tags = [player.tag for player in clan.members]
                player_links = await self.bot.link_client.get_links(*clan_member_tags)
                unlinked_players_embed = clan_responder.unlinked_players(clan, player_links)
                await res.edit_original_message(embed=unlinked_players_embed)

            elif res.values[0] == "trophies":
                embed = clan_responder.player_trophy_sort(clan)
                await res.edit_original_message(embed=embed)

            elif res.values[0] == "townhalls":
                embed = await clan_responder.player_townhall_sort(clan)
                await res.edit_original_message(embed=embed)

            elif res.values[0] == "clan":
                await res.edit_original_message(embed=main)

            elif res.values[0] == "opt":
                embed = await clan_responder.opt_status(clan)
                await res.edit_original_message(embed=embed)

            elif res.values[0] == "warlog":
                warlog = await self.bot.coc_client.get_warlog(clan.tag, limit=25)
                embed = clan_responder.war_log(clan, warlog)
                await res.edit_original_message(embed=embed)

            elif res.values[0] == "stroop":
                embed: disnake.Embed = await clan_responder.super_troop_list(clan)

                values = f"{embed.fields[0].value}\n"
                embed.set_field_at(
                    0, name="**Not Boosting:**",
                    value=values, inline=False)

                await res.edit_original_message(embed=embed)

            elif res.values[0] == "cwl":
                dates = await self.bot.coc_client.get_seasons(29000022)
                dates.append(self.bot.gen_season_date())
                dates = reversed(dates)
                embed = await clan_responder.cwl_performance(clan=clan, dates=dates)

                # embed = await self.cwl_performance(clan)
                await res.edit_original_message(embed=embed)

    @clan.sub_command(
        name="player-links",
        description="List of un/linked players in clan")
    async def linked_clans(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """

        # initializing player link list
        clan_member_tags = []
        for player in clan.members:
            clan_member_tags.append(player.tag)
        player_links = await self.bot.link_client.get_links(*clan_member_tags)

        linked_players_embed = clan_responder.linked_players(
            ctx.guild.members, clan, player_links)
        unlinked_players_embed = clan_responder.unlinked_players(
            clan, player_links)

        unlinked_players_embed.description += (
            f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"linked_{clan.tag}"))

        await ctx.edit_original_message(
            embeds=[linked_players_embed, unlinked_players_embed],
            components=buttons)

    @clan.sub_command(
        name="sorted-trophies",
        description="List of clan members, sorted by trophies")
    async def player_trophy(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """

        embed = clan_responder.player_trophy_sort(clan)
        embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"trophies_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(
        name="sorted-townhall",
        description="List of clan members, sorted by townhall")
    async def player_th(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """

        embed = await clan_responder.player_townhall_sort(clan)
        embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"townhall_{clan.tag}"))

        await ctx.edit_original_message(
            embed=embed, components=buttons)

    @clan.sub_command(
        name="war-preferences",
        description="List of player's war preferences")
    async def war_opt(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """

        embed = await clan_responder.opt_status(clan)
        embed.description += f"Last Refreshed: <t:{int(datetime.now().timestamp())}:R>"

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"waropt_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(
        name="war-log",
        description="List of clan's last 25 war win & losses")
    async def clan_war_log(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """

        if not clan.public_war_log:
            embed = disnake.Embed(
                description="Clan has a private war log.",
                color=disnake.Color.red())
            embed.set_thumbnail(url=clan.badge.url)
            return await ctx.edit_original_message(embed=embed)

        warlog = await self.bot.coc_client.get_warlog(clan.tag, limit=25)

        embed = clan_responder.war_log(clan, warlog)
        embed.description += (
            f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="",
            emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"warlog_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(
        name="super-troops",
        description="List of clan member's boosted & unboosted troops")
    async def clan_super_troops(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """

        embed: disnake.Embed = await clan_responder.super_troop_list(clan)

        values = (
            f"{embed.fields[0].value}\n"
            f"Last Refreshed: <t:{int(datetime.now().timestamp())}:R>")
        embed.set_field_at(
            0, name="**Not Boosting:**",
            value=values, inline=False)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"stroops_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(
        name="board",
        description="Simple embed, with overview of a clan")
    async def clan_board(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter),
            button_text: str = None, button_link: str = None):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            button_text: can add an extra button to this board, this is the text for it
            button_link:can add an extra button to this board, this is the link for it
        """

        db_clan = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})

        clan_legend_ranking = await self.bot.clan_leaderboard_db.find_one(
            {"tag": clan.tag})

        embed = await clan_responder.clan_overview(
            clan=clan, db_clan=db_clan,
            clan_legend_ranking=clan_legend_ranking, previous_season = self.bot.gen_previous_season_date(),
            season=self.bot.gen_season_date(), bot=self.bot)

        values = (
            f"{embed.fields[-1].value}"
            f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

        embed.set_field_at(len(
            embed.fields) - 1, name="**Boosted Super Troops:**",
            value=values, inline=False)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"clanboard_{clan.tag}"))

        buttons.append_item(disnake.ui.Button(
            label=f"Clan Link", emoji="🔗", url=clan.share_link))

        if button_text is not None and button_link is not None:
            buttons.append_item(disnake.ui.Button(
                label=button_text, emoji="🔗", url=button_link))

        try:
            await ctx.edit_original_message(
                embed=embed, components=buttons)

        except disnake.errors.HTTPException:
            embed = disnake.Embed(
                description="Not a valid button link.",
                color=disnake.Color.red())

            return await ctx.edit_original_message(embed=embed)

    @clan.sub_command(
        name="compo",
        description="Townhall composition of a clan")
    async def clan_compo(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """

        clan_members = []
        clan_members += [member.tag for member in clan.members]
        member_list = await self.bot.get_players(tags=clan_members, custom=False)

        embed = clan_responder.clan_th_composition(
            clan=clan, member_list=member_list)

        await ctx.edit_original_message(embed=embed)

    @clan.sub_command(
        name="capital",
        description=(
            "Get stats on raids & donations "
            "during selected time period"))
    async def clan_capital_stats(
            self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), weekend: str = commands.Param(default=None, name="weekend")):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        #await ctx.response.defer()
        if weekend is None:
            weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot)

        (raid_embed, total_looted, total_attacks) = clan_responder.clan_raid_weekend_raid_stats(clan=clan, raid_log_entry=weekend_raid_entry)
        donation_embed = await clan_responder.clan_raid_weekend_donation_stats(clan=clan, weekend=weekend, bot=self.bot)

        buttons = raid_buttons(self.bot, [])
        if "No raid found!" in raid_embed.description:
            await ctx.send(embed=donation_embed, components=buttons)
        else:
            if weekend_raid_entry.total_loot != 0:
                file = await capital_gen.generate_raid_result_image(raid_entry=weekend_raid_entry, clan=clan)
                raid_embed.set_image(file=file)
            await ctx.send(embed=raid_embed, components=buttons)

        '''
        data = []
        index = []

        for tag in member_tags:
            if not raid_weekends:
                looted = 0
                attacks = 0

            else:
                looted = total_looted[tag]
                attacks = total_attacks[tag]

            try:
                data.append([
                    tag, donated_data[tag],
                    number_donated_data[tag], looted, attacks])

            except:
                continue

            name = coc.utils.get(clan.members, tag=tag)
            index.append(name.name)
            
        
        buttons = raid_buttons(self.bot, data)

        if not raid_weekends:
            await ctx.edit_original_message(embed=embeds["donations"], components=buttons)

        else:
            await ctx.edit_original_message(embed=embeds["raids"], components=buttons)
        '''
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for(
                    "message_interaction", check=check, timeout=600)

            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break
            await res.response.defer()
            if res.data.custom_id == "donations":
                await res.edit_original_message(embed=donation_embed, attachments=[])

            elif res.data.custom_id == "raids":
                await res.edit_original_message(embed=raid_embed, attachments=[])


    @clan.sub_command(
        name="last-online",
        description="List of most recently online players in clan")
    async def last_online(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):

        member_tags = [member.tag for member in clan.members]
        members = await self.bot.get_players(
            tags=member_tags, custom=True)

        embed = clan_responder.create_last_online(
            clan=clan, clan_members=members)
        embed.description += (
            f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"lo_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(
        name="activities",
        description="Activity count of how many times a player has been seen online")
    async def activities(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), season=commands.Param(default=None, name="season")):
        member_tags = [member.tag for member in clan.members]
        members = await self.bot.get_players(tags=member_tags, custom=True)

        _season = ""
        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(month=int(month - 1), year=int(year))
            month = end_date.month
            if month <= 9:
                month = f"0{month}"

            season_date = f"{end_date.year}-{month}"
            _season = f"_{end_date.year}-{month}"

        else:
            season_date = self.bot.gen_season_date()

        embed = clan_responder.create_activities(clan=clan, clan_members=members, season=season_date, bot=self.bot)
        embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"act_{_season}_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(
        name="games",
        description="Points earned in clan games by clan members")
    async def clan_games(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter),
            season=commands.Param(default=None, name="season")):

        member_tags = [member.tag for member in clan.members]

        _season = ""
        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(
                month=int(month-1), year=int(year))
            month = end_date.month

            if month <= 9:
                month = f"0{month}"

            season_date = f"{end_date.year}-{month}"

            _season = f"_{end_date.year}-{month}"

        else:
            diff_days = datetime.utcnow().replace(tzinfo=tiz) - coc.utils.get_season_end().replace(tzinfo=tiz)
            if diff_days.days <= 3:
                sea = coc.utils.get_season_start().replace(tzinfo=tiz).date()
                season_date = f"{sea.year}-{sea.month}"
            else:
                season_date = clan_utils.gen_season_date()

        tags = await self.bot.player_stats.distinct(
            "tag", filter={f"clan_games.{season_date}.clan": clan.tag})
        all_tags = list(set(member_tags + tags))

        tasks = []
        for tag in all_tags:
            results = await self.bot.player_stats.find_one(
                {"tag": tag})

            task = asyncio.ensure_future(
                self.bot.coc_client.get_player(
                    player_tag=tag, cls=MyCustomPlayer,
                    bot=self.bot, results=results))

            tasks.append(task)

        player_responses = await asyncio.gather(*tasks)

        embed = clan_responder.create_clan_games(
            clan=clan, player_list=player_responses,
            member_tags=member_tags,
            season_date=season_date)

        embed.description += (
            f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"clangames{_season}_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(
        name="donations",
        description="Donations given & received by clan members")
    async def clan_donations(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter),
            season=commands.Param(default=None, name="season")):

        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(
                month=int(month-1), year=int(year))

            month = end_date.month
            if month <= 9:
                month = f"0{month}"
            _season = f"_{end_date.year}-{month}"
            season_date = f"{end_date.year}-{month}"

        else:
            _season = ""
            season_date = clan_utils.gen_season_date()

        tasks = []
        for member in clan.members:
            results = await self.bot.player_stats.find_one({"tag": member.tag})
            task = asyncio.ensure_future(
                self.bot.coc_client.get_player(
                    player_tag=member.tag, cls=MyCustomPlayer, bot=self.bot,
                    results=results))
            tasks.append(task)
        player_responses = await asyncio.gather(*tasks)

        embed = clan_responder.clan_donations(
            clan=clan, type="donated",
            season_date=season_date,
            player_list=player_responses
        )

        embed.description += (
            f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

        buttons = disnake.ui.ActionRow()

        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"donated{_season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(
            label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,
            style=disnake.ButtonStyle.green, custom_id=f"received{_season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(
            label="Ratio", emoji=self.bot.emoji.ratio.partial_emoji,
            style=disnake.ButtonStyle.green, custom_id=f"ratio{_season}_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(
        name='activity-graph',
        description="Get a graph showing average clan members on per an hour")
    async def activity_graph(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter),
            timezone=commands.Param(name="timezone")):

        if timezone not in pytz.common_timezones:
            return await ctx.edit_original_message(content=(
                "Not a valid timezone, please choose one of the 300+ "
                "options in the autocomplete"))

        file = await clan_utils.create_graph([clan], timezone=pytz.timezone(timezone), bot=self.bot)

        clan_tags = await self.bot.clan_db.distinct(
            "tag", filter={"server": ctx.guild.id})

        dropdown = []
        clan_dict = {}

        if clan_tags:
            clans = await self.bot.get_clans(tags=clan_tags)
            select_menu_options = []

            clans = sorted(
                clans, key=lambda x: x.member_count, reverse=True)

            for count, clan in enumerate(clans):
                clan_dict[clan.tag] = clan
                emoji = await self.bot.create_new_badge_emoji(
                    url=clan.badge.url)

                if count < 25:
                    select_menu_options.append(disnake.SelectOption(
                        label=clan.name,
                        emoji=self.bot.partial_emoji_gen(
                            emoji_string=emoji),
                        value=clan.tag))

            select = disnake.ui.Select(
                options=select_menu_options,
                # the placeholder text to show when no options have been chosen
                placeholder="Mix & Match Clans",
                min_values=1,  # the minimum number of options a user must select
                # the maximum number of options a user can select
                max_values=len(select_menu_options),
            )

            dropdown = [disnake.ui.ActionRow(select)]

        await ctx.edit_original_message(file=file, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for(
                    "message_interaction", check=check,
                    timeout=600)
            except:
                await msg.edit(components=[])
                break

            await res.response.defer()

            selected_clans = [clan_dict[value] for value in res.values]
            file = await clan_utils.create_graph(selected_clans, timezone=pytz.timezone(timezone), bot=self.bot)

            await res.edit_original_message(file=file, attachments=[])

    @clan.sub_command(
        name="war-stats",
        description="Get war stats of players in a clan")
    async def war_stats_clan(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter),
            season=commands.Param(default=None, name="season")):

        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            start_date = int(coc.utils.get_season_start(
                month=int(month-1), year=int(year)).timestamp())
            end_date = int(coc.utils.get_season_end(
                month=int(month-1), year=int(year)).timestamp())

        else:
            start_date = int(coc.utils.get_season_start().timestamp())
            end_date = int(coc.utils.get_season_end().timestamp())


        members = [member.tag for member in clan.members]
        players = await self.bot.get_players(tags=members, custom=True)
        off_hr_embed = await clan_responder.create_offensive_hitrate(bot=self.bot, clan=clan, players=players, start_timestamp=start_date,
                                                           end_timestamp=end_date)
        components = clan_responder.stat_components(bot=self.bot)
        await ctx.edit_original_message(embed=off_hr_embed, components=components)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        board_type = "Offensive Hitrate"
        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                return await msg.edit(components=[])
                break
            await res.response.defer()
            # is a list of th levels
            if res.values[0].isdigit():
                th_levels = [int(value) for value in res.values]
                if board_type == "Offensive Hitrate":
                    embed = await clan_responder.create_offensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                start_timestamp=start_date, end_timestamp=end_date,
                                                                townhall_level=th_levels)
                elif board_type == "Defensive Rate":
                    embed = await clan_responder.create_defensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                start_timestamp=start_date, end_timestamp=end_date,
                                                                townhall_level=th_levels)
                elif board_type == "Stars Leaderboard":
                    embed = await clan_responder.create_stars_leaderboard(clan=clan, players=players,
                                                                start_timestamp=start_date, end_timestamp=end_date,
                                                                townhall_level=th_levels)
                await res.edit_original_message(embed=embed)
            # is a filter type
            elif res.values[0] in ["Fresh Hits", "Non-Fresh", "random", "cwl", "friendly"]:
                fresh_type = [False, True]
                if "Non-Fresh" not in res.values:
                    fresh_type.remove(False)
                if "Fresh Hits" not in res.values:
                    fresh_type.remove(True)
                if fresh_type == []:
                    fresh_type = [False, True]
                war_types = ["random", "cwl", "friendly"]
                for type in ["random", "cwl", "friendly"]:
                    if type not in res.values:
                        war_types.remove(type)
                if war_types == []:
                    war_types = ["random", "cwl", "friendly"]
                if board_type == "Offensive Hitrate":
                    embed = await clan_responder.create_offensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                start_timestamp=start_date, end_timestamp=end_date,
                                                                fresh_type=fresh_type, war_types=war_types)
                elif board_type == "Defensive Rate":
                    embed = await clan_responder.create_defensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                start_timestamp=start_date, end_timestamp=end_date,
                                                                fresh_type=fresh_type, war_types=war_types)
                elif board_type == "Stars Leaderboard":
                    embed = await clan_responder.create_stars_leaderboard(clan=clan, players=players,
                                                                start_timestamp=start_date, end_timestamp=end_date,
                                                                fresh_type=fresh_type, war_types=war_types)
                await res.edit_original_message(embed=embed)
            # changing the board type
            elif res.values[0] in ["Offensive Hitrate", "Defensive Rate", "Stars Leaderboard"]:
                board_type = res.values[0]
                if board_type == "Offensive Hitrate":
                    embed = await clan_responder.create_offensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                start_timestamp=start_date, end_timestamp=end_date)
                elif board_type == "Defensive Rate":
                    embed = await clan_responder.create_defensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                start_timestamp=start_date, end_timestamp=end_date)
                elif board_type == "Stars Leaderboard":
                    embed = await clan_responder.create_stars_leaderboard(clan=clan, players=players,
                                                                start_timestamp=start_date, end_timestamp=end_date)
                await res.edit_original_message(embed=embed)



    @clan.sub_command(
        name="ping",
        description=(
            "Ping members in the clan "
            "based on different characteristics"))
    async def clan_ping(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):

        embed = disnake.Embed(
            description=(
                "Choose the characteristics you "
                "would like to ping for below:"),
            color=disnake.Color.green())

        options = []
        members = await self.bot.get_players(
            tags=[member.tag for member in clan.members])

        ths = set()

        # type: coc.Player
        for member in members:
            ths.add(member.town_hall)

        characteristic_types = [
            "War Opted In",  "War Opted Out",
            "War Attacks Remaining"] + [f"Townhall {th}" for th in list(ths)]

        for type in characteristic_types:
            options.append(disnake.SelectOption(label=type, value=type))

        select = disnake.ui.Select(
            options=options,
            # the placeholder text to show when no options have been chosen
            placeholder="Select Types to Ping",
            # the minimum number of options a user must select
            min_values=1,
            # the maximum number of options a user can select
            max_values=len(characteristic_types))

        dropdown = [disnake.ui.ActionRow(select)]

        await ctx.edit_original_message(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for(
                "message_interaction", check=check, timeout=600)

        except:
            return await msg.edit(components=[])

        await res.response.defer()

        to_ping = set()
        tag_to_name = {}
        tag_to_th = {}

        # type: coc.Player
        for player in members:
            tag_to_name[player.tag] = player.name
            tag_to_th[player.tag] = player.town_hall

            if f"Townhall {player.town_hall}" in res.values:
                to_ping.add(player.tag)

            if player.war_opted_in:
                if "War Opted In" in res.values:
                    to_ping.add(player.tag)

            if not player.war_opted_in:
                if "War Opted Out" in res.values:
                    to_ping.add(player.tag)

        if "War Attacks Remaining" in res.values:
            war: coc.ClanWar = await self.bot.get_clanwar(clan.tag)

            if war is not None:
                for war_member in war.clan.members:
                    if not war_member.attacks:
                        tag_to_name[war_member.tag] = war_member.name
                        tag_to_th[war_member.tag] = war_member.town_hall

                        to_ping.add(war_member.tag)

        links = await self.bot.link_client.get_links(*list(to_ping))

        # badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
        missing_text = ""
        for player_tag, discord_id in links:
            name = tag_to_name[player_tag]
            discord_member = disnake.utils.get(
                ctx.guild.members, id=discord_id)

            if discord_member is None:
                missing_text += (
                    f"{self.bot.fetch_emoji(tag_to_th[player_tag])}{name} | "
                    f"{player_tag}\n")

            else:
                missing_text += (
                    f"{self.bot.fetch_emoji(tag_to_th[player_tag])}{name} | "
                    f"{discord_member.mention}\n")

        if missing_text == "":
            missing_text = "No Players Found"

        await res.edit_original_message(
            embed=None,
            components=[],
            content=missing_text)



    '''    @clan.sub_command(name="export", description="Export info about this clan")
    async def clan_export(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        (image, file) = await self.create_war_export(clan)
        await ctx.edit_original_message(files=[image, file])


    async def create_last_season_trophies_export(self, ctx, clan):
        workbook = xlsxwriter.Workbook(f'ExportInfo/{clan.tag}_last_season_end.xlsx')
        worksheet = workbook.add_worksheet("Legend_Trophies")

        background_color = "white"
        letter_color = "black"
        bold = workbook.add_format(
            {"font_color": letter_color, 'bold': True, "bg_color": background_color, "align": "center"})
        center = workbook.add_format({"font_color": letter_color, "align": "center", "bg_color": background_color})
        perc_hr = workbook.add_format({"font_color": letter_color, 'num_format': '0.0%', "bg_color": background_color})
        blue_letters = workbook.add_format({"font_color": "blue", "bg_color": background_color})
        white_back = workbook.add_format({"font_color": letter_color, "bg_color": background_color})
        gold_letters = workbook.add_format({"align": "center", "font_color": "orange", "bg_color": background_color})
        row = 0
        col = 0

        types = ["Rank", "TH", "Name", "Trophies"]

        length_list = [len(x) for x in types]
        for i, width in enumerate(length_list):
            worksheet.set_column(i, i, width)

        all_players_info = [types]
        clan_members: list[coc.Player] = await self.bot.get_players(tags=[member.tag for member in clan.members])

        sort_list = []
        for player in clan_members:
            try:
                id = player.legend_statistics.previous_season.id
                start = utils.get_season_start().replace(tzinfo=tiz).date()
                mon = start.month
                if mon <= 9:
                    mon = f"0{mon}"
                season = f"{start.year}-{mon}"
                if str(id) != season:
                    continue
                legend_trophies = player.legend_statistics.previous_season.trophies
                sort_list.append([player.name, player, legend_trophies])
            except:
                continue

        sort_list = sorted(sort_list, key=lambda l: (-l[-1], l[0]), reverse=False)
        clan_members = [member[1] for member in sort_list]

        longest_name = 0
        for rank, player in enumerate(clan_members, 1):
            player_info = [rank, player.town_hall, player.name, player.legend_statistics.previous_season.trophies]
            longest_name = max(longest_name, len(player.name))
            all_players_info.append(player_info)

        worksheet.set_column(2, 2, longest_name + 1)
        for data in all_players_info:
            for item in data:
                if row != 0:
                    if col == 0:
                        worksheet.write(row, col, item, gold_letters)
                    elif col == 1:
                        worksheet.write(row, col, item, blue_letters)
                    elif col == 2:
                        worksheet.write(row, col, item, white_back)
                    elif col == 3:
                        worksheet.write(row, col, item, center)
                else:
                    worksheet.write(row, col, item, bold)
                col += 1
            row += 1
            col = 0

        workbook.close()
        file = disnake.File(f'ExportInfo/{clan.tag}_last_season_end.xlsx', filename=f"{clan.name}_last_season_end.xlsx")
        excel2img.export_img(f'ExportInfo/{clan.tag}_last_season_end.xlsx',
                             f"ExportInfo/{clan.tag}_last_season_end.png", "",
                             f"Legend_Trophies!A1:D{min(len(clan_members) + 1, 50)}")
        image = disnake.File(f'ExportInfo/{clan.tag}_last_season_end.png', filename=f"text.png")
        await ctx.edit_original_message(files=[image, file])

    async def create_member_export(self, ctx, clan):
        num = random.randint(1, 10)
        workbook = xlsxwriter.Workbook(f'member_export{num}.xlsx')
        worksheet = workbook.add_worksheet()
        bold = workbook.add_format({'bold': True})

        row = 0
        col = 0

        types = ["Name", "TH"]
        for hero in coc.HERO_ORDER:
            types.append(hero)
        for troop in coc.HOME_TROOP_ORDER:
            types.append(troop)

        length_list = [len(x) for x in types]
        for i, width in enumerate(length_list):
            worksheet.set_column(i, i, width)

        all_players_info = [types]
        clan_members: list[coc.Player] = await self.bot.get_players(tags=[member.tag for member in clan.members])
        longest_name = 0
        for player in clan_members:
            player_info = [player.name, player.town_hall]
            longest_name = max(longest_name, len(player.name))
            for hero_name in coc.HERO_ORDER:
                hero = player.get_hero(name=hero_name)
                if hero is None:
                    hero_level = 0
                else:
                    hero_level = hero.level
                player_info.append(hero_level)

            for troop_name in coc.HOME_TROOP_ORDER:
                troop = player.get_troop(name=troop_name)
                if troop is None:
                    troop_level = 0
                else:
                    troop_level = troop.level
                player_info.append(troop_level)

            all_players_info.append(player_info)

        worksheet.set_column(0, 0, longest_name + 1)
        for data in all_players_info:
            for item in data:
                if col != 0 and row != 0:
                    worksheet.write(row, col, item)
                else:
                    worksheet.write(row, col, item, bold)
                col += 1
            row += 1
            col = 0

        workbook.close()
        file = disnake.File(f'member_export{num}.xlsx', filename=f"{clan.name}_member_stats.xlsx")
        await ctx.edit_original_message(file=file)

    async def create_war_export(self, clan):
        workbook = xlsxwriter.Workbook(f'ExportInfo/war_stats{clan.tag}.xlsx')

        clan_members: list[MyCustomPlayer] = await self.bot.get_players(tags=[member.tag for member in clan.members], custom=True)
        worksheet = workbook.add_worksheet("Hitrates")

        await self.create_war_hitrate(clan_members=clan_members, workbook=workbook, worksheet=worksheet)
        await self.create_war_defrate(clan_members=clan_members, workbook=workbook, worksheet=worksheet)
        await self.create_war_starlb(clan_members=clan_members, workbook=workbook, worksheet=worksheet)


        workbook.close()
        file = disnake.File(f'ExportInfo/war_stats{clan.tag}.xlsx', filename=f"{clan.name}_war_stats.xlsx")
        excel2img.export_img(f'ExportInfo/war_stats{clan.tag}.xlsx', f"ExportInfo/war_stats{clan.tag}.png", "", f"Hitrates!A1:T{min(len(clan_members) + 1, 26)}")
        image = disnake.File(f'ExportInfo/war_stats{clan.tag}.png', filename=f"test.png")
        return (image, file)

    async def create_war_hitrate(self, clan_members, workbook, worksheet):
        background_color = "white"
        letter_color = "black"
        bold = workbook.add_format(
            {"font_color": letter_color, 'bold': True, "bg_color": background_color, "align": "center"})
        center = workbook.add_format({"font_color": letter_color, "align": "center", "bg_color": background_color})
        perc_hr = workbook.add_format({"font_color": letter_color, 'num_format': '0.0%', "bg_color": background_color})
        blue_letters = workbook.add_format({"font_color": "blue", "bg_color": background_color})
        white_back = workbook.add_format({"font_color": letter_color, "bg_color": background_color})
        gold_letters = workbook.add_format({"align": "center", "font_color": "orange", "bg_color": background_color})
        row = 0
        col = 0

        types = ["Rank", "TH", "Name", "  Total  ", "  3★  ", "Total Stars"]

        length_list = [len(x) for x in types]
        for i, width in enumerate(length_list):
            worksheet.set_column(i, i, width)

        all_players_info = [types]

        sort_list = []
        player_hr = {}
        for player in clan_members:
            hitrate = await player.hit_rate()
            hitrate = hitrate[0]

            sort_list.append(
                [player.name, player, hitrate.average_triples])
            player_hr[player.tag] = hitrate

        hitrate_sort_list = sorted(sort_list, key=lambda l: (-l[-1], l[0]), reverse=False)
        hitrate_clan_members = [member[1] for member in hitrate_sort_list]

        longest_name = 0
        for rank, player in enumerate(hitrate_clan_members, 1):
            hitrate = player_hr[player.tag]
            player_info = [rank, player.town_hall, player.name, f"{hitrate.total_triples}/{hitrate.num_attacks}",
                           hitrate.average_triples, hitrate.total_stars]
            longest_name = max(longest_name, len(player.name))
            all_players_info.append(player_info)

        worksheet.set_column(2, 2, longest_name + 1)
        for data in all_players_info:
            for item in data:
                if row != 0:
                    if col == 0:
                        worksheet.write(row, col, item, gold_letters)
                    elif col == 1:
                        worksheet.write(row, col, item, blue_letters)
                    elif col == 2:
                        worksheet.write(row, col, item, white_back)
                    elif col == 3:
                        worksheet.write(row, col, item, center)
                    elif col == 4:
                        worksheet.write(row, col, item, perc_hr)
                    elif col == 5:
                        worksheet.write(row, col, item, center)
                else:
                    worksheet.write(row, col, item, bold)
                col += 1
            row += 1
            col = 0

    async def create_war_defrate(self, clan_members, workbook, worksheet):
        background_color = "white"
        letter_color = "black"
        bold = workbook.add_format(
            {"font_color": letter_color, 'bold': True, "bg_color": background_color, "align": "center"})
        center = workbook.add_format({"font_color": letter_color, "align": "center", "bg_color": background_color})
        perc_hr = workbook.add_format({"font_color": letter_color, 'num_format': '0.0%', "bg_color": background_color})
        blue_letters = workbook.add_format({"font_color": "blue", "bg_color": background_color})
        white_back = workbook.add_format({"font_color": letter_color, "bg_color": background_color})
        gold_letters = workbook.add_format({"align": "center", "font_color": "orange", "bg_color": background_color})
        row = 0
        col = 7
        og_col = 7

        types = ["Rank", "TH", "Name", "  Total  ", "  DR  ", "Total Stars"]

        length_list = [len(x) for x in types]
        for i, width in enumerate(length_list):
            worksheet.set_column(i + og_col, i + og_col, width)

        all_players_info = [types]

        sort_list = []
        player_dr = {}
        for player in clan_members:
            defense_rate = await player.defense_rate()
            defense_rate = defense_rate[0]
            if defense_rate.num_attacks == 0:
                continue
            sort_list.append(
                [player.name, player, defense_rate.average_triples, round(100 - (defense_rate.average_triples * 100), 1)])
            player_dr[player.tag] = defense_rate

        def_rate_sort_list = sorted(sort_list, key=lambda l: (-l[-2], l[0]), reverse=False)
        def_rate_clan_members = [member[1] for member in def_rate_sort_list]

        longest_name = 0
        for rank, player in enumerate(def_rate_clan_members, 1):
            def_rate = player_dr[player.tag]
            player_info = [rank, player.town_hall, player.name, f"{def_rate.total_triples}/{def_rate.num_attacks}",
                           def_rate.average_triples, def_rate.total_stars]
            longest_name = max(longest_name, len(player.name))
            all_players_info.append(player_info)

        worksheet.set_column(og_col + 2, og_col + 2, longest_name + 1)
        for data in all_players_info:
            for item in data:
                if row != 0:
                    if col == og_col:
                        worksheet.write(row, col, item, gold_letters)
                    elif col == og_col + 1:
                        worksheet.write(row, col, item, blue_letters)
                    elif col == og_col + 2:
                        worksheet.write(row, col, item, white_back)
                    elif col == og_col + 3:
                        worksheet.write(row, col, item, center)
                    elif col == og_col + 4:
                        worksheet.write(row, col, item, perc_hr)
                    elif col == og_col + 5:
                        worksheet.write(row, col, item, center)
                else:
                    worksheet.write(row, col, item, bold)
                col += 1
            row += 1
            col = og_col

    async def create_war_starlb(self, clan_members, workbook, worksheet):
        background_color = "white"
        letter_color = "black"
        bold = workbook.add_format(
            {"font_color": letter_color, 'bold': True, "bg_color": background_color, "align": "center"})
        center = workbook.add_format({"font_color": letter_color, "align": "center", "bg_color": background_color})
        perc_hr = workbook.add_format({"font_color": letter_color, 'num_format': '0.0%', "bg_color": background_color})
        blue_letters = workbook.add_format({"font_color": "blue", "bg_color": background_color})
        white_back = workbook.add_format({"font_color": letter_color, "bg_color": background_color})
        gold_letters = workbook.add_format({"align": "center", "font_color": "orange", "bg_color": background_color})
        row = 0
        col = 14
        og_col = 14

        types = ["Rank", "TH", "Name", "Stars", "Attacks", "Triples"]

        length_list = [len(x) for x in types]
        for i, width in enumerate(length_list):
            worksheet.set_column(i + og_col, i + og_col, width)

        all_players_info = [types]

        sort_list = []
        player_hr = {}
        for player in clan_members:
            hit_rate = await player.hit_rate()
            hit_rate = hit_rate[0]

            sort_list.append(
                [player.name, player, hit_rate.total_stars])
            player_hr[player.tag] = hit_rate

        star_sort_list = sorted(sort_list, key=lambda l: (-l[-1], l[0]), reverse=False)
        star_clan_members = [member[1] for member in star_sort_list]

        longest_name = 0
        for rank, player in enumerate(star_clan_members, 1):
            hit_rate = player_hr[player.tag]
            player_info = [rank, player.town_hall, player.name, hit_rate.total_stars, hit_rate.num_attacks, hit_rate.total_triples]
            longest_name = max(longest_name, len(player.name))
            all_players_info.append(player_info)

        worksheet.set_column(og_col + 2, og_col + 2, longest_name + 1)
        for data in all_players_info:
            for item in data:
                if row != 0:
                    if col == og_col:
                        worksheet.write(row, col, item, gold_letters)
                    elif col == og_col + 1:
                        worksheet.write(row, col, item, blue_letters)
                    elif col == og_col + 2:
                        worksheet.write(row, col, item, white_back)
                    elif col == og_col + 3:
                        worksheet.write(row, col, item, center)
                    elif col == og_col + 4:
                        worksheet.write(row, col, item, center)
                    elif col == og_col + 5:
                        worksheet.write(row, col, item, center)
                else:
                    worksheet.write(row, col, item, bold)
                col += 1
            row += 1
            col = og_col
    '''


    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        time = datetime.now().timestamp()
        if "linked_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            # initializing player link list
            clan_member_tags = []
            for player in clan.members:
                clan_member_tags.append(player.tag)
            player_links = await self.bot.link_client.get_links(*clan_member_tags)

            linked_players_embed = clan_responder.linked_players(
                ctx.guild.members, clan, player_links)
            unlinked_players_embed = clan_responder.unlinked_players(
                clan, player_links)

            unlinked_players_embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey, custom_id=f"linked_{clan.tag}"))

            await ctx.edit_original_message(
                embeds=[linked_players_embed, unlinked_players_embed],
                components=buttons)

        elif "trophies_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            embed = clan_responder.player_trophy_sort(clan)
            embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"trophies_{clan.tag}"))

            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "waropt_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            embed = await clan_responder.opt_status(clan)
            embed.description += f"Last Refreshed: <t:{int(datetime.now().timestamp())}:R>"

            await ctx.edit_original_message(embed=embed)

        elif "warlog_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            warlog = await self.bot.coc_client.get_warlog(clan.tag, limit=25)

            embed = clan_responder.war_log(clan, warlog)
            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "stroops_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            embed: disnake.Embed = await clan_responder.super_troop_list(clan)

            values = (
                f"{embed.fields[0].value}\n"
                f"Last Refreshed: <t:{int(datetime.now().timestamp())}:R>")
            embed.set_field_at(
                0, name="**Not Boosting:**",
                value=values, inline=False)

            await ctx.edit_original_message(embed=embed)

        elif "clanboard_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            db_clan = await self.bot.clan_db.find_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]})

            clan_legend_ranking = await self.bot.clan_leaderboard_db.find_one(
                {"tag": clan.tag})

            embed = await clan_responder.clan_overview(
            clan=clan, db_clan=db_clan,
            clan_legend_ranking=clan_legend_ranking, previous_season = self.bot.gen_previous_season_date(),
            season=self.bot.gen_season_date(), bot=self.bot)

            values = (
                f"{embed.fields[-1].value}"
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            embed.set_field_at(len(
                embed.fields) - 1, name="**Boosted Super Troops:**",
                value=values, inline=False)

            await ctx.edit_original_message(embed=embed)

        elif "townhall_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            embed = await clan_responder.player_townhall_sort(clan)
            embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

            await ctx.edit_original_message(embed=embed)

        elif "lo_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            member_tags = [member.tag for member in clan.members]
            members = await self.bot.get_players(
                tags=member_tags, custom=True)

            embed = clan_responder.create_last_online(
                clan=clan, clan_members=members)
            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "clangames_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]
            else:
                diff_days = datetime.utcnow().replace(tzinfo=tiz) - coc.utils.get_season_end().replace(tzinfo=tiz)
                if diff_days.days <= 3:
                    sea = coc.utils.get_season_start().replace(tzinfo=tiz).date()
                    season_date = f"{sea.year}-{sea.month}"
                else:
                    season_date = clan_utils.gen_season_date()

            member_tags = [member.tag for member in clan.members]

            tags = await self.bot.player_stats.distinct(
                "tag", filter={f"clan_games.{season_date}.clan": clan.tag})
            all_tags = list(set(member_tags + tags))

            tasks = []
            for tag in all_tags:
                results = await self.bot.player_stats.find_one(
                    {"tag": tag})

                task = asyncio.ensure_future(
                    self.bot.coc_client.get_player(
                        player_tag=tag, cls=MyCustomPlayer,
                        bot=self.bot, results=results))

                tasks.append(task)

            player_responses = await asyncio.gather(*tasks)

            embed = clan_responder.create_clan_games(
                clan=clan, player_list=player_responses,
                member_tags=member_tags,
                season_date=season_date)

            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "donated_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]

            else:
                season_date = clan_utils.gen_season_date()

            tasks = []
            for member in clan.members:
                results = await self.bot.player_stats.find_one({"tag": member.tag})
                task = asyncio.ensure_future(
                    self.bot.coc_client.get_player(
                        player_tag=member.tag, cls=MyCustomPlayer, bot=self.bot,
                        results=results))
                tasks.append(task)
            player_responses = await asyncio.gather(*tasks)

            embed = clan_responder.clan_donations(
                clan=clan, type="donated",
                season_date=season_date,
                player_list=player_responses)

            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "received_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]

            else:
                season_date = clan_utils.gen_season_date()

            tasks = []
            for member in clan.members:
                results = await self.bot.player_stats.find_one({"tag": member.tag})
                task = asyncio.ensure_future(
                    self.bot.coc_client.get_player(
                        player_tag=member.tag, cls=MyCustomPlayer, bot=self.bot,
                        results=results))
                tasks.append(task)
            player_responses = await asyncio.gather(*tasks)

            embed = clan_responder.clan_donations(
                clan=clan, type="received",
                season_date=season_date,
                player_list=player_responses)

            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "ratio_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]

            else:
                season_date = clan_utils.gen_season_date()

            tasks = []
            for member in clan.members:
                results = await self.bot.player_stats.find_one({"tag": member.tag})
                task = asyncio.ensure_future(
                    self.bot.coc_client.get_player(
                        player_tag=member.tag, cls=MyCustomPlayer, bot=self.bot,
                        results=results))
                tasks.append(task)
            player_responses = await asyncio.gather(*tasks)

            embed = clan_responder.clan_donations(
                clan=clan, type="ratio",
                season_date=season_date,
                player_list=player_responses)

            embed.description += (
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            await ctx.edit_original_message(embed=embed)

        elif "act_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]
            else:
                season_date = clan_utils.gen_season_date()

            member_tags = [member.tag for member in clan.members]
            members = await self.bot.get_players(
                tags=member_tags, custom=True)

            embed = clan_responder.create_activities(
                clan=clan, clan_members=members, season=season_date, bot=self.bot)

            embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

            await ctx.edit_original_message(embed=embed)

    @war_stats_clan.autocomplete("season")
    @clan_donations.autocomplete("season")
    @clan_games.autocomplete("season")
    @activities.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]

    @clan_capital_stats.autocomplete("weekend")
    async def weekend(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        weekends = gen_raid_weekend_datestrings(number_of_weeks=25)
        matches = []
        for weekend in weekends:
            if query.lower() in weekend.lower():
                matches.append(weekend)
        return matches

    @linked_clans.autocomplete("clan")
    @player_trophy.autocomplete("clan")
    @war_opt.autocomplete("clan")
    @clan_war_log.autocomplete("clan")
    @clan_super_troops.autocomplete("clan")
    @clan_board.autocomplete("clan")
    @get_clan.autocomplete("clan")
    @clan_capital_stats.autocomplete("clan")
    @player_th.autocomplete("clan")
    @clan_compo.autocomplete("clan")
    @last_online.autocomplete("clan")
    @clan_games.autocomplete("clan")
    @clan_donations.autocomplete("clan")
    @activity_graph.autocomplete("clan")
    @war_stats_clan.autocomplete("clan")
    @activities.autocomplete("clan")
    @clan_ping.autocomplete("clan")
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
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]

    @activity_graph.autocomplete("timezone")
    async def timezone_autocomplete(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        all_tz = pytz.common_timezones
        return_list = []
        for tz in all_tz:
            if query.lower() in tz.lower():
                return_list.append(tz)
        return return_list[:25]


