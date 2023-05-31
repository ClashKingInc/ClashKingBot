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
# import excel2img
import xlsxwriter
from ImageGen import ClanCapitalResult as capital_gen

from utils.constants import item_to_name

# TODO- FIX CLAN GAMES SEASON CHOOSING

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


    @clan.sub_command(name="sorted",description="List of clan members, sorted by any attribute")
    async def player_trophy(self, ctx: disnake.ApplicationCommandInteraction,clan: coc.Clan = commands.Param(converter=clan_converter),
                            sort_by: str = commands.Param(choices=sorted(item_to_name.keys()))):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            sort_by: Sort by any attribute
        """

        players: list[coc.Player] = await self.bot.get_players(tags=[member.tag for member in clan.members], custom=False)
        embed = await self.clan_sort(players=players, clan=clan, sort_by=sort_by)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"clansort-{clan.tag}-{sort_by}"))

        await ctx.edit_original_message(embed=embed, components=[buttons])




    @clan.sub_command(name="board", description="Simple embed, with overview of a clan")
    async def clan_board(self, ctx: disnake.ApplicationCommandInteraction,clan: coc.Clan = commands.Param(converter=clan_converter),
                         auto_refresh = commands.Param(default=False, choices=["True"]),
                         simple=commands.Param(default=False, choices=["True"]),
                         button_text: str = None, button_link: str = None, image: disnake.Attachment = None):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            auto_refresh: Have this embed refresh, you can only have one of these per a clan per a server
            button_text: can add an extra button to this board, this is the text for it
            button_link:can add an extra button to this board, this is the link for it
            image: image to add to embed
            simple: a more simple embed style with less info
        """

        if not ctx.author.guild_permissions.manage_guild:
            auto_refresh = False

        db_clan = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})

        clan_legend_ranking = await self.bot.clan_leaderboard_db.find_one(
            {"tag": clan.tag})

        if not simple:
            embed = await clan_responder.clan_overview(
                clan=clan, db_clan=db_clan,
                clan_legend_ranking=clan_legend_ranking, previous_season=self.bot.gen_previous_season_date(),
                season=self.bot.gen_season_date(), bot=self.bot)
        else:
            embed = None

        embed.timestamp = datetime.now()

        if image is not None:
            embed.set_image(url=image.url)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"clanboard_{clan.tag}"))

        buttons.append_item(disnake.ui.Button(label=f"Clan Link", emoji="🔗", url=clan.share_link))

        if button_text is not None and button_link is not None:
            buttons.append_item(disnake.ui.Button(label=button_text, emoji="🔗", url=button_link))

        try:
            await ctx.edit_original_message(content="Sent")
            msg = await ctx.original_message()
            await msg.delete()
            await ctx.channel.send(embed=embed, components=buttons)
        except disnake.errors.HTTPException:
            embed = disnake.Embed(description="Not a valid button link.",color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

    @clan.sub_command(name="compo",description="Townhall composition of a clan")
    async def clan_compo(self, ctx: disnake.ApplicationCommandInteraction,clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        clan_members = [member.tag for member in clan.members]
        member_list = await self.bot.get_players(tags=clan_members, custom=False)
        embed = clan_responder.clan_th_composition(clan=clan, member_list=member_list)
        await ctx.edit_original_message(embed=embed)

    @clan.sub_command(name="capital", description="Get stats on raids & donations during selected time period")
    async def clan_capital_stats(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
            weekend: str = commands.Param(default=None, name="weekend")):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        # await ctx.response.defer()
        limit = 25
        if weekend is None:
            limit = 2
            weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot, limit=limit)

        (raid_embed, total_looted, total_attacks) = clan_responder.clan_raid_weekend_raid_stats(clan=clan,
                                                                                                raid_log_entry=weekend_raid_entry)
        donation_embed = await clan_responder.clan_raid_weekend_donation_stats(clan=clan, weekend=weekend, bot=self.bot)

        buttons = raid_buttons(self.bot, [])
        if "No raid found!" in raid_embed.description:
            await ctx.send(embed=donation_embed, components=buttons)
        else:
            if weekend_raid_entry.total_loot != 0:
                file = await capital_gen.generate_raid_result_image(raid_entry=weekend_raid_entry, clan=clan)
                raid_embed.set_image(file=file)
            await ctx.send(embed=raid_embed, components=buttons)

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

    @clan.sub_command(name="last-online",description="List of most recently online players in clan")
    async def last_online(self, ctx: disnake.ApplicationCommandInteraction,clan: coc.Clan = commands.Param(converter=clan_converter)):

        member_tags = [member.tag for member in clan.members]
        members = await self.bot.get_players(tags=member_tags, custom=True)

        embed = clan_responder.create_last_online(clan=clan, clan_members=members)
        embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"lo_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="activities",description="Activity count of how many times a player has been seen online")
    async def activities(self, ctx: disnake.ApplicationCommandInteraction,clan: coc.Clan = commands.Param(converter=clan_converter),season=commands.Param(default=None, name="season")):
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

    @clan.sub_command(name="games", description="Points earned in clan games by clan members")
    async def clan_games(self, ctx: disnake.ApplicationCommandInteraction,clan: coc.Clan = commands.Param(converter=clan_converter),
            season=commands.Param(default=None, name="season")):

        member_tags = [member.tag for member in clan.members]

        _season = ""
        if season is not None:
            month = int(list(calendar.month_name).index(season.split(" ")[0]))
            year = season.split(" ")[1]

            if month <= 9:
                month = f"0{month}"

            season_date = f"{year}-{month}"
            _season = f"_{year}-{month}"

        else:
            season_date = self.bot.gen_games_season()

        tags = await self.bot.player_stats.distinct("tag", filter={f"clan_games.{season_date}.clan": clan.tag})
        all_tags = list(set(member_tags + tags))

        players = await self.bot.get_players(tags=all_tags)

        embed = clan_responder.create_clan_games(
            clan=clan, player_list=players,
            member_tags=member_tags,
            season_date=season_date)

        embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"clangames{_season}_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="donations", description="Donations given & received by clan members")
    async def clan_donations(self, ctx: disnake.ApplicationCommandInteraction,clan: coc.Clan = commands.Param(converter=clan_converter), season=commands.Param(default=None, name="season")):

        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(
                month=int(month - 1), year=int(year))

            month = end_date.month
            if month <= 9:
                month = f"0{month}"
            _season = f"_{end_date.year}-{month}"
            season_date = f"{end_date.year}-{month}"

        else:
            _season = ""
            season_date = clan_utils.gen_season_date()

        player_responses = await self.bot.get_players(tags=[member.tag for member in clan.members])

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

    @clan.sub_command(name='activity-graph',description="Get a graph showing average clan members on per an hour")
    async def activity_graph(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), timezone=commands.Param(name="timezone")):

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

    @clan.sub_command(name="war-stats",description="Get war stats of players in a clan")
    async def war_stats_clan(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter),
            season=commands.Param(default=None, name="season")):

        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            start_date = int(coc.utils.get_season_start(
                month=int(month - 1), year=int(year)).timestamp())
            end_date = int(coc.utils.get_season_end(
                month=int(month - 1), year=int(year)).timestamp())

        else:
            start_date = int(coc.utils.get_season_start().timestamp())
            end_date = int(coc.utils.get_season_end().timestamp())

        members = [member.tag for member in clan.members]
        players = await self.bot.get_players(tags=members, custom=True)
        off_hr_embed = await clan_responder.create_offensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                     start_timestamp=start_date,
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
                                                                          start_timestamp=start_date,
                                                                          end_timestamp=end_date,
                                                                          townhall_level=th_levels)
                elif board_type == "Defensive Rate":
                    embed = await clan_responder.create_defensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                          start_timestamp=start_date,
                                                                          end_timestamp=end_date,
                                                                          townhall_level=th_levels)
                elif board_type == "Stars Leaderboard":
                    embed = await clan_responder.create_stars_leaderboard(clan=clan, players=players,
                                                                          start_timestamp=start_date,
                                                                          end_timestamp=end_date,
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
                                                                          start_timestamp=start_date,
                                                                          end_timestamp=end_date,
                                                                          fresh_type=fresh_type, war_types=war_types)
                elif board_type == "Defensive Rate":
                    embed = await clan_responder.create_defensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                          start_timestamp=start_date,
                                                                          end_timestamp=end_date,
                                                                          fresh_type=fresh_type, war_types=war_types)
                elif board_type == "Stars Leaderboard":
                    embed = await clan_responder.create_stars_leaderboard(clan=clan, players=players,
                                                                          start_timestamp=start_date,
                                                                          end_timestamp=end_date,
                                                                          fresh_type=fresh_type, war_types=war_types)
                await res.edit_original_message(embed=embed)
            # changing the board type
            elif res.values[0] in ["Offensive Hitrate", "Defensive Rate", "Stars Leaderboard"]:
                board_type = res.values[0]
                if board_type == "Offensive Hitrate":
                    embed = await clan_responder.create_offensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                          start_timestamp=start_date,
                                                                          end_timestamp=end_date)
                elif board_type == "Defensive Rate":
                    embed = await clan_responder.create_defensive_hitrate(bot=self.bot, clan=clan, players=players,
                                                                          start_timestamp=start_date,
                                                                          end_timestamp=end_date)
                elif board_type == "Stars Leaderboard":
                    embed = await clan_responder.create_stars_leaderboard(clan=clan, players=players,
                                                                          start_timestamp=start_date,
                                                                          end_timestamp=end_date)
                await res.edit_original_message(embed=embed)

    @clan.sub_command(name="ping",description="Ping members in the clan based on different characteristics")
    async def clan_ping(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):

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
                                   "War Opted In", "War Opted Out",
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
        missing_text = []
        text = ""
        for player_tag, discord_id in links:
            name = tag_to_name[player_tag]
            discord_member = disnake.utils.get(
                ctx.guild.members, id=discord_id)

            if discord_member is None:
                new_text = f"{self.bot.fetch_emoji(tag_to_th[player_tag])}{name} | {player_tag}\n"
                if len(missing_text) + len(new_text) >= 1990:
                    missing_text.append(text)
                    text = ""
                text += new_text
            else:
                new_text = f"{self.bot.fetch_emoji(tag_to_th[player_tag])}{name} | {discord_member.mention}\n"
                if len(missing_text) + len(new_text) >= 1990:
                    missing_text.append(text)
                    text = ""
                text += new_text

        if text != "":
            missing_text.append(text)

        if missing_text == "":
            missing_text = "No Players Found"

        await res.edit_original_message(
            embed=None,
            components=[],
            content="||Ping Sent||")
        for item in missing_text:
            await ctx.followup.send(content=item)

    '''    @clan.sub_command(name="export", description="Export info about this clan")
    async def clan_export(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        (image, file) = await self.create_war_export(clan)
        await ctx.edit_original_message(files=[image, file])


    
    '''

    async def clan_sort(self, players, clan: coc.Clan, sort_by: str):
        og_sort = sort_by
        sort_by = item_to_name[sort_by]

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

        longest = get_longest(players=players, attribute=sort_by)
        if "ach_" not in sort_by and sort_by not in ["season_rank", "heroes"]:
            attr = players[0].__getattribute__(sort_by)
            if isinstance(attr, str) or isinstance(attr, coc.Role) or isinstance(attr, coc.League):
                players = sorted(players, key=lambda x: str(x.__getattribute__(sort_by)))
            else:
                players = sorted(players, key=lambda x: x.__getattribute__(sort_by), reverse=True)
        elif "ach_" in sort_by:
            players = sorted(players,
                             key=lambda x: x.get_achievement(name=sort_by.split('_')[-1], default_value=0).value,
                             reverse=True)
        elif sort_by == "season_rank":
            def sort_func(a_player):
                try:
                    a_rank = a_player.legend_statistics.best_season.rank
                    return a_rank
                except:
                    return 0

            players = sorted(players, key=sort_func, reverse=False)
        else:
            longest = 3

            def sort_func(a_player):
                a_rank = sum([hero.level for hero in a_player.heroes if hero.is_home_base])
                return a_rank

            players = sorted(players, key=sort_func, reverse=True)

        text = ""
        for count, player in enumerate(players, 1):
            if sort_by in ["role", "tag", "heroes", "ach_Friend in Need", "town_hall"]:
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
                text += f"`{spot:3}`{emoji}`{player.__getattribute__(sort_by):{longest}} {player.name[:13]}`\n"
            elif "ach_" in sort_by:
                text += f"`{spot:3}`{emoji}`{player.get_achievement(name=sort_by.split('_')[-1], default_value=0).value:{longest}} {player.name[:13]}`\n"
            elif sort_by == "season_rank":
                try:
                    rank = player.legend_statistics.best_season.rank
                except:
                    rank = " N/A"
                text += f"`{spot:3}`{emoji}`#{rank:<{longest}} {player.name[:13]}`\n"
            else:
                cum_heroes = sum([hero.level for hero in player.heroes if hero.is_home_base])
                text += f"`{spot:3}`{emoji}`{cum_heroes:3} {player.name[:13]}`\n"

        embed = disnake.Embed(title=f"{clan.name} sorted by {og_sort}", description=text, color=disnake.Color.green())
        return embed



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

        elif "clansort-" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("-"))[1]
            sort_by = (str(ctx.data.custom_id).split("-"))[-1]
            clan = await self.bot.getClan(clan)

            players: list[coc.Player] = await self.bot.get_players(tags=[member.tag for member in clan.members], custom=False)
            embed = await self.clan_sort(players=players, clan=clan, sort_by=sort_by)
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "waropt_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)

            embeds = await clan_responder.opt_status(self.bot, clan)
            embeds[-1].description += f"Last Refreshed: <t:{int(datetime.now().timestamp())}:R>"

            await ctx.edit_original_message(embeds=embeds)

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
                clan_legend_ranking=clan_legend_ranking, previous_season=self.bot.gen_previous_season_date(),
                season=self.bot.gen_season_date(), bot=self.bot)

            values = (
                f"{embed.fields[-1].value}"
                f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>")

            embed.set_field_at(len(
                embed.fields) - 1, name="**Boosted Super Troops:**",
                               value=values, inline=False)

            try:
                embed.set_image(url=ctx.message.embeds[0].image.url)
            except:
                pass

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

            season_date = self.bot.gen_games_season()

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
    @activities.autocomplete("season")
    @clan_games.autocomplete("season")
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
    @clan_compo.autocomplete("clan")
    @last_online.autocomplete("clan")
    @clan_donations.autocomplete("clan")
    @activity_graph.autocomplete("clan")
    @war_stats_clan.autocomplete("clan")
    @activities.autocomplete("clan")
    @clan_ping.autocomplete("clan")
    @progress.autocomplete("clan")
    @clan_games.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id}).sort("name", 1)
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        if clan_list == [] and len(query) >= 3:
            if coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
            else:
                clan = None
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
