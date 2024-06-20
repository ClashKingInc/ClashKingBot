import asyncio
import io
from datetime import datetime
from enum import Enum
from typing import List

import chat_exporter
import disnake
from disnake import ButtonStyle, Embed
from disnake.ui import Button

from classes.bot import CustomClient
from exceptions.CustomExceptions import ButtonAlreadyExists, ButtonNotFound
from utility.cdn import upload_html_to_cdn


text_style_conversion = {
    'Blue': disnake.ButtonStyle.primary,
    'Grey': disnake.ButtonStyle.secondary,
    'Green': disnake.ButtonStyle.success,
    'Red': disnake.ButtonStyle.danger,
}


class LOG_TYPE(Enum):
    BUTTON_CLICK = 1
    STATUS_CHANGE = 2
    TICKET_CLOSE = 3


class OpenTicket:
    def __init__(self, bot: CustomClient, open_ticket: dict):
        self.bot = bot
        self.user = open_ticket.get('user')
        self.channel = open_ticket.get('channel')
        self.thread = open_ticket.get('thread')
        self.number: int = open_ticket.get('number', 1)
        self.apply_account: str = open_ticket.get('account_apply')
        self.naming_convention: str = open_ticket.get('naming')
        self.panel_name: str = open_ticket.get('panel')
        self.status: str = open_ticket.get('status')
        self.clan: str = open_ticket.get('set_clan')

    async def set_clan(self, clan_tag):
        await self.bot.open_tickets.update_one({'channel': self.channel}, {'$set': {'set_clan': clan_tag}})

    async def set_ticket_status(self, status: str):
        await self.bot.open_tickets.update_one({'channel': self.channel}, {'$set': {'status': status}})
        self.status = status

    async def rename_ticket(self):
        naming_convention = self.naming_convention
        coc_account = None
        if self.apply_account is not None:
            coc_account = await self.bot.getPlayer(player_tag=self.apply_account, custom=False, cache_data=False)

        user = await self.bot.getch_user(self.user)
        status_emoji = {'open': '✅', 'sleep': '🌙', 'closed': '❌'}
        types = {
            '{ticket_count}': self.number,
            '{user}': user.name if user is not None else '',
            '{account_name}': coc_account.name if coc_account is not None else '',
            '{account_th}': coc_account.town_hall if coc_account is not None else '',
            '{ticket_status}': self.status,
            '{emoji_status}': status_emoji[self.status],
        }

        for type, replace in types.items():
            naming_convention = naming_convention.replace(type, str(replace))
        return str(naming_convention)


class ApproveMessages:
    def __init__(self, data):
        self.name = data.get('name')
        self.message = data.get('message')


