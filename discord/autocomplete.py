import re

import coc
import disnake
import pytz
from coc.miscmodels import Timestamp
from disnake.ext import commands
from expiring_dict import ExpiringDict

from classes.bot import CustomClient
from commands.help.utils import get_all_commands
from commands.reminders.utils import gen_capital_times, gen_clan_games_times, gen_inactivity_times, gen_roster_times, gen_war_times
from utility.clash.capital import gen_raid_weekend_datestrings
from utility.constants import TH_FILTER_OPTIONS, TOWNHALL_LEVELS
from utility.general import create_superscript
from utility.search import all_names, family_names, search_name_with_tag


USER_ACCOUNT_CACHE = ExpiringDict()


class Autocomplete(commands.Cog, name='Autocomplete'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]

    async def category(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({'server': ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={'server': ctx.guild.id})
        categories = []
        for tClan in await tracked.to_list(length=limit):
            category = tClan.get('category')
            if query.lower() in category.lower() and category not in categories:
                categories.append(category)
        return categories[:25]

    async def clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        if ctx.guild is None:
            guild_id = 0
        else:
            guild_id = ctx.guild.id
        if ctx.filled_options.get('family') is not None:
            if len(ctx.filled_options.get('family').split('|')) == 2:
                guild_id = int(ctx.filled_options.get('family').split('|')[-1])

        clan_list = []
        if query == '':
            pipeline = [
                {'$match': {'server': guild_id}},
                {'$sort': {'name': 1}},
                {'$limit': 25},
            ]
        else:
            pipeline = [
                {
                    '$search': {
                        'index': 'clan_name',
                        'autocomplete': {
                            'query': query,
                            'path': 'name',
                        },
                    }
                },
                {'$match': {'server': guild_id}},
            ]
        results = await self.bot.clan_db.aggregate(pipeline=pipeline).to_list(length=None)
        for document in results:
            clan_list.append(f'{document.get("name")} | {document.get("tag")}')

        if clan_list == [] and len(query) >= 3:
            if coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
            else:
                clan = None
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=10)
                for clan in results:
                    league = str(clan.war_league).replace('League ', '')
                    clan_list.append(f'{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}')
            else:
                clan_list.append(f'{clan.name} | {clan.tag}')
                return clan_list
        return clan_list[:25]

    async def multi_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        guild_id = ctx.guild.id
        if ctx.filled_options.get('family') is not None:
            if len(ctx.filled_options.get('family').split('|')) == 2:
                guild_id = int(ctx.filled_options.get('family').split('|')[-1])

        previous_query = ''
        old_query = query
        if len(query.split(',')) >= 2:
            previous_query = ','.join(query.split(',')[:-1]) + ','
            query = query.split(',')[-1]
            if query == ' ':
                query = ''
        clan_list = []
        if query == '':
            pipeline = [
                {'$match': {'server': guild_id}},
                {'$sort': {'name': 1}},
                {'$limit': 25},
            ]
        else:
            pipeline = [
                {
                    '$search': {
                        'index': 'clan_name',
                        'autocomplete': {
                            'query': query,
                            'path': 'name',
                        },
                    }
                },
                {'$match': {'server': guild_id}},
            ]
        results = await self.bot.clan_db.aggregate(pipeline=pipeline).to_list(length=None)
        for document in results:
            previous_split = old_query.split(',')[:-1]
            previous_split = [item.strip() for item in previous_split]
            if f'{document.get("name")} | {document.get("tag")}' in previous_split:
                continue
            clan_list.append(f'{previous_query}{document.get("name")} | {document.get("tag")}')
        return clan_list[:25]

    async def family_players(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await family_names(bot=self.bot, query=query, guild=ctx.guild)
        return names

    async def all_players(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await all_names(bot=self.bot, query=query)
        return names

    async def banned_players(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        query = re.escape(query)
        if query == '':
            names = await self.bot.banlist.find({'server': ctx.guild_id}, limit=25).to_list(length=25)
        else:
            names = await self.bot.banlist.find(
                {
                    '$and': [
                        {'server': ctx.guild_id},
                        {'name': {'$regex': f'^(?i).*{query}.*$'}},
                    ]
                },
                limit=25,
            ).to_list(length=25)
        return [f'{n.get("name")} | {n.get("VillageTag")}' for n in names]

    async def legend_players(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        query = re.escape(query)
        results = await search_name_with_tag(bot=self.bot, poster=False, query=query)
        legend_profile = await self.bot.legend_profile.find_one({'discord_id': ctx.author.id})
        if legend_profile:
            profile_tags = legend_profile.get('profile_tags', [])
            documents = await self.bot.player_stats.find(
                {'$and': [{'tag': {'$in': profile_tags}}, {'league': 'Legend League'}]},
                {'tag': 1, 'name': 1, 'townhall': 1},
            ).to_list(length=None)
            results = [
                (f'‡{create_superscript(document.get("townhall", 0))}{document.get("name")}' + ' | ' + document.get('tag'))
                for document in documents
                if query.lower() in document.get('name').lower()
            ] + results
        return results[:25]

    async def server(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        matches = []
        for guild in self.bot.guilds:
            if guild.member_count < 250:
                continue
            if query.lower() in guild.name.lower():
                matches.append(f'{guild.name} | {guild.id}')
            if len(matches) == 25:
                break
        return matches

    async def timezone(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        all_tz = pytz.common_timezones
        return_list = []
        for tz in all_tz:
            if query.lower() in tz.lower():
                return_list.append(tz)
        return return_list[:25]

    async def raid_weekend(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        weekends = gen_raid_weekend_datestrings(number_of_weeks=25)
        matches = []
        for weekend in weekends:
            if query.lower() in weekend.lower():
                matches.append(weekend)
        return matches

    async def ticket_panel(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        aliases = await self.bot.tickets.distinct('name', filter={'server_id': ctx.guild.id})
        alias_list = []
        for alias in aliases:
            if query.lower() in alias.lower():
                alias_list.append(f'{alias}')
        return alias_list[:25]

    async def multi_ticket_panel(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        aliases = await self.bot.tickets.distinct('name', filter={'server_id': ctx.guild.id})
        alias_list = []
        for alias in ['All Panels'] + aliases:
            if query.lower() in alias.lower():
                alias_list.append(f'{alias}')
        return alias_list[:25]

    async def new_categories(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        categories = await self.bot.clan_db.distinct('category', filter={'server': ctx.guild.id})
        starter_categories = ['General', 'Feeder', 'War', 'Esports']
        if query != '':
            starter_categories.insert(0, query)
        categories = starter_categories + [c for c in categories if c not in starter_categories]
        return categories[:25]

    async def th_filters(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        always = ['Equal Th Only'] + [str(t) for t in TOWNHALL_LEVELS] + TH_FILTER_OPTIONS
        if query != '':
            always = [a for a in always if query.lower() in a.lower()]
        return always[:25]

    async def user_accounts(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        user_option = ctx.filled_options.get('user', ctx.user.id)
        cached_accounts = USER_ACCOUNT_CACHE.get(user_option)
        if cached_accounts is None:
            accounts = await self.bot.link_client.get_linked_players(user_option)
            if accounts:
                accounts = await self.bot.get_players(tags=accounts, custom=False, use_cache=True)
                accounts.sort(key=lambda x: (x.town_hall, x.trophies), reverse=True)
                accounts = [f'{a.name} | {a.tag}' for a in accounts]
                USER_ACCOUNT_CACHE.ttl(ctx.user.id, accounts, ttl=120)
        else:
            accounts = cached_accounts
        return [a for a in accounts if query.lower() in a.lower()][:25]

    async def embeds(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        server_embeds = await self.bot.custom_embeds.find({'server': ctx.guild_id}, {'name': 1}).to_list(length=None)
        return [e.get('name') for e in server_embeds if query.lower() in e.get('name').lower()][:25]

    async def ticket_panel_buttons(self, ctx: disnake.ApplicationCommandInteraction, query: str):

        ticket_panels = await self.bot.tickets.find({'server_id': ctx.guild.id}, {'name': 1, '_id': 0, 'components.label': 1}).to_list(length=None)
        alias_list = []
        for panel in ticket_panels:
            panel_name = panel.get('name')
            for component in panel.get('components', []):
                alias = f"{component.get('label')} ({panel_name})"
                if query.lower() in alias.lower():
                    alias_list.append(alias)

        return alias_list[:25]

    async def ticket_buttons(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        panel_name = ctx.filled_options['panel_name']
        if panel_name == '':
            return []
        aliases = await self.bot.tickets.distinct(
            'components.label',
            filter={'$and': [{'server_id': ctx.guild.id}, {'name': panel_name}]},
        )
        alias_list = []
        for alias in aliases:
            if query.lower() in alias.lower():
                alias_list.append(f'{alias}')
        return alias_list[:25]

    async def reminder_times(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        if ctx.filled_options['type'] == 'War & CWL':
            all_times = gen_war_times()
        elif ctx.filled_options['type'] == 'Clan Capital':
            all_times = gen_capital_times()
        elif ctx.filled_options['type'] == 'Clan Games':
            all_times = gen_clan_games_times()
        elif ctx.filled_options['type'] == 'Inactivity':
            all_times = gen_inactivity_times()
        elif ctx.filled_options['type'] == 'Roster':
            all_times = gen_roster_times()
        else:
            return ['Not a valid reminder type']
        if len(query.split(',')) >= 2:
            new_query = query.split(',')[-1]
            previous_split = query.split(',')[:-1]
            previous_split = [item.strip() for item in previous_split]
            previous = ', '.join(previous_split)
            return [f'{previous}, {time}' for time in all_times if new_query.lower().strip() in time.lower() and time not in previous_split][:25]
        else:
            return [time for time in all_times if query.lower() in time.lower()][:25]

    async def previous_wars(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        if ctx.filled_options['clan'] != '':
            clan = await self.bot.getClan(ctx.filled_options['clan'])
            results = (
                await self.bot.clan_wars.find(
                    {
                        '$or': [
                            {'data.clan.tag': clan.tag},
                            {'data.opponent.tag': clan.tag},
                        ]
                    }
                )
                .sort('data.endTime', -1)
                .limit(25)
                .to_list(length=25)
            )
            options = []
            previous = set()
            prep_list = [
                5 * 60,
                15 * 60,
                30 * 60,
                60 * 60,
                2 * 60 * 60,
                4 * 60 * 60,
                6 * 60 * 60,
                8 * 60 * 60,
                12 * 60 * 60,
                16 * 60 * 60,
                20 * 60 * 60,
                24 * 60 * 60,
            ]

            for result in results:
                custom_id = result.get('custom_id')
                clan_name = result.get('data').get('clan').get('name')
                clan_tag = result.get('data').get('clan').get('tag')
                opponent_name = result.get('data').get('opponent').get('name')
                end_time = result.get('data').get('endTime')
                end_time = Timestamp(data=end_time)
                unique_id = result.get('war_id')
                if unique_id in previous:
                    continue
                previous.add(unique_id)
                days_ago = abs(end_time.seconds_until) // (24 * 3600)
                if days_ago == 0:
                    t = days_ago % (24 * 3600)
                    hour = t // 3600
                    time_text = f'{hour}H ago'
                else:
                    time_text = f'{days_ago}D ago'

                if result.get('data').get('tag') is not None:
                    type = 'CWL'
                elif (
                    Timestamp(data=result.get('data').get('startTime')).time - Timestamp(data=result.get('data').get('preparationStartTime')).time
                ).seconds in prep_list:
                    type = 'FW'
                else:
                    type = 'REG'

                if clan_tag == clan.tag:
                    text = f'{opponent_name} | {time_text} | {type} | {custom_id}'
                else:
                    text = f'{clan_name} | \u200e{time_text} | {type} | {custom_id}'
                if query.lower() in text.lower():
                    options.append(text)
            return options

    async def roster_alias(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        aliases = await self.bot.rosters.distinct('alias', filter={'server_id': ctx.guild_id})
        alias_list = []
        if ctx.data.focused_option.name == 'roster_' or ctx.options.get('role-refresh'):
            if ctx.options.get('columns'):
                alias_list.append('SET ALL')
            else:
                alias_list.append('REFRESH ALL')
        for alias in aliases:
            if query.lower() in alias.lower():
                alias_list.append(f'{alias}')
        return alias_list[:25]

    async def strike_ids(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        if selected := ctx.options.get('remove', {}).get('player'):
            tag: str = selected.split('|')[-1]
            results = await self.bot.strikelist.find({'$and': [{'tag': tag.replace(' ', '')}, {'server': ctx.guild.id}]}).to_list(length=None)
        else:
            results = await self.bot.strikelist.find({'server': ctx.guild.id}).to_list(length=None)
        return_text = []
        for result in results:
            text = f"{result.get('strike_id')} | {result.get('reason')}"
            if query.lower() in text.lower():
                return_text.append(text[:100])
            if len(return_text) == 25:
                break
        return return_text[:25]

    async def command_autocomplete(self, ctx: disnake.ApplicationCommandInteraction, query: str) -> list[str]:
        commands: dict[str, list[disnake.ext.commands.InvokableSlashCommand]] = get_all_commands(bot=self.bot)
        return [c.qualified_name for command_list in commands.values() for c in command_list if query.lower() in c.qualified_name.lower()][:25]

    async def command_category_autocomplete(self, ctx: disnake.ApplicationCommandInteraction, query: str) -> list[str]:
        commands: dict[str, list[disnake.ext.commands.InvokableSlashCommand]] = get_all_commands(bot=self.bot)
        categories = commands.keys()
        return [c for c in categories if query.lower() in c.lower()][:25]

    async def country_names(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        locations = await self.bot.get_country_names()
        results = []
        if query.lower() in 'Global':
            results.append('Global')
        for location in locations:
            if query.lower() in location.name.lower():
                ignored = ['Africa', 'Europe', 'North America', 'South America', 'Asia']
                if location.name not in ignored:
                    if location.name not in results:
                        results.append(location.name)
        return results[0:25]


def setup(bot: CustomClient):
    bot.add_cog(Autocomplete(bot))
