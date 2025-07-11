import coc
import hikari
import lightbulb
import pendulum as pend
from hikari.components import ButtonStyle
from hikari.impl import ContainerComponentBuilder as Container
from hikari.impl import InteractiveButtonBuilder as Button
from hikari.impl import MediaGalleryComponentBuilder as Media
from hikari.impl import MediaGalleryItemBuilder as MediaItem
from hikari.impl import MessageActionRowBuilder as ActionRow
from hikari.impl import SeparatorComponentBuilder as Separator
from hikari.impl import TextDisplayComponentBuilder as Text

from api.client import ClashKingAPIClient
from classes.cocpy.client import CustomClashClient
from classes.exceptions import MessageException
from commands.ext.autocomplete import banned_players
from utility.cdn import upload_to_cdn
from utility.constants import ORANGE_ACCENT, RED_ACCENT
from utility.emojis import fetch_emoji
from utility.time import ts
from utility.translations import translation

group = lightbulb.Group(
    name="ban",
    description="command-ban-description",
    default_member_permissions=hikari.Permissions.MANAGE_GUILD,
    localize=True
)


@group.register()
class BanAdd(
    lightbulb.SlashCommand,
    name="add",
    description="command-ban-add-description",
    localize=True,
):
    player = lightbulb.string(
        "player-autocomplete-name",
        "player-autocomplete-description",
        localize=True
    )
    reason = lightbulb.string(
        "reason-option",
        "reason-description",
        default=None,
        localize=True
    )
    dm_player = lightbulb.string(
        "dm-player-option",
        "dm-player-description",
        default=None,
        localize=True
    )

    image = lightbulb.attachment(
        "image-option",
        "image-option-description",
        default=None,
        localize=True
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        components = await add_ban_page(
            player_tag=self.player,
            reason=self.reason,
            dm_player=self.dm_player,
            image=self.image
        )
        await ctx.respond(components=components)

@lightbulb.di.with_di
async def add_ban_page(
    player_tag: str,
    reason: str | None = None,
    dm_player: str | None = None,
    image: hikari.Attachment | None = None,
    ctx: lightbulb.Context = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    ck_client: ClashKingAPIClient = lightbulb.di.INJECTED,
    coc_client: CustomClashClient = lightbulb.di.INJECTED,
):
    _ = translation(ctx=ctx)
    player = await coc_client.get_player(player_tag=player_tag)
    guild = bot.cache.get_guild(ctx.guild_id)

    if image:
        payload = await image.read()
        image = await upload_to_cdn(payload=payload, folder="bans", filetype=image.extension, id=image.id)

    ban = await ck_client.add_ban(
        server_id=guild.id,
        player_tag=player.tag,
        reason=reason,
        added_by=ctx.member.id,
        image=image,
    )

    clan_text = _('no-clan')
    if player.clan:
        clan_text = f'Clan: {player.clan.name}'

    image_text = f"\n**{_('image-evidence')}:**" if image else ""
    components = [
        Container(
            components=[
                Text(content=(
                    f'## Banned {fetch_emoji(player.town_hall)}[{player.name}]({player.share_link}) ({player.tag})\n'
                    f"-# {clan_text}\n"
                )),
                Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                Text(content=(
                    f"{_('ban-details',
                     ban_type=ban.status.capitalize(),
                     date=ts(pend.now(tz="UTC")).small_full_date,
                     discord_mention=ctx.member.mention)}\n"
                    f'**{_("reason-notes")}:** {reason or _('reason-default')}'
                    f"{image_text}"
                )),
                *([Media(items=[MediaItem(media=image)])] if image is not None else []),
                Text(content="-# <:creator:1126649651626508308> Code ClashKing ❤️")
            ],
            accent_color=RED_ACCENT
        )
    ]

    '''if dm_player is not None:
        linked_account = await bot.link_client.get_link(player_tag=player.tag)
        if linked_account:
            server_member = await guild.getch_member(linked_account)
            if server_member:
                try:
                    await server_member.send(content=dm_player, embed=embed)
                    embed.set_footer(text=_('notified-dm'))
                except:
                    embed.set_footer(text=_('notified-dm-fail'))'''
    #await send_ban_log(bot=bot, guild=guild, reason=embed)

    return components



