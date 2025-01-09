import disnake
import pytz
from disnake.ext import commands

from utility.general import calculate_time


utc = pytz.utc

from classes.bot import CustomClient
from classes.DatabaseClient.Classes.settings import DatabaseClan
from exceptions.CustomExceptions import MissingWebhookPerms


class VoiceStatCron(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.scheduler.add_job(self.voice_update, 'interval', minutes=15)

    async def voice_update(self):
        results = self.bot.server_db.find()
        limit = await self.bot.server_db.count_documents(filter={})
        for r in await results.to_list(length=limit):
            channel = r.get('cwlCountdown')
            server = r.get('server')
            if server not in self.bot.OUR_GUILDS:
                continue
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel_id=channel, raise_exception=True)
                    time_ = await calculate_time('CWL')
                    prev_name = channel.name
                    text = f'CWL {time_}'
                    if '|' in prev_name:
                        custom = prev_name.split('|')[0]
                        text = f'{custom}| {text}'
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({'server': server}, {'$set': {'cwlCountdown': None}})

            channel = r.get('gamesCountdown')
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel_id=channel, raise_exception=True)
                    time_ = await calculate_time('Clan Games')
                    prev_name = channel.name
                    text = f'CG {time_}'
                    if '|' in prev_name:
                        custom = prev_name.split('|')[0]
                        text = f'{custom}| {text}'
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({'server': server}, {'$set': {'gamesCountdown': None}})

            channel = r.get('raidCountdown')
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel_id=channel, raise_exception=True)
                    time_ = await calculate_time('Raid Weekend')
                    prev_name = channel.name
                    text = f'Raids {time_}'
                    if '|' in prev_name:
                        custom = prev_name.split('|')[0]
                        text = f'{custom}| {text}'
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({'server': server}, {'$set': {'raidCountdown': None}})

            channel = r.get('eosCountdown')
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel_id=channel, raise_exception=True)
                    time_ = await calculate_time('EOS')
                    prev_name = channel.name
                    text = f'EOS {time_}'
                    if '|' in prev_name:
                        custom = prev_name.split('|')[0]
                        text = f'{custom}| {text}'
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({'server': server}, {'$set': {'eosCountdown': None}})

            channel = r.get('eosDayCountdown')
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel_id=channel, raise_exception=True)
                    time_ = await calculate_time('Season Day')
                    prev_name = channel.name
                    text = f'Day {time_}'
                    if '|' in prev_name:
                        custom = prev_name.split('|')[0]
                        text = f'{custom}| {text}'
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({'server': server}, {'$set': {'eosDayCountdown': None}})

            channel = r.get('memberCount')
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel_id=channel, raise_exception=True)
                    member_tags = await self.bot.get_family_member_tags(guild_id=server)
                    await channel.edit(name=f'{len(member_tags)} Clan Members')
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({'server': server}, {'$set': {'memberCount': None}})

        for clan_result in await self.bot.clan_db.find({'warCountdown': {'$ne': None}}).to_list(length=None):
            try:
                db_clan = DatabaseClan(bot=self.bot, data=clan_result)

                if db_clan.server_id not in self.bot.OUR_GUILDS:
                    continue

                try:
                    channel = await self.bot.getch_channel(channel_id=db_clan.war_countdown, raise_exception=True)
                    war = await self.bot.get_clanwar(clanTag=db_clan.tag)
                    time_ = await calculate_time('War Score', war=war)
                    prev_name = channel.name
                    if ':' not in prev_name:
                        raise MissingWebhookPerms
                    previous_identifier = prev_name.split(':')[0]
                    text = f'{previous_identifier}: {time_}'
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                    await db_clan.set_war_countdown(id=None)
            except Exception:
                continue

        war_tags = await self.bot.clan_db.distinct('tag', filter={'warTimerCountdown': {'$ne': None}})
        wars = await self.bot.get_clan_wars(tags=war_tags)
        war_map = {w.clan.tag: w for w in wars if w is not None}
        for clan_result in await self.bot.clan_db.find({'warTimerCountdown': {'$ne': None}}).to_list(length=None):
            try:
                db_clan = DatabaseClan(bot=self.bot, data=clan_result)
                if db_clan.server_id not in self.bot.OUR_GUILDS:
                    continue

                try:
                    channel = await self.bot.getch_channel(channel_id=db_clan.war_timer_countdown, raise_exception=True)
                    war = war_map.get(db_clan.tag)
                    time_ = await calculate_time('War Timer', war=war)
                    prev_name = channel.name
                    if ':' not in prev_name:
                        raise MissingWebhookPerms
                    previous_identifier = prev_name.split(':')[0]
                    text = f'{previous_identifier}: {time_}'
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                    await db_clan.set_war_timer_countdown(id=None)
            except Exception:
                continue


def setup(bot: CustomClient):
    bot.add_cog(VoiceStatCron(bot))
