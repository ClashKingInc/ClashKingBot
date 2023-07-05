from disnake.ext import commands
import disnake
from utils.components import create_components, townhall_component, clan_component, role_component
from utils.discord_utils import interaction_handler
from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from main import check_commands
from datetime import timedelta
import pytz

utc = pytz.utc
import coc
import random
import string
from main import scheduler
from typing import List


class Strikes(commands.Cog, name="Strikes"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    async def player_converter(self, player_tag: str):
        player = await self.bot.getPlayer(player_tag=player_tag, raise_exceptions=True)
        return player

    @commands.slash_command(name="strike", description="stuff")
    async def strike(self, ctx):
        pass

    @strike.sub_command(name="add", description="Issue strikes to a player")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_add(self, ctx: disnake.ApplicationCommandInteraction,
                         player: coc.Player = commands.Param(converter=player_converter),
                         reason: str = commands.Param(name="reason"),
                         rollover_days: int = commands.Param(name="rollover_days", default=None),
                         strike_weight: int = commands.Param(name="strike_weight", default=1)):
        """
            Parameters
            ----------
            player: player to issue a strike to
            reason: reason for strike
            rollover_days: number of days until this strike is removed (auto), (default - never)
            strike_weight: number of strikes this should count as (default 1)
        """
        await ctx.response.defer()
        embed = await self.strike_player(ctx, player, reason, rollover_days, strike_weight)
        await ctx.edit_original_message(embed=embed)

    @strike.sub_command(name='list', description="List of server (or clan) striked players")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_list(self, ctx: disnake.ApplicationCommandInteraction,
                          view=commands.Param(choices=["Strike View", "Player View"]),
                          clan=commands.Param(default=None, converter=clan_converter),
                          player=commands.Param(default=None, converter=player_converter),
                          strike_amount: int = commands.Param(default=1)):
        """
            Parameters
            ----------
            view: show in strike view (each strike individually) or by player
            clan: clan to pull strikes for
            player: player to pull_strikes for
            strike_amount: only show strikes with more than this amount (only for player view)
        """
        if clan is not None:
            results = await self.bot.clan_db.find_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        await ctx.response.defer()
        embeds = await self.create_embeds(ctx=ctx, strike_clan=clan, strike_player=player, view=view, strike_amount=strike_amount)
        if embeds == []:
            embed = disnake.Embed(
                description="No striked players on this server.",
                color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
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

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)

    @strike.sub_command(name="remove", description="Remove a strike by ID")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_remove(self, ctx: disnake.ApplicationCommandInteraction, strike_id: str):
        strike_id = strike_id.upper()
        result_ = await self.bot.strikelist.find_one({"$and": [
            {"strike_id": strike_id},
            {"server": ctx.guild.id}
        ]})
        if result_ is None:
            embed = disnake.Embed(description=f"Strike with ID {strike_id} does not exist.", color=disnake.Color.red())
            return await ctx.send(embed=embed)
        await self.bot.strikelist.delete_one({"$and": [
            {"strike_id": strike_id},
            {"server": ctx.guild.id}
        ]})
        embed = disnake.Embed(description=f"Strike {strike_id} removed.", color=disnake.Color.green())
        return await ctx.send(embed=embed)

    '''@commands.slash_command(name="autostrike", description="stuff")
    async def autostrikes(self, ctx):
        pass

    def gen_percent(self):
        return [f"{x}%" for x in range(1, 101)]

    def gen_capital_gold(self):
        return [f"Under {x} Capital Gold" for x in range(5000, 105000, 5000)]

    def gen_missed_hits_war(self):
        return ["Per Missed Hit"]

    def gen_missed_hits_capital(self):
        return ["1+ hit", "2+ hits", "3+ hits", "4+ hits", "5+ hits"]

    def gen_days(self):
        return [f"{x} days" for x in range(1, 31)]

    def gen_points(self):
        return [f"Under {x} points" for x in range(500, 4500, 500)]

    @autostrikes.sub_command(name="create", description="Create autostrikes for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def autostrikes_create(self, ctx: disnake.ApplicationCommandInteraction,
                                 type=commands.Param(
                                     choices=["War Hit Performance (percent)", "Capital Raid Performance (loot)",
                                              "Capital Dono Performance (loot)", "Missed War Hits (hits)",
                                              "Sat Out of War (days)", "Missed Capital Hits (hits)",
                                              "Inactivity (days)", "Clan Games (points)"]),
                                 number: str = commands.Param(name="number"),
                                 weight: int = 1, rollover_days: int = None):
        """
            Parameters
            ----------
            type: type of autostrike
            number: can be days, percent, etc, to strike for
            weight: (default 1) weight to give these infractions
            rollover_days: (default forever) days to keep this strike around
        """

        await ctx.response.defer()
        # clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        clan_tags = await self.bot.clan_db.distinct("tag")
        clans = await self.bot.get_clans(tags=clan_tags[:50])
        clan_page = 0
        clan_dropdown = clan_component(bot=self.bot, all_clans=clans, clan_page=clan_page)
        th_dropdown = townhall_component(bot=self.bot)
        role_dropdown = role_component()

        page_buttons = [
            disnake.ui.Button(label="Save", emoji=self.bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green,
                              custom_id="Save")
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)
        embed = disnake.Embed(title="**Choose options/filters**")
        next_footer = f"{type} AutoStrike | Weight: {weight} | Rollover Days: {rollover_days}"
        embed.set_footer(text=f"{next_footer}\nBy default, autostrikes apply to all th's and roles")
        clans_chosen = []
        ths_chosen = []
        roles_chosen = []
        await ctx.send(embed=embed, components=[clan_dropdown, th_dropdown, role_dropdown, page_buttons])
        message = await ctx.original_message()
        save = False
        while not save:
            try:
                res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, msg=message)
            except:
                return await message.edit(components=[])
            if "button" in str(res.data.component_type):
                if not clans_chosen:
                    await res.send(content="Must select at least one clan", ephemeral=True)
                else:
                    save = True
            elif "string_select" in str(res.data.component_type):
                if "th_" in res.values[0]:
                    ths_chosen = [int(th.split("_")[-1]) for th in res.values]
                    embed.description = self.chosen_text(clans=clans_chosen, ths=ths_chosen, roles=roles_chosen)
                    await message.edit(embed=embed)
                elif any("clanpage_" in s for s in res.values):
                    clan_page = int(next(value for value in res.values if "clanpage_" in value).split("_")[-1])
                    clan_dropdown = clan_component(bot=self.bot, all_clans=clans, clan_page=clan_page)
                    await message.edit(embed=embed,
                                       components=[clan_dropdown, th_dropdown, role_dropdown, page_buttons])
                elif any("clantag_" in s for s in res.values):
                    clan_tags = [tag.split('_')[-1] for tag in res.values if "clantag_" in tag]
                    for tag in clan_tags:
                        clan = coc.utils.get(clans, tag=tag)
                        if clan in clans_chosen:
                            clans_chosen.remove(clan)
                        else:
                            clans_chosen.append(clan)
                    embed.description = self.chosen_text(clans=clans_chosen, ths=ths_chosen, roles=roles_chosen)
                    await message.edit(embed=embed)
                else:
                    roles_chosen = res.values
                    embed.description = self.chosen_text(clans=clans_chosen, ths=ths_chosen, roles=roles_chosen)
                    await message.edit(embed=embed)

        for clan in clans_chosen:
            await self.bot.autostrikes.insert_one({

            })
        embed.title = "**AutoStrikes Saved**"
        embed._colour = disnake.Color.green()
        embed.set_footer(text=next_footer)
        await message.edit(components=[], embed=embed)

    def chosen_text(self, clans: List[coc.Clan], ths, roles):
        text = ""
        if clans:
            text += "**CLANS:**\n"
            for clan in clans:
                text += f"• {clan.name} ({clan.tag})\n"
        if ths:
            text += "**THS:**\n"
            for th in ths:
                text += f"• {self.bot.fetch_emoji(name=th)} TH{th}\n"
        if roles:
            text += "**ROLES:**\n"
            for role in roles:
                text += f"• {role}\n"
        return text

    @autostrikes_create.autocomplete("number")
    async def number_gen(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        filled_option = ctx.filled_options["type"]
        if filled_option == "":
            return []

        if filled_option == "War Hit Performance (percent)":
            list_options = self.gen_percent()
        elif filled_option == "Capital Raid Performance (loot)":
            list_options = self.gen_capital_gold()
        elif filled_option == "Capital Dono Performance (loot)":
            list_options = self.gen_capital_gold()
        elif filled_option == "Missed War Hits (hits)":
            list_options = self.gen_missed_hits_war()
        elif filled_option == "Sat Out of War (days)":
            list_options = self.gen_days()
        elif filled_option == "Missed Capital Hits (hits)":
            list_options = self.gen_missed_hits_capital()
        elif filled_option == "Inactivity (days)":
            list_options = self.gen_days()
        elif filled_option == "Clan Games (points)":
            list_options = self.gen_points()

        return [option for option in list_options if query.lower() in option.lower()][:25]

    @autostrikes.sub_command(name="remove", description="Remove autostrikes for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def autostrikes_add(self, ctx: disnake.ApplicationCommandInteraction):
        pass
    '''

    @strike_add.autocomplete("player")
    @strike_list.autocomplete("player")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names

    async def add_autostrike(self, guild: disnake.Guild, autostrike_type: str, basic_filter: float, weight: int,
                             rollover_days: int):
        pass

    async def strike_player(self, ctx, player: coc.Player, reason: str, rollover_days, strike_weight):
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")

        source = string.ascii_letters
        strike_id = str(''.join((random.choice(source) for i in range(5)))).upper()

        is_used = await self.bot.strikelist.find_one({"strike_id": strike_id})
        while is_used is not None:
            strike_id = str(''.join((random.choice(source) for i in range(5)))).upper()
            is_used = await self.bot.strikelist.find_one({"strike_id": strike_id})

        if rollover_days is not None:
            now = datetime.utcnow().replace(tzinfo=utc)
            rollover_days = now + timedelta(rollover_days)
            rollover_days = int(rollover_days.timestamp())

        await self.bot.strikelist.insert_one({
            "tag": player.tag,
            "date_created": dt_string,
            "reason": reason,
            "server": ctx.guild.id,
            "added_by": ctx.author.id,
            "strike_weight": strike_weight,
            "rollover_date": rollover_days,
            "strike_id": strike_id
        })

        results = await self.bot.strikelist.find({"$and": [
            {"tag": player.tag},
            {"server": ctx.guild.id}
        ]}).to_list(length=100)
        num_strikes = sum([result.get("strike_weight") for result in results])

        if rollover_days is not None:
            rollover_days = f"<t:{rollover_days}:f>"
        else:
            rollover_days = "Never"
        embed = disnake.Embed(
            description=f"**Strike added to [{player.name}]({player.share_link}) by {ctx.author.mention}.**\n"
                        f"Strike Weight: {strike_weight}, Total Strikes Now: {num_strikes}\n"
                        f"Rollover: {rollover_days}\n"
                        f"Reason: {reason}",
            color=disnake.Color.green())
        embed.set_footer(text=f"Strike ID: {strike_id}")
        return embed

    async def create_embeds(self, ctx, strike_clan, view, strike_amount, strike_player=None):
        text = []
        hold = ""
        num = 0
        tags = await self.bot.strikelist.distinct("tag", filter={"server": ctx.guild.id})
        all = self.bot.strikelist.find({"server": ctx.guild.id}).sort("date_created", 1)
        limit = await self.bot.strikelist.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return []

        players = await self.bot.get_players(tags=tags, custom=False)
        if view == "Strike View":
            for strike in await all.to_list(length=limit):
                tag = strike.get("tag")
                player = coc.utils.get(players, tag=tag)
                if player is None:
                    continue
                if strike_clan is not None:
                    if player.clan is None:
                        continue
                    if player.clan.tag != strike_clan.tag:
                        continue
                if strike_player is not None:
                    if strike_player.tag != player.tag:
                        continue
                name = player.name
                for char in ["`", "*", "_", "~", "´"]:
                    name = name.replace(char, "", len(player.name))
                date = strike.get("date_created")
                date = date[:10]
                reason = strike.get("reason")

                added_by = ""
                if strike.get("added_by") is not None:
                    user = await self.bot.getch_user(strike.get("added_by"))
                    added_by = f"{user}"
                clan = f"{player.clan.name}, {str(player.role)}" if player.clan is not None else "No Clan"

                rollover_days = strike.get("rollover_date")
                if rollover_days is not None:
                    rollover_days = f"<t:{rollover_days}:f>"
                else:
                    rollover_days = "Never"

                hold += f"{self.bot.fetch_emoji(player.town_hall)}[{name}]({player.share_link}) | {player.tag}\n" \
                        f"{clan} | ID: {strike.get('strike_id')}\n" \
                        f"Added on: {date}, by {added_by}\n" \
                        f"Rollover Date: {rollover_days}\n" \
                        f"*{reason}*\n\n"
                num += 1
                if num == 10:
                    text.append(hold)
                    hold = ""
                    num = 0

        elif view == "Player View":
            for tag in tags:
                player = coc.utils.get(players, tag=tag)
                if player is None:
                    continue
                if strike_clan is not None:
                    if player.clan is None:
                        continue
                    if player.clan.tag != strike_clan.tag:
                        continue
                if strike_player is not None:
                    if strike_player.tag != player.tag:
                        continue
                name = player.name
                for char in ["`", "*", "_", "~", "´"]:
                    name = name.replace(char, "", len(player.name))

                results = await self.bot.strikelist.find({"$and": [
                    {"tag": tag},
                    {"server": ctx.guild.id}
                ]}).sort("date_created", 1).to_list(length=100)

                total_strike_weight = sum([result.get("strike_weight") for result in results if (r := (result.get("rollover_date") if result.get("rollover_date") is not None else 9999999999999)) >= int(datetime.now().timestamp())])
                num_strikes = len(results)
                if num_strikes < strike_amount:
                    continue
                strike_reason_ids = "\n".join(
                    [f"`{result.get('strike_id')}` - {result.get('reason')}" for result in results])
                most_recent = results[0].get("date_created")[:10]
                clan = f"{player.clan.name}, {str(player.role)}" if player.clan is not None else "No Clan"

                hold += f"{self.bot.fetch_emoji(player.town_hall)}[{name}]({player.share_link}) | {clan}\n" \
                        f"Most Recent Strike: {most_recent}\n" \
                        f"\# of Strikes: {num_strikes}, Weight: {total_strike_weight}\nStrikes:\n" \
                        f"{strike_reason_ids}\n\n"
                num += 1
                if num == 10:
                    text.append(hold)
                    hold = ""
                    num = 0

        if num != 0:
            text.append(hold)

        embeds = []
        for t in text:
            embed = disnake.Embed(title=f"{ctx.guild.name} Strike List",
                                  description=t,
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)

        return embeds


def setup(bot: CustomClient):
    bot.add_cog(Strikes(bot))