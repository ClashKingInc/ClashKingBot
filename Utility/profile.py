import coc
import disnake
from coc.raid import RaidLogEntry
from datetime import date, timedelta, datetime
from disnake.ext import commands
from Utility.profile_embeds import *
from Assets.emojiDictionary import emojiDictionary
from Utility.pagination import button_pagination
from utils.search import search_results
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from utils.troop_methods import heros, heroPets
from Assets.thPicDictionary import thDictionary
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from typing import List
import asyncio
import pytz
utc = pytz.utc

class profiles(commands.Cog, name="Profile"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
    @commands.slash_command(name="player")
    async def player(self, ctx):
        pass

    @player.sub_command(name="lookup", description="Lookup players or discord users")
    async def lookup(self, ctx: disnake.ApplicationCommandInteraction, tag: str=None, discord_user:disnake.Member=None):
        """
            Parameters
            ----------
            tag: (optional) tag to lookup
            discord_user: (optional) discord user to lookup
        """
        search_query = None
        if tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif tag is not None:
            search_query = tag
        else:
            search_query = str(discord_user.id)

        await ctx.response.defer()
        results = await search_results(self.bot, search_query)

        if results == []:
            return await ctx.edit_original_message(content="No results were found.", embed=None)
        msg = await ctx.original_message()

        await button_pagination(self.bot, ctx, msg, results)


    @player.sub_command(name="account-list", description="List of accounts a user has & average th compo")
    async def list(self, ctx: disnake.ApplicationCommandInteraction, discord_user:disnake.Member=None):
        if discord_user is None:
            search_query = str(ctx.author.id)
        else:
            search_query = str(discord_user.id)
        await ctx.response.defer()

        results = await search_results(self.bot, search_query)

        if results == []:
            return await ctx.edit_original_message(content="No results were found.")

        text = ""
        total = 0
        sumth = 0
        results = results[:100]
        for player in results:
            emoji = emojiDictionary(player.town_hall)
            th = player.town_hall
            sumth += th
            total += 1
            text += f"{emoji} {player.name}\n"

        average = round((sumth / total), 2)
        embed = disnake.Embed(
            description=text,
            color=disnake.Color.green())

        embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
        await ctx.edit_original_message(embed=embed)


    @player.sub_command(name="invite", description="Embed with basic info & link for a player to be invited")
    async def invite(self, ctx, player_tag):
        player = await self.bot.getPlayer(player_tag)
        if player is None:
            return await ctx.send("Not a valid playerTag.")

        clan = ""
        try:
            clan = player.clan.name
            clan = f"{clan}"
        except:
            clan = "None"
        hero = heros(player)
        pets = heroPets(player)
        if hero is None:
            hero = ""
        else:
            hero = f"**Heroes:**\n{hero}\n"

        if pets is None:
            pets = ""
        else:
            pets = f"**Pets:**\n{pets}\n"

        tag = player.tag.strip("#")
        embed = disnake.Embed(title=f"Invite {player.name} to your clan:",
                              description=f"{player.name} - TH{player.town_hall}\n" +
                                          f"Tag: {player.tag}\n" +
                                          f"Clan: {clan}\n" +
                                          f"Trophies: {player.trophies}\n"
                                          f"War Stars: {player.war_stars}\n"
                                          f"{hero}{pets}"
                                          f'[View Stats](https://www.clashofstats.com/players/{tag}) | [Open in Game]({player.share_link})',
                              color=disnake.Color.green())
        if player.town_hall > 4:
            embed.set_thumbnail(url=thDictionary(player.town_hall))

        await ctx.send(embed=embed)

    @player.sub_command(name="upgrades", description="Show upgrades needed for an account")
    async def upgrades(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str=None, discord_user:disnake.Member=None):
        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

        await ctx.response.defer()
        results = await search_results(self.bot, search_query)
        embed = upgrade_embed(self.bot, results[0])
        components = []
        if len(results) > 1:
            player_results = []
            for count, player in enumerate(results):
                player_results.append(
                    disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji,
                                         value=f"{count}"))
            profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)
            st2 = disnake.ui.ActionRow()
            st2.append_item(profile_select)
            components = [st2]
        await ctx.send(embeds=embed, components=components)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                     timeout=600)
            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break

            await res.response.defer()
            current_page = int(res.values[0])
            embed = upgrade_embed(self.bot, results[current_page])
            await res.edit_original_message(embeds=embed)

    @player.sub_command(name="war-stats", description="War stats of a player or discord user")
    async def war_stats_player(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str=None, discord_user:disnake.Member=None, start_date = 0, end_date = 9999999999):
        """
            Parameters
            ----------
            player_tag: (optional) player to view war stats on
            discord_user: (optional) discord user's accounts to view war stats of
            start_date: (optional) filter stats by date, default is to view this season
            end_date: (optional) filter stats by date, default is to view this season
        """
        await ctx.response.defer()
        if start_date != 0 and end_date != 9999999999:
            start_date = int(datetime.strptime(start_date, "%d %B %Y").timestamp())
            end_date = int(datetime.strptime(end_date, "%d %B %Y").timestamp())
        else:
            start_date = int(coc.utils.get_season_start().timestamp())
            end_date = int(coc.utils.get_season_end().timestamp())

        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

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


    @player.sub_command(name="to-do", description="Get a list of things to be done (war attack, legends hits, capital raids etc)")
    async def to_do(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member=None):
        await ctx.response.defer()
        if discord_user is None:
            discord_user = ctx.author
        linked_accounts = await search_results(self.bot, str(discord_user.id))
        embed = disnake.Embed(title=f"{discord_user.display_name} To-Do List", color=disnake.Color.green())

        if linked_accounts == []:
            embed.description = "No accounts linked, use `/link` to get started!"
            return await ctx.edit_original_message(embed=embed)

        war_hits_to_do = await self.get_war_hits(linked_accounts=linked_accounts)
        if war_hits_to_do != "":
            embed.add_field(name="War Hits", value=war_hits_to_do, inline=False)

        legend_hits_to_do = await self.get_legend_hits(linked_accounts=linked_accounts)
        if legend_hits_to_do != "":
            embed.add_field(name="Legend Hits", value=legend_hits_to_do, inline=False)

        raid_hits_to_do = await self.get_raid_hits(linked_accounts=linked_accounts)
        if raid_hits_to_do != "":
            embed.add_field(name="Raid Hits", value=raid_hits_to_do, inline=False)

        inactive_to_do = await self.get_inactive(linked_accounts=linked_accounts)
        if inactive_to_do != "":
            embed.add_field(name="Inactive Accounts (48+ hr)", value=inactive_to_do, inline=False)

        if len(embed.fields) == 0:
            embed.description = "You're all caught up chief!"

        await ctx.edit_original_message(embed=embed)

    async def get_war_hits(self, linked_accounts: List[MyCustomPlayer]):
        async def get_clan_wars(clan_tag, player):
            war = await self.bot.get_clanwar(clanTag=clan_tag)
            if war is not None and war.end_time.seconds_until <= 0:
                war = None
            return (player, war)

        tasks = []
        for player in linked_accounts:
            if player.clan is not None:
                task = asyncio.ensure_future(get_clan_wars(clan_tag=player.clan.tag, player=player))
                tasks.append(task)
        wars = await asyncio.gather(*tasks)

        war_hits = ""
        for player, war in wars:
            if war is None:
                continue
            war: coc.ClanWar
            our_player = coc.utils.get(war.members, tag=player.tag)
            if our_player is None:
                continue
            attacks = our_player.attacks
            required_attacks = war.attacks_per_member
            if len(attacks) < required_attacks:
                war_hits += f"({len(attacks)}/{required_attacks}) | <t:{int(war.end_time.time.replace(tzinfo=utc).timestamp())}:R> - {player.name}\n"
        return war_hits


    async def get_legend_hits(self, linked_accounts: List[MyCustomPlayer]):
        legend_hits_remaining = ""
        for player in linked_accounts:
            if player.is_legends():
                if player.legend_day().num_attacks.integer < 8:
                    legend_hits_remaining += f"({player.legend_day().num_attacks.integer}/8) - {player.name}\n"
        return legend_hits_remaining


    async def get_raid_hits(self, linked_accounts: List[MyCustomPlayer]):
        async def get_raid(clan_tag, player):
            weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
            weekend_raid_entry = await get_raidlog_entry(clan=player.clan, weekend=weekend, bot=self.bot)
            if weekend_raid_entry is not None and str(weekend_raid_entry.state) == "ended":
                weekend_raid_entry = None
            return (player, weekend_raid_entry)

        tasks = []
        for player in linked_accounts:
            if player.clan is not None:
                task = asyncio.ensure_future(get_raid(clan_tag=player.clan.tag, player=player))
                tasks.append(task)
        wars = await asyncio.gather(*tasks)

        raid_hits = ""
        for player, raid_log_entry in wars:
            if raid_log_entry is None:
                continue
            raid_log_entry: RaidLogEntry
            our_player = coc.utils.get(raid_log_entry.members, tag=player.tag)
            if our_player is None:
                attacks = 0
                required_attacks = 6
            else:
                attacks = our_player.attack_count
                required_attacks = our_player.attack_limit + our_player.bonus_attack_limit
            if attacks < required_attacks:
                raid_hits += f"({attacks}/{required_attacks}) - {player.name}\n"
        return raid_hits


    async def get_inactive(self, linked_accounts: List[MyCustomPlayer]):
        now = int(datetime.now(tz=utc).timestamp())
        inactive_text = ""
        for player in linked_accounts:
            last_online = player.last_online
            #48 hours in seconds
            if last_online is None:
                continue
            if now - last_online >= (48 * 60 * 60):
                inactive_text += f"<t:{last_online}:R> - {player.name}\n"
        return inactive_text


    # UTILS
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
            text += f"`Def 0 Stars` | `{hr_nums}` | {round(100 - (hr.average_zeros * 100), 1)}%\n"
        if hr.total_ones != 0:
            hr_nums = f"{hr.total_ones}/{hr.num_attacks}".center(5)
            text += f"`Def 1 Stars` | `{hr_nums}` | {round(100 - (hr.average_ones * 100), 1)}%\n"
        if hr.total_twos != 0:
            hr_nums = f"{hr.total_twos}/{hr.num_attacks}".center(5)
            text += f"`Def 2 Stars` | `{hr_nums}` | {round(100 - (hr.average_twos * 100), 1)}%\n"
        if hr.total_triples != 0:
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`Def 3 Stars` | `{hr_nums}` | {round(100 - (hr.average_triples * 100), 1)}%\n"

        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**Star Count %'s**", value=text + "­\n", inline=False)

        fresh_hr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
        nonfresh_hr = await player.hit_rate(fresh_type=[False], start_timestamp=start_date, end_timestamp=end_date)
        fresh_dr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
        nonfresh_dr = await player.defense_rate(fresh_type=[False], start_timestamp=start_date,
                                                end_timestamp=end_date)
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
        random_dr = await player.defense_rate(war_types=["random"], start_timestamp=start_date,
                                              end_timestamp=end_date)
        cwl_dr = await player.defense_rate(war_types=["cwl"], start_timestamp=start_date, end_timestamp=end_date)
        friendly_dr = await player.defense_rate(war_types=["friendly"], start_timestamp=start_date,
                                                end_timestamp=end_date)
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

        lost_hr = await player.hit_rate(war_statuses=["lost", "losing"], start_timestamp=start_date,
                                        end_timestamp=end_date)
        win_hr = await player.hit_rate(war_statuses=["winning", "won"], start_timestamp=start_date,
                                       end_timestamp=end_date)
        lost_dr = await player.defense_rate(war_statuses=["lost", "losing"], start_timestamp=start_date,
                                            end_timestamp=end_date)
        win_dr = await player.defense_rate(war_statuses=["winning", "won"], start_timestamp=start_date,
                                           end_timestamp=end_date)
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
                disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji,
                                     value=f"{count}"))
        profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        return [st2]


    # AUTOCOMPLETES
    @war_stats_player.autocomplete("start_date")
    @war_stats_player.autocomplete("end_date")
    async def date_autocomp(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        today = date.today()
        date_list = [today - timedelta(days=day) for day in range(365)]
        return [dt.strftime("%d %B %Y") for dt in date_list if
                query.lower() in str(dt.strftime("%d %B, %Y")).lower()][:25]


    @invite.autocomplete("player_tag")
    @lookup.autocomplete("tag")
    @upgrades.autocomplete("player_tag")
    @war_stats_player.autocomplete("player_tag")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names


def setup(bot: CustomClient):
    bot.add_cog(profiles(bot))