@group.register()
class BanRemove(
    lightbulb.SlashCommand,
    name="remove",
    description="command-ban-remove-description",
    localize=True
):
    player = lightbulb.string(
        "options-player",
        "options-player-description",
        autocomplete=banned_players,
        localize=True
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        components = await remove_ban_page(player_tag=self.player)
        await ctx.respond(components=components)


@lightbulb.di.with_di
async def remove_ban_page(
    player_tag: str,
    ctx: lightbulb.Context = lightbulb.di.INJECTED,
    bot: hikari.GatewayBot = lightbulb.di.INJECTED,
    ck_client: ClashKingAPIClient = lightbulb.di.INJECTED,
    coc_client: CustomClashClient = lightbulb.di.INJECTED,
):
    _ = translation(ctx=ctx)
    player = await coc_client.get_player(player_tag=player_tag)
    try:
        ban = await ck_client.remove_ban(server_id=ctx.guild_id, player_tag=player.tag)
    except:
        raise MessageException(_('not-banned', player_name=player.name))

    components = [
        Container(components=[
            Text(content=_(
                'unbanned',
                player_name=player.name,
                player_link=player.share_link,
                discord_mention=ctx.member.mention,
            ))
        ], accent_color=ORANGE_ACCENT)
    ]

    return components





@group.register()
class BanList(
    lightbulb.SlashCommand,
    name="list",
    description="command-ban-list-description",
    localize=True
):
    @lightbulb.invoke
    async def invoke(
            self,
            ctx: lightbulb.Context
    ) -> None:

        components_list = await ban_list_page()

        await ctx.respond(components=components_list[0])

@lightbulb.di.with_di
async def ban_list_page(
    ctx: lightbulb.Context = lightbulb.di.INJECTED,
    ck_client: ClashKingAPIClient = lightbulb.di.INJECTED,
    coc_client: CustomClashClient = lightbulb.di.INJECTED,
) -> list[list[Container]]:
    _ = translation(ctx=ctx)

    bans = await ck_client.get_ban_list(server_id=ctx.guild_id)

    guild = await ctx.client.rest.fetch_guild(guild=ctx.guild_id)
    components_list = []

    banned_players = []

    # Iterate through the PlayerIterator asynchronously
    async for player in coc_client.get_players(player_tags=bans.key_list()):
        banned_players.append(player)

    sections = []
    for count, ban in enumerate(bans, 1):
        banned_player = coc.utils.get(banned_players, tag=ban.tag)
        clan = _('no-clan')
        if banned_player.clan is not None:
            clan = f'{banned_player.clan.name}, {banned_player.role}'

        added_by = ''

        if ban.added_by is not None:
            user = guild.get_member(ban.added_by)
            if not user:
                user = await ctx.client.rest.fetch_member(guild, ban.added_by)
            added_by = f'**{_("ban-added-by")}** {user.mention} ({user})\n'

        ban_date = pend.parse(str(ban.date_created), tz="UTC")
        section_text = (
            f'**{fetch_emoji(banned_player.town_hall)}[{banned_player.name}]({banned_player.share_link})** ({banned_player.tag})\n'
            f'-# {clan}\n'
            f'{added_by}'
            f'**{_("ban-added-on")}** {ts(ban_date).slash_date} ({ts(ban_date).relative})'
        )
        if ban.notes not in ['None', 'No Notes']:
            section_text += f'\n**{_("reason-notes")}:** {ban.notes}'

        sections.extend([
            Separator(divider=True, spacing=hikari.SpacingType.SMALL),
            Text(
                content=section_text
            ),
            *([Media(items=[MediaItem(media=ban.image)])] if ban.image else [])
        ])
        if count % 10 == 0 or count == len(banned_players):

            '''if ctx.interaction.locale == 'en-US':
                sections.insert(0,
                    Media(
                        items=[
                            MediaItem(media="https://media.discordapp.net/attachments/1197924424863731792/1383496210773704764/fbXmYhP.png?ex=68505240&is=684f00c0&hm=3996c74525c1f0995aba8c4e2592708d776a5ddb35ef95361444a93ea3db627a&=&format=webp&quality=lossless&width=1670&height=278")
                        ]
                    ),
                )
            else:'''
            sections.insert(0, Text(content="## Ban List"))

            if len(banned_players) > 10:
                sections.extend([
                    Separator(divider=True, spacing=hikari.SpacingType.SMALL),
                    ActionRow(components=[
                        Button(custom_id="banlist_left", emoji="⬅️", style=ButtonStyle.SECONDARY),
                        Button(custom_id="banlist_right", emoji="➡️", style=ButtonStyle.SECONDARY)
                    ]),
                    Text(content=f"-# Page {count // 10 + 1} of {len(banned_players) // 10 + 1}"),
                ])
            components = [
                Container(
                    accent_color=RED_ACCENT,
                    components=sections
                ),
            ]
            sections = []
            components_list.append(components)

    return components_list



