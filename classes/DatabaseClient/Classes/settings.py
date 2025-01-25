from typing import TYPE_CHECKING, List, Union

import coc
import disnake

from utility.constants import AUTOREFRESH_TRIGGERS, ROLE_TREATMENT_TYPES


if TYPE_CHECKING:
    from classes.bot import CustomClient
else:
    from disnake import AutoShardedClient as CustomClient

from coc import utils

from exceptions.CustomExceptions import MessageException


class DatabaseServer:
    def __init__(self, bot: CustomClient, data: dict):
        self.bot = bot
        self.__data = data
        self._data = data
        self.server_id = data.get('server')

        self.autoboard_limit = data.get('autoboard_limit', 0)

        self.leadership_eval = data.get('leadership_eval', True)
        self.prefix = data.get('prefix', 'do ')
        self.greeting = data.get('greeting')
        self.use_api_token = data.get('api_token', True)
        self.league_roles = [MultiTypeRole(bot=bot, data=d) for d in data.get('eval', {}).get('league_roles', [])]
        self.builder_league_roles = [MultiTypeRole(bot=bot, data=d) for d in data.get('eval', {}).get('builder_league_roles', [])]
        self.ignored_roles = [EvalRole(bot=bot, data=d) for d in data.get('eval', {}).get('ignored_roles', [])]
        self.family_roles = [EvalRole(bot=bot, data=d) for d in data.get('eval', {}).get('family_roles', [])]
        self.not_family_roles = [EvalRole(bot=bot, data=d) for d in data.get('eval', {}).get('not_family_roles', [])]
        self.only_family_roles = [EvalRole(bot=bot, data=d) for d in data.get('eval', {}).get('only_family_roles', [])]
        self.family_elder_roles = [
            EvalRole(bot=bot, data=d) for d in data.get('eval', {}).get('family_position_roles', []) if d.get('type') == 'family_elder_roles'
        ]
        self.family_coleader_roles = [
            EvalRole(bot=bot, data=d) for d in data.get('eval', {}).get('family_position_roles', []) if d.get('type') == 'family_co-leader_roles'
        ]
        self.family_leader_roles = [
            EvalRole(bot=bot, data=d) for d in data.get('eval', {}).get('family_position_roles', []) if d.get('type') == 'family_leader_roles'
        ]

        self.townhall_roles = [TownhallRole(bot=bot, data=d) for d in data.get('eval', {}).get('townhall_roles', [])]
        self.builderhall_roles = [BuilderHallRole(bot=bot, data=d) for d in data.get('eval', {}).get('builderhall_roles', [])]

        self.achievement_roles = [AchievementRole(data=d) for d in data.get('achievement_roles', [])]

        self.status_roles = [StatusRole(data=d) for d in data.get('status_roles', {}).get('discord', [])]

        self.clans = [DatabaseClan(bot=bot, data=d) for d in data.get('clans', [])]
        self.category_roles = data.get('category_roles', {})

        self.blacklisted_roles: List[int] = data.get('blacklisted_roles', [])
        self.role_treatment: List[str] = data.get('role_treatment', ROLE_TREATMENT_TYPES)
        self.auto_eval_nickname: bool = data.get('auto_eval_nickname', False)
        self.autoeval_triggers = set(data.get('autoeval_triggers', AUTOREFRESH_TRIGGERS))
        self.auto_eval_log = data.get('autoeval_log')
        self.auto_eval_status = data.get('autoeval', False)

        self.family_label = data.get('family_label', '')
        self.banlist_channel = data.get('banlist')
        self.strike_log_channel = data.get('strike_log')
        self.reddit_feed = data.get('reddit_feed')
        self.embed_color = disnake.Color(data.get('embed_color', 0x2ECC71))
        self.tied_stats_only = data.get('tied', True)

        self.family_nickname_convention = data.get('nickname_rule', '{discord_display_name}')
        self.non_family_nickname_convention = data.get('non_family_nickname_rule', '{discord_display_name}')
        self.change_nickname = data.get('change_nickname', True)
        self.flair_non_family: bool = data.get('flair_non_family', True)

        self.clan_link_parse = data.get('link_parse', {}).get('clan', True)
        self.army_link_parse = data.get('link_parse', {}).get('army', True)
        self.player_link_parse = data.get('link_parse', {}).get('player', True)
        self.base_link_parse = data.get('link_parse', {}).get('base', True)
        self.show_command_parse = data.get('link_parse', {}).get('show', True)
        self.link_parse_channels: list[int] = [int(i) for i in data.get('link_parse', {}).get('channels', [])]

        self.welcome_link_log = ServerLog(parent=self, type='welcome_link')

    async def set_flair_non_family(self, option: bool):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'flair_non_family': option}})

    async def set_allowed_link_parse(self, type: str, status: bool):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {f'link_parse.{type}': status}})

    async def set_allowed_link_parse_channels(self, channel_ids: list[int]):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {f'link_parse.channels': channel_ids}})

    async def set_change_nickname(self, status: bool):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'change_nickname': status}})

    async def set_full_whitelist_role(self, id: int | None):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'full_whitelist_role': id}})

    async def set_family_nickname_convention(self, rule: str):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'nickname_rule': rule}})

    async def set_non_family_nickname_convention(self, rule: str):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'non_family_nickname_rule': rule}})

    async def set_auto_eval_nickname(self, status: bool):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'auto_eval_nickname': status}})

    async def set_auto_eval_triggers(self, triggers: List[str]):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'autoeval_triggers': triggers}})

    async def set_auto_eval_log(self, id: int | None):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'autoeval_log': id}})

    async def set_banlist_channel(self, id: Union[int, None]):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'banlist': id}})

    async def set_strike_log_channel(self, id: Union[int, None]):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'strike_log': id}})

    async def set_api_token(self, status: bool):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'api_token': status}})

    async def set_autoboard_limit(self, limit: int):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'autoboard_limit': limit}})

    async def set_leadership_eval(self, status: bool):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'leadership_eval': status}})

    async def add_blacklisted_role(self, id: int):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$push': {'blacklisted_roles': id}})

    async def remove_blacklisted_role(self, id: int):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$pull': {'blacklisted_roles': id}})

    async def set_role_treatment(self, treatment: List[str]):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'role_treatment': treatment}})

    async def set_tied_stats(self, state: bool):
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'tied': state}})

    async def set_hex_code(self, hex_code: str):
        hex_code = hex_code.replace('#', '')
        hex_code = int(hex_code, 16)
        await self.bot.server_db.update_one({'server': self.server_id}, {'$set': {'embed_color': hex_code}})

    async def get_achievement_role_by_type(self, type: str, award_type: str = None):

        result = self.__data.get('achievement_roles', {}).get(type, [])
        if award_type is not None:
            result = filter(
                lambda x: (x.get('amount') > 100 if award_type == 'amount' else x.get('amount') <= 100),
                result,
            )
        return result

    async def add_achievement_role(self, type: str, season: str, amount: int, role_id: int):
        # scope = both, family, clan
        await self.bot.server_db.update_one(
            {'server': self.server_id},
            {
                '$addToSet': {
                    f'achievement_roles': {
                        'type': type,
                        'season': season,
                        'amount': amount,
                        'id': role_id,
                    }
                }
            },
        )

    async def add_status_role(self, months: int, role_id: int, type: str):
        # Retrieve the current set of status roles
        current_roles = await self.bot.server_db.find_one({'server': self.server_id}, {f'status_roles.{type}': 1})

        # Extract the current roles for the given type
        current_roles_set = current_roles.get('status_roles', {}).get(type, [])

        # Check if the months value already exists in the set
        if any(role['months'] == months for role in current_roles_set):
            # Update the existing role with the same months value
            await self.bot.server_db.update_one(
                {'server': self.server_id, f'status_roles.{type}.months': months},
                {'$set': {f'status_roles.{type}.$.id': role_id}},
            )
        else:
            # Add the new role if the months value does not exist
            await self.bot.server_db.update_one(
                {'server': self.server_id},
                {'$addToSet': {f'status_roles.{type}': {'months': months, 'id': role_id}}},
            )

    async def remove_status_role(self, months: int, type: str):
        await self.bot.server_db.update_one(
            {'server': self.server_id},
            {'$pull': {f'status_roles.{type}': {'months': months}}},
        )

    def get_clan(self, clan_tag: str, silent=False):
        matching_clan = utils.get(self.clans, tag=clan_tag)
        if matching_clan is None:
            if not silent:
                raise MessageException(f'There is no clan ({clan_tag}) linked to this server.')
            else:
                return None
        return matching_clan


