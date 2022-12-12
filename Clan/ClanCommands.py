from collections import defaultdict
from utils.clash import create_weekend_list, weekend_timestamps
from utils.components import raid_buttons
from utils.discord_utils import partial_emoji_gen
from CustomClasses.CustomPlayer import MyCustomPlayer
from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands
from Clan.ClanResponder import (
    clan_overview,
    linked_players,
    unlinked_players,
    player_trophy_sort
)
import math
import coc
import disnake
import asyncio
import pandas as pd
import pytz
import calendar
import emoji
tiz = pytz.utc


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
        pass

    @clan.sub_command(name="search", description="lookup clan by tag")
    async def getclan(
            self, ctx: disnake.ApplicationCommandInteraction,
            clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Search by clan tag or select an option from the autocomplete
        """

        await ctx.response.defer()
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

        embed = await clan_overview(
            clan=clan, db_clan=db_clan,
            clan_legend_ranking=clan_legend_ranking)

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
                clan_member_tags = []
                for player in clan.members:
                    clan_member_tags.append(player.tag)

                player_links = await self.bot.link_client.get_links(*clan_member_tags)

                linked_players_embed = linked_players(
                    ctx.guild.members, clan, player_links)

                await res.edit_original_message(embed=linked_players_embed)

            elif res.values[0] == "unlink":
                # initializing player link list
                clan_member_tags = []
                for player in clan.members:
                    clan_member_tags.append(player.tag)

                player_links = await self.bot.link_client.get_links(*clan_member_tags)

                unlinked_players_embed = unlinked_players(
                    clan, player_links)

                await res.edit_original_message(embed=unlinked_players_embed)

            elif res.values[0] == "trophies":
                embed = player_trophy_sort(clan)
                embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

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

        await ctx.response.defer()

        # initializing player link list
        clan_member_tags = []
        for player in clan.members:
            clan_member_tags.append(player.tag)
        player_links = await self.bot.link_client.get_links(*clan_member_tags)

        linked_players_embed = linked_players(
            ctx.guild.members, clan, player_links)
        unlinked_players_embed = unlinked_players(
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

        await ctx.response.defer()

        embed = player_trophy_sort(clan)
        embed.description += f"\nLast Refreshed: <t:{int(datetime.now().timestamp())}:R>"

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"trophies_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="sorted-townhall", description="List of clan members, sorted by townhall")
    async def player_th(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        embed = await self.player_townhall_sort(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"townhall_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="war-preferences", description="List of player's war preferences")
    async def war_opt(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        embed = await self.opt_status(clan)
        embed.description += f"Last Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"waropt_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="war-log", description="List of clan's last 25 war win & losses")
    async def clan_war_log(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

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
    async def clan_super_troops(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        embed: disnake.Embed = await self.stroop_list(clan)
        values = embed.fields[0].value + f"\nLast Refreshed: <t:{int(time)}:R>"
        embed.set_field_at(0, name="**Not Boosting:**",
                           value=values, inline=False)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"stroops_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="board", description="Simple embed, with overview of a clan")
    async def clan_board(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), button_text: str = None, button_link: str = None):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            button_text: can add an extra button to this board, this is the text for it
            button_link:can add an extra button to this board, this is the link for it
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        embed = await self.clan_overview(ctx, clan)
        values = embed.fields[-1].value + \
            f"\nLast Refreshed: <t:{int(time)}:R>"
        embed.set_field_at(len(
            embed.fields) - 1, name="**Boosted Super Troops:**", value=values, inline=False)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji,
                            style=disnake.ButtonStyle.grey, custom_id=f"clanboard_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(
            label=f"Clan Link", emoji="🔗", url=clan.share_link))
        if button_text is not None and button_link is not None:
            buttons.append_item(disnake.ui.Button(
                label=button_text, emoji="🔗", url=button_link))

        try:
            await ctx.edit_original_message(embed=embed, components=buttons)
        except disnake.errors.HTTPException:
            embed = disnake.Embed(description="Not a valid button link.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

    @clan.sub_command(name="compo", description="Townhall composition of a clan")
    async def clan_compo(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        thcount = defaultdict(int)
        total = 0
        sumth = 0

        clan_members = []

        clan_members += [member.tag for member in clan.members]
        list_members = await self.bot.get_players(tags=clan_members, custom=False)
        for player in list_members:
            th = player.town_hall
            sumth += th
            total += 1
            thcount[th] += 1

        stats = ""
        for th_level, th_count in sorted(thcount.items(), reverse=True):
            if (th_level) <= 9:
                th_emoji = self.bot.fetch_emoji(th_level)
                stats += f"{th_emoji} `TH{th_level} ` : {th_count}\n"
            else:
                th_emoji = self.bot.fetch_emoji(th_level)
                stats += f"{th_emoji} `TH{th_level}` : {th_count}\n"

        average = round((sumth / total), 2)
        embed = disnake.Embed(title=f"{clan.name} Townhall Composition", description=stats,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        embed.set_footer(
            text=f"Average Th: {average}\nTotal: {total} accounts")
        await ctx.edit_original_message(embed=embed)

    @clan.sub_command(name="capital-stats", description="Get stats on raids & donations during selected time period")
    async def clan_capital_stats(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        #weekend = commands.Param(default="Current Week", choices=["Current Week", "Last Week", "Last 4 Weeks (all)"])
        weekend = "Current Week"
        await ctx.response.defer()
        raidlog = await self.bot.coc_client.get_raidlog(clan.tag)
        choice_to_date = {"Current Week": [0], "Last Week": [1], "Last 4 Weeks (all)": [
            0, 1, 2, 3]}
        weekend_times = weekend_timestamps()
        weekend_dates = create_weekend_list(option=weekend)
        member_tags = [member.tag for member in clan.members]

        embeds = {}
        other_tags = []
        columns = ["Tag", "Donated", "Number of Donations",
                   "Raided", "Number of Raids"]
        donated_data = {}
        number_donated_data = {}

        for week in weekend_dates:
            tags = await self.bot.player_stats.distinct("tag", filter={f"capital_gold.{week}.raided_clan": clan.tag})
            other_tags += tags
        all_tags = list(set(member_tags + other_tags))
        tasks = []
        for tag in all_tags:
            results = await self.bot.player_stats.find_one({"tag": tag})
            task = asyncio.ensure_future(self.bot.coc_client.get_player(
                player_tag=tag, cls=MyCustomPlayer, bot=self.bot, results=results))
            tasks.append(task)
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        donation_text = []
        for player in responses:
            if isinstance(player, coc.errors.NotFound):
                continue
            player: MyCustomPlayer
            for char in ["`", "*", "_", "~", "´", "`"]:
                name = player.name.replace(char, "")
            sum_donated = 0
            len_donated = 0
            for week in weekend_dates:
                cc_stats = player.clan_capital_stats(week=week)
                sum_donated += sum(cc_stats.donated)
                len_donated += len(cc_stats.donated)
            donation = f"{sum_donated}".ljust(6)

            donated_data[player.tag] = sum_donated
            number_donated_data[player.tag] = len_donated

            if sum_donated == 0 and len(weekend_dates) > 1:
                continue
            if player.tag in member_tags:
                donation_text.append(
                    [f"{self.bot.emoji.capital_gold}`{donation}`: {name}", sum_donated])
            else:
                donation_text.append(
                    [f"{self.bot.emoji.deny_mark}`{donation}`: {name}", sum_donated])

        donation_text = sorted(donation_text, key=lambda l: l[1], reverse=True)
        donation_text = [line[0] for line in donation_text]
        donation_text = "\n".join(donation_text)
        donation_embed = disnake.Embed(
            title=f"**{clan.name} Donation Totals**", description=donation_text, color=disnake.Color.green())
        donation_embed.set_footer(
            text=f"Donated: {'{:,}'.format(sum(donated_data.values()))}")
        embeds["donations"] = donation_embed

        raid_weekends = []
        for week in choice_to_date[weekend]:
            raid_weekend = self.get_raid(raid_log=raidlog, before=weekend_times[week],
                                         after=weekend_times[week + 1])
            if raid_weekend is not None:
                raid_weekends.append(raid_weekend)

        total_medals = 0
        if not raid_weekends:
            raid_embed = disnake.Embed(
                title=f"**{clan.name} Raid Totals**", description="No raids", color=disnake.Color.green())
            embeds["raids"] = raid_embed
        else:
            total_attacks = defaultdict(int)
            total_looted = defaultdict(int)
            attack_limit = defaultdict(int)
            name_list = {}
            members_not_looted = member_tags.copy()
            for raid_weekend in raid_weekends:
                for member in raid_weekend.members:
                    name_list[member.tag] = member.name
                    total_attacks[member.tag] += member.attack_count
                    total_looted[member.tag] += member.capital_resources_looted
                    attack_limit[member.tag] += (member.attack_limit +
                                                 member.bonus_attack_limit)
                    if len(raid_weekends) == 1 and member.tag in members_not_looted:
                        members_not_looted.remove(member.tag)

            district_dict = {1: 135, 2: 225, 3: 350, 4: 405, 5: 460}
            capital_dict = {2: 180, 3: 360, 4: 585, 5: 810,
                            6: 1115, 7: 1240, 8: 1260, 9: 1375, 10: 1450}
            attacks_done = sum(list(total_attacks.values()))
            raids = raid_weekends[0].attack_log
            for raid_clan in raids:
                for district in raid_clan.districts:
                    if int(district.destruction) == 100:
                        if district.id == 70000000:
                            total_medals += capital_dict[int(
                                district.hall_level)]
                        else:
                            total_medals += district_dict[int(
                                district.hall_level)]
                    else:
                        #attacks_done -= len(district.attacks)
                        pass

            print(total_medals)
            print(attacks_done)
            total_medals = math.ceil(total_medals/attacks_done) * 6

            raid_text = []
            for tag, amount in total_looted.items():
                raided_amount = f"{amount}".ljust(6)
                name = name_list[tag]
                for char in ["`", "*", "_", "~"]:
                    name = name.replace(char, "", 10)
                # print(tag)
                # print(member_tags)
                if tag in member_tags:
                    raid_text.append(
                        [f"\u200e{self.bot.emoji.capital_gold}`{total_attacks[tag]}/{attack_limit[tag]} {raided_amount}`: \u200e{name}", amount])
                else:
                    raid_text.append(
                        [f"\u200e{self.bot.emoji.deny_mark}`{total_attacks[tag]}/{attack_limit[tag]} {raided_amount}`: \u200e{name}", amount])

            if len(raid_weekends) == 1:
                for member in members_not_looted:
                    name = coc.utils.get(clan.members, tag=member)
                    raid_text.append(
                        [f"{self.bot.emoji.capital_gold}`{0}/{6*len(raid_weekends)} {0}`: {name.name}", 0])

            raid_text = sorted(raid_text, key=lambda l: l[1], reverse=True)
            raid_text = [line[0] for line in raid_text]
            raid_text = "\n".join(raid_text)
            if len(raid_weekends) == 1:
                rw = raid_weekends[0]
                offensive_reward = rw.offensive_reward * 6
                if total_medals > offensive_reward:
                    offensive_reward = total_medals
                defensive_reward = rw.defensive_reward
                raid_text += f"\n\n{self.bot.emoji.raid_medal}{offensive_reward} + {self.bot.emoji.raid_medal}{defensive_reward} = {self.bot.emoji.raid_medal}{offensive_reward + defensive_reward}"
                raid_text += "\n`Offense + Defense = Total`"
            raid_embed = disnake.Embed(
                title=f"**{clan.name} Raid Totals**", description=raid_text, color=disnake.Color.green())
            raid_embed.set_footer(
                text=f"Spots: {len(total_attacks.values())}/50 | Attacks: {sum(total_attacks.values())}/300 | Looted: {'{:,}'.format(sum(total_looted.values()))}")
            embeds["raids"] = raid_embed

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
                data.append([tag, donated_data[tag],
                            number_donated_data[tag], looted, attacks])
            except:
                continue
            name = coc.utils.get(clan.members, tag=tag)
            index.append(name.name)

        buttons = raid_buttons(self.bot, data)

        if not raid_weekends:
            await ctx.edit_original_message(embed=donation_embed, components=buttons)
        else:
            await ctx.edit_original_message(embed=raid_embed, components=buttons)

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
            if res.data.custom_id == "donations":
                await res.edit_original_message(embed=embeds["donations"])
            elif res.data.custom_id == "raids":
                await res.edit_original_message(embed=embeds["raids"])
            elif res.data.custom_id == "capseason":
                file = self.create_excel(
                    columns=columns, index=index, data=data, weekend=weekend)
                await res.send(file=file, ephemeral=True)

    @clan.sub_command(name="capital-raids", description="See breakdown of clan's raids per clan & week")
    async def clan_capital_raids(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), weekend=commands.Param(default="Current Week", choices=["Current Week", "Last Week", "2 Weeks Ago"])):
        await ctx.response.defer()
        raidlog = await self.bot.coc_client.get_raidlog(clan.tag)
        choice_to_date = {"Current Week": 0, "Last Week": 1,  "2 Weeks Ago": 2}
        weekend_times = weekend_timestamps()

        embed = disnake.Embed(
            description=f"**{clan.name} Clan Capital Raids**", color=disnake.Color.green())
        raid_weekend = self.get_raid(
            raid_log=raidlog, before=weekend_times[choice_to_date[weekend]], after=weekend_times[choice_to_date[weekend] + 1])
        if raid_weekend is None:
            embed = disnake.Embed(
                description=f"**{clan.name} has no capital raids in the time frame - {weekend}**", color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        raids = raid_weekend.attack_log

        select_menu_options = [disnake.SelectOption(
            label="Overview", emoji=self.bot.emoji.sword_clash.partial_emoji, value="Overview")]
        embeds = {}
        total_attacks = 0
        total_looted = 0
        for raid_clan in raids:
            url = raid_clan.badge.url.replace(".png", "")
            emoji = disnake.utils.get(
                self.bot.emojis, name=url[-15:].replace("-", ""))
            if emoji is None:
                emoji = await self.bot.create_new_badge_emoji(url=raid_clan.badge.url)
            else:
                emoji = f"<:{emoji.name}:{emoji.id}>"
            looted = sum(district.looted for district in raid_clan.districts)
            total_looted += looted
            total_attacks += raid_clan.attack_count
            embed.add_field(name=f"{emoji}\u200e{raid_clan.name}", value=f"> {self.bot.emoji.sword} Attacks: {raid_clan.attack_count}\n"
                            f"> {self.bot.emoji.capital_gold} Looted: {'{:,}'.format(looted)}", inline=False)
            select_menu_options.append(disnake.SelectOption(
                label=raid_clan.name, emoji=self.bot.partial_emoji_gen(emoji_string=emoji), value=raid_clan.tag))

            # create detailed embeds

            detail_embed = disnake.Embed(
                description=f"**Attacks on {raid_clan.name}**", color=disnake.Color.green())
            for district in raid_clan.districts:
                attack_text = ""
                for attack in district.attacks:
                    attack_text += f"> \u200e{attack.destruction}% - \u200e{attack.attacker_name}\n"
                if district.id == 70000000:
                    emoji = self.bot.fetch_emoji(
                        name=f"Capital_Hall{district.hall_level}")
                else:
                    emoji = self.bot.fetch_emoji(
                        name=f"District_Hall{district.hall_level}")
                if attack_text == "":
                    attack_text = "None"
                detail_embed.add_field(
                    name=f"{emoji}{district.name}", value=attack_text, inline=False)

            embeds[raid_clan.tag] = detail_embed

        embed.set_footer(
            text=f"Attacks: {total_attacks}/300 | Looted: {'{:,}'.format(total_looted)}")
        embeds["Overview"] = embed
        select = disnake.ui.Select(
            options=select_menu_options,
            # the placeholder text to show when no options have been chosen
            placeholder="Detailed View",
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
                await msg.edit(components=[])
                break

            await res.response.edit_message(embed=embeds[res.values[0]])

    @clan.sub_command(name="last-online", description="List of most recently online players in clan")
    async def last_online(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        await ctx.response.defer()
        time = datetime.now().timestamp()
        embed = await self.create_last_online(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"lo_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)
        await ctx.edit_original_message(embed=embed)

    @clan.sub_command(name="activities", description="Activity count of how many times a player has been seen online")
    async def activities(self, ctx: disnake.ApplicationCommandInteraction,
                         clan: coc.Clan = commands.Param(converter=clan_converter)):
        await ctx.response.defer()
        time = datetime.now().timestamp()
        embed = await self.create_activities(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"act_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)
        await ctx.edit_original_message(embed=embed)

    def get_raid(self, raid_log, after, before):
        for raid in raid_log:
            time_start = int(raid.start_time.time.timestamp())
            if before > time_start > after:
                return raid
        return None

    def create_excel(self, columns, index, data, weekend):
        df = pd.DataFrame(data, index=index, columns=columns)
        df.to_excel('ClanCapitalStats.xlsx', sheet_name=f'{weekend}')
        return disnake.File("ClanCapitalStats.xlsx", filename=f"{weekend}_clancapital.xlsx")

    @clan.sub_command(name="games", description="Points earned in clan games by clan members")
    async def clan_games(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), season=commands.Param(default=None, name="season")):
        await ctx.response.defer()
        time = datetime.now().timestamp()
        _season = ""
        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(
                month=int(month-1), year=int(year))
            month = end_date.month
            if month <= 9:
                month = f"0{month}"
            embed = await self.create_clan_games(clan, date=f"{end_date.year}-{month}")
            _season = f"_{end_date.year}-{month}"
        else:
            embed = await self.create_clan_games(clan)

        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"clangames{_season}_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="donations", description="Donations given & received by clan members")
    async def clan_donations(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), season=commands.Param(default=None, name="season")):
        await ctx.response.defer()
        _season = ""
        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(
                month=int(month-1), year=int(year))
            month = end_date.month
            if month <= 9:
                month = f"0{month}"
            embed = await self.create_donations(clan, type="donated", date=f"{end_date.year}-{month}")
            _season = f"_{end_date.year}-{month}"
        else:
            embed = await self.create_donations(clan, type="donated")

        time = datetime.now().timestamp()
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji,
                            style=disnake.ButtonStyle.grey, custom_id=f"donated{_season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,
                            style=disnake.ButtonStyle.green, custom_id=f"received{_season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(label="Ratio", emoji=self.bot.emoji.ratio.partial_emoji,
                            style=disnake.ButtonStyle.green, custom_id=f"ratio{_season}_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name='lastonline-graph', description="Get a graph showing average clan members on per an hour")
    async def last_online_graph(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), timezone=commands.Param(name="timezone")):
        await ctx.response.defer()
        if timezone not in pytz.common_timezones:
            return await ctx.edit_original_message(content="Not a valid timezone, please choose one of the 300+ options in the autocomplete")
        file = await self.create_graph([clan], timezone=pytz.timezone(timezone))

        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        dropdown = []
        clan_dict = {}
        if clan_tags:
            clans = await self.bot.get_clans(tags=clan_tags)
            select_menu_options = []
            clans = sorted(clans, key=lambda x: x.member_count, reverse=True)
            for count, clan in enumerate(clans):
                clan_dict[clan.tag] = clan
                emoji = await self.bot.create_new_badge_emoji(url=clan.badge.url)
                if count < 25:
                    select_menu_options.append(
                        disnake.SelectOption(label=clan.name, emoji=self.bot.partial_emoji_gen(emoji_string=emoji),
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
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            await res.response.defer()

            selected_clans = [clan_dict[value] for value in res.values]
            file = await self.create_graph(selected_clans, timezone=pytz.timezone(timezone))
            await res.edit_original_message(file=file, attachments=[])

    @clan.sub_command(name="war-stats", description="Get war stats of players in a clan")
    async def war_stats_clan(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
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

            # is a list of th levels
            if res.values[0].isdigit():
                th_levels = [int(value) for value in res.values]
                if board_type == "Offensive Hitrate":
                    embed = await self.create_offensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date, townhall_level=th_levels)
                elif board_type == "Defensive Rate":
                    embed = await self.create_defensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date, townhall_level=th_levels)
                elif board_type == "Stars Leaderboard":
                    embed = await self.create_stars_leaderboard(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date, townhall_level=th_levels)
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
                    embed = await self.create_offensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date, fresh_type=fresh_type, war_types=war_types)
                elif board_type == "Defensive Rate":
                    embed = await self.create_defensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date, fresh_type=fresh_type, war_types=war_types)
                elif board_type == "Stars Leaderboard":
                    embed = await self.create_stars_leaderboard(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date, fresh_type=fresh_type, war_types=war_types)
                await res.edit_original_message(embed=embed)

            # changing the board type
            elif res.values[0] in ["Offensive Hitrate", "Defensive Rate", "Stars Leaderboard"]:
                board_type = res.values[0]
                if board_type == "Offensive Hitrate":
                    embed = await self.create_offensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date)
                elif board_type == "Defensive Rate":
                    embed = await self.create_defensive_hitrate(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date)
                elif board_type == "Stars Leaderboard":
                    embed = await self.create_stars_leaderboard(clan=clan, players=players, start_timestamp=start_date, end_timestamp=end_date)
                await res.edit_original_message(embed=embed)

    @clan.sub_command(name="ping", description="Ping members in the clan based on different characteristics")
    async def clan_ping(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        await ctx.response.defer()
        embed = disnake.Embed(
            description="Choose the characteristics you would like to ping for below:", color=disnake.Color.green())
        options = []
        members = await self.bot.get_players(tags=[member.tag for member in clan.members])
        ths = set()
        for member in members:  # type: coc.Player
            ths.add(member.town_hall)
        characteristic_types = ["War Opted In",  "War Opted Out",
                                "War Attacks Remaining"] + [f"Townhall {th}" for th in list(ths)]
        for type in characteristic_types:
            options.append(disnake.SelectOption(label=type, value=type))
        select = disnake.ui.Select(
            options=options,
            # the placeholder text to show when no options have been chosen
            placeholder="Select Types to Ping",
            min_values=1,  # the minimum number of options a user must select
            # the maximum number of options a user can select
            max_values=len(characteristic_types),
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await ctx.edit_original_message(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()

        to_ping = set()
        tag_to_name = {}
        tag_to_th = {}
        for player in members:  # type: coc.Player
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
                missing_text += f"{self.bot.fetch_emoji(tag_to_th[player_tag])}{name} | {player_tag}\n"
            else:
                missing_text += f"{self.bot.fetch_emoji(tag_to_th[player_tag])}{name} | {discord_member.mention}\n"
        if missing_text == "":
            missing_text = "No Players Found"

        await res.edit_original_message(embed=None, components=[], content=missing_text)

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

            linked_players_embed = linked_players(
                ctx.guild.members, clan, player_links)
            unlinked_players_embed = unlinked_players(
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

            embed = player_trophy_sort(clan)
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
            values = embed.fields[0].value + \
                f"\nLast Refreshed: <t:{int(time)}:R>"
            embed.set_field_at(0, name="**Not Boosting:**",
                               value=values, inline=False)
            await ctx.edit_original_message(embed=embed)
        elif "clanboard_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.clan_overview(ctx, clan)
            values = embed.fields[-1].value + \
                f"\nLast Refreshed: <t:{int(time)}:R>"
            embed.set_field_at(len(
                embed.fields) - 1, name="**Boosted Super Troops:**", value=values, inline=False)
            await ctx.edit_original_message(embed=embed)
        elif "townhall_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.player_townhall_sort(clan)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "lo_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.create_last_online(clan)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "clangames_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            if len(str(ctx.data.custom_id).split("_")) == 3:
                season = (str(ctx.data.custom_id).split("_"))[-2]
                embed: disnake.Embed = await self.create_clan_games(clan, season)
            else:
                embed: disnake.Embed = await self.create_clan_games(clan)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "donated_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            if len(str(ctx.data.custom_id).split("_")) == 3:
                season = (str(ctx.data.custom_id).split("_"))[-2]
                embed: disnake.Embed = await self.create_donations(clan, type="donated", date=season)
            else:
                embed: disnake.Embed = await self.create_donations(clan, type="donated")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "received_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            if len(str(ctx.data.custom_id).split("_")) == 3:
                season = (str(ctx.data.custom_id).split("_"))[-2]
                embed: disnake.Embed = await self.create_donations(clan, type="received", date=season)
            else:
                embed: disnake.Embed = await self.create_donations(clan, type="received")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "ratio_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            if len(str(ctx.data.custom_id).split("_")) == 3:
                season = (str(ctx.data.custom_id).split("_"))[-2]
                embed: disnake.Embed = await self.create_donations(clan, type="ratio", date=season)
            else:
                embed: disnake.Embed = await self.create_donations(clan, type="received")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "act_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.create_activities(clan)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

    @war_stats_clan.autocomplete("season")
    @clan_donations.autocomplete("season")
    @clan_games.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]

    @clan_capital_raids.autocomplete("clan")
    @linked_clans.autocomplete("clan")
    @player_trophy.autocomplete("clan")
    @war_opt.autocomplete("clan")
    @clan_war_log.autocomplete("clan")
    @clan_super_troops.autocomplete("clan")
    @clan_board.autocomplete("clan")
    @getclan.autocomplete("clan")
    @clan_capital_stats.autocomplete("clan")
    @player_th.autocomplete("clan")
    @clan_compo.autocomplete("clan")
    @last_online.autocomplete("clan")
    @clan_games.autocomplete("clan")
    @clan_donations.autocomplete("clan")
    @last_online_graph.autocomplete("clan")
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

    @last_online_graph.autocomplete("timezone")
    async def timezone_autocomplete(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        all_tz = pytz.common_timezones
        return_list = []
        for tz in all_tz:
            if query.lower() in tz.lower():
                return_list.append(tz)
        return return_list[:25]

    def stat_components(self):
        options = []
        for townhall in reversed(range(6, 16)):
            options.append(disnake.SelectOption(
                label=f"Townhall {townhall}", emoji=self.bot.fetch_emoji(name=townhall), value=str(townhall)))
        th_select = disnake.ui.Select(
            options=options,
            # the placeholder text to show when no options have been chosen
            placeholder="Select Townhalls",
            min_values=1,  # the minimum number of options a user must select
            # the maximum number of options a user can select
            max_values=len(options),
        )

        options = []
        real_types = ["Fresh Hits", "Non-Fresh", "random", "cwl", "friendly"]
        for count, filter in enumerate(["Fresh Hits", "Non-Fresh", "Random Wars", "CWL", "Friendly Wars"]):
            options.append(disnake.SelectOption(
                label=f"{filter}", value=real_types[count]))
        filter_select = disnake.ui.Select(
            options=options,
            # the placeholder text to show when no options have been chosen
            placeholder="Select Filters",
            min_values=1,  # the minimum number of options a user must select
            # the maximum number of options a user can select
            max_values=len(options),
        )

        options = []
        emojis = [self.bot.emoji.sword_clash.partial_emoji,
                  self.bot.emoji.shield.partial_emoji, self.bot.emoji.war_star.partial_emoji]
        for count, type in enumerate(["Offensive Hitrate", "Defensive Rate", "Stars Leaderboard"]):
            options.append(disnake.SelectOption(
                label=f"{type}", emoji=emojis[count], value=type))
        stat_select = disnake.ui.Select(
            options=options,
            # the placeholder text to show when no options have been chosen
            placeholder="Select Stat Type",
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )

        dropdown = [disnake.ui.ActionRow(th_select), disnake.ui.ActionRow(
            filter_select), disnake.ui.ActionRow(stat_select)]
        return dropdown

    async def create_offensive_hitrate(self, clan: coc.Clan, players: list[coc.Player],
                                       townhall_level: list = [], fresh_type: list = [False, True], start_timestamp: int = 0, end_timestamp: int = 9999999999,
                                       war_types: list = ["random", "cwl", "friendly"], war_statuses=["lost", "losing", "winning", "won"]):
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

        ranked = sorted(
            ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
        text = "`# TH  NUM    HR%    NAME       `\n"
        for count, rank in enumerate(ranked, 1):
            spot_emoji = self.bot.get_number_emoji(color="gold", number=count)
            text += f"{spot_emoji}{rank[0]}"
        if len(ranked) == 0:
            text = "No War Attacks Tracked Yet."
        embed = disnake.Embed(title=f"Offensive Hit Rates",
                              description=text, colour=disnake.Color.green())

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
        embed.set_footer(icon_url=clan.badge.url,
                         text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
        return embed

    async def create_defensive_hitrate(self, clan: coc.Clan, players: list[coc.Player],
                                       townhall_level: list = [], fresh_type: list = [False, True], start_timestamp: int = 0, end_timestamp: int = 9999999999,
                                       war_types: list = ["random", "cwl", "friendly"], war_statuses=["lost", "losing", "winning", "won"]):
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

        ranked = sorted(
            ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
        text = "`# TH  NUM    DR%    NAME       `\n"
        for count, rank in enumerate(ranked, 1):
            spot_emoji = self.bot.get_number_emoji(color="gold", number=count)
            text += f"{spot_emoji}{rank[0]}"
        if len(ranked) == 0:
            text = "No War Attacks Tracked Yet."
        embed = disnake.Embed(title=f"Defensive Rates",
                              description=text, colour=disnake.Color.green())

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
        embed.set_footer(icon_url=clan.badge.url,
                         text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
        return embed

    async def create_stars_leaderboard(self, clan: coc.Clan, players: list[coc.Player],
                                       townhall_level: list = [], fresh_type: list = [False, True], start_timestamp: int = 0, end_timestamp: int = 9999999999,
                                       war_types: list = ["random", "cwl", "friendly"], war_statuses=["lost", "losing", "winning", "won"]):
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
            stars = f"{hr.total_stars}/{hr.num_attacks}".center(5)
            destruction = f"{int(hr.total_destruction)}%".ljust(5)
            return [f"{stars} {destruction} {name}\n", round(hr.average_triples * 100, 3), name, hr.total_stars, player.town_hall]

        for player in players:  # type: MyCustomPlayer
            task = asyncio.ensure_future(fetch_n_rank(player=player))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        ranked = [response for response in responses if response is not None]

        ranked = sorted(
            ranked, key=lambda l: (-l[-2], -l[1], l[2]), reverse=False)
        text = "```#   ★     DSTR%  NAME       \n"
        for count, rank in enumerate(ranked, 1):
            #spot_emoji = self.bot.get_number_emoji(color="gold", number=count)
            count = f"{count}.".ljust(3)
            text += f"{count} {rank[0]}"
        text += "```"
        if len(ranked) == 0:
            text = "No War Attacks Tracked Yet."
        embed = disnake.Embed(title=f"Star Leaderboard",
                              description=text, colour=disnake.Color.green())

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
        embed.set_footer(icon_url=clan.badge.url,
                         text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
        return embed
