import disnake
import coc
import random
import string
import pendulum as pend

from classes.bot import CustomClient
from disnake.ext import commands
from datetime import timedelta
from discord.options import convert, autocomplete
from utility.components import create_components, townhall_component, clan_component, role_component
from utility.discord_utils import interaction_handler
from utility.discord_utils import check_commands
from typing import List


class Strikes(commands.Cog, name="Strikes"):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="strike", description="stuff")
    async def strike(self, ctx):
        pass

    @strike.sub_command(name="add", description="Issue strikes to a player")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_add(self, ctx: disnake.ApplicationCommandInteraction,
                         player: coc.Player = commands.Param(converter=convert.player),
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
                          clan=commands.Param(default=None, converter=convert.clan),
                          player=commands.Param(default=None, converter=convert.player),
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


    @commands.slash_command(name="autostrike", description="stuff")
    async def autostrikes(self, ctx):
        pass



    @autostrikes.sub_command(name="add", description="Create autostrikes for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def autostrikes_create(self, ctx: disnake.ApplicationCommandInteraction,
                                 why=commands.Param(
                                     choices=["War Hit Performance (percent)", "Capital Raid Performance (loot)",
                                              "Capital Dono Performance (loot)", "Missed War Hits (hits)",
                                              "Sat Out of War (days)", "Missed Capital Hits (hits)",
                                              "Inactivity (days)", "Clan Games (points)"]),
                                 number: str = commands.Param(name="number"),
                                 weight: int = 1,
                                 rollover_days: int = None):
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



    @strike_add.autocomplete("player")
    @strike_list.autocomplete("player")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names

    @strike_list.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id}).sort("name", 1)
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        return clan_list[0:25]





def setup(bot: CustomClient):
    bot.add_cog(Strikes(bot))