class ServerLog:
    def __init__(self, parent: DatabaseServer, type: str):
        self.data = parent._data.get('logs', {}).get(type, {})
        self.webhook = self.data.get('webhook')
        self.thread = self.data.get('thread')
        self.embeds = self.data.get('embeds')
        self.buttons = self.data.get('buttons')
        self.button_color = self.data.get('button_color')
        self.parent = parent
        self.type = type

    async def get_webhook_channel_mention(self) -> Union[None, str]:
        if self.webhook is not None:
            if self.thread is None:
                try:
                    webhook = await self.parent.bot.getch_webhook(self.webhook)
                    return webhook.channel.mention
                except:
                    return None
            else:
                try:
                    channel = await self.parent.bot.getch_channel(self.thread, raise_exception=True)
                    return channel.mention
                except:
                    return None
        return None

    async def set_webhook(self, id: Union[int, None]):
        await self.parent.bot.server_db.update_one(
            {'server': self.parent.server_id},
            {'$set': {f'logs.{self.type}.webhook': id}},
        )

    async def set_thread(self, id: Union[int, None]):
        await self.parent.bot.server_db.update_one(
            {'server': self.parent.server_id},
            {'$set': {f'logs.{self.type}.thread': id}},
        )

    async def set_embeds(self, embeds: list[dict] | None):
        await self.parent.bot.server_db.update_one(
            {'server': self.parent.server_id},
            {'$set': {f'logs.{self.type}.embeds': embeds}},
        )

    async def set_buttons(self, buttons: list[str] | None, button_color: str = None):
        await self.parent.bot.server_db.update_one(
            {'server': self.parent.server_id},
            {
                '$set': {
                    f'logs.{self.type}.buttons': buttons,
                    f'logs.{self.type}.button_color': button_color,
                }
            },
        )


