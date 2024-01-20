import disnake
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from typing import List
import coc
from utility.clash.other import gen_season_date
from utility.constants import BOARD_TYPES
from typing import Union

bot = CustomClient()

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


def leaderboard_components(bot: CustomClient, current_page, num_players):
    length = num_players

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

def clan_board_components(bot: CustomClient, season: Union[str, None], clan_tag: str, type: str):
    buttons = disnake.ui.ActionRow()
    if season is None or season == bot.gen_season_date():
        buttons.append_item(disnake.ui.Button(
            label="", emoji=bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"00_{type}_{season}_{clan_tag}"))
    buttons.append_item(disnake.ui.Button(
        label="", emoji=bot.emoji.red_pin.partial_emoji,
        style=disnake.ButtonStyle.grey, custom_id=f"00_FREEZE" if season is None else "00_PIN"))
    buttons.append_item(disnake.ui.Button(
        label="", emoji=bot.emoji.calendar.partial_emoji,
        style=disnake.ButtonStyle.grey, custom_id=f"00_SEASON_{type}_{season}_{clan_tag}"))

    types_select = []
    emojis = [bot.emoji.globe, bot.emoji.globe, bot.emoji.magnify_glass, bot.emoji.troop, bot.emoji.clan_castle, bot.emoji.ratio, bot.emoji.discord,
              bot.emoji.opt_in, bot.fetch_emoji("Super Hog Rider"), bot.emoji.clan_games, bot.emoji.clock,
              bot.emoji.calendar, bot.emoji.war_star, bot.emoji.cwl_medal]
    for b_type, emoji in zip(BOARD_TYPES, emojis):
        types_select.append(
            disnake.SelectOption(label=b_type, emoji=emoji.partial_emoji,
                                 value=f"00_{b_type.replace(' ', '-').lower()}_{season}_{clan_tag}"))
    types_select = disnake.ui.Select(options=types_select, placeholder="Board Types", max_values=1)
    types_select = disnake.ui.ActionRow(types_select)
    components = [types_select, buttons]
    return components


def clan_component(bot: CustomClient, all_clans: List[coc.Clan], clan_page:int =0, max_choose=None):
    clan_options = []
    length = 24
    if clan_page >= 1:
        length = length - 1
    clans = all_clans[(length * clan_page):(length * clan_page) + length]
    if clan_page >= 1:
        clan_options.append(disnake.SelectOption(label=f"Previous 25 Clans", emoji=bot.emoji.back.partial_emoji, value=f"clanpage_{clan_page - 1}"))
    for count, clan in enumerate(clans):
        clan_options.append(disnake.SelectOption(label=f"{clan.name} ({clan.tag})", value=f"clantag_{clan.tag}"))
    if len(clans) == length and (len(all_clans) > (length * clan_page) + length):
        clan_options.append(disnake.SelectOption(label=f"Next 25 Clans", emoji=bot.emoji.forward.partial_emoji, value=f"clanpage_{clan_page + 1}"))

    clan_select = disnake.ui.Select(
        options=clan_options,
        placeholder=f"Select Clan(s)",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(clans) if max_choose is None else max_choose,  # the maximum number of options a user can select
    )

    return disnake.ui.ActionRow(clan_select)

async def basic_clan_dropdown(clans: List[coc.Clan], max_choose=1):
    clan_options = []
    clans.sort(key=lambda x : x.member_count)
    for count, clan in enumerate(clans[:25]):
        clan_options.append(disnake.SelectOption(label=f"{clan.name} ({clan.tag})", value=f"{clan.tag}"))

    clan_select = disnake.ui.Select(
        options=clan_options,
        placeholder=f"Select Clan(s)",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=max_choose,  # the maximum number of options a user can select
    )

    return disnake.ui.ActionRow(clan_select)


def townhall_component(bot: CustomClient):
    options = []
    nums = reversed([x for x in range(2, 16)])
    for num in nums:
        options.append(disnake.SelectOption(label=f"Townhall {num}", emoji=bot.fetch_emoji(name=num).partial_emoji,
                                            value=f"th_{num}"))
    th_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Townhalls",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    return disnake.ui.ActionRow(th_select)


def role_component():
    options = []
    role_types = ["Member", "Elder", "Co-Leader", "Leader"]
    for role in role_types:
        options.append(disnake.SelectOption(label=f"{role}", value=f"{role}"))
    role_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Roles",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    return disnake.ui.ActionRow(role_select)


