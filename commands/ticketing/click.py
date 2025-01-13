from datetime import datetime
from typing import List

import coc
import disnake
import pendulum as pend
import pytz
from disnake.ext import commands

from classes.bot import CustomClient
from classes.database.models.player.stats import StatsPlayer
from classes.tickets import LOG_TYPE, OpenTicket, TicketPanel
from utility.discord_utils import interaction_handler

from .utils import ask_questions, message_convertor, open_ticket


tiz = pytz.utc
from utility.player_pagination import button_pagination


class TicketClick(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_dropdown(self, ctx: disnake.MessageInteraction):
        selected = ctx.values[0]
        if 'ticketviewer_' in selected:
            await ctx.response.defer(ephemeral=True, with_message=True)
            tag = (selected.split('_'))[-1]
            msg = await ctx.original_message()
            player = await self.bot.getPlayer(player_tag=tag, custom=True)
            if player is None:
                return await ctx.edit_original_response(content='No player found.')
            return await button_pagination(self.bot, ctx, msg, [player])

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        # TO-DO Remove
        if 'redditplayer_' in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True, with_message=True)
            tag = (str(ctx.data.custom_id).split('_'))[-1]
            msg = await ctx.original_message()
            player = await self.bot.getPlayer(player_tag=tag, custom=True)
            if player is None:
                return await ctx.edit_original_response(content='No player found.')
            await button_pagination(self.bot, ctx, msg, [player])

        if ctx.data.custom_id == 'approve_applicant':
            await ctx.response.defer(ephemeral=True)

            result = await self.bot.open_tickets.find_one({'channel': ctx.channel.id})
            ticket = OpenTicket(bot=self.bot, open_ticket=result)
            if ticket.status == 'closed':
                return await ctx.send(content='Ticket already closed', ephemeral=True)

            if ctx.user.id == ticket.user:
                return await ctx.send(content="You don't have permissions to do this", ephemeral=True)

            panel_settings = await self.bot.tickets.find_one(
                {'$and': [{'server_id': ctx.guild.id}, {'name': ticket.panel_name}]}
            )
            panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)

            if not panel.approve_messages:
                return await ctx.send(
                    content='No messages are set up, use `/ticket apply-messages`',
                    ephemeral=True,
                )

            options = []
            for message in panel.approve_messages[:25]:
                options.append(disnake.SelectOption(label=message.name, value=f'aprmsg_{message.name}'))

            select = disnake.ui.Select(
                options=options,
                placeholder='Select Message To Send',
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            dropdown = [disnake.ui.ActionRow(select)]
            msg: disnake.Message = await ctx.followup.send(components=dropdown, ephemeral=True)

            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, msg=msg, no_defer=True)
            await msg.delete()
            # await res.send(content="Sent!", ephemeral=True)
            approve_msg = panel.get_message(name=res.values[0].split('_')[-1])
            message, left_over = await message_convertor(
                bot=self.bot, ctx=ctx, message=approve_msg.message, ticket=ticket
            )
            if left_over:
                await res.response.send_modal(
                    title='Custom Fields',
                    custom_id=f'customfield-{int(datetime.utcnow().timestamp())}',
                    components=[
                        disnake.ui.TextInput(
                            label=f'{field}',
                            placeholder='',
                            custom_id=f'{field}',
                            required=True,
                            style=disnake.TextInputStyle.single_line,
                            max_length=75,
                        )
                        for field in left_over[:5]
                    ],
                )

                def check(res):
                    return ctx.author.id == res.author.id

                try:
                    modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                        'modal_submit',
                        check=check,
                        timeout=300,
                    )
                except:
                    return
                await modal_inter.response.defer(ephemeral=True)
                custom = {}
                for field, response in modal_inter.text_values.items():
                    custom[str(field)] = response
                message, left_over = await message_convertor(
                    bot=self.bot,
                    ctx=ctx,
                    message=message,
                    ticket=ticket,
                    custom_field=custom,
                )
                await modal_inter.edit_original_response(content='Done')

            await ctx.channel.send(content=message)

        if ctx.data.custom_id == 'set_clan':
            await ctx.response.defer(ephemeral=True)
            result = await self.bot.open_tickets.find_one({'channel': ctx.channel.id})
            ticket = OpenTicket(bot=self.bot, open_ticket=result)
            if ticket.status == 'closed':
                return await ctx.send(content='Ticket already closed', ephemeral=True)
            if ctx.user.id == ticket.user:
                return await ctx.send(content="You don't have permissions to do this", ephemeral=True)

            clan_tags = await self.bot.clan_db.distinct('tag', filter={'server': ctx.guild.id})

            if not clan_tags:
                # TO-DO, use command id & new name
                await ctx.send(
                    content='No clans set up on this server. Get started with `/addclan`',
                    ephemeral=True,
                )
            clans = await self.bot.get_clans(tags=clan_tags)
            select_menu_options = []
            clans = sorted(clans, key=lambda x: x.member_count, reverse=True)

            for count, clan in enumerate(clans):
                emoji = await self.bot.create_new_badge_emoji(url=clan.badge.url)
                if count < 25:
                    select_menu_options.append(
                        disnake.SelectOption(
                            label=clan.name,
                            emoji=self.bot.partial_emoji_gen(emoji_string=emoji),
                            value=clan.tag,
                        )
                    )

            select = disnake.ui.Select(
                options=select_menu_options,
                # the placeholder text to show when no options have been chosen
                placeholder='Select Clans',
                min_values=1,  # the minimum number of options a user must select
                # the maximum number of options a user can select
                max_values=1,
            )

            dropdown = [disnake.ui.ActionRow(select)]
            msg = await ctx.followup.send(
                content='**Choose Clans To Send Player To:**',
                components=dropdown,
                ephemeral=True,
            )
            res: disnake.MessageInteraction = await interaction_handler(ctx=ctx, msg=msg, bot=self.bot)
            await msg.delete()
            apply_clans = res.values[0]
            await ticket.set_clan(apply_clans)

        if ctx.data.custom_id == 'close_ticket':
            await ctx.response.defer(ephemeral=True)

            result = await self.bot.open_tickets.find_one({'channel': ctx.channel.id})
            ticket = OpenTicket(bot=self.bot, open_ticket=result)
            if ctx.user.id == ticket.user and ctx.user.id != 706149153431879760:
                return await ctx.send(
                    content="You don't have permissions to delete this ticket",
                    ephemeral=True,
                )
            await ticket.set_ticket_status(status='delete')
            panel_settings = await self.bot.tickets.find_one(
                {'$and': [{'server_id': ctx.guild.id}, {'name': ticket.panel_name}]}
            )
            panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)

            await panel.send_log(
                log_type=LOG_TYPE.TICKET_CLOSE,
                user=ctx.user,
                ticket_channel=ctx.channel,
                ticket=ticket,
            )
            await ctx.channel.delete()

        def is_unix_timestamp(timestamp: str) -> bool:
            """
            Check if a string is a valid Unix timestamp.

            Args:
                timestamp (str): The string to check.

            Returns:
                bool: True if the string is a valid Unix timestamp, False otherwise.
            """
            try:
                # Ensure the string can be converted to an integer
                ts_int = int(timestamp)

                # Check if the timestamp is within a reasonable range for Unix time
                pend.from_timestamp(ts_int)
                return True
            except (ValueError, OverflowError):
                return False

        panel_settings = None
        if is_unix_timestamp(ctx.data.custom_id.split('_')[-1]):
            panel_settings = await self.bot.tickets.find_one(
                {
                    '$and': [
                        {'server_id': ctx.guild.id},
                        {'name': ctx.data.custom_id.split('_')[0]},
                    ]
                }
            )
        if panel_settings is not None:
            member = await ctx.guild.getch_member(ctx.user.id)
            panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)
            button = panel.get_button(custom_id=ctx.data.custom_id)
            if button is None:
                return await ctx.send('Button No Longer Exists', ephemeral=True)
            await button.send_log(log_type=LOG_TYPE.BUTTON_CLICK, user=ctx.user)

            players = []
            embeds = await button.get_message()
            message = None

            if button.account_apply or not button.questions:
                await ctx.response.defer(ephemeral=True)

            if button.account_apply:
                linked_accounts = await self.bot.get_tags(ping=str(ctx.user.id))
                if not linked_accounts:
                    buttons = disnake.ui.ActionRow()
                    for button in [
                        disnake.ui.Button(
                            label='Link Account',
                            emoji='🔗',
                            style=disnake.ButtonStyle.green,
                            custom_id='Start Link',
                        ),
                        disnake.ui.Button(
                            label='Help',
                            emoji='❓',
                            style=disnake.ButtonStyle.grey,
                            custom_id='Link Help',
                        ),
                    ]:
                        buttons.append_item(button)
                    return await ctx.send(
                        content='No accounts linked to you. Click the button below to link. '
                        '**Once you are done, please open a ticket again.**',
                        components=buttons,
                        ephemeral=True,
                    )

                accounts: List[StatsPlayer] = await self.bot.get_players(tags=linked_accounts, custom=True)
                accounts.sort(key=lambda x: x.town_hall, reverse=True)
                options = []
                failed_accounts = False
                for account in accounts:
                    data_requirements = button.get_townhall_requirement(townhall_level=account.town_hall)
                    meet_hero_req = True
                    name_to_req = {
                        'Barbarian King': data_requirements.barbarian_king,
                        'Archer Queen': data_requirements.archer_queen,
                        'Grand Warden': data_requirements.grand_warden,
                        'Royal Champion': data_requirements.royal_champ,
                    }
                    text = ''
                    for hero in account.heroes:
                        text += f'{hero.name} | {hero.level},'
                        if hero.is_builder_base:
                            continue
                        if not name_to_req.get(hero.name):
                            continue
                        if hero.level < name_to_req.get(hero.name):
                            meet_hero_req = False
                            break
                    if (
                        account.town_hall >= button.townhall_minimum
                        and meet_hero_req
                        and account.war_stars >= data_requirements.war_stars
                    ):
                        options.append(
                            disnake.SelectOption(
                                label=account.name,
                                emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji,
                                value=f'{account.tag}',
                            )
                        )
                    else:
                        failed_accounts = True

                if not options:
                    return await ctx.send(
                        content=f'Sorry, you have no accounts that meet the TH{button.townhall_minimum} & up plus Hero & War Stars Requirement '
                        f"to apply here. If you do but the account wasn't shown, or have other questions, speak to your server leadership to help get it linked :)",
                        ephemeral=True,
                    )

                options = options[:25]
                select = disnake.ui.Select(
                    options=options,
                    placeholder='Select Account(s)',
                    # the placeholder text to show when no options have been chosen
                    min_values=1,  # the minimum number of options a user must select
                    max_values=min(
                        button.number_allowed_to_apply, len(options)
                    ),  # the maximum number of options a user can select
                )
                dropdown = [disnake.ui.ActionRow(select)]
                text = ''
                if failed_accounts:
                    text = '(Some accounts have been hidden due to not hitting the minimum applicant requirements of this server)'
                message = await ctx.followup.send(
                    content=f'Select Account to Apply With {text}',
                    components=dropdown,
                    ephemeral=True,
                )

                res: disnake.MessageInteraction = await interaction_handler(
                    bot=self.bot,
                    ctx=ctx,
                    msg=message,
                    no_defer=(button.questions != []),
                )
                ctx = res
                players = [coc.utils.get(accounts, tag=tag) for tag in res.values]
                if not button.questions:
                    if res.response.is_done():
                        await res.edit_original_response(content='Done!', components=[])
                    else:
                        await res.response.send_message(content='Done!', components=[], ephemeral=True)

            if button.questions:
                if message:
                    await message.delete()
                (message, questionaire_embed) = await ask_questions(bot=self.bot, ctx=ctx, questions=button.questions)
                embeds.append(questionaire_embed)

            channels = await open_ticket(
                bot=self.bot,
                ticket_panel=panel,
                button=button,
                ctx=ctx,
                coc_account=players[0] if players else None,
            )

            if message is None:
                await ctx.send(f'Ticket opened -> {channels[0].mention}', ephemeral=True)
            else:
                await message.edit(f'Ticket opened -> {channels[0].mention}', components=[])

            dropdown = []
            if len(players) >= 2:
                options = []
                for account in players:
                    options.append(
                        disnake.SelectOption(
                            label=account.name,
                            emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji,
                            value=f'ticketviewer_{account.tag}',
                        )
                    )
                select = disnake.ui.Select(
                    options=options,
                    placeholder='View Applicant Accounts',
                    # the placeholder text to show when no options have been chosen
                    min_values=1,  # the minimum number of options a user must select
                    max_values=1,  # the maximum number of options a user can select
                )
                dropdown = [disnake.ui.ActionRow(select)]
            elif len(players) == 1:
                dropdown = [
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label='Applicant Account',
                            emoji=self.bot.fetch_emoji(name=players[0].town_hall).partial_emoji,
                            style=disnake.ButtonStyle.grey,
                            custom_id=f'redditplayer_{players[0].tag}',
                        )
                    )
                ]

            next_action_row = disnake.ui.ActionRow()
            for b in [
                disnake.ui.Button(
                    label='Delete Ticket',
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'close_ticket',
                ),
                disnake.ui.Button(
                    label='Set Clan',
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'set_clan',
                ),
                disnake.ui.Button(
                    label='Messages',
                    style=disnake.ButtonStyle.green,
                    custom_id=f'approve_applicant',
                ),
            ]:
                next_action_row.append_item(b)

            for channel in channels:
                if channel.type == disnake.ChannelType.text:
                    m = await channel.send(embeds=embeds, components=dropdown + [next_action_row])
                else:
                    m = await channel.send(embeds=embeds[1:], components=dropdown)
                await m.pin()

            try:
                if button.roles_to_add:
                    roles_to_add = [disnake.utils.get(member.guild.roles, id=int(role)) for role in button.roles_to_add]
                    roles_to_add = [r for r in roles_to_add if r is not None]
                    await member.add_roles(*[r for r in roles_to_add if r is not None])

                if button.roles_to_remove:
                    roles_to_remove = [
                        disnake.utils.get(member.guild.roles, id=int(role)) for role in button.roles_to_remove
                    ]
                    roles_to_remove = [r for r in roles_to_remove if r is not None]
                    await member.remove_roles(*[r for r in roles_to_remove if r is not None])
            except Exception:
                await channels[0].send('**Could not add/remove roles**')

            all_ticket_nums = await self.bot.open_tickets.distinct('number', filter={'server': ctx.guild.id})
            if not all_ticket_nums:
                all_ticket_nums = [0]

            await self.bot.open_tickets.insert_one(
                {
                    'user': ctx.user.id,
                    'channel': channels[0].id,
                    'thread': channels[-1].id if len(channels) >= 2 else None,
                    'status': 'open',
                    'number': max(all_ticket_nums) + 1,
                    'apply_account': players[0].tag if players else None,
                    'naming': button.naming_convention,
                    'panel': panel.panel_name,
                    'server': ctx.guild.id,
                }
            )
