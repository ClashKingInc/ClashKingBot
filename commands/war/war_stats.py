import random

import emoji
import hikari
import lightbulb
import pendulum as pend
from hikari.components import ButtonStyle
from hikari.impl import ContainerComponentBuilder as Container
from hikari.impl import InteractiveButtonBuilder as Button
from hikari.impl import MessageActionRowBuilder as ActionRow
from hikari.impl import SectionComponentBuilder as Section
from hikari.impl import SelectOptionBuilder as SelectOption
from hikari.impl import TextDisplayComponentBuilder as Text
from hikari.impl import TextSelectMenuBuilder as TextSelectMenu
from hikari.impl import ThumbnailComponentBuilder as Thumbnail
from lightbulb import Choice

from api.client import ClashKingAPIClient
from api.player import WarStatsPlayer
from classes.cocpy.client import CustomClashClient
from classes.mongo import MongoClient
from commands.ext.autocomplete import clan, season
from commands.ext.components import register_action
from utility.constants import EMBED_ROW_LIMIT, ICON_PLACEHOLDERS
from utility.emojis import fetch_emoji
from utility.formatting import fmt, truncate_display_width
from utility.time import gen_season_date, month_to_ym, season_start_end


class WarStats(
    lightbulb.SlashCommand,
    name='stats',
    description='command-war-stats-description',
    localize=True,
):
    attack_type = lightbulb.string(
        'options-attack-type',
        'options-attack-type-description',
        choices=[
            Choice(
                name='choices-attacks',
                value='attacks',
                localize=True,
            ),
            Choice(
                name='choices-defenses',
                value='defenses',
                localize=True,
            ),
        ],
        localize=True,
    )

    clan = lightbulb.string(
        'options-clan',
        'options-clan-description',
        localize=True,
        autocomplete=clan,
        default=None,
    )

    user = lightbulb.user(
        'options-user',
        'options-user-description',
        localize=True,
        default=None,
    )

    group = lightbulb.string(
        'options-group',
        'options-group-description',
        localize=True,
        autocomplete=clan,
        default=None,
    )

    townhalls = lightbulb.string(
        'options-townhall-filter',
        'options-townhall-filter-description',
        localize=True,
        default=None,
    )

    war_types = lightbulb.string(
        'options-war-types',
        'options-war-types-description',
        localize=True,
        default=5,
    )

    season = lightbulb.string(
        'options-season',
        'options-season-description',
        localize=True,
        autocomplete=season,
        default=None,
    )

    days = lightbulb.integer(
        'options-days',
        'options-days-description',
        localize=True,
        autocomplete=clan,
        min_value=1,
        default=None,
    )

    wars = lightbulb.integer(
        'options-wars',
        'options-wars-description',
        localize=True,
        min_value=1,
        default=None,
    )

    limit = lightbulb.integer(
        'options-limit',
        'options-limit-description',
        localize=True,
        min_value=1,
        default=50,
    )

    min_attacks = lightbulb.integer(
        'options-min-attacks',
        'options-min-attacks-description',
        localize=True,
        default=0,
    )

    only_in_clan = lightbulb.boolean(
        'options-only-in-clan',
        'options-only-in-clan-description',
        localize=True,
        default=False,
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, mongo: MongoClient) -> None:

        time_start = pend.from_timestamp(timestamp=0, tz='UTC')
        time_end = pend.from_timestamp(timestamp=9999999999, tz='UTC')

        date_range = ''
        if self.days:
            time_start = pend.now('UTC').subtract(days=self.days)
            date_range = f'Last {self.days} days'
        elif self.wars:
            date_range = f'Last {self.wars} wars'
        else:
            self.season = self.season or gen_season_date(as_text=True)
            season_string = month_to_ym(self.season, locale=ctx.interaction.locale.replace('-', '_'))
            time_start, time_end = season_start_end(season_string)
            date_range = f'{self.season}'

        if self.war_types != 5:
            war_type_map = {'Regular': 1, 'Friendly': 2, 'CWL': 4}
            bitmap = 0
            for wt in self.war_types.split(','):
                wt = wt.strip()
                bitmap += war_type_map[wt]
            self.war_types = bitmap

        data = {
            '_id': str(ctx.interaction.id),
            'guild_id': ctx.guild_id,
            'user': self.user.id if self.user else None,
            'clan_tag': self.clan,
            'townhall_filter': self.townhalls,
            'sort_by': ['avg_three_stars'],
            'show': ['townhall', 'avg_three_stars', 'three_stars', 'name'],
            'time_start': time_start,
            'time_end': time_end,
            'war_types': self.war_types,
            'number_of_wars': self.wars or 1000,
            'limit': self.limit,
            'min_attacks': self.min_attacks,
            'date_range': date_range,
            'page': 0,
            'ascending': True,
        }
        await mongo.button_store.insert_one(data)
        container = await war_stats_page(action_id=str(ctx.interaction.id), **data)
        await ctx.respond(components=container[0])