class EvalRole:
    def __init__(self, bot: CustomClient, data):
        self.server: int = data.get('server')
        self.id: int = data.get('role')


class BuilderHallRole(EvalRole):
    def __init__(self, bot: CustomClient, data):
        super().__init__(bot=bot, data=data)
        self.builderhall: str = data.get('bh')


class MultiTypeRole(EvalRole):
    def __init__(self, bot: CustomClient, data):
        super().__init__(bot=bot, data=data)
        self.type: str = data.get('type')


class AchievementRole:
    def __init__(self, data: dict):
        self.type = data.get('type')
        self.season = data.get('season')
        self.amount = data.get('amount')
        self.id = data.get('id')

    @property
    def is_rank(self):
        return self.amount <= 100


class StatusRole:
    def __init__(self, data: dict):
        self.months = data.get('months')
        self.id = data.get('id')


class TownhallRole(EvalRole):
    def __init__(self, bot: CustomClient, data):
        super().__init__(bot=bot, data=data)
        self.townhall: str = data.get('th')


class DatabaseClan:
    def __init__(self, bot: CustomClient, data):
        self.name = data.get('name')
        self.bot = bot
        self.data = data
        self.server_id = data.get('server')
        self.tag = data.get('tag')
        self.leadership_eval = data.get('leadership_eval')
        self.category = data.get('category')
        self.member_role = data.get('generalRole')
        self.leader_role = data.get('leaderRole')
        self.abbreviation = data.get('abbreviation', '')
        self.clan_channel = data.get('clanChannel')
        self.join_log = Join_Log(parent=self, type='join_log')
        self.leave_log = Join_Log(parent=self, type='leave_log')
        self.capital_donations = ClanLog(parent=self, type='capital_donations')
        self.capital_attacks = ClanLog(parent=self, type='capital_attacks')
        self.raid_map = ClanLog(parent=self, type='raid_map')
        self.capital_weekly_summary = ClanLog(parent=self, type='capital_weekly_summary')
        self.raid_panel = CapitalPanel(parent=self, type='new_raid_panel')
        self.donation_log = ClanLog(parent=self, type='donation_log')
        self.clan_achievement_log = ClanLog(parent=self, type='clan_achievement_log')
        self.clan_requirements_log = ClanLog(parent=self, type='clan_requirements_log')
        self.clan_description_log = ClanLog(parent=self, type='clan_description_log')
        self.cwl_lineup_change_log = ClanLog(parent=self, type='cwl_lineup_change')

        self.super_troop_boost_log = ClanLog(parent=self, type='super_troop_boost')
        self.role_change = ClanLog(parent=self, type='role_change')
        self.troop_upgrade = ClanLog(parent=self, type='troop_upgrade')
        self.th_upgrade = ClanLog(parent=self, type='th_upgrade')
        self.league_change = ClanLog(parent=self, type='league_change')
        self.spell_upgrade = ClanLog(parent=self, type='spell_upgrade')
        self.hero_upgrade = ClanLog(parent=self, type='hero_upgrade')
        self.hero_equipment_upgrade = ClanLog(parent=self, type='hero_equipment_upgrade')

        self.name_change = ClanLog(parent=self, type='name_change')
        self.ban_alert_channel = data.get('ban_alert_channel')
        self.war_log = ClanLog(parent=self, type='war_log')
        self.war_panel = WarPanel(parent=self, type='war_panel')
        self.legend_log_attacks = ClanLog(parent=self, type='legend_log_attacks')
        self.legend_log_defenses = ClanLog(parent=self, type='legend_log_defenses')
        self.greeting = data.get('greeting', '')
        self.war_countdown = data.get('warCountdown')
        self.war_timer_countdown = data.get('warTimerCountdown')
        self.member_count_warning = MemberCountWarning(parent=self)
        self.auto_greet_option = data.get('auto_greet_option', 'Never')

    async def set_war_countdown(self, id: Union[int, None]):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'warCountdown': id}},
        )

    async def set_war_timer_countdown(self, id: Union[int, None]):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'warTimerCountdown': id}},
        )

    async def set_clan_channel(self, id: Union[int, None]):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'clanChannel': id}},
        )

    async def set_member_role(self, id: Union[int, None]):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'generalRole': id}},
        )

    async def set_leadership_role(self, id: Union[int, None]):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'leaderRole': id}},
        )

    async def set_ban_alert_channel(self, id: Union[int, None]):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'ban_alert_channel': id}},
        )

    async def set_greeting(self, text: str):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'greeting': text}},
        )

    async def set_auto_greet(self, option: str):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'auto_greet_option': option}},
        )

    async def set_category(self, category: str):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'category': category}},
        )

    async def set_nickname_label(self, abbreviation: str):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'abbreviation': abbreviation}},
        )

    async def set_strike_button(self, set: bool):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'logs.leave_log.strike_button': set}},
        )

    async def set_ban_button(self, set: bool):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'logs.leave_log.ban_button': set}},
        )

    async def set_profile_button(self, set: bool):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {'logs.join_log.profile_button': set}},
        )

    async def add_refresh_board(self, type: str, scope: str, message_id: int, webhook_id: int):
        await self.bot.refresh_boards.insert_one(
            {
                'type': type,
                'scope': scope,
                'message_id': message_id,
                'webhook_id': webhook_id,
            }
        )

    async def set_server_event_creation_status(self, type: str, status: bool):
        await self.bot.clan_db.update_one(
            {'$and': [{'tag': self.tag}, {'server': self.server_id}]},
            {'$set': {f'events.{type.lower()}': status}},
        )


