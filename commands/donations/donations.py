
import random

import coc.utils
import hikari
import lightbulb
from hikari.impl import ContainerComponentBuilder as Container
from hikari.impl import InteractiveButtonBuilder as Button
from hikari.impl import MessageActionRowBuilder as ActionRow
from hikari.impl import SectionComponentBuilder as Section
from hikari.impl import SelectOptionBuilder as SelectOption
from hikari.impl import TextDisplayComponentBuilder as Text
from hikari.impl import TextSelectMenuBuilder as TextSelectMenu
from hikari.impl import ThumbnailComponentBuilder as Thumbnail

from api.client import ClashKingAPIClient
from classes.mongo import MongoClient
from commands.ext.autocomplete import clan, season
from commands.ext.components import register_action
from utility.time import gen_season_date
from utility.constants import BUTTON_COLOR, ICON_PLACEHOLDERS
from utility.emojis import emojis, fetch_emoji
from utility.translations import translation

loader = lightbulb.Loader()


@loader.command()
class Donations(
    lightbulb.SlashCommand,
    name='donations',
    description='command-compo-description',
    localize=True,
):

    clan = lightbulb.string(
        'options-clan',
        'options-clan-description',
        localize=True,
        autocomplete=clan,
        default=None,
    )

    group = lightbulb.string(
        'options-group',
        'options-group-description',
        localize=True,
        autocomplete=clan,
        default=None,
    )

    season = lightbulb.string(
        'options-season',
        'options-season-description',
        localize=True,
        default=None,
        autocomplete=season,
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context, mongo: MongoClient) -> None:
        data = {
            '_id': str(ctx.interaction.id),
            'guild_id': ctx.guild_id,
            'group': self.group,
            'clan_tag': self.clan,
            'season': self.season,
        }
        await mongo.button_store.insert_one(data)
        components = await donations_page(action_id=str(ctx.interaction.id), **data)
        await ctx.respond(components=components)


@lightbulb.di.with_di
async def donations_page(
    clan_tag: str | None,
    group: str | None,
    guild_id: int | None,
    season: str | None,
    action_id: str,
    ck_client: ClashKingAPIClient = lightbulb.di.INJECTED,
    color: hikari.Color = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    ctx: lightbulb.Context = lightbulb.di.INJECTED,
    **kwargs,
):
    _ = translation(ctx=ctx)

    season = season or gen_season_date()

    if clan_tag:
        clan_tag = coc.utils.correct_tag(clan_tag.split('|')[-1])
        compo = await ck_client.get_clan_compo(clan_tags=[clan_tag])
        badge = compo.clan.badge.url
        title = compo.clan.name
    elif group:
        clan_tags = []
        compo = await ck_client.get_clan_compo(clan_tags=[clan_tag])
    else:
        guild_clans = await ck_client.get_basic_server_clan_list(server_id=guild_id)
        clan_tags = [c.tag for c in guild_clans]
        compo = await ck_client.get_clan_compo(clan_tags=clan_tags)
        guild = bot.cache.get_guild(guild_id)
        badge = guild.make_icon_url() or random.choice(ICON_PLACEHOLDERS)
        title = guild.name

    compo_dict = compo.__dict__.get(compo_type)

    formats = {
        'townhall': '`{value:3}` {icon}`TH{key:<2}`\n',
        'trophies': '`{value:3}` {icon}`{key}+ Trophies`\n',
        'location': '`{value:3}` {icon}`{key}`\n',
        'role': '`{value:3}` {icon}`{key}`\n',
        'league': '`{value:3}` {icon}`{key}`\n',
    }

    text = ''
    total = 0
    field_to_sort = 1 if compo_type != 'townhall' else 0
    for key, value in sorted(compo_dict.items(), key=lambda x: int(x[field_to_sort]), reverse=True):
        icon = ''
        if compo_type == 'townhall':
            icon = fetch_emoji(int(key))
            total += int(key) * value
        elif compo_type == 'location':
            icon = f':flag_{key.lower()}:'
            key = compo.country_map.get(key)
        elif compo_type == 'league':
            icon = fetch_emoji(name=key)
        text += f'{formats.get(compo_type).format(key=key, value=value, icon=icon)}'

    footer_text = _('num-accounts', num=compo.total_members)
    if total:
        footer_text += f' | {_("average-townhall")}: {round((total / compo.total_members), 2)}'

    select_options = [SelectOption(label=_(f'choices-{choice}'), value=choice) for choice in formats.keys()]

    components = [
        Container(
            components=[
                Section(
                    accessory=Thumbnail(media=badge),
                    components=[Text(content=(f'## {title}\n' f'{text}'))],
                ),
                ActionRow(
                    components=[
                        TextSelectMenu(
                            options=select_options,
                            max_values=1,
                            custom_id=f'compo_select:{action_id}',
                            placeholder=_('placeholder-select-type'),
                        )
                    ]
                ),
                Text(content=f'-# {footer_text}'),
            ],
            accent_color=color,
        ),
        ActionRow(
            components=[
                Button(
                    style=BUTTON_COLOR,
                    emoji=emojis.refresh.partial_emoji,
                    custom_id=f'compo_refresh:{action_id}',
                )
            ]
        ),
    ]
    return components


@register_action('compo_refresh')
@lightbulb.di.with_di
async def compo_refresh(**kwargs):
    components = await compo_page(**kwargs)
    return components


@register_action('compo_select')
@lightbulb.di.with_di
async def compo_select(mongo: MongoClient, **kwargs):
    ctx: lightbulb.components.MenuContext = kwargs.get('ctx')
    value = ctx.interaction.values[0]
    data = {
        'compo_type': value,
    }
    kwargs['compo_type'] = value
    await mongo.button_store.update_one({'_id': kwargs.get('action_id')}, {'$set': data})
    components = await compo_page(**kwargs)
    return components