class BaseTicket:
    def __init__(self, bot: CustomClient, panel_settings):
        self.bot = bot
        self.panel_settings = panel_settings
        self.panel_name = panel_settings.get('name')
        self.panel_server: disnake.Guild = bot.get_guild(self.panel_settings.get('server_id'))
        self.status_change_log = self.panel_settings.get('status_change_log')
        self.ticket_button_click_log = self.panel_settings.get('ticket_button_click_log')
        self.ticket_close_log = self.panel_settings.get('ticket_close_log')
        # self._embed_data = asyncio.get_running_loop().run_until_complete(bot.custom_embeds.find_one({"$and": [{"server": self.panel_server.id}, {"name": self.panel_settings.get("embed_name")}]}))

    async def send_log(
        self,
        log_type: LOG_TYPE,
        user: disnake.User,
        ticket: OpenTicket = None,
        ticket_channel: disnake.TextChannel = None,
    ):
        components = []
        if log_type == LOG_TYPE.BUTTON_CLICK:
            embed = disnake.Embed(
                description=f'**Button Clicked**\n'
                f' - User: {user.mention}({user})\n'
                f' - Button: {self.label}\n'
                f' - Panel: {self.panel_name}\n'
                f' - Time: {self.bot.timestamper(unix_time=int(datetime.utcnow().timestamp())).cal_date}',
                color=disnake.Color(2829617),
            )
            embed.set_author(name=user.name, icon_url=user.display_avatar.url)
            channel = self.ticket_button_click_log

        elif log_type == LOG_TYPE.STATUS_CHANGE:
            ticket_user = await self.bot.getch_user(ticket.user)
            embed = disnake.Embed(
                description=f'**Status Changed | {ticket.status.capitalize()}**\n'
                f' - By: {user.mention}\n'
                f' - Ticket: {ticket_channel.name}, {ticket_user.mention}({ticket_user})\n'
                f' - Time: {self.bot.timestamper(unix_time=int(datetime.utcnow().timestamp())).cal_date}',
                color=disnake.Color(2829617),
            )
            embed.set_author(name=user.name, icon_url=user.display_avatar.url)
            channel = self.status_change_log

        elif log_type == LOG_TYPE.TICKET_CLOSE:
            ticket_user = await self.bot.getch_user(ticket.user)
            creation_time = disnake.utils.snowflake_time(ticket_channel.id)
            embed = disnake.Embed(
                description=f'**Ticket Closed**\n'
                f' - By: {user.mention}\n'
                f' - Ticket: {ticket_channel.name}, {ticket_user.mention}({ticket_user})\n'
                f' - Time: {self.bot.timestamper(unix_time=int(datetime.now().timestamp())).cal_date}\n'
                f' - Ticket Creation: {self.bot.timestamper(unix_time=int(creation_time.timestamp())).cal_date}',
                color=disnake.Color(2829617),
            )
            embed.set_author(name=user.name, icon_url=user.display_avatar.url)
            channel = self.ticket_close_log

            buttons = disnake.ui.ActionRow()
            if ticket.thread is not None:
                thread_channel = await self.bot.getch_channel(channel_id=ticket.thread)
                if thread_channel is not None:
                    transcript = await chat_exporter.export(thread_channel)
                    link = await upload_html_to_cdn(
                        bytes_=io.BytesIO(transcript.encode()),
                        id=f'transcript-{thread_channel.id}',
                    )
                    link = f'https://api.clashking.xyz/renderhtml?url={link}'
                    buttons = disnake.ui.ActionRow()
                    buttons.append_item(disnake.ui.Button(label=f'Thread Transcript', url=link))

            transcript = await chat_exporter.export(ticket_channel)
            link = await upload_html_to_cdn(
                bytes_=io.BytesIO(transcript.encode()),
                id=f'transcript-{ticket_channel.id}',
            )
            link = f'https://api.clashking.xyz/renderhtml?url={link}'
            buttons.append_item(disnake.ui.Button(label=f'Channel Transcript', url=link))
            components = [buttons]

        try:
            channel = await self.bot.getch_channel(channel)
            if channel is not None:
                await channel.send(embed=embed, components=components)
        except Exception:
            pass


class TicketPanel(BaseTicket):
    def __init__(self, bot: CustomClient, panel_settings):
        super().__init__(bot, panel_settings)
        self.buttons: List[Ticket_Buttons] = [
            Ticket_Buttons(
                button_data=button_data | {'count': count},
                bot=bot,
                panel_settings=panel_settings,
            )
            for count, button_data in enumerate(self.panel_settings.get('components', []))
        ]
        self.open_category: int = self.panel_settings.get('open-category')
        self.sleep_category: int = self.panel_settings.get('sleep-category')
        self.closed_category: int = self.panel_settings.get('closed-category')
        self.approve_messages: List[ApproveMessages] = [ApproveMessages(data=msg) for msg in self.panel_settings.get('approve_messages', [])]

    def get_message(self, name: str):
        msg = next((msg for msg in self.approve_messages if msg.name == name), None)
        return msg

    async def add_edit_approve_messages(self, name: str, message: str):
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$pull': {'approve_messages': {'name': name}}},
        )
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$push': {'approve_messages': {'name': name, 'message': message}}},
        )

    async def create_button(self, label: str, color: str, emoji: str = None):
        button = self.get_button(label=label)
        if button is not None:
            raise ButtonAlreadyExists

        button_id = f'{self.panel_name}_{int(datetime.utcnow().timestamp())}'
        button = Button(
            label=label,
            emoji=emoji,
            style=text_style_conversion[color],
            custom_id=button_id,
        )

        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {
                '$push': {'components': button.to_component_dict()},
                '$set': {
                    f'{button_id}_settings': {
                        'message': None,
                        'questions': None,
                        'mod_role': None,
                        'private_thread': False,
                        'roles_to_add': None,
                        'roles_to_remove': None,
                        'apply_clans': None,
                        'account_apply': False,
                        'player_info': False,
                    }
                },
            },
        )

    async def edit_button(self, button: str, new_text: str, new_color: str, new_emoji: str = None):
        button = self.get_button(label=button)
        if button is None:
            raise ButtonNotFound

        new_button = disnake.ui.Button(
            label=new_text,
            emoji=new_emoji,
            style=text_style_conversion[new_color],
            custom_id=button.custom_id,
        )
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$unset': {f'components.{button.count_spot}': 1}},
        )
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$pull': {f'components': None}},
        )
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$push': {'components': new_button.to_component_dict()}},
        )

    def get_button(self, label: str = None, custom_id: str = None):
        if label is not None:
            button = next((button for button in self.buttons if button.label == label), None)
        else:
            button = next(
                (button for button in self.buttons if button.custom_id == custom_id),
                None,
            )
        return button