class MemberCountWarning:
    def __init__(self, parent: DatabaseClan):
        self.data = parent.data.get('member_count_warning', {})
        self.channel = self.data.get('channel')
        self.above = self.data.get('above')
        self.below = self.data.get('below')
        self.role = self.data.get('role')
        self.parent = parent

    async def set_channel(self, id: Union[int, None]):
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'member_count_warning.channel': id}},
        )

    async def set_above(self, num: Union[int, None]):
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'member_count_warning.above': num}},
        )

    async def set_below(self, num: Union[int, None]):
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'member_count_warning.below': num}},
        )

    async def set_role(self, id: Union[int, None]):
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'member_count_warning.role': id}},
        )


class ClanLog:
    def __init__(self, parent: DatabaseClan, type: str):
        self.data = parent.data.get('logs', {}).get(type, {})
        self.webhook = self.data.get('webhook')
        self.thread = self.data.get('thread')
        self.parent = parent
        self.type = type

    async def get_webhook_channel_mention(self) -> Union[None, str]:
        if self.webhook is not None:
            if self.thread is None:
                try:
                    webhook = await self.parent.bot.getch_webhook(self.webhook)
                    return webhook.channel.mention
                except:
                    return None
            else:
                try:
                    channel = await self.parent.bot.getch_channel(self.thread, raise_exception=True)
                    return channel.mention
                except:
                    return None
        return None

    async def set_webhook(self, id: Union[int, None]):
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'logs.{self.type}.webhook': id}},
        )

    async def set_thread(self, id: Union[int, None]):
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'logs.{self.type}.thread': id}},
        )


