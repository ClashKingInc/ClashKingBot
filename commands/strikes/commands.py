import coc
import disnake
import pendulum as pend
from disnake.ext import commands

from classes.bot import CustomClient
from discord.options import autocomplete, convert
from utility.components import create_components
from utility.discord_utils import check_commands

from .utils import add_strike, create_embeds


class Strikes(commands.Cog, name='Strikes'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='strike', description='stuff')
    async def strike(self, ctx):
        await ctx.response.defer()

    @strike.sub_command(name='add', description='Issue strikes to a player')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_add(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        player: coc.Player = commands.Param(converter=convert.player, autocomplete=autocomplete.family_players),
        reason: str = commands.Param(name='reason'),
        rollover_days: int = commands.Param(default=None),
        strike_weight: int = commands.Param(default=1),
        dm_player: str = commands.Param(default=None),
    ):
        """
        Parameters
        ----------
        player: player to issue a strike to
        reason: reason for strike
        rollover_days: number of days until this strike is removed (auto), (default - never)
        strike_weight: number of strikes this should count as (default 1)
        """
        embed = await add_strike(
            bot=self.bot,
            player=player,
            added_by=ctx.author,
            guild=ctx.guild,
            reason=reason,
            rollover_days=rollover_days,
            strike_weight=strike_weight,
            dm_player=dm_player,
        )
        await ctx.edit_original_message(embed=embed)

    @strike.sub_command(name='list', description='List of server (or clan) striked players')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_list(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        view: str = commands.Param(choices=['Strike View', 'Player View']),
        clan: coc.Clan = commands.Param(default=None, converter=convert.clan, autocomplete=autocomplete.clan),
        user: disnake.Member = None,
        strike_amount: int = commands.Param(default=1),
        view_expired_strikes: bool = commands.Param(default=False, converter=convert.basic_bool, choices=['True', 'False']),
        view_non_family: bool = commands.Param(default=False, converter=convert.basic_bool, choices=['True', 'False']),
    ):
        """
        Parameters
        ----------
        view: show in strike view (each strike individually) or by player
        clan: clan to pull strikes for
        user: discord user to pull strikes for
        strike_amount: only show those with more strikes than this amount (only for player view)
        view_expired_strikes: view strikes that have rolled over
        view_non_family: view strikes of players that aren't in your clans anymore
        """

        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild.id)
        embeds = await create_embeds(
            bot=self.bot,
            guild=ctx.guild,
            view=view,
            strike_clan=clan,
            strike_user=user,
            strike_amount=strike_amount,
            view_non_family=view_non_family or (user is not None),
            view_expired_strikes=view_expired_strikes,
            embed_color=embed_color,
        )

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', check=check, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == 'Previous':
                current_page -= 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == 'Next':
                current_page += 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == 'Print':
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)

    @strike.sub_command(name='remove', description='Remove a strike by ID')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_remove(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        strike_id: str = commands.Param(converter=None, autocomplete=autocomplete.strike_ids, default=None),
    ):
        strike_id = strike_id.split('|')[0].strip()
        strike_id = strike_id.upper()
        result_ = await self.bot.strikelist.find_one({'$and': [{'strike_id': strike_id}, {'server': ctx.guild.id}]})
        if result_ is None:
            embed = disnake.Embed(
                description=f'Strike with ID {strike_id} does not exist.',
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed)
        await self.bot.strikelist.delete_one({'$and': [{'strike_id': strike_id}, {'server': ctx.guild.id}]})
        embed = disnake.Embed(description=f'Strike {strike_id} removed.', color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @strike.sub_command_group(name="clear", description="Clear strikes from a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clear(self, ctx: disnake.ApplicationCommandInteraction):
        pass  # container only, never called directly

    @clear.sub_command(name='all', description='Remove all strikes from a clan')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_clear_all(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            clan=commands.Param(default=None, converter=convert.clan, autocomplete=autocomplete.clan),
    ):
        clan_tag = clan.tag
        result_ = await self.bot.strikelist.find_one({
            '$and': [{'clan': clan_tag}, {'server': ctx.guild.id}]
        })

        if result_ is None:
            embed = disnake.Embed(
                description=f'All strikes in {clan} cleared.',
                color=disnake.Color.red(),
            )
            return await ctx.send(embed=embed)

        delete_result = await self.bot.strikelist.delete_many({
            '$and': [{'clan': clan_tag}, {'server': ctx.guild.id}]
        })

        embed = disnake.Embed(
            description=f'Cleared {delete_result.deleted_count} strikes from {clan_tag}.',
            color=disnake.Color.orange()
        )
        return await ctx.send(embed=embed)

    @clear.sub_command(name='date', description='Remove clan strikes in a date range')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def strike_clear_date(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            clan=commands.Param(default=None, converter=convert.clan, autocomplete=autocomplete.clan),
            time_range: str = commands.Param(
                choices=["Last Week", "Last Month", "Last 90 Days"],
                default="Last Week"
            ),
    ):
        now = pend.now("UTC")

        if time_range == "Last Week":
            cutoff = now.subtract(weeks=1)
        elif time_range == "Last Month":
            cutoff = now.subtract(months=1)
        else:
            cutoff = now.subtract(days=90)

        cutoff_timestamp = cutoff.to_datetime_string()

        result_ = await self.bot.strikelist.find_one({
            "$and": [
                {"clan": clan, "server": ctx.guild.id},
                {"date_created": {"$gte": cutoff_timestamp}}
            ]
        })

        if result_ is None:
            embed = disnake.Embed(
                description=f"No strikes found for {clan} in selected time range.",
                color=disnake.Color.red()
            )
            return await ctx.send(embed=embed)

        delete_result = await self.bot.strikelist.delete_many({
            "$and": [
                {"clan": clan, "server": ctx.guild.id},
                {"date_created": {"$gte": cutoff_timestamp}}
            ]
        })

        embed = disnake.Embed(
            description=f"Deleted {delete_result.deleted_count} strikes from {clan} from the {time_range.lower()}.",
            color=disnake.Color.green()
        )
        return await ctx.send(embed=embed)

    """@commands.slash_command(name='autostrike', description='stuff')
    async def autostrikes(self, ctx):
        pass

    @autostrikes.sub_command(name='war', description='Create autostrike for missing war attacks')
    async def war_autostrikes(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        war_type: str = commands.Param(choices=['War', 'CWL', 'Both']),
        weight: int = commands.Param(ge=1, le=25),
        rollover_days: int = commands.Param(ge=1, le=365, default=None),
        clan: coc.Clan = commands.Param(default=None, autocomplete=autocomplete.clan, converter=convert.clan),
    ):
        raise MessageException('Command under construction')"""

    '''@autostrikes.sub_command(name="add", description="Create autostrikes for your server")
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


    @autostrikes.sub_command(name="remove", description="Remove autostrikes for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def autostrikes_add(self, ctx: disnake.ApplicationCommandInteraction):
        pass'''


def setup(bot: CustomClient):
    bot.add_cog(Strikes(bot))
