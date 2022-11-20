import coc
import disnake
import pytz
import asyncio
import calendar
import emoji

from datetime import date, timedelta, datetime
from utils.search import search_results
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from typing import List

tiz = pytz.utc

class WarStats(commands.Cog, name="War Stats"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    @commands.slash_command(name="war-stats", description="Attack statistics")
    async def war_stats(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @war_stats.sub_command(name="player", description="Get attack statistics for a player or discord user")
    async def war_stats_player(self, ctx: disnake.ApplicationCommandInteraction, tag_or_user = None, start_date = 0, end_date = 9999999999):
        """
            Parameters
            ----------
            tag_or_user: player or discord user to view war stats on
            start_date: filter stats by date, default is to view this season
            end_date: filter stats by date, default is to view this season
        """
        await ctx.response.defer()
        if start_date != 0 and end_date != 9999999999:
            start_date = int(datetime.strptime(start_date, "%d %B %Y").timestamp())
            end_date = int(datetime.strptime(end_date, "%d %B %Y").timestamp())
        else:
            start_date = int(coc.utils.get_season_start().timestamp())
            end_date = int(coc.utils.get_season_end().timestamp())

        if tag_or_user is None:
            search_query = str(ctx.author.id)
        elif coc.utils.is_valid_tag(str(tag_or_user)):
            search_query = tag_or_user
        else:
            search_query = await self.bot.pingToMember(ctx=ctx, ping=tag_or_user, no_fetch=True)

        players = await search_results(self.bot, search_query)
        if players == []:
            embed = disnake.Embed(description="**No matching player/discord user found**", colour=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await self.create_player_hr(player=players[0], start_date=start_date, end_date=end_date)
        await ctx.edit_original_message(embed=embed, components=self.player_components(players))
        if len(players) == 1:
            return
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
            page = int(res.values[0])
            embed = await self.create_player_hr(player=players[page], start_date=start_date, end_date=end_date)
            await res.edit_original_message(embed=embed)

    @war_stats.sub_command(name="clan", description="Get attack statistics for clan members")
    async def war_stats_clan(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                             season = commands.Param(default=None, name="season")):
        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            start_date = int(coc.utils.get_season_start(month=int(month), year=int(year)).timestamp())
            end_date = int(coc.utils.get_season_end(month=int(month), year=int(year)).timestamp())
        else:
            start_date = int(coc.utils.get_season_start().timestamp())
            end_date = int(coc.utils.get_season_end().timestamp())

        members = [member.tag for member in clan.members]
        await ctx.response.defer()
        players = await self.bot.get_players(tags=members, custom=True)
        off_hr_embed = await self.create_offensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date)
        components = self.stat_components()
        await ctx.edit_original_message(embed=off_hr_embed, components=components)

        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id


        board_type = "Offensive Hitrate"
        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
            except:
                return await msg.edit(components=[])
                break

            await res.response.defer()

            #is a list of th levels
            if res.values[0].isdigit():
                th_levels = [int(value) for value in res.values]
                if board_type == "Offensive Hitrate":
                    embed = await self.create_offensive_hitrate(clan=clan, players=players,start_timestamp=start_date, end_timestamp=end_date, townhall_level=th_levels)
                elif board_type == "Defensive Rate":
                    embed = await self.create_defensive_hitrate(clan=clan, players=players,start_timestamp=start_date, end_timestamp=end_date, townhall_level=th_levels)
                elif board_type == "Stars Leaderboard":
                    embed = await self.create_stars_leaderboard(clan=clan, players=players,start_timestamp=start_date, end_timestamp=end_date, townhall_level=th_levels)
                await res.edit_original_message(embed=embed)
            #is a filter type
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
                    embed = await self.create_offensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date, fresh_type=fresh_type, war_types=war_types)
                elif board_type == "Defensive Rate":
                    embed = await self.create_defensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date, fresh_type=fresh_type, war_types=war_types)
                elif board_type == "Stars Leaderboard":
                    embed = await self.create_stars_leaderboard(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date, fresh_type=fresh_type, war_types=war_types)
                await res.edit_original_message(embed=embed)

            #changing the board type
            elif res.values[0] in ["Offensive Hitrate", "Defensive Rate", "Stars Leaderboard"]:
                board_type = res.values[0]
                if board_type == "Offensive Hitrate":
                    embed = await self.create_offensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date)
                elif board_type == "Defensive Rate":
                    embed = await self.create_defensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date)
                elif board_type == "Stars Leaderboard":
                    embed = await self.create_stars_leaderboard(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date)
                await res.edit_original_message(embed=embed)

    '''
    @war_stats.sub_command(name="leaderboard", description="The best attack stats across the bot")
    async def attack_stats_leaderboard(self, ctx: disnake.ApplicationCommandInteraction):
        pass
    '''

    #AUTOCOMPLETES
    @war_stats_player.autocomplete("start_date")
    @war_stats_player.autocomplete("end_date")
    async def date_autocomp(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        today = date.today()
        date_list = [today - timedelta(days=day) for day in range(365)]
        return [dt.strftime("%d %B %Y") for dt in date_list if query.lower() in str(dt.strftime("%d %B, %Y")).lower()][:25]

    @war_stats_clan.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons =  self.bot.gen_season_date(seasons_ago=13)[1:]
        return [season for season in seasons if query.lower() in season.lower()]

    @war_stats_clan.autocomplete("clan")
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
                results = await self.bot.coc_client.search_clans(name=query, limit=25)
                for clan in results:
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {clan.war_league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]




    #UTILS
    async def create_player_hr(self, player: MyCustomPlayer, start_date, end_date):
        embed = disnake.Embed(title=f"{player.name} War Stats", colour=disnake.Color.green())
        time_range = f"{datetime.fromtimestamp(start_date).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_date).strftime('%m/%d/%y')}"
        embed.set_footer(icon_url=player.town_hall_cls.image_url, text=time_range)
        hitrate = await player.hit_rate(start_timestamp=start_date, end_timestamp=end_date)
        hr_text = ""
        for hr in hitrate:
            hr_type = f"{hr.type}".ljust(5)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            hr_text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if hr_text == "":
            hr_text = "No war hits tracked.\n"
        embed.add_field(name="**Triple Hit Rate**", value=hr_text + "­\n", inline=False)

        defrate = await player.defense_rate(start_timestamp=start_date, end_timestamp=end_date)
        def_text = ""
        for hr in defrate:
            hr_type = f"{hr.type}".ljust(5)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            def_text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if def_text == "":
            def_text = "No war defenses tracked.\n"
        embed.add_field(name="**Triple Defense Rate**", value=def_text + "­\n", inline=False)


        text = ""
        hr = hitrate[0]
        footer_text = f"Avg. Off Stars: `{round(hr.average_stars, 2)}`"
        if hr.total_zeros != 0:
            hr_nums = f"{hr.total_zeros}/{hr.num_attacks}".center(5)
            text += f"`Off 0 Stars` | `{hr_nums}` | {round(hr.average_zeros * 100, 1)}%\n"
        if hr.total_ones != 0:
            hr_nums = f"{hr.total_ones}/{hr.num_attacks}".center(5)
            text += f"`Off 1 Stars` | `{hr_nums}` | {round(hr.average_ones * 100, 1)}%\n"
        if hr.total_twos != 0:
            hr_nums = f"{hr.total_twos}/{hr.num_attacks}".center(5)
            text += f"`Off 2 Stars` | `{hr_nums}` | {round(hr.average_twos * 100, 1)}%\n"
        if hr.total_triples != 0:
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`Off 3 Stars` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"

        hr = defrate[0]
        footer_text += f"\nAvg. Def Stars: `{round(hr.average_stars, 2)}`"
        if hr.total_zeros != 0:
            hr_nums = f"{hr.total_zeros}/{hr.num_attacks}".center(5)
            text += f"`Def 0 Stars` | `{hr_nums}` | {round(hr.average_zeros + 1 * 100, 1)}%\n"
        if hr.total_ones != 0:
            hr_nums = f"{hr.total_ones}/{hr.num_attacks}".center(5)
            text += f"`Def 1 Stars` | `{hr_nums}` | {round(hr.average_ones + 1 * 100, 1)}%\n"
        if hr.total_twos != 0:
            hr_nums = f"{hr.total_twos}/{hr.num_attacks}".center(5)
            text += f"`Def 2 Stars` | `{hr_nums}` | {round(hr.average_twos + 1 * 100, 1)}%\n"
        if hr.total_triples != 0:
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`Def 3 Stars` | `{hr_nums}` | {round(hr.average_triples + 1 * 100, 1)}%\n"

        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**Star Count %'s**", value=text + "­\n", inline=False)

        fresh_hr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
        nonfresh_hr = await player.hit_rate(fresh_type=[False], start_timestamp=start_date, end_timestamp=end_date)
        fresh_dr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
        nonfresh_dr = await player.defense_rate(fresh_type=[False], start_timestamp=start_date, end_timestamp=end_date)
        hitrates = [fresh_hr, nonfresh_hr, fresh_dr, nonfresh_dr]
        names = ["Fresh HR", "Non-Fresh HR", "Fresh DR", "Non-Fresh DR"]
        text = ""
        for count, hr in enumerate(hitrates):
            hr = hr[0]
            if hr.num_attacks == 0:
                continue
            hr_type = f"{names[count]}".ljust(12)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**Fresh/Not Fresh**", value=text + "­\n", inline=False)

        random = await player.hit_rate(war_types=["random"], start_timestamp=start_date, end_timestamp=end_date)
        cwl = await player.hit_rate(war_types=["cwl"], start_timestamp=start_date, end_timestamp=end_date)
        friendly = await player.hit_rate(war_types=["friendly"], start_timestamp=start_date, end_timestamp=end_date)
        random_dr = await player.defense_rate(war_types=["random"], start_timestamp=start_date, end_timestamp=end_date)
        cwl_dr = await player.defense_rate(war_types=["cwl"], start_timestamp=start_date, end_timestamp=end_date)
        friendly_dr = await player.defense_rate(war_types=["friendly"], start_timestamp=start_date, end_timestamp=end_date)
        hitrates = [random, cwl, friendly, random_dr, cwl_dr, friendly_dr]
        names = ["War HR", "CWL HR", "Friendly HR", "War DR", "CWL DR", "Friendly DR"]
        text = ""
        for count, hr in enumerate(hitrates):
            hr = hr[0]
            if hr.num_attacks == 0:
                continue
            hr_type = f"{names[count]}".ljust(11)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**War Type**", value=text + "­\n", inline=False)

        war_sizes = list(range(5, 55, 5))
        hitrates = []
        for size in war_sizes:
            hr = await player.hit_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
            hitrates.append(hr)
        for size in war_sizes:
            hr = await player.defense_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
            hitrates.append(hr)

        text = ""
        names = [f"{size}v{size} HR" for size in war_sizes] + [f"{size}v{size} DR" for size in war_sizes]
        for count, hr in enumerate(hitrates):
            hr = hr[0]
            if hr.num_attacks == 0:
                continue
            hr_type = f"{names[count]}".ljust(8)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**War Size**", value=text + "­\n", inline=False)


        lost_hr = await player.hit_rate(war_statuses=["lost", "losing"], start_timestamp=start_date, end_timestamp=end_date)
        win_hr = await player.hit_rate(war_statuses=["winning", "won"], start_timestamp=start_date, end_timestamp=end_date)
        lost_dr = await player.defense_rate(war_statuses=["lost", "losing"], start_timestamp=start_date, end_timestamp=end_date)
        win_dr = await player.defense_rate(war_statuses=["winning", "won"], start_timestamp=start_date, end_timestamp=end_date)
        hitrates = [lost_hr, win_hr, lost_dr, win_dr]
        names = ["Losing HR", "Winning HR", "Losing DR", "Winning DR"]
        text = ""
        for count, hr in enumerate(hitrates):
            hr = hr[0]
            if hr.num_attacks == 0:
                continue
            hr_type = f"{names[count]}".ljust(11)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**War Status**", value=text + "­\n", inline=False)
        embed.description = footer_text

        return embed

    def player_components(self, players: List[MyCustomPlayer]):
        player_results = []
        if len(players) == 1:
            return player_results
        for count, player in enumerate(players):
            player_results.append(
                disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji,value=f"{count}"))
        profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        return [st2]

    def stat_components(self):
        options = []
        for townhall in reversed(range(6, 16)):
            options.append(disnake.SelectOption(label=f"Townhall {townhall}", emoji=self.bot.fetch_emoji(name=townhall),value=str(townhall)))
        th_select = disnake.ui.Select(
            options=options,
            placeholder="Select Townhalls",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )

        options = []
        real_types = ["Fresh Hits", "Non-Fresh", "random", "cwl", "friendly"]
        for count, filter in enumerate(["Fresh Hits", "Non-Fresh", "Random Wars", "CWL", "Friendly Wars"]):
            options.append(disnake.SelectOption(label=f"{filter}", value=real_types[count]))
        filter_select = disnake.ui.Select(
            options=options,
            placeholder="Select Filters",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )

        options = []
        emojis = [self.bot.emoji.sword_clash.partial_emoji, self.bot.emoji.shield.partial_emoji, self.bot.emoji.war_star.partial_emoji]
        for count, type in enumerate(["Offensive Hitrate", "Defensive Rate", "Stars Leaderboard"]):
            options.append(disnake.SelectOption(label=f"{type}", emoji=emojis[count], value=type))
        stat_select = disnake.ui.Select(
            options=options,
            placeholder="Select Stat Type",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )

        dropdown = [disnake.ui.ActionRow(th_select), disnake.ui.ActionRow(filter_select), disnake.ui.ActionRow(stat_select)]
        return dropdown

    async def create_offensive_hitrate(self, clan: coc.Clan, players: List[coc.Player],
            townhall_level:list = [], fresh_type: list = [False, True], start_timestamp:int = 0, end_timestamp: int = 9999999999,
                                       war_types: list= ["random", "cwl", "friendly"], war_statuses = ["lost", "losing", "winning", "won"]):
        if not townhall_level:
            townhall_level = list(range(1, 17))

        tasks = []
        async def fetch_n_rank(player: MyCustomPlayer):
            hitrate = await player.hit_rate(townhall_level=townhall_level, fresh_type=fresh_type, start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                            war_types=war_types, war_statuses=war_statuses)
            hr = hitrate[0]
            if hr.num_attacks == 0:
                return None
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            name = emoji.replace_emoji(player.name, "")
            name = str(name)[0:12]
            name = f"{name}".ljust(12)
            destr = f"{round(hr.average_triples * 100, 1)}%".rjust(6)
            return [f"{player.town_hall_cls.emoji}` {hr_nums} {destr} {name}`\n", round(hr.average_triples * 100, 3), name, hr.num_attacks, player.town_hall]

        for player in players:  # type: MyCustomPlayer
            task = asyncio.ensure_future(fetch_n_rank(player=player))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        ranked = [response for response in responses if response is not None]

        ranked = sorted(ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
        text = "`# TH  NUM    HR%    NAME       `\n"
        for count, rank in enumerate(ranked, 1):
            spot_emoji = self.bot.get_number_emoji(color="gold", number=count)
            text += f"{spot_emoji}{rank[0]}"
        embed = disnake.Embed(title=f"Offensive Hit Rates", description=text, colour=disnake.Color.green())

        filter_types = []
        if True in fresh_type:
            filter_types.append("Fresh")
        if False in fresh_type:
            filter_types.append("Non-Fresh")
        for type in war_types:
            filter_types.append(str(type).capitalize())
        filter_types = ", ".join(filter_types)
        time_range = "This Season"
        if start_timestamp != 0 and end_timestamp != 9999999999:
            time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
        embed.set_footer(icon_url=clan.badge.url, text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
        return embed

    async def create_defensive_hitrate(self, clan: coc.Clan, players: List[coc.Player],
            townhall_level:list = [], fresh_type: list = [False, True], start_timestamp:int = 0, end_timestamp: int = 9999999999,
                                       war_types: list= ["random", "cwl", "friendly"], war_statuses = ["lost", "losing", "winning", "won"]):
        if not townhall_level:
            townhall_level = list(range(1, 17))

        tasks = []
        async def fetch_n_rank(player: MyCustomPlayer):
            hitrate = await player.defense_rate(townhall_level=townhall_level, fresh_type=fresh_type, start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                            war_types=war_types, war_statuses=war_statuses)
            hr = hitrate[0]
            if hr.num_attacks == 0:
                return None
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            name = emoji.replace_emoji(player.name, "")
            name = str(name)[0:12]
            name = f"{name}".ljust(12)
            destr = f"{round(hr.average_triples * 100, 1)}%".rjust(6)
            return [f"{player.town_hall_cls.emoji} `{hr_nums} {destr} {name}`\n", round(hr.average_triples * 100, 3), name, hr.num_attacks, player.town_hall]

        for player in players:  # type: MyCustomPlayer
            task = asyncio.ensure_future(fetch_n_rank(player=player))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        ranked = [response for response in responses if response is not None]

        ranked = sorted(ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
        text = "`# TH  NUM    DR%    NAME       `\n"
        for count, rank in enumerate(ranked, 1):
            spot_emoji = self.bot.get_number_emoji(color="gold", number=count)
            text += f"{spot_emoji}{rank[0]}"
        embed = disnake.Embed(title=f"Defensive Rates", description=text, colour=disnake.Color.green())

        filter_types = []
        if True in fresh_type:
            filter_types.append("Fresh")
        if False in fresh_type:
            filter_types.append("Non-Fresh")
        for type in war_types:
            filter_types.append(str(type).capitalize())
        filter_types = ", ".join(filter_types)
        time_range = "This Season"
        if start_timestamp != 0 and end_timestamp != 9999999999:
            time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
        embed.set_footer(icon_url=clan.badge.url, text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
        return embed

    async def create_stars_leaderboard(self, clan: coc.Clan, players: List[coc.Player],
            townhall_level:list = [], fresh_type: list = [False, True], start_timestamp:int = 0, end_timestamp: int = 9999999999,
                                       war_types: list= ["random", "cwl", "friendly"], war_statuses = ["lost", "losing", "winning", "won"]):
        if not townhall_level:
            townhall_level = list(range(1, 17))

        tasks = []
        async def fetch_n_rank(player: MyCustomPlayer):
            hitrate = await player.hit_rate(townhall_level=townhall_level, fresh_type=fresh_type, start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                            war_types=war_types, war_statuses=war_statuses)
            hr = hitrate[0]
            if hr.num_attacks == 0:
                return None
            name = str(player.name)[0:12]
            name = f"{name}".ljust(12)
            stars = f"{hr.total_stars}".ljust(3)
            destruction = f"{int(hr.total_destruction)}%".ljust(5)
            return [f"{stars} {destruction} {name}\n", round(hr.average_triples * 100, 3), name, hr.total_stars, player.town_hall]

        for player in players:  # type: MyCustomPlayer
            task = asyncio.ensure_future(fetch_n_rank(player=player))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        ranked = [response for response in responses if response is not None]

        ranked = sorted(ranked, key=lambda l: (-l[-2], -l[1], l[2]), reverse=False)
        text = "```#   ★   DSTR%  NAME       \n"
        for count, rank in enumerate(ranked, 1):
            #spot_emoji = self.bot.get_number_emoji(color="gold", number=count)
            count = f"{count}.".ljust(3)
            text += f"{count} {rank[0]}"
        text += "```"
        embed = disnake.Embed(title=f"Star Leaderboard", description=text, colour=disnake.Color.green())

        filter_types = []
        if True in fresh_type:
            filter_types.append("Fresh")
        if False in fresh_type:
            filter_types.append("Non-Fresh")
        for type in war_types:
            filter_types.append(str(type).capitalize())
        filter_types = ", ".join(filter_types)
        time_range = "This Season"
        if start_timestamp != 0 and end_timestamp != 9999999999:
            time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
        embed.set_footer(icon_url=clan.badge.url, text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
        return embed
def setup(bot: CustomClient):
    bot.add_cog(WarStats(bot))