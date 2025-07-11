import asyncio
import base64
import uuid
from datetime import datetime

import disnake
from disnake import ButtonStyle
from disnake.ext import commands
from exceptions.CustomExceptions import *

from classes.bot import CustomClient
from classes.tickets import LOG_TYPE, OpenTicket, TicketPanel
from discord import convert
from utility.discord_utils import check_commands, interaction_handler

from .click import TicketClick


class TicketCommands(TicketClick, commands.Cog, name='Ticket Commands'):
    def __init__(self, bot: CustomClient):
        super().__init__(bot)
        self.bot = bot

    @commands.slash_command(name='ticket')
    async def ticket(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    # PANELS
    @ticket.sub_command(
        name='panel-create',
        description='Get started here! Create your first ticket panel',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_panel_create(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        panel_name: str,
        embed: str = commands.Param(autocomplete=autocomplete.embeds),
    ):
        """
        Parameters
        ----------
        panel_name: name for panel
        embed: embed to use, can be created with /embed create
        """
        await ctx.response.defer()
        lookup = await self.bot.custom_embeds.find_one({'$and': [{'server': ctx.guild_id}, {'name': embed}]})
        if lookup is None:
            raise MessageException('No embed with that name found on this server')

        result = await self.bot.tickets.find_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        if result is not None:
            raise PanelAlreadyExists

        button = disnake.ui.Button(
            label='Open Ticket',
            emoji='📩',
            style=disnake.ButtonStyle.grey,
            custom_id=f'{panel_name}_0',
        )

        await self.bot.tickets.insert_one(
            {
                'name': panel_name,
                'server_id': ctx.guild.id,
                'components': [button.to_component_dict()],
                'embed_name': embed,
                f'{panel_name}_0_settings': {
                    'message': None,
                    'questions': None,
                    'mod_role': None,
                    'private_thread': False,
                    'roles_to_add': None,
                    'roles_to_remove': None,
                    'apply_clans': None,
                    'account_apply': False,
                    'player_info': False,
                    'ping_staff': True,
                },
            }
        )

        embed_data = lookup.get('data')
        embeds = [disnake.Embed.from_dict(data=e) for e in embed_data.get('embeds', [])]
        button = disnake.ui.Button(
            label='Open Ticket',
            emoji='📩',
            style=disnake.ButtonStyle.grey,
            custom_id=f'{panel_name}_0',
            disabled=True,
        )

        await ctx.edit_original_message(
            content='This is what your panel will look like. (You can change what embed the ticketing uses with `/ticket panel-edit` or edit the embed itself via `/embed edit`)\n'
            f'{embed_data.get("content", "") or ""}',
            embeds=embeds,
            components=[button],
        )

    @ticket.sub_command(name='panel-post', description='Post your created ticket panels anywhere!')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_panel_post(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
    ):
        """
        Parameters
        ----------
        panel_name: name of panel
        """
        await ctx.response.defer(ephemeral=True)
        result = await self.bot.tickets.find_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        if result is None:
            raise PanelNotFound

        apply_account = False
        for key, value in result.items():
            if '_settings' in key:
                if value.get('account_apply', False):
                    apply_account = True
                    break

        embed_name = result.get('embed_name')
        embed_data = await self.bot.custom_embeds.find_one({'$and': [{'server': ctx.guild_id}, {'name': embed_name}]})
        embed_data = embed_data.get('data')

        action_buttons = [[], [], [], [], []]
        row = 0
        result_components = result.get('components', [])
        if apply_account:
            result_components += [
                {
                    'type': 2,
                    'style': 2,
                    'disabled': False,
                    'label': 'Link Account',
                    'custom_id': 'Start Link',
                    'emoji': {'name': '🔗', 'id': None},
                }
            ]
        for component in result_components:
            emoji = component.get('emoji')
            if emoji is not None:
                if emoji.get('id') is not None:
                    emoji = self.bot.partial_emoji_gen(f"<:{emoji.get('name')}:{emoji.get('id')}>")
                else:
                    emoji = emoji.get('name')
            style = {
                1: disnake.ButtonStyle.primary,
                2: disnake.ButtonStyle.secondary,
                3: disnake.ButtonStyle.success,
                4: disnake.ButtonStyle.danger,
            }
            action_buttons[row].append(
                disnake.ui.Button(
                    label=component.get('label'),
                    emoji=emoji,
                    style=style[component.get('style')],
                    custom_id=component.get('custom_id'),
                )
            )
            if len(action_buttons[row]) == 5:
                row += 1

        all_buttons = []
        for button_row in action_buttons:
            if not button_row:
                continue
            buttons = disnake.ui.ActionRow()
            for button in button_row:
                buttons.append_item(button)
            all_buttons.append(buttons)

        embeds = [disnake.Embed.from_dict(data=e) for e in embed_data.get('embeds', [])]
        await ctx.channel.send(
            content=embed_data.get('content', '') or '',
            embeds=embeds,
            components=all_buttons,
        )
        await ctx.edit_original_response(content='Panel Posted!')

    @ticket.sub_command(name='panel-edit', description='Change what embed your ticket panel uses')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_panel_edit(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
        embed: str = commands.Param(autocomplete=autocomplete.embeds),
    ):
        """
        Parameters
        ----------
        panel_name: name of panel
        embed: embed to use, can be created with /embed create
        """
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        if result is None:
            raise PanelNotFound

        lookup = await self.bot.custom_embeds.find_one({'$and': [{'server': ctx.guild_id}, {'name': embed}]})
        if lookup is None:
            raise MessageException('No embed with that name found on this server')

        await self.bot.tickets.update_one(
            {'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]},
            {'$set': {'embed_name': embed}},
        )
        await ctx.edit_original_message(content='Panel updated to use new embed', components=None)

    @ticket.sub_command(
        name='panel-delete',
        description='Delete a panel (and everything attached to it)',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_panel_delete(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
    ):
        await ctx.response.defer()
        result = await self.bot.tickets.find_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        if result is None:
            raise PanelNotFound
        await self.bot.tickets.delete_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        await ctx.send(content=f'**{panel_name} Panel Deleted**')

    @ticket.sub_command(
        name='open-message',
        description='Customize the message that is sent when a ticket is opened',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_message(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        ticket_button: tuple[str, str] = commands.Param(
            autocomplete=autocomplete.ticket_panel_buttons,
            converter=convert.ticket_button,
        ),
        embed: str = commands.Param(autocomplete=autocomplete.embeds),
    ):
        await ctx.response.defer()
        button_name, panel_name = ticket_button

        result = await self.bot.tickets.find_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        if result is None:
            raise PanelNotFound

        button_id = next((x for x in result.get('components') if x.get('label') == button_name), None)
        if button_id is None:
            raise ButtonNotFound

        lookup = await self.bot.custom_embeds.find_one({'$and': [{'server': ctx.guild_id}, {'name': embed}]})
        if lookup is None:
            raise MessageException('No embed with that name found on this server')

        embed_data = lookup.get('data')
        embeds = [disnake.Embed.from_dict(data=e) for e in embed_data.get('embeds', [])]

        await self.bot.tickets.update_one(
            {'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]},
            {'$set': {f"{button_id.get('custom_id')}_settings.new_message": embed}},
        )

        await ctx.edit_original_message(
            content=f'`Custom message set for {button_name} button on {panel_name} panel`\n'
            f'{embed_data.get("content", "") or ""}',
            embeds=embeds,
        )

    @ticket.sub_command(name='roles', description='Manage Roles around Tickets being opened')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_roles(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        ticket_button: tuple[str, str] = commands.Param(
            autocomplete=autocomplete.ticket_panel_buttons,
            converter=convert.ticket_button,
        ),
        mode=commands.Param(choices=['Add Roles', 'Remove Roles']),
        remove=commands.Param(default='False', choices=['True']),
    ):

        await ctx.response.defer()
        button_name, panel_name = ticket_button

        result = await self.bot.tickets.find_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        if result is None:
            raise PanelNotFound
        button_id = next((x for x in result.get('components') if x.get('label') == button_name), None)
        if button_id is None:
            raise ButtonNotFound

        type = 'roles_to_add' if mode == 'Add Roles' else 'roles_to_remove'

        if remove == 'True':
            await self.bot.tickets.update_one(
                {'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]},
                {'$set': {f"{button_id.get('custom_id')}_settings.{type}": []}},
            )
            return await ctx.send(
                embed=disnake.Embed(
                    description=f'{mode} removed for {button_name} button on {panel_name} panel',
                    color=disnake.Color.green(),
                )
            )

        role_select = disnake.ui.RoleSelect(placeholder='Choose Roles (max 10)', max_values=10)
        dropdown = [disnake.ui.ActionRow(role_select)]
        if mode == 'Add Roles':
            await ctx.send(
                content='**Choose roles to be added on ticket open**',
                components=dropdown,
            )
        else:
            await ctx.send(
                content='**Choose roles to be removed on ticket open**',
                components=dropdown,
            )

        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx, function=None, bot=self.bot)
        ticket_roles = res.values

        result = await self.bot.tickets.find_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        button_id = next((x for x in result.get('components') if x.get('label') == button_name), None)
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]},
            {'$set': {f"{button_id.get('custom_id')}_settings.{type}": ticket_roles}},
        )
        await res.edit_original_message(content=f'**{button_name} Button {mode} Saved!**', components=[])

    @ticket.sub_command(name='settings', description='Set settings for ticket panel & buttons')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_account_apply(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        ticket_panel: str = commands.Param(autocomplete=autocomplete.ticket_panel),
    ):
        await ctx.response.defer(ephemeral=True)
        random_uuid = uuid.uuid4()
        uuid_bytes = random_uuid.bytes
        base64_uuid = base64.urlsafe_b64encode(uuid_bytes).rstrip(b'=')
        url_safe_uuid = base64_uuid.decode('utf-8')
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': ctx.guild.id}, {'name': ticket_panel}]},
            {'$set': {'token': url_safe_uuid}},
        )
        await ctx.send(
            content=f'Edit your roster here -> https://api.clashk.ing/ticketing?token={url_safe_uuid}',
            ephemeral=True,
        )

    @ticket.sub_command(
        name='apply-rules',
        description='Set hero restrictions & more on accounts applying',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_apply_rules(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        ticket_button: tuple[str, str] = commands.Param(
            autocomplete=autocomplete.ticket_panel_buttons,
            converter=convert.ticket_button,
        ),
        show_my_current_rules: str = commands.Param(default='False', choices=['True']),
    ):
        if show_my_current_rules == 'True':
            return await ctx.send('*Coming Soon*', ephemeral=True)
        await ctx.response.defer()

        button_name, panel_name = ticket_button

        panel_settings = await self.bot.tickets.find_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        if panel_settings is None:
            raise PanelNotFound
        panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)
        button = panel.get_button(label=button_name)

        buttons = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label='Upload Requirements',
                    style=ButtonStyle.grey,
                    custom_id='upload_requirements',
                )
            )
        ]

        example_text = (
            '```TH, BK, AQ, GW, RC, WARST,\n '
            '9, 10, 15,  0,  0,   250,\n'
            '10, 25, 25,  0,  0,   300,\n'
            '11, 35, 35, 15,  0,   350,\n'
            '12, 40, 40, 25,  0,   400,\n'
            '13, 55, 55, 35, 10,   450,\n'
            '14, 65, 65, 45, 20,   500,\n'
            '15, 75, 75, 55, 30,   600,```'
        )

        embed = disnake.Embed(
            description='**Copy the text above**\n'
            '- Make Any Edits (may be easier on desktop)\n'
            "- You can add/remove TH's on the example text, as long as same format\n"
            '- Click Button and Upload to Modal & Submit',
            color=disnake.Color(2829617),
        )

        await ctx.send(embed=embed, content=example_text, components=buttons)

        res: disnake.ApplicationCommandInteraction = await interaction_handler(bot=self.bot, ctx=ctx, no_defer=True)
        await res.response.send_modal(
            title='Townhall Requirements Upload',
            custom_id=f'threq-{int(datetime.now().timestamp())}',
            components=[
                disnake.ui.TextInput(
                    label='Requirements Here',
                    placeholder='Requirements Must be in the correct format',
                    custom_id='th_req',
                    required=True,
                    style=disnake.TextInputStyle.paragraph,
                    max_length=1000,
                )
            ],
        )

        def check(r):
            return res.author.id == r.author.id

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                'modal_submit',
                check=check,
                timeout=300,
            )
        except Exception:
            raise ExpiredComponents
        try:
            await modal_inter.response.defer(ephemeral=True)
        except Exception:
            pass

        requirements: str = modal_inter.text_values['th_req']
        try:
            requirements = requirements.replace('```', '')
            split_req = requirements.split(',')
            headers = split_req[:6]
            rest = split_req[6:]
            index = 0
            key = 0
            new_data = {}
            for r in rest:
                r = r.replace('\n', '').replace(' ', '')
                if r == '':
                    continue
                if r.isdigit():
                    r = int(r)
                if index == 0:
                    new_data[str(r)] = {}
                    key = str(r)
                new_data[key][headers[index].replace(' ', '')] = r
                index += 1
                if index == 6:
                    index = 0
        except Exception:
            return await modal_inter.send(content='Invalid Format, Please Run Command & Try Again')

        await button.set_townhall_requirements(requirements=new_data)
        await modal_inter.send(content=f'Requirements Stored\n```{requirements}```')
        buttons = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label='Upload Requirements',
                    style=ButtonStyle.grey,
                    custom_id='upload_requirements',
                    disabled=True,
                )
            )
        ]
        await ctx.edit_original_message(components=buttons)

    @ticket.sub_command(name='apply-messages', description='Set up to 25 approve/deny messages')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ticket_messages(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        panel_name: str = commands.Param(autocomplete=autocomplete.ticket_panel),
        name: str = commands.Param(),
    ):
        result = await self.bot.tickets.find_one({'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]})
        if result is None:
            raise PanelNotFound
        ticket = TicketPanel(bot=self.bot, panel_settings=result)

        await ctx.response.send_modal(
            title='Approve/Deny Messages',
            custom_id=f'approvemsg-{int(datetime.utcnow().timestamp())}',
            components=[
                disnake.ui.TextInput(
                    label='Message',
                    placeholder='',
                    custom_id='approve_msg',
                    required=True,
                    style=disnake.TextInputStyle.paragraph,
                    max_length=1000,
                )
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
        await ticket.add_edit_approve_messages(name=name, message=modal_inter.text_values['approve_msg'])
        await modal_inter.send(content='Message Added/Edited/Updated')

    @ticket.sub_command(name='status', description='Change status of ticket')
    @commands.check_any(commands.has_permissions(manage_channels=True), check_commands())
    async def ticket_status(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        status: str = commands.Param(choices=['open', 'sleep', 'close', 'delete']),
    ):
        await ctx.response.defer(ephemeral=True)

        if status == 'close':
            status = 'closed'

        ticket_data = await self.bot.open_tickets.find_one({'channel': ctx.channel.id})
        if ticket_data is None:
            return await ctx.send('Not a ticket channel')

        ticket = OpenTicket(bot=self.bot, open_ticket=ticket_data)
        if ticket.status == status:
            return await ctx.send(content=f'Ticket already {status}')

        await ticket.set_ticket_status(status=status)
        panel_settings = await self.bot.tickets.find_one(
            {'$and': [{'server_id': ctx.guild.id}, {'name': ticket.panel_name}]}
        )
        panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)

        await panel.send_log(
            log_type=LOG_TYPE.STATUS_CHANGE,
            user=ctx.user,
            ticket_channel=ctx.channel,
            ticket=ticket,
        )

        if status == 'delete':
            await panel.send_log(
                log_type=LOG_TYPE.TICKET_CLOSE,
                user=ctx.user,
                ticket_channel=ctx.channel,
                ticket=ticket,
            )
            await ctx.send(content='Deleting channel in 15 seconds')
            await asyncio.sleep(15)
            return await ctx.channel.delete()

        member = await ctx.guild.getch_member(ticket.user)
        if status == 'closed' or status == 'open':
            user_overwrite = disnake.PermissionOverwrite()
            user_overwrite.view_channel = status == 'open'
            channel: disnake.TextChannel = ctx.channel
            await channel.set_permissions(member, overwrite=user_overwrite)

        if 'status' in ticket.naming_convention:
            new_name = await ticket.rename_ticket()
            await ctx.channel.edit(name=new_name)

        category = None
        if panel_settings.get(f'{status}-category') is not None:
            category = await self.bot.getch_channel(panel_settings.get(f'{status}-category'))

        if category is None:
            category: disnake.CategoryChannel = ctx.channel.category
        await ctx.channel.edit(category=category)

        await ctx.send(content=f'Ticket status switched to {status}')

    @ticket.sub_command(name='add', description='Add a member to a ticket')
    @commands.check_any(commands.has_permissions(manage_channels=True), check_commands())
    async def ticket_add(self, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member):
        await ctx.response.defer()
        result = await self.bot.open_tickets.find_one({'channel': ctx.channel.id})
        if result is None:
            return await ctx.send('Not a ticket channel')
        user_overwrite = disnake.PermissionOverwrite()
        user_overwrite.view_channel = True
        user_overwrite.external_emojis = True
        user_overwrite.add_reactions = True
        user_overwrite.read_message_history = True
        user_overwrite.send_messages = True
        user_overwrite.attach_files = True
        await ctx.channel.set_permissions(member, overwrite=user_overwrite)
        await ctx.send(f'**{member.mention} added to this ticket by {ctx.user.mention}**')

    @ticket.sub_command(name='opt', description='Opt in/out of a ticket')
    @commands.check_any(commands.has_permissions(manage_channels=True), check_commands())
    async def ticket_opt(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        opt=commands.Param(choices=['In', 'Out']),
    ):
        await ctx.response.defer(ephemeral=True)
        result = await self.bot.open_tickets.find_one({'channel': ctx.channel.id})
        if result is None:
            return await ctx.send('Not a ticket channel')
        if opt == 'In':
            await self.bot.open_tickets.update_one({'channel': ctx.channel.id}, {'$push': {'opted_in': ctx.user.id}})
        else:
            await self.bot.open_tickets.update_one({'channel': ctx.channel.id}, {'$pull': {'opted_in': ctx.user.id}})
        await ctx.send(content=f'Opted {opt} now!')

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if (
            not message.author.bot
            and isinstance(message.channel, disnake.TextChannel)
            and message.channel.topic == 'Ticketing powered by ClashKing!'
        ):
            if message.guild.id in self.bot.OUR_GUILDS:
                result = await self.bot.open_tickets.find_one({'channel': message.channel.id})
                if result is not None:
                    if message.author.id != result.get('user'):
                        return
                    opted_in = result.get('opted_in')
                    if opted_in is not None:
                        text = ''
                        for user in opted_in:
                            text += f'<@{user}> '
                        await message.channel.send(content=text, delete_after=1)


def setup(bot):
    bot.add_cog(TicketCommands(bot))