class TownhallRequirements:
    def __init__(self, data):
        self.townhall = data.get('TH', 0)
        self.barbarian_king = data.get('BK', 0)
        self.archer_queen = data.get('AQ', 0)
        self.grand_warden = data.get('GW', 0)
        self.royal_champ = data.get('RC', 0)
        self.war_stars = data.get('WARST', 0)


class Ticket_Buttons(BaseTicket):
    def __init__(self, bot: CustomClient, panel_settings, button_data):
        super().__init__(bot, panel_settings)
        self.button_data = button_data
        self.bot = bot
        self.custom_id = button_data.get('custom_id')
        self.style = button_data.get('style')
        self.label = button_data.get('label')
        self.count_spot = button_data.get('count')
        self.settings = panel_settings.get(f'{self.custom_id}_settings')
        self.message: Embed = (
            Embed.from_dict(data=self.settings.get('message'))
            if self.settings.get('message') is not None
            else Embed(
                description='This ticket will be handled shortly!\nPlease be patient.',
                color=disnake.Color.green(),
            )
        )

        self.roles_to_add: List[int] = self.settings.get('roles_to_add', []) if self.settings.get('roles_to_add') is not None else []
        self.roles_to_remove: List[int] = self.settings.get('roles_to_remove', []) if self.settings.get('roles_to_remove') is not None else []

        self.questions: List[str] = self.settings.get('questions', [])
        self.clans_can_apply: List[str] = self.settings.get('apply_clans', [])
        self.account_apply: bool = self.settings.get('account_apply', False)
        self.number_allowed_to_apply: int = self.settings.get('num_apply', 25)
        self.townhall_minimum: int = self.settings.get('th_min', 0)
        self.send_player_info: bool = self.settings.get('player_info', False)
        self.townhall_requirements: dict = self.settings.get('townhall_requirements', {})
        self.private_thread: bool = self.settings.get('private_thread', False)

        self.ping_staff_roles: List[int] = self.settings.get('mod_role', []) if self.settings.get('mod_role') is not None else []
        self.no_ping_staff_roles: List[int] = self.settings.get('no_ping_mod_role', []) if self.settings.get('no_ping_mod_role') is not None else []

        self.naming_convention: str = self.settings.get('naming', '{ticket_count}-{user}')

    def get_townhall_requirement(self, townhall_level: int):
        specific_townhall_requirement = self.townhall_requirements.get(str(townhall_level), {'TH': townhall_level})
        return TownhallRequirements(data=specific_townhall_requirement)

    async def set_townhall_requirements(self, requirements: dict):
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$set': {f'{self.custom_id}_settings.townhall_requirements': requirements}},
        )

    async def set_player_info(self, state: bool):
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$set': {f'{self.custom_id}_settings.player_info': state}},
        )

    async def set_account_apply(self, state: bool):
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$set': {f'{self.custom_id}_settings.account_apply': state}},
        )

    async def set_townhall_minimum(self, level: int):
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$set': {f'{self.custom_id}_settings.th_min': level}},
        )

    async def set_number_allowed_to_apply(self, num: int):
        await self.bot.tickets.update_one(
            {'$and': [{'server_id': self.panel_server.id}, {'name': self.panel_name}]},
            {'$set': {f'{self.custom_id}_settings.num_apply': num}},
        )

    @property
    def button(self):
        emoji = self.button_data.get('emoji')
        if emoji is not None:
            if emoji.get('id') is not None:
                emoji = self.bot.partial_emoji_gen(f"<:{emoji.get('name')}:{emoji.get('id')}>")
            else:
                emoji = emoji.get('name')
        style = {
            1: ButtonStyle.primary,
            2: ButtonStyle.secondary,
            3: ButtonStyle.success,
            4: ButtonStyle.danger,
        }
        return Button(
            label=self.label,
            emoji=emoji,
            style=style[self.style],
            custom_id=self.custom_id,
        )
