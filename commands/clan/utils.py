
from classes.bot import CustomClient
from collections import defaultdict
import coc

def townhall_composition(players: list[coc.Player | coc.ClanMember], bot: CustomClient) -> str:
    count = defaultdict(int)

    for player in players:
        count[player.town_hall] += 1

    th_comp_string = ''
    for th_level, th_count in sorted(count.items(), reverse=True):
        th_emoji = bot.fetch_emoji(th_level)
        th_comp_string += f'{th_emoji}`{th_count}` '

    return th_comp_string


def super_troop_composition(players: list[coc.Player | coc.ClanMember], bot: CustomClient) -> str:
    super_troops = defaultdict(int)

    for player in players:
        for troop in player.troops:
            if troop.is_active:
                super_troops[troop.name] += 1

    boosted = ''
    for troop, count in super_troops.items():
        super_troop_emoji = bot.fetch_emoji(name=troop)
        boosted += f'{super_troop_emoji}`x{count} `'

    return boosted or None