class Join_Log(ClanLog):
    def __init__(self, parent: DatabaseClan, type: str):
        super().__init__(parent=parent, type=type)
        self.strike_button = self.data.get('strike_button', False)
        self.ban_button = self.data.get('ban_button', False)
        self.profile_button = self.data.get('profile_button', False)


class WarPanel(ClanLog):
    def __init__(self, parent: DatabaseClan, type: str):
        super().__init__(parent=parent, type=type)
        self.war_id = self.data.get('war_id')
        self.message_id = self.data.get('war_message')
        self.channel_id = self.data.get('war_channel')

    async def set_war_id(self, war: coc.ClanWar):
        war_id = f'{war.clan.tag}v{war.opponent.tag}-{int(war.preparation_start_time.time.timestamp())}'
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'logs.{self.type}.war_id': war_id}},
        )

    async def set_message_id(self, id: Union[str, None]):
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'logs.{self.type}.war_message': id}},
        )

    async def set_channel_id(self, id: Union[str, None]):
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'logs.{self.type}.war_channel': id}},
        )


class CapitalPanel(ClanLog):
    def __init__(self, parent: DatabaseClan, type: str):
        super().__init__(parent=parent, type=type)
        self.raid_id = self.data.get('raid_id')
        self.message_id = self.data.get('raid_message')

    async def set_raid_id(self, raid: coc.RaidLogEntry):
        raid_id = f'{raid.clan_tag}v{int(raid.start_time.time.timestamp())}'
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'logs.{self.type}.raid_id': raid_id}},
        )

    async def set_message_id(self, id: Union[str, None]):
        await self.parent.bot.clan_db.update_one(
            {'$and': [{'tag': self.parent.tag}, {'server': self.parent.server_id}]},
            {'$set': {f'logs.{self.type}.raid_message': id}},
        )


