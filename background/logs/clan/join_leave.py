from functools import partial

import disnake

from api.models.settings import Join_Log
from background.logs.utils import get_available_logs, send_logs
from classes.bot import CustomClient
from classes.events import ClanJoinLeaveEvent, log_event
from utility.clash.other import basic_heros, leagueAndTrophies


@log_event(cls=ClanJoinLeaveEvent.join_leave)
async def clan_join_leave(bot: CustomClient, event: ClanJoinLeaveEvent):
    if event.members_joined:
        logs = await get_available_logs(bot=bot, event=event)

        if logs:
            player_tags = [member.tag for member in event.members_joined]
            player_map = await bot.get_players(tags=player_tags, use_cache=False, custom=False, as_mapping=True)

            embeds, components = [], []

            for member in event.members_joined:
                player = player_map.get(member.tag)
                if not player:
                    continue

                hero_info = basic_heros(bot=bot, player=player)
                th_emoji = bot.fetch_emoji(player.town_hall)

                embed = disnake.Embed(
                    description=(
                        f'[**{player.name}** ({player.tag})]({player.share_link})\n'
                        f'**{th_emoji}{player.town_hall}'
                        f'{leagueAndTrophies(bot=bot, player=player)}'
                        f'{bot.emoji.war_star}{player.war_stars}{hero_info}**\n'
                    ),
                    color=disnake.Color.green(),
                )
                embed.set_footer(
                    icon_url=event.clan.badge.url,
                    text=f'Joined {event.clan.name} [{event.clan.member_count}/50]',
                )
                embeds.append(embed)
                components.append(partial(join_components, bot=bot, player_tag=player.tag))

            if bot._config.is_main:
                await send_logs(
                    bot=bot,
                    available_logs=logs,
                    attribute='join_log',
                    embeds=embeds,
                    components=components,
                )

    if event.members_left:
        logs = await get_available_logs(bot=bot, event=event)

        if logs:
            player_map = await bot.get_players(
                tags=[m.tag for m in event.members_left],
                use_cache=False,
                custom=False,
                as_mapping=True,
            )

            embeds, components = [], []
            for member in event.members_left:
                player = player_map.get(member.tag)
                if not player:
                    continue
                th_emoji = bot.fetch_emoji(player.town_hall)
                embed = disnake.Embed(
                    description=f'[**{player.name}** ({player.tag})]({player.share_link})\n'
                    + f'**{th_emoji}{player.town_hall}{leagueAndTrophies(bot=bot, player=player)}(#{member.clan_rank})'
                    + f'{bot.emoji.up_green_arrow}{player.donations}{bot.emoji.down_red_arrow}{player.received}'
                    + f'{bot.emoji.pin}{member.role.in_game_name}**\n',
                    color=disnake.Color.red(),
                )
                if player.clan is not None and player.clan.tag != event.clan.tag:
                    embed.set_footer(
                        icon_url=player.clan.badge.url,
                        text=f'Left {event.clan.name} [{event.clan.member_count}/50] and Joined {player.clan.name}',
                    )
                else:
                    embed.set_footer(
                        icon_url=event.clan.badge.url,
                        text=f'Left {event.clan.name} [{event.clan.member_count}/50]',
                    )
                embeds.append(embed)
                components.append(partial(leave_components, player_tag=player.tag))

            await send_logs(
                bot=bot,
                available_logs=logs,
                attribute='leave_log',
                embeds=embeds,
                components=components,
            )


def join_components(bot: CustomClient, log: Join_Log, player_tag: str) -> list:
    if log.profile_button:
        button = disnake.ui.Button(
            label='',
            emoji=bot.emoji.user_search.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f'redditplayer_{player_tag}',
        )
        return [disnake.ui.ActionRow(button)]
    return []


def leave_components(log: Join_Log, player_tag: str) -> list:
    stat = []
    if log.ban_button:
        stat += [
            disnake.ui.Button(
                label='Ban',
                emoji='🔨',
                style=disnake.ButtonStyle.red,
                custom_id=f'jlban_{player_tag}',
            )
        ]
    if log.strike_button:
        stat += [
            disnake.ui.Button(
                label='Strike',
                emoji='✏️',
                style=disnake.ButtonStyle.grey,
                custom_id=f'jlstrike_{player_tag}',
            )
        ]
    if not stat:
        return []
    buttons = disnake.ui.ActionRow()
    for button in stat:
        buttons.append_item(button)
    return [buttons]
