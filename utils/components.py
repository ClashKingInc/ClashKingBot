import disnake
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from typing import List


def create_components(current_page, embeds, print=False):
    length = len(embeds)
    if length == 1:
        return []

    if not print:
        page_buttons = [
            disnake.ui.Button(label="", emoji="◀️", style=disnake.ButtonStyle.grey, disabled=(current_page == 0),
                              custom_id="Previous"),
            disnake.ui.Button(label=f"Page {current_page + 1}/{length}", style=disnake.ButtonStyle.grey,
                              disabled=True),
            disnake.ui.Button(label="", emoji="▶️", style=disnake.ButtonStyle.grey,
                              disabled=(current_page == length - 1), custom_id="Next")
            ]
    else:
        page_buttons = [
            disnake.ui.Button(label="", emoji="◀️", style=disnake.ButtonStyle.grey, disabled=(current_page == 0),
                              custom_id="Previous"),
            disnake.ui.Button(label=f"Page {current_page + 1}/{length}", style=disnake.ButtonStyle.grey,
                              disabled=True),
            disnake.ui.Button(label="", emoji="▶️", style=disnake.ButtonStyle.grey,
                              disabled=(current_page == length - 1), custom_id="Next"),
            disnake.ui.Button(label="", emoji="🖨️", style=disnake.ButtonStyle.grey,
                              custom_id="Print")
        ]

    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    return [buttons]


def raid_buttons(bot: CustomClient, data):
    page_buttons = [
        disnake.ui.Button(label="Raids", emoji=bot.emoji.sword_clash.partial_emoji, style=disnake.ButtonStyle.grey,
                          custom_id="raids"),
        disnake.ui.Button(label="Donations", emoji=bot.emoji.capital_gold.partial_emoji, style=disnake.ButtonStyle.grey,
                          custom_id="donations")
        ]
    if data != []:
        page_buttons.append(disnake.ui.Button(label="Excel File", emoji="📊", style=disnake.ButtonStyle.green,
                          custom_id="capseason"))
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    return [buttons]


def leaderboard_components(bot: CustomClient, current_page, embeds, ctx):
    length = len(embeds)

    select = disnake.ui.Select(
        options=[  # the options in your dropdown
            disnake.SelectOption(label="Alphabetic", emoji=bot.emoji.alphabet.partial_emoji, value="0"),
            disnake.SelectOption(label="Started", emoji=bot.emoji.start.partial_emoji, value="1"),
            disnake.SelectOption(label="Offense", emoji=bot.emoji.blue_sword.partial_emoji, value="2"),
            disnake.SelectOption(label="Defense", emoji=bot.emoji.blue_shield.partial_emoji, value="4"),
            disnake.SelectOption(label="Trophies", emoji=bot.emoji.blue_trophy.partial_emoji, value="6")
        ],
        placeholder=f"📁 Sort Type",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )
    selects = disnake.ui.ActionRow()
    selects.append_item(select)

    if length == 1:
        return [selects]

    page_buttons = [
        disnake.ui.Button(label="", emoji=bot.emoji.back.partial_emoji, style=disnake.ButtonStyle.grey,
                          disabled=(current_page == 0),
                          custom_id="Previous"),
        disnake.ui.Button(label=f"Page {current_page + 1}/{length}", style=disnake.ButtonStyle.grey,
                          disabled=True),
        disnake.ui.Button(label="", emoji=bot.emoji.forward.partial_emoji,
                          style=disnake.ButtonStyle.grey,
                          disabled=(current_page == length - 1), custom_id="Next")
    ]

    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    return [selects, buttons]


def player_components(players: List[MyCustomPlayer]):
    player_results = []
    if len(players) == 1:
        return player_results
    for count, player in enumerate(players):
        player_results.append(
            disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji,
                                 value=f"{count}"))
    profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)

    st2 = disnake.ui.ActionRow()
    st2.append_item(profile_select)

    return [st2]