class CustomServer:
    def __init__(self, guild: disnake.Guild, bot: CustomClient):
        self.guild = guild
        self.bot = bot
        self.server = None
        self.clans = []

    @property
    async def leadership_eval_choice(self):
        server = await self.bot.server_db.find_one({'server': self.guild.id})
        eval_option = server.get('leadership_eval', True)
        return True if eval_option is None else eval_option

    @property
    async def nickname_choice(self):
        server = await self.bot.server_db.find_one({'server': self.guild.id})
        auto_nick_type = server.get('auto_nick', 'Clan Abbreviations')
        return 'Clan Abbreviations' if auto_nick_type is None else auto_nick_type

    @property
    async def family_label(self):
        server = await self.bot.server_db.find_one({'server': self.guild.id})
        family_label = server.get('family_label')
        return '' if family_label is None else family_label

    async def change_leadership_eval(self, option: bool):
        await self.bot.server_db.update_one({'server': self.guild.id}, {'$set': {'leadership_eval': option}})

    async def change_auto_nickname(self, type: str):
        await self.bot.server_db.update_one({'server': self.guild.id}, {'$set': {'auto_nick': type}})

    async def set_family_label(self, label: str):
        await self.bot.server_db.update_one({'server': self.guild.id}, {'$set': {'family_label': label}})

    @property
    async def clan_list(self):
        clan_tags = []
        tracked = self.bot.clan_db.find({'server': self.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={'server': self.guild.id})
        if limit == 0:
            return clan_tags
        for tClan in await tracked.to_list(length=limit):
            clan_tags.append(tClan.get('tag'))
        return clan_tags

    async def initialize_server(self, with_clans=True):
        self.server = await self.bot.server_db.find_one({'server': self.guild.id})
        if with_clans:
            tracked = self.bot.clan_db.find({'server': self.guild.id})
            limit = await self.bot.clan_db.count_documents(filter={'server': self.guild.id})
            for clan in await tracked.to_list(length=limit):
                self.clans.append(clan)

    @property
    def banlist_channel(self):
        banlist = self.server.get('banlist')
        return f'<#{banlist}>' if banlist is not None else banlist

    @property
    def clan_greeting(self):
        greeting = self.server.get('greeting')
        return f'Welcome to {self.guild.name}!' if greeting is None else greeting

    @property
    def leadership_eval(self):
        eval = self.server.get('leadership_eval')
        return 'Off' if eval is False else 'On'

    @property
    def reddit_feed(self):
        reddit = self.server.get('reddit_feed')
        return f'<#{reddit}>' if reddit is not None else reddit

    @property
    def server_clans(self):
        return [ServerClan(clan, self.bot) for clan in self.clans]

    @property
    def reminders(self):
        return [clan.reminders for clan in self.server_clans]


class ServerClan:
    def __init__(self, clan_result, bot):
        self.clan_result = clan_result
        self.bot: CustomClient = bot

    @property
    def name(self):
        return self.clan_result.get('name')

    @property
    def tag(self):
        return self.clan_result.get('tag')

    @property
    def clan_channel(self):
        channel = self.clan_result.get('clanChannel')
        return f'<#{channel}>' if channel is not None else channel

    @property
    def member_role(self):
        role = self.clan_result.get('generalRole')
        return f'<@&{role}>' if role is not None else role

    @property
    def leader_role(self):
        role = self.clan_result.get('leaderRole')
        return f'<@&{role}>' if role is not None else role

    @property
    def join_log(self):
        channel = self.clan_result.get('joinlog')
        return f'<#{channel}>' if channel is not None else channel

    @property
    def capital_log(self):
        channel = self.clan_result.get('clan_capital')
        return f'<#{channel}>' if channel is not None else channel

    @property
    def war_log(self):
        channel = self.clan_result.get('war_log')
        return f'<#{channel}>' if channel is not None else channel

    @property
    async def legend_log(self):
        legend_log = self.clan_result.get('legend_log')
        if legend_log is None:
            return legend_log
        webhook = legend_log.get('webhook')
        thread = legend_log.get('thread')
        if webhook is None:
            return webhook
        if thread is not None:
            return f'<#{thread}>'
        try:
            webhook = await self.bot.fetch_webhook(webhook)
            return webhook.channel.mention
        except:
            return webhook

    @property
    def reminders(self):
        return Reminders(self.clan_result, self.bot)


class Reminders:
    def __init__(self, clan_result, bot):
        self.clan_result = clan_result
        self.reminders = clan_result.get('reminders')
        self.bot = bot

    @property
    def clan_capital_reminder(self):
        if self.reminders is None:
            return Reminder(
                clan_tag=None,
                reminder_result=self.reminders,
                bot=self.bot,
                reminder_type='clan_capital',
            )
        return Reminder(
            clan_tag=self.clan_result.get('tag'),
            reminder_result=self.reminders.get('clan_capital'),
            bot=self.bot,
            reminder_type='clan_capital',
        )


class Reminder:
    def __init__(self, clan_tag, reminder_result, bot, reminder_type):
        self.clan_tag = clan_tag
        self.reminder_result = reminder_result
        self.bot: CustomClient = bot
        self.reminder_type = reminder_type

    @property
    def channel(self):
        if self.reminder_result is None:
            return Channel(channel_id=None)
        return Channel(channel_id=self.reminder_result.get('channel'))

    async def set_channel(self, channel_id: int):
        await self.bot.reminders.update_one(
            {'tag': self.clan_tag},
            {'$set': {f'reminders.{self.reminder_type}.channel': channel_id}},
        )

    async def set_time(self, time: str, setting: bool):
        await self.bot.reminders.update_one(
            {'tag': self.clan_tag},
            {'$set': {f'reminders.{self.reminder_type}.{time}': setting}},
        )


class Channel:
    def __init__(self, channel_id):
        self.channel_id = channel_id

    def __str__(self):
        return None if self.channel_id is None else f'<#{self.channel_id}>'
