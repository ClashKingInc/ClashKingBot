from typing import List, Union

import coc
import disnake

from classes.bot import CustomClient
from classes.database.models.player.stats import StatsPlayer


def button_generator(bot: CustomClient, button_id: str, current_page: int = 0, max_page: int = 1, print: bool = False):
    if max_page == 1:
        return [
            disnake.ui.Button(
                label='',
                emoji=bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f'{button_id}:page=-1',
            )
        ]

    page_buttons = [
        disnake.ui.Button(
            label='Prev',
            style=disnake.ButtonStyle.grey,
            disabled=(current_page == 0),
            custom_id=f'{button_id}:page={current_page - 1}',
        ),
        disnake.ui.Button(
            label=f'{current_page + 1}/{max_page}',
            style=disnake.ButtonStyle.grey,
            disabled=True,
        ),
        disnake.ui.Button(
            label='Next',
            style=disnake.ButtonStyle.grey,
            disabled=(current_page == max_page - 1),
            custom_id=f'{button_id}:page={current_page + 1}',
        ),
    ]

    buttons = []
    for button in page_buttons:
        buttons.append(button)

    if print:
        buttons.append(
            disnake.ui.Button(label='', emoji='🖨️', style=disnake.ButtonStyle.grey, custom_id=f'{button_id}:page=PRINT')
        )

    return [buttons]




def clan_component(bot: CustomClient, all_clans: List[coc.Clan], clan_page: int = 0, max_choose=None):
    clan_options = []
    length = 24
    if clan_page >= 1:
        length = length - 1
    clans = all_clans[(length * clan_page) : (length * clan_page) + length]
    if clan_page >= 1:
        clan_options.append(disnake.SelectOption(label=f'< Previous 25 Clans', value=f'clanpage_{clan_page - 1}'))
    for count, clan in enumerate(clans):
        clan_options.append(disnake.SelectOption(label=f'{clan.name} ({clan.tag})', value=f'clantag_{clan.tag}'))
    if len(clans) == length and (len(all_clans) > (length * clan_page) + length):
        clan_options.append(disnake.SelectOption(label=f'Next 25 Clans >', value=f'clanpage_{clan_page + 1}'))

    clan_select = disnake.ui.Select(
        options=clan_options,
        placeholder=f'Select Clan(s)',  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=(
            len(clans) if max_choose is None else max_choose
        ),  # the maximum number of options a user can select
    )

    return disnake.ui.ActionRow(clan_select)




async def basic_clan_dropdown(clans: List[coc.Clan], max_choose=1):
    clan_options = []
    clans.sort(key=lambda x: x.member_count)
    for count, clan in enumerate(clans[:25]):
        clan_options.append(disnake.SelectOption(label=f'{clan.name} ({clan.tag})', value=f'{clan.tag}'))

    clan_select = disnake.ui.Select(
        options=clan_options,
        placeholder=f'Select Clan(s)',  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=max_choose,  # the maximum number of options a user can select
    )

    return disnake.ui.ActionRow(clan_select)