@register_action('war_stats')
@lightbulb.di.with_di
async def war_stats_page(
    clan_tag: str | None,
    guild_id: int,
    action_id: str,
    sort_by: list[str],
    show: list[str],
    townhall_filter: str,
    time_start: pend.DateTime,
    time_end: pend.DateTime,
    number_of_wars: int,
    war_types: int,
    limit: int,
    min_attacks: int,
    date_range: str,
    ascending: bool,
    coc_client: CustomClashClient = lightbulb.di.INJECTED,
    ck_client: ClashKingAPIClient = lightbulb.di.INJECTED,
    color: hikari.Color = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    **kwargs,
):
    if clan_tag:
        clan = await coc_client.get_clan(tag=clan_tag)
        clan_tags = [clan.tag]
        badge = clan.badge.url
        title = f'## {clan.name} War Stats'
    else:
        guild_clans = await ck_client.get_basic_server_clan_list(server_id=guild_id)
        clan_tags = [c.tag for c in guild_clans]
        guild = bot.cache.get_guild(guild_id)
        badge = guild.make_icon_url() or random.choice(ICON_PLACEHOLDERS)
        title = f'## {guild.name} War Stats'

    all_war_stats = await ck_client.get_clan_war_stats(
        clan_tags=clan_tags,
        war_types=war_types,
        timestamp_start=time_start.int_timestamp,
        timestamp_end=time_end.int_timestamp,
        townhall_filter=townhall_filter,
        limit=number_of_wars,
    )

    label_map = {
        'name': 'Name',
        'townhall': 'Townhall',
        'tag': 'Player Tag',
        'avg_three_stars': '3 Star %',
        'avg_two_stars': '2 Star %',
        'avg_one_stars': '1 Star %',
        'avg_zero_stars': '0 Star %',
        'three_stars': '# of 3 Stars',
        'two_stars': '# of 2 Stars',
        'attacks': 'Total # of Attacks',
        'avg_order': 'Avg Attack Order',
        'avg_defender_position': 'Avg Defender Position',
        'avg_destruction': 'Avg Destruction',
        'avg_duration': 'Avg Duration',
        'avg_stars': 'Avg Stars',
        'avg_fresh': 'Fresh %',
        'missed_hits': 'Missed Attacks',
        'stars': 'Total Stars',
    }

    def sort(x: WarStatsPlayer):
        if sort_by[0] in ['name', 'townhall', 'tag']:
            item = x.__dict__[sort_by[0]]
            if isinstance(item, str):
                return emoji.replace_emoji(item)
            return item
        return x.__dict__[sort_by[0]]

    master_components = []
    components = []

    all_war_stats = sorted(
        [s for s in all_war_stats if s.attacks >= min_attacks], key=lambda x: sort(x), reverse=ascending
    )[:limit]

    text = ''
    for placement, player in enumerate(all_war_stats, 1):   # type: int, WarStatsPlayer
        """if player.tag not in clan.members_dict.keys():
        continue"""

        legend = f"{fetch_emoji('blank').emoji_string} `"
        th = fetch_emoji(f'blue_{placement}')
        text += f'`{placement:>{len(str(placement + EMBED_ROW_LIMIT - 1))}} ' if not th else f'{th} `'

        for count, item in enumerate(show):

            if item == 'name':
                text += f'{truncate_display_width(player.name, 12, remove_emojis=True):<12}'
                legend += 'Name'.ljust(12)
            elif item == 'townhall':
                text += f'{player.townhall:>2}'
                legend += 'TH'
            elif item == 'tag':
                text += f'{player.tag:<9}'
                legend += 'tag'.ljust(9)
            elif item == 'avg_three_stars':
                text += fmt(player.avg_three_stars, '>4.1f', True, '%')
                legend += '3%'.ljust(5)
            elif item == 'three_stars':
                text += f'{player.three_stars}/{player.attacks}'.ljust(6)
                legend += '# of 3'.ljust(6)
            elif item == 'avg_two_stars':
                text += fmt(player.avg_two_stars, '>4.1f', True, '%')
                legend += 'Avg 2'.ljust(5)
            elif item == 'two_stars':
                text += f'{player.two_stars}/{player.attacks}'.ljust(6)
                legend += '# of 2'.ljust(6)
            elif item == 'avg_one_stars':
                text += fmt(player.avg_one_stars, '>4.1f', True, '%')
                legend += 'Avg 1'.ljust(5)
            elif item == 'avg_zero_stars':
                text += fmt(player.avg_zero_stars, '>4.1f', True, '%')
                legend += 'Avg 0'.ljust(5)
            elif item == 'attacks':
                text += f'{player.attacks:>3}'
                legend += 'Atk'
            elif item == 'avg_order':
                text += f'{player.avg_order:>4.1f}'
                legend += 'Ord'.ljust(4)
            elif item == 'avg_defender_position':
                text += f'{player.avg_defender_position:>4.1f}'
                legend += 'DPos'.ljust(4)
            elif item == 'avg_destruction':
                text += fmt(player.avg_destruction, '>4.1f', True, '%')
                legend += 'Destr'.ljust(5)
            elif item == 'avg_duration':
                text += f'{player.avg_duration:>3}'
                legend += 'Dur'.ljust(3)
            elif item == 'avg_stars':
                text += f'{player.avg_stars:>4.1f}'
                legend += 'AvgS'.ljust(4)
            elif item == 'total_stars':
                text += f'{player.stars:>3}'
            elif item == 'avg_fresh':
                text += fmt(player.avg_fresh, '>4.1f', True, '%')
                legend += 'Frsh'.ljust(5)
            elif item == 'missed_hits':
                text += f'{player.missed_hits:>3}'
                legend += 'Mis'.ljust(3)

            if count + 1 != len(show):
                text += ' '
                legend += ' '

        text += '`\n'
        legend += '`\n'

        if placement % EMBED_ROW_LIMIT == 0 or placement == len(all_war_stats):
            th_types = f'- Townhalls: {townhall_filter.capitalize()}'
            select_options = [SelectOption(label=label, value=value) for value, label in label_map.items()]
            sort_options = [
                SelectOption(
                    label='Ascending',
                    value='ascending',
                    description='You can only select these along with another sort option',
                ),
                SelectOption(
                    label='Descending',
                    value='descending',
                    description='You can only select these along with another sort option',
                ),
            ]
            current_page = ((placement - 1) // EMBED_ROW_LIMIT) + 1
            total_pages = (len(all_war_stats) + EMBED_ROW_LIMIT - 1) // EMBED_ROW_LIMIT

            pages = [
                ActionRow(
                    components=[
                        Button(
                            custom_id=f'war_stats_page_back:{action_id}',
                            emoji='⬅️',
                            style=ButtonStyle.SECONDARY,
                            is_disabled=(placement == EMBED_ROW_LIMIT),
                        ),
                        Button(
                            custom_id='page',
                            label=f'{current_page}/{total_pages}',
                            style=ButtonStyle.SECONDARY,
                            is_disabled=True,
                        ),
                        Button(
                            custom_id=f'war_stats_page_forward:{action_id}',
                            emoji='➡️',
                            style=ButtonStyle.SECONDARY,
                            is_disabled=(placement == len(all_war_stats)),
                        ),
                    ]
                )
            ]
            if total_pages == 1:
                pages = []
            components.extend(
                [
                    Section(
                        accessory=Thumbnail(media=badge),
                        components=[
                            Text(
                                content=(
                                    f'{title}\n' f'{th_types}, Sort: {label_map.get(sort_by[0])}\n' f'- {date_range}'
                                )
                            )
                        ],
                    ),
                    Text(content=f'{legend}{text}'),
                    ActionRow(
                        components=[
                            TextSelectMenu(
                                options=select_options + sort_options,
                                custom_id=f'war_stats_sort_by:{action_id}',
                                placeholder='Sort By',
                                max_values=2,
                            )
                        ]
                    ),
                    ActionRow(
                        components=[
                            TextSelectMenu(
                                options=select_options,
                                custom_id=f'war_stats_show:{action_id}',
                                placeholder='Choose Columns',
                                max_values=4,
                            )
                        ]
                    ),
                    *pages,
                ]
            )

            container = [
                Container(components=components, accent_color=color),
                ActionRow(
                    components=[
                        Button(custom_id=f'war_stats_refresh:{action_id}', emoji='🔄', style=ButtonStyle.SECONDARY),
                        Button(
                            custom_id=f'war_stats_excel:{action_id}',
                            emoji=fetch_emoji(name='excel').partial_emoji,
                            style=ButtonStyle.SUCCESS,
                        ),
                    ]
                ),
            ]
            master_components.append(container)
            components = []
            text = ''

    return master_components


@register_action('war_stats_sort_by')
@lightbulb.di.with_di
async def war_stats_sort_by(mongo: MongoClient, **kwargs):
    ctx: lightbulb.components.MenuContext = kwargs.get('ctx')
    values: list[str] = list(ctx.interaction.values)

    ascending = 'ascending' in values
    descending = 'descending' in values

    if ascending:
        values.remove('ascending')

    if descending:
        values.remove('descending')

    if not values:
        raise Exception

    kwargs['sort_by'] = values
    data = {
        'sort_by': values,
    }

    if ascending:
        kwargs['ascending'] = True
        data['ascending'] = True
    elif descending:
        kwargs['ascending'] = False
        data['ascending'] = False

    await mongo.button_store.update_one({'_id': kwargs.get('action_id')}, {'$set': data})
    return (await war_stats_page(**kwargs))[kwargs.get('page')]


@register_action('war_stats_show')
@lightbulb.di.with_di
async def war_stats_show(mongo: MongoClient, **kwargs):
    ctx: lightbulb.components.MenuContext = kwargs.get('ctx')
    values = ctx.interaction.values
    if 'name' not in values:
        raise Exception
    data = {
        'show': values,
        'sort_by': [values[0]],
        'page': 0,
    }
    await mongo.button_store.update_one({'_id': kwargs.get('action_id')}, {'$set': data})
    kwargs['show'] = values
    kwargs['sort_by'] = [values[0]]
    return (await war_stats_page(**kwargs))[0]


@register_action('war_stats_page_back')
@lightbulb.di.with_di
async def war_stats_page_back(mongo: MongoClient, **kwargs):
    page = kwargs.get('page')
    components = await war_stats_page(**kwargs)
    page = min(len(components) - 1, page - 1)
    await mongo.button_store.update_one({'_id': kwargs.get('action_id')}, {'$set': {'page': page}})
    return components[page]


@register_action('war_stats_page_forward')
@lightbulb.di.with_di
async def war_stats_page_forward(mongo: MongoClient, **kwargs):
    page = kwargs.get('page')
    components = await war_stats_page(**kwargs)
    page = min(len(components) - 1, page + 1)
    await mongo.button_store.update_one({'_id': kwargs.get('action_id')}, {'$set': {'page': page}})
    return components[page]


@register_action('war_stats_refresh')
@lightbulb.di.with_di
async def war_stats_refresh(mongo: MongoClient, **kwargs):
    page = kwargs.get('page')
    components = await war_stats_page(**kwargs)
    return components[page]


@register_action('war_stats_excel', no_return=True)
@lightbulb.di.with_di
async def war_stats_excel(**kwargs):
    ctx: lightbulb.components.MenuContext = kwargs.get('ctx')
    await ctx.respond(content='Soon ;)', ephemeral=True)
