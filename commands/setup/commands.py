from typing import Union

import coc
import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from classes.DatabaseClient.Classes.settings import DatabaseClan
from discord import autocomplete, convert, options
from exceptions.CustomExceptions import *
from utility.components import clan_component
from utility.discord_utils import check_commands, get_webhook_for_channel, interaction_handler
from utility.general import calculate_time, get_guild_icon

from .utils import add_clan


class SetupCommands(commands.Cog, name='Setup'):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.color = disnake.Color.dark_theme()

    @commands.slash_command(name='setup')
    async def setup(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @setup.sub_command(name='server', description='Set settings for your server')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def server_settings(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        ban_log_channel: Union[disnake.TextChannel, disnake.Thread] = None,
        strike_log_channel: disnake.TextChannel | disnake.Thread = None,
        change_nicknames: str = commands.Param(default=None, choices=['On', 'Off']),
        family_nickname_convention: str = commands.Param(default=None),
        non_family_nickname_convention: str = commands.Param(default=None),
        flair_non_family: str = commands.Param(default=None, choices=['True', 'False']),
        api_token: str = commands.Param(default=None, choices=['Use', "Don't Use"]),
        leadership_eval: str = commands.Param(default=None, choices=['True', 'False']),
        full_whitelist_role: disnake.Role = None,
        embed_color: str = commands.Param(default=None, converter=convert.hex_code),
        followed_reddit_accounts: str = None,
    ):
        """
        Parameters
        ----------
        change_nicknames: whether or not the bot should change nicknames
        full_whitelist_role: role that can run any command on the bot in your server
        followed_reddit_accounts: must have reddit feed set up, a comma seperated list of reddit accounts to follow
        """

        await ctx.response.defer()
        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
        changed_text = ''
        if ban_log_channel is not None:
            await db_server.set_banlist_channel(id=ban_log_channel.id)
            changed_text += f'- **Ban Log Channel:** {ban_log_channel.mention}\n'
        if strike_log_channel is not None:
            await db_server.set_strike_log_channel(id=strike_log_channel.id)
            changed_text += f'- **Strike Log Channel:** {strike_log_channel.mention}\n'
        if api_token is not None:
            await db_server.set_api_token(status=(api_token == 'Use'))
            changed_text += f'- **Api Token:** `{api_token}`\n'
        if leadership_eval is not None:
            await db_server.set_leadership_eval(status=(leadership_eval == 'True'))
            changed_text += f'- **Leadership Eval:** `{leadership_eval}`\n'
        if embed_color is not None:
            await db_server.set_hex_code(hex_code=embed_color)
            changed_text += f'- **Embed Color:** `{embed_color}`\n'
        if change_nicknames is not None:
            await db_server.set_change_nickname(status=(change_nicknames == 'On'))
            changed_text += f'- **Change Nicknames:** `{change_nicknames}`\n'
        if family_nickname_convention is not None:
            if '{discord_display_name}' in family_nickname_convention and family_nickname_convention != '{discord_display_name}':
                raise MessageException('{discord_display_name} must be used by itself in a convention}')
            await db_server.set_family_nickname_convention(rule=family_nickname_convention)
            changed_text += f'- **Family Nickname Convention:** `{family_nickname_convention}`\n'
        if non_family_nickname_convention is not None:
            if '{discord_display_name}' in non_family_nickname_convention and non_family_nickname_convention != '{discord_display_name}':
                raise MessageException('{discord_display_name} must be used by itself in a convention}')
            await db_server.set_non_family_nickname_convention(rule=non_family_nickname_convention)
            changed_text += f'- **Non Family Nickname Convention:** `{non_family_nickname_convention}`\n'
        if flair_non_family is not None:
            await db_server.set_flair_non_family(option=(flair_non_family == 'True'))
            changed_text += f'- **Assign Flair Roles to Non-Family:** `{flair_non_family}`\n'
        if full_whitelist_role is not None:
            if full_whitelist_role.is_default():
                raise MessageException('Full Whitelist Role cannot be `@everyone`')
            await db_server.set_full_whitelist_role(id=full_whitelist_role.id)
            changed_text += f'- **Full Whitelist Role:** `{full_whitelist_role.mention}`\n'
        if followed_reddit_accounts is not None:
            reddit_accounts = followed_reddit_accounts.split(',')
            await self.bot.server_db.update_one(
                {'server': ctx.guild.id},
                {'$set': {'reddit_accounts': reddit_accounts}},
            )
            changed_text += f'- **Followed Reddit Accounts:** `{followed_reddit_accounts}`\n'

        if changed_text == '':
            changed_text = 'No Changes Made!'
        embed = disnake.Embed(
            title=f'{ctx.guild.name} Settings Changed',
            description=changed_text,
            color=disnake.Color.green(),
        )
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.edit_original_message(embed=embed)

    @setup.sub_command(name='clan', description='Set settings for a clan')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clan_settings(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.clan,
        member_role: disnake.Role = commands.Param(description='Role assigned to clan members', default=None),
        leadership_role: disnake.Role = commands.Param(description='Role assigned to clan coleads + leader', default=None),
        clan_channel: Union[disnake.TextChannel, disnake.Thread] = commands.Param(default=None, description='Channel where ban & welcome messages go'),
        greeting: str = commands.Param(autocomplete=autocomplete.embeds, default=None),
        auto_greet: str = commands.Param(choices=['Never', 'First Join', 'Every Join'], default=None),
        category: str = commands.Param(default=None, autocomplete=autocomplete.category),
        ban_alert_channel: Union[disnake.TextChannel, disnake.Thread] = None,
        clan_abbreviation: str = None,
        strike_button=commands.Param(default=None, choices=['True', 'False']),
        ban_button=commands.Param(default=None, choices=['True', 'False']),
        profile_button=commands.Param(default=None, choices=['True', 'False']),
    ):
        """
        Parameters
        ----------
        clan_abbreviation: used in nickname conventions
        """

        await ctx.response.defer()
        results = await self.bot.clan_db.find_one({'$and': [{'tag': clan.tag}, {'server': ctx.guild.id}]})
        if results is None:
            raise ThingNotFound('**This clan is not set up on this server. Use `/addclan` to get started.**')
        db_clan = DatabaseClan(bot=self.bot, data=results)
        changed_text = ''

        if greeting is not None:
            lookup = await self.bot.custom_embeds.find_one({'$and': [{'server': ctx.guild_id}, {'name': greeting}]})
            if lookup is None:
                raise MessageException('No embed/message with that name found on this server')
            await db_clan.set_greeting(text=greeting)
            changed_text += f'- **Greeting set to the embed/message:** {greeting}'
        if member_role is not None:
            await db_clan.set_member_role(id=member_role.id)
            changed_text += f'- **Member Role:** {member_role.mention}\n'
        if auto_greet is not None:
            await db_clan.set_auto_greet(option=auto_greet)
            changed_text += f'- **Auto Greet:** {auto_greet}\n'
        if leadership_role is not None:
            await db_clan.set_leadership_role(id=leadership_role.id)
            changed_text += f'- **Leadership Role:** {leadership_role.mention}\n'
        if clan_channel is not None:
            await db_clan.set_clan_channel(id=clan_channel.id)
            changed_text += f'- **Clan Channel:** {clan_channel.mention}\n'
        if category is not None:
            await db_clan.set_category(category=category)
            changed_text += f'- **Category:** `{category}`\n'
        if ban_alert_channel is not None:
            await db_clan.set_ban_alert_channel(id=ban_alert_channel.id)
            changed_text += f'- **Ban Alert Channel:** {ban_alert_channel.mention}\n'
        if clan_abbreviation is not None:
            await db_clan.set_nickname_label(abbreviation=clan_abbreviation[:16])
            changed_text += f'- **Clan Abbreviation:** `{clan_abbreviation[:16]}`\n'
        if strike_button is not None:
            await db_clan.set_strike_button(set=(strike_button == 'True'))
            changed_text += f'- **Strike Button:** `{strike_button}`\n'
        if ban_button is not None:
            await db_clan.set_ban_button(set=(ban_button == 'True'))
            changed_text += f'- **Ban Button:** `{ban_button}`\n'
        if profile_button is not None:
            await db_clan.set_profile_button(set=(profile_button == 'True'))
            changed_text += f'- **Profile Button:** `{profile_button}`\n'
        if changed_text == '':
            changed_text = 'No Changes Made!'
        embed = disnake.Embed(
            title=f'{clan.name} Settings Changed',
            description=changed_text,
            color=disnake.Color.green(),
        )
        embed.set_thumbnail(url=clan.badge.url)
        await ctx.edit_original_message(embed=embed)

    @setup.sub_command(
        name='member-count-warning',
        description='Set a warning when member count gets to a certain level',
    )
    async def member_count_warning(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.clan,
        below: int = commands.Param(default=0),
        above: int = commands.Param(default=0),
        ping: disnake.Role = None,
        channel: Union[disnake.TextChannel, disnake.Thread] = None,
    ):
        if channel is None:
            channel = ctx.channel
        results = await self.bot.clan_db.find_one({'$and': [{'tag': clan.tag}, {'server': ctx.guild.id}]})
        if results is None:
            raise ThingNotFound('**This clan is not set up on this server. Use `/addclan` to get started.**')
        db_clan = DatabaseClan(bot=self.bot, data=results)
        await db_clan.member_count_warning.set_above(num=above)
        await db_clan.member_count_warning.set_below(num=below)
        await db_clan.member_count_warning.set_channel(id=channel.id)
        if ping is not None:
            await db_clan.member_count_warning.set_role(id=ping.id)

        text = f'Member Count Warning for {clan.name}({clan.tag}) set in {channel.id}. Will warn when reaching {below} & {above}.'
        if ping is not None:
            text += f' Will ping {ping.mention}.'
        embed = disnake.Embed(description=text, color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.url)
        await ctx.edit_original_message(embed=embed)

    @setup.sub_command(
        name='user-settings',
        description='Set bot settings for yourself like main account or timezone',
    )
    async def user_settings(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        user: disnake.Member,
        default_main_account: coc.Player = commands.Param(
            default=None,
            converter=convert.player,
            autocomplete=autocomplete.user_accounts,
        ),
        server_main_account: coc.Player = commands.Param(
            default=None,
            converter=convert.player,
            autocomplete=autocomplete.user_accounts,
        ),
        private_mode: str = commands.Param(default=None, choices=['True', 'False']),
    ):
        await ctx.response.defer()
        if user.id != ctx.user.id and not (
            ctx.user.guild_permissions.manage_guild or self.bot.white_list_check(ctx=ctx, command_name='setup user-settings')
        ):
            raise MessageException('Missing permissions to run this command. Must have `Manage Server` Perms or be whitelisted `/whitelist add`')

        changed_text = ''
        if private_mode is not None and ctx.user.id == user.id:
            changed_text += f'Private mode set to `{private_mode}`\n'
            await self.bot.user_settings.update_one(
                {'discord_user': user.id},
                {'$set': {'private_mode': (private_mode == 'True')}},
                upsert=True,
            )
        if default_main_account is not None and ctx.user.id == user.id:
            changed_text += f'Default Main Account set to `{default_main_account.name} ({default_main_account.tag})`\n'
            await self.bot.user_settings.update_one(
                {'discord_user': user.id},
                {'$set': {'main_account': default_main_account.tag}},
                upsert=True,
            )
        if server_main_account is not None:
            changed_text += f'Server Main Account set to `{server_main_account.name} ({server_main_account.tag})`\n'
            await self.bot.user_settings.update_one(
                {'discord_user': user.id},
                {'$set': {f'server_main_account.{ctx.guild.id}': server_main_account.tag}},
                upsert=True,
            )
        embed = disnake.Embed(
            title=f'{user.name} Settings Changed',
            description=changed_text,
            color=disnake.Color.green(),
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @setup.sub_command(name='list', description='List of setup & settings')
    async def settings_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)

        clans = await self.bot.get_clans(tags=[c.tag for c in db_server.clans])
        clans.sort(key=lambda x: x.name)

        embed = disnake.Embed(title=f'{ctx.guild.name} Server Settings', color=db_server.embed_color)
        banlist_channel = f'<#{db_server.banlist_channel}>' if db_server.banlist_channel is not None else None
        reddit_feed = f'<#{db_server.reddit_feed}>' if db_server.reddit_feed is not None else None

        embed.add_field(name='Banlist Channel:', value=banlist_channel, inline=True)
        embed.add_field(name='Reddit Feed:', value=reddit_feed, inline=True)
        embed.add_field(name='Leadership Eval:', value=f'{db_server.leadership_eval}', inline=True)
        embed.add_field(name='Use API Token:', value=f'{db_server.use_api_token}', inline=True)
        embed.add_field(name='Nickname Setting:', value=f'{db_server.change_nickname}', inline=True)

        dropdown = [clan_component(bot=self.bot, all_clans=clans, clan_page=0, max_choose=1)]

        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        async def create_settings_embed(clan: DatabaseClan, got_clan: coc.Clan):
            embed = disnake.Embed(title=f'{clan.name}', color=db_server.embed_color)
            embed.set_thumbnail(url=got_clan.badge.url)
            member_role = f'<@&{clan.member_role}>' if clan.member_role is not None else None
            leader_role = f'<@&{clan.leader_role}>' if clan.leader_role is not None else None
            clan_channel = f'<#{clan.clan_channel}>' if clan.clan_channel is not None else None
            embed.add_field(name='Member Role:', value=member_role, inline=True)
            embed.add_field(name='Leadership Role:', value=leader_role, inline=True)
            embed.add_field(name='Clan Channel:', value=clan_channel, inline=True)
            if clan.greeting:
                embed.add_field(name='Greeting:', value=f'{clan.greeting}', inline=True)

            embed.add_field(
                name='Join Log:',
                value=f'{(await clan.join_log.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Leave Log:',
                value=f'{(await clan.leave_log.get_webhook_channel_mention())}',
                inline=True,
            )

            embed.add_field(
                name='War Log:',
                value=f'{(await clan.war_log.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='War Panel:',
                value=f'{(await clan.war_panel.get_webhook_channel_mention())}',
                inline=True,
            )

            embed.add_field(
                name='Capital Dono Log:',
                value=f'{(await clan.capital_donations.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Capital Atk Log:',
                value=f'{(await clan.capital_attacks.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Capital Weekly Summary:',
                value=f'{(await clan.capital_weekly_summary.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Capital Raid Panel:',
                value=f'{(await clan.raid_panel.get_webhook_channel_mention())}',
                inline=True,
            )

            embed.add_field(
                name='Donation Log:',
                value=f'{(await clan.donation_log.get_webhook_channel_mention())}',
                inline=True,
            )

            embed.add_field(
                name='Super Troop Boost Log:',
                value=f'{(await clan.super_troop_boost_log.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Role Change Log:',
                value=f'{(await clan.role_change.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Troop Upgrade Log:',
                value=f'{(await clan.troop_upgrade.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='TH Upgrade Log:',
                value=f'{(await clan.th_upgrade.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='League Change Log:',
                value=f'{(await clan.league_change.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Spell Upgrade Log:',
                value=f'{(await clan.spell_upgrade.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Hero Upgrade Log:',
                value=f'{(await clan.hero_upgrade.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Name Change Log:',
                value=f'{(await clan.name_change.get_webhook_channel_mention())}',
                inline=True,
            )

            embed.add_field(
                name='Legend Atk Log:',
                value=f'{(await clan.legend_log_attacks.get_webhook_channel_mention())}',
                inline=True,
            )
            embed.add_field(
                name='Legend Def Log:',
                value=f'{(await clan.legend_log_defenses.get_webhook_channel_mention())}',
                inline=True,
            )

            return embed

        await ctx.edit_original_message(embed=embed, components=dropdown)
        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            if 'clanpage_' in res.values[0]:
                page = int(res.values[0].split('_')[-1])
                dropdown = [clan_component(bot=self.bot, all_clans=clans, clan_page=page, max_choose=1)]
                await res.edit_original_message(components=dropdown)
                continue
            clan_tag = res.values[0].split('_')[-1]
            got_clan: coc.Clan = coc.utils.get(clans, tag=clan_tag)
            clan: DatabaseClan = coc.utils.get(db_server.clans, tag=got_clan.tag)
            embed = await create_settings_embed(clan=clan, got_clan=got_clan)
            await res.edit_original_message(embed=embed)

    @setup.sub_command(
        name='category-order',
        description='Change the order family categories display on /family-clans',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def family_category_order(self, ctx: disnake.ApplicationCommandInteraction):
        categories = await self.bot.clan_db.distinct('category', filter={'server': ctx.guild.id})
        select_options = []
        for category in categories:
            select_options.append(disnake.SelectOption(label=category, value=category))
        select = disnake.ui.Select(
            options=select_options,
            placeholder='Categories',  # the placeholder text to show when no options have been chosen
            min_values=len(select_options),  # the minimum number of options a user must select
            max_values=len(select_options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        embed = disnake.Embed(
            description='**Select from the categories below in the order you would like them to be in**',
            color=disnake.Color.green(),
        )
        await ctx.edit_original_message(embed=embed, components=dropdown)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', check=check, timeout=600)
        except:
            return await msg.edit(components=[])
        await res.response.defer()
        await self.bot.server_db.update_one({'server': ctx.guild.id}, {'$set': {'category_order': res.values}})
        new_order = ', '.join(res.values)
        embed = disnake.Embed(
            description=f'New Category Order: `{new_order}`',
            color=disnake.Color.green(),
        )
        await res.edit_original_message(embed=embed)

    @setup.sub_command(name='logs', description='Set a variety of different clan logs for your server!')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def set_log_add(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = commands.Param(converter=convert.clan, autocomplete=autocomplete.clan),
        mode: str = commands.Param(choices=['Add/Edit', 'Remove']),
        channel: Union[disnake.TextChannel, disnake.Thread] = commands.Param(default=None),
    ):
        await ctx.response.defer()

        results = await self.bot.clan_db.find_one({'$and': [{'tag': clan.tag}, {'server': ctx.guild.id}]})
        if results is None:
            raise ThingNotFound('**This clan is not set up on this server. Use `/addclan` to get started.**')

        db_clan = DatabaseClan(bot=self.bot, data=results)
        channel = ctx.channel if channel is None else channel

        clan_log_types = {
            'Member Join': db_clan.join_log,
            'Member Leave': db_clan.leave_log,
            'Member Donation': db_clan.donation_log,
            'Clan Achievements': db_clan.clan_achievement_log,
            'Clan Requirements': db_clan.clan_requirements_log,
            'Clan Description': db_clan.clan_description_log,
        }
        war_log_types = {
            'War Log': db_clan.war_log,
            'War Panel': db_clan.war_panel,
            'CWL Lineup Change': db_clan.cwl_lineup_change_log,
        }
        capital_log_types = {
            'Capital Donations': db_clan.capital_donations,
            'Capital Attacks': db_clan.capital_attacks,
            'Capital Panel': db_clan.raid_panel,
            'Capital Weekly Summary': db_clan.capital_weekly_summary,
        }
        player_log_types = {
            'Role Change': db_clan.role_change,
            'Troop Upgrade': db_clan.troop_upgrade,
            'Super Troop Boosts': db_clan.super_troop_boost_log,
            'Townhall Upgrade': db_clan.th_upgrade,
            'League Change': db_clan.league_change,
            'Spell Upgrade': db_clan.spell_upgrade,
            'Hero Upgrade': db_clan.hero_upgrade,
            'Hero Equipment Upgrade': db_clan.hero_equipment_upgrade,
            'Name Change': db_clan.name_change,
            'Legend Attacks': db_clan.legend_log_attacks,
            'Legend Defenses': db_clan.legend_log_defenses,
        }
        master_log_types = clan_log_types | war_log_types | capital_log_types | player_log_types
        if mode == 'Remove':
            for log_types in [
                clan_log_types,
                war_log_types,
                capital_log_types,
                player_log_types,
            ]:
                for log_type, log in log_types.copy().items():
                    if log.webhook is None:
                        del log_types[log_type]

        dropdown = []
        for name, log_types in zip(
            ['Clan Logs', 'War Logs', 'Capital Logs', 'Player Logs'],
            [clan_log_types, war_log_types, capital_log_types, player_log_types],
        ):
            options = []
            for log_type in log_types.keys():
                options.append(
                    disnake.SelectOption(
                        label=log_type,
                        emoji=self.bot.emoji.clock.partial_emoji,
                        value=log_type,
                    )
                )
            if options:
                select = disnake.ui.Select(
                    options=options,
                    placeholder=name,  # the placeholder text to show when no options have been chosen
                    min_values=1,  # the minimum number of options a user must select
                    max_values=len(options),  # the maximum number of options a user can select
                )
                dropdown.append(disnake.ui.ActionRow(select))

        if dropdown:
            dropdown.append(
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label='Save',
                        emoji=self.bot.emoji.green_check.partial_emoji,
                        style=disnake.ButtonStyle.green,
                        custom_id='Save',
                    )
                )
            )
        else:
            raise MessageException('No Logs Set Up to Remove')

        channel_text = '' if mode == 'Remove' else f'in {channel.mention}'
        embed = disnake.Embed(
            description=f'Choose the logs that you would like to {mode.lower()} for {clan.name} {channel_text}\n'
            f'Visit https://docs.clashking.xyz/clan-setups/log-setup for more info',
            color=disnake.Color.green(),
        )
        await ctx.edit_original_message(embed=embed, components=dropdown)

        if mode == 'Add/Edit':
            webhook = await get_webhook_for_channel(channel=channel, bot=self.bot)
            thread = None
            if isinstance(channel, disnake.Thread):
                await channel.add_user(self.bot.user)
                thread = channel.id

        clicked_save = False
        values = []
        while not clicked_save:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            if res.component.type == disnake.ComponentType.button:
                break
            for value in res.values:
                values.append(value)

        text = ''
        for value in values:
            log = master_log_types[value]
            if mode == 'Add/Edit':
                await log.set_webhook(id=webhook.id)
                await log.set_thread(id=thread)
                mention = webhook.channel.mention if thread is None else f'<#{thread}>'
                text += f'{self.bot.emoji.green_check}{value} | {mention}\n'
            elif mode == 'Remove':
                await log.set_webhook(id=None)
                await log.set_thread(id=None)
                text += f'{self.bot.emoji.green_check}{value} Removed\n'

        embed = disnake.Embed(title=f'Logs for {clan.name}', description=text, color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=[])

    @setup.sub_command(
        name='reddit-recruit-feed',
        description='Feed of searching for a clan posts on the recruiting subreddit',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def reddit_recruit(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        channel: Union[disnake.TextChannel, disnake.Thread],
        role_to_ping: disnake.Role = None,
        remove=commands.Param(default=None, choices=['Remove Feed']),
    ):
        """
        Parameters
        ----------
        channel: channel to set the feed to
        role_to_ping: role to ping when a new recruit appears
        remove: option to remove this feed
        """
        await ctx.response.defer()

        if remove is None:
            role_id = None if role_to_ping is None else role_to_ping.id
            await self.bot.server_db.update_one(
                {'server': ctx.guild.id},
                {'$set': {'reddit_feed': channel.id, 'reddit_role': role_id}},
            )

            embed = disnake.Embed(
                description=f'**Reddit Recruit feed set to {channel.mention}**',
                color=disnake.Color.green(),
            )

        else:
            await self.bot.server_db.update_one(
                {'server': ctx.guild.id},
                {'$set': {'reddit_feed': None, 'reddit_role': None}},
            )

            embed = disnake.Embed(
                description='**Reddit Recruit feed removed**',
                color=disnake.Color.green(),
            )

        return await ctx.edit_original_message(embed=embed)

    @setup.sub_command(name='countdowns', description='Create countdowns for your server')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def voice_setup(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = commands.Param(default=None, autocomplete=autocomplete.clan, converter=convert.clan),
    ):
        """
        Parameters
        ----------
        clan: for war countdowns
        """
        await ctx.response.defer()

        types = [
            'CWL',
            'Clan Games',
            'Raid Weekend',
            'EOS',
            'Clan Member Count',
            'Season Day',
            'War Score',
            'War Timer',
        ]
        emojis = [
            self.bot.emoji.cwl_medal,
            self.bot.emoji.clan_games,
            self.bot.emoji.raid_medal,
            self.bot.emoji.trophy,
            self.bot.emoji.people,
            self.bot.emoji.trophy,
            self.bot.emoji.war_star,
            self.bot.emoji.war_star,
        ]
        if clan is None:
            types = types[:-2]
            emojis = emojis[:-2]
        else:
            types = types[-2:]
            emojis = emojis[-2:]
        options = []
        for type, emoji in zip(types, emojis):
            options.append(
                disnake.SelectOption(
                    label=type if type != 'EOS' else 'EOS (End of Season)',
                    emoji=emoji.partial_emoji,
                    value=type,
                )
            )

        select = disnake.ui.Select(
            options=options,
            placeholder='Select Options',  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        await ctx.edit_original_message(
            content='**Select Countdowns/Statbars to Create Below**',
            components=dropdown,
        )

        res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)

        results_list = []
        for type in res.values:
            try:
                if type == 'Clan Games':
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f'CG {time_}')
                elif type == 'Raid Weekend':
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f'Raids {time_}')
                elif type == 'Clan Member Count':
                    clan_tags = await self.bot.clan_db.distinct('tag', filter={'server': ctx.guild.id})
                    results = await self.bot.player_stats.count_documents(filter={'clan_tag': {'$in': clan_tags}})
                    channel = await ctx.guild.create_voice_channel(name=f'{results} Clan Members')
                elif type == 'EOS':
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f'EOS {time_}')
                elif type == 'Season Day':
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f'Day {time_}')
                elif type == 'War Score':
                    war = await self.bot.get_clanwar(clanTag=clan.tag)
                    time_ = await calculate_time(type, war=war)
                    channel = await ctx.guild.create_voice_channel(name=f'{clan.name}: {time_}')
                elif type == 'War Timer':
                    war = await self.bot.get_clanwar(clanTag=clan.tag)
                    time_ = await calculate_time(type, war=war)
                    channel = await ctx.guild.create_voice_channel(name=f'{clan.name}: {time_}')
                else:
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f'{type} {time_}')

                overwrite = disnake.PermissionOverwrite()
                overwrite.view_channel = True
                overwrite.connect = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                results_list.append((type, channel))
            except:
                embed = disnake.Embed(
                    description='Bot requires admin to create & set permissions for channel. **Channel will not update**',
                    color=disnake.Color.red(),
                )
                return await ctx.send(embed=embed)

        for type, channel in results_list:
            if type == 'CWL':
                await self.bot.server_db.update_one({'server': ctx.guild.id}, {'$set': {'cwlCountdown': channel.id}})
            elif type == 'Clan Games':
                await self.bot.server_db.update_one({'server': ctx.guild.id}, {'$set': {'gamesCountdown': channel.id}})
            elif type == 'Raid Weekend':
                await self.bot.server_db.update_one({'server': ctx.guild.id}, {'$set': {'raidCountdown': channel.id}})
            elif type == 'Clan Member Count':
                await self.bot.server_db.update_one({'server': ctx.guild.id}, {'$set': {'memberCount': channel.id}})
            elif type == 'War Score':
                await self.bot.clan_db.update_one(
                    {'$and': [{'tag': clan.tag}, {'server': ctx.guild.id}]},
                    {'$set': {'warCountdown': channel.id}},
                )
            elif type == 'War Timer':
                await self.bot.clan_db.update_one(
                    {'$and': [{'tag': clan.tag}, {'server': ctx.guild.id}]},
                    {'$set': {'warTimerCountdown': channel.id}},
                )
            elif type == 'Season Day':
                await self.bot.server_db.update_one({'server': ctx.guild.id}, {'$set': {'eosDayCountdown': channel.id}})

            else:
                await self.bot.server_db.update_one({'server': ctx.guild.id}, {'$set': {'eosCountdown': channel.id}})

        embed = disnake.Embed(
            description=f"`{', '.join(res.values)}` Stat Bars Created",
            color=disnake.Color.green(),
        )
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await res.edit_original_message(content='', embed=embed, components=[])

    @setup.sub_command(name='events', description='Create automatic events for your server')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def server_events(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        type: str = commands.Param(choices=['War']),
        clan: coc.Clan = commands.Param(autocomplete=autocomplete.clan, converter=convert.clan),
        status: str = commands.Param(choices=['Enable', 'Disable']),
    ):
        await ctx.response.defer()

        if 'COMMUNITY' not in ctx.guild.features:
            raise MessageException('Must be a community server to enable this feature')

        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild.id)

        db_clan = db_server.get_clan(clan_tag=clan.tag)
        await db_clan.set_server_event_creation_status(type=type.replace(' ', '_'), status=(status == 'Enable'))

        embed = disnake.Embed(
            description=f'{type} Server Events for {clan.name} {status}d',
            color=disnake.Color.green(),
        )
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.edit_original_message(content='', embed=embed, components=[])

    @setup.sub_command(name='link-parse', description='Turn link parsing types on/off')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def link_parse(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        army_links: str = commands.Param(default=None, choices=['On', 'Off'], description="Turn army links into an embed like /army"),
        player_links: str = commands.Param(default=None, choices=['On', 'Off'], description="Turn player links into a simple info embed"),
        clan_links: str = commands.Param(default=None, choices=['On', 'Off'], description="Turn clan links into an embed like /clan search"),
        base_links: str = commands.Param(default=None, choices=['On', 'Off'], description="Turn base links into an embed like /base"),
        show_parse: str = commands.Param(default=None, description='the -show command', choices=['On', 'Off']),
        manage_whitelist: bool = commands.Param(default=None, choices=['True'],
                                                        converter=convert.basic_bool, description="Set parsing to only happen in specific channels"),
    ):
        await ctx.response.defer()
        ck_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)

        if manage_whitelist:
            channel_select = disnake.ui.ChannelSelect(
                placeholder="Select channels",
                custom_id="channel_select",
                max_values=25,
                channel_types=[disnake.ChannelType.text]
            )
            remove_whitelist_button = disnake.ui.Button(
                label="Remove All Whitelists", style=disnake.ButtonStyle.danger, custom_id="remove_whitelist"
            )
            await ctx.send(
                content="Choose up to 25 channels to explicitly whitelist for parsing or remove whitelisting all together.\n"
                        "-# Hint: Start typing to view more channels",
                components=[
                    [channel_select],
                    [remove_whitelist_button],
                ],
            )

            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)

            if res.component.custom_id == "channel_select":
                selected_channels = res.values
                await ck_server.set_allowed_link_parse_channels(channel_ids=selected_channels)

                # Create an embed for the selected channels
                embed = disnake.Embed(
                    title="Parse Whitelist Channels Updated",
                    description="\n".join([f"<#{c}>" for c in selected_channels]),
                    color=ck_server.embed_color
                )
                embed.set_footer(text="Changes saved successfully!")
                await res.edit_original_message(
                    content=None,  # Clear the content
                    embed=embed,  # Add the embed
                    components=[]  # Clear the components
                )

            elif res.component.custom_id == "remove_whitelist":
                await ck_server.set_allowed_link_parse_channels(channel_ids=[])

                # Create an embed for removing whitelist
                embed = disnake.Embed(
                    title="Parse Whitelist Channels Removed",
                    description="All Parse Whitelisted Channels have been removed.",
                    color=ck_server.embed_color
                )
                embed.set_footer(text="Changes saved successfully!")
                await res.edit_original_message(
                    content=None,  # Clear the content
                    embed=embed,  # Add the embed
                    components=[]  # Clear the components
                )
            return
        else:
            link_types = ['army', 'player', 'clan', 'base', 'show']
            text = ''
            for link_type, option in zip(link_types, [army_links, player_links, clan_links, base_links, show_parse]):
                if option is None:
                    continue
                await ck_server.set_allowed_link_parse(type=link_type, status=(option == 'On'))
                text += f'- {link_type.capitalize()} Link Parse - `{option}`\n'
            if not text:
                text = "No options were updated"
            embed = disnake.Embed(
                title=f'Link Parse Settings Updated',
                description=text,
                color=ck_server.embed_color,
            )
            embed.set_author(name=ctx.guild.name, icon_url=get_guild_icon(ctx.guild))
            await ctx.send(embed=embed)

    @commands.slash_command(name='addclan', description='Add a clan to the server')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def addClan(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.clan,
        category: str = commands.Param(autocomplete=autocomplete.new_categories),
        member_role: disnake.Role = commands.Param(name='member_role'),
        clan_channel: disnake.TextChannel = commands.Param(name='clan_channel'),
        leadership_role: disnake.Role = None,
    ):
        """
        Parameters
        ----------
        clan: clan to add to server
        category: choose a category or type your own
        member_role: role that all members of this clan receive
        leadership_role: role that co & leaders of this clan would receive
        clan_channel: channel where ban pings & welcome messages should go
        """
        await ctx.response.defer()
        if member_role.is_bot_managed():
            embed = disnake.Embed(
                description=f'Clan Roles cannot be bot roles.',
                color=disnake.Color.red(),
            )
            return await ctx.edit_original_message(embed=embed)

        if leadership_role is not None and leadership_role.is_bot_managed():
            embed = disnake.Embed(
                description=f'Clan Roles cannot be bot roles.',
                color=disnake.Color.red(),
            )
            return await ctx.edit_original_message(embed=embed)

        if member_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(
                description=f'Member Role cannot be {ctx.guild.default_role.mention}.',
                color=disnake.Color.red(),
            )
            return await ctx.edit_original_message(embed=embed)

        if leadership_role is not None and leadership_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(
                description=f'Leadership Role cannot be {ctx.guild.default_role.mention}.',
                color=disnake.Color.red(),
            )
            return await ctx.edit_original_message(embed=embed)

        if leadership_role is not None and member_role.id == leadership_role.id:
            embed = disnake.Embed(
                description='Member Role & Leadership Role cannot be the same.',
                color=disnake.Color.red(),
            )
            return await ctx.edit_original_message(embed=embed)

        # check if clan is already linked
        results = await self.bot.clan_db.find_one({'$and': [{'tag': clan.tag}, {'server': ctx.guild.id}]})
        if results is not None:
            embed = disnake.Embed(
                description=f'{clan.name} is already linked to this server.',
                color=disnake.Color.red(),
            )
            return await ctx.edit_original_message(embed=embed)

        await self.bot.clan_db.insert_one(
            {
                'name': clan.name,
                'tag': clan.tag,
                'generalRole': member_role.id,
                'leaderRole': None if leadership_role is None else leadership_role.id,
                'category': category,
                'server': ctx.guild.id,
                'clanChannel': None if clan_channel is None else clan_channel.id,
            }
        )

        embed = disnake.Embed(
            title=f'{clan.name} successfully added.',
            description=f'Clan Tag: {clan.tag}\n'
            f'General Role: {member_role.mention}\n'
            f'Leadership Role: {None if leadership_role is None else leadership_role.mention}\n'
            f'Clan Channel: {None if clan_channel is None else clan_channel.mention}\n'
            f'Category: {category}',
            color=disnake.Color.green(),
        )
        embed.set_thumbnail(url=clan.badge.large)
        await ctx.edit_original_message(embed=embed)

    @commands.slash_command(name='removeclan', description='Remove a clan from the server')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def removeClan(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = commands.Param(converter=convert.clan_no_errors, autocomplete=autocomplete.clan),
    ):
        """
        Parameters
        ----------
        clan: clan to add to server [clan tag, alias, or autocomplete]
        """
        await ctx.response.defer()
        results = await self.bot.clan_db.find_one({'$and': [{'tag': clan.tag}, {'server': ctx.guild.id}]})
        if results is None:
            embed = disnake.Embed(
                description=f'{clan.name} is not currently set-up as a family clan.',
                color=disnake.Color.red(),
            )
            return await ctx.edit_original_message(embed=embed)

        embed = disnake.Embed(
            description=f'Are you sure you want to remove {clan.name} [{clan.tag}]?',
            color=disnake.Color.red(),
        )
        embed.set_thumbnail(url=clan.badge.large)

        page_buttons = [
            disnake.ui.Button(
                label='Yes',
                emoji='✅',
                style=disnake.ButtonStyle.green,
                custom_id='Yes',
            ),
            disnake.ui.Button(label='No', emoji='❌', style=disnake.ButtonStyle.red, custom_id='No'),
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)

        await ctx.edit_original_message(embed=embed, components=[buttons])
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        chose = False
        while chose is False:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', check=check, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author.id != ctx.author.id:
                await res.send(
                    content='You must run the command to interact with components.',
                    ephemeral=True,
                )
                continue

            chose = res.data.custom_id

            if chose == 'No':
                embed = disnake.Embed(
                    description=f'Sorry to hear that. Canceling the command now.',
                    color=disnake.Color.green(),
                )
                embed.set_thumbnail(url=clan.badge.large)
                return await res.response.edit_message(embed=embed, components=[])

        await self.bot.clan_db.find_one_and_delete({'$and': [{'tag': clan.tag}, {'server': ctx.guild.id}]})

        await self.bot.reminders.delete_many({'$and': [{'clan': clan.tag}, {'server': ctx.guild.id}]})
        embed = disnake.Embed(
            description=f'{clan.name} removed as a family clan.',
            color=disnake.Color.green(),
        )
        embed.set_thumbnail(url=clan.badge.large)
        return await msg.edit(embed=embed, components=[])


def setup(bot: CustomClient):
    bot.add_cog(SetupCommands(bot))
