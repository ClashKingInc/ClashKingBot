import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import coc
import emoji
from pytz import utc


if TYPE_CHECKING:
    from classes.bot import CustomClient


async def superTroops(player, asArray=False):
    troops = player.troop_cls
    troops = player.troops

    boostedTroops = []

    for x in range(len(troops)):
        troop = troops[x]
        if troop.is_active:
            # print (troop.name)
            boostedTroops.append(troop.name)

    if asArray:
        return boostedTroops

    return str(boostedTroops)


def heros(bot: 'CustomClient', player: coc.Player):
    def get_level_emoji(hero: coc.Hero):
        color = 'blue'
        if hero.level == hero.get_max_level_for_townhall(townhall=player.town_hall):
            color = 'gold'
        return bot.get_number_emoji(color=color, number=hero.level)

    gear_to_hero = defaultdict(list)
    for gear in player.equipment:
        if gear.hero is not None:
            gear_to_hero[gear.hero].append(gear)

    hero_string = ''
    for hero in player.heroes:
        if not hero.is_home_base:
            continue
        gear_text = ' | '
        for gear in gear_to_hero.get(hero.name, []):
            color = 'blue'
            if gear.level == gear.max_level:
                color = 'gold'
            emoji = bot.get_number_emoji(color=color, number=gear.level)
            gear_text += f'{bot.fetch_emoji(gear.name)}{emoji}'
        if gear_text == ' | ':
            gear_text = ''
        hero_string += f'{bot.fetch_emoji(hero.name)}{get_level_emoji(hero)}{gear_text}\n'

    if not hero_string:
        return None

    return ''.join(hero_string)


def basic_heros(bot, player: coc.Player):
    hero_string = ''
    for hero in player.heroes:
        if not hero.is_home_base:
            continue
        hero_string += f'{bot.fetch_emoji(hero.name)}{hero.level}'

    if not hero_string:
        return ''

    return hero_string


def spells(player, bot: 'CustomClient'):
    spells = player.spells
    if not spells:
        return None
    spellList = ''
    levelList = ''

    def get_level_emoji(spell: coc.Spell):
        color = 'blue'
        if spell.level == spell.get_max_level_for_townhall(townhall=player.town_hall):
            color = 'gold'
        return bot.get_number_emoji(color=color, number=spell.level)

    for x in range(len(spells)):
        theSpells = coc.SPELL_ORDER
        # print(str(regTroop))
        spell = spells[x]
        if spell.name in theSpells:
            if spell.name == 'Poison Spell':
                spellList += '\n' + levelList + '\n'
                levelList = ''
            spellList += f'{bot.fetch_emoji(spell.name).emoji_string} '
            levelList += str(get_level_emoji(spell))

            if spell.level <= 10:
                levelList += ' '

    spellList += '\n' + levelList + '\n'

    return spellList


def troops(player, bot: 'CustomClient'):
    troops = player.troops
    if not troops:
        return None
    troopList = ''
    levelList = ''

    def get_level_emoji(troop: coc.Troop):
        color = 'blue'
        if troop.level == troop.get_max_level_for_townhall(townhall=player.town_hall):
            color = 'gold'
        return bot.get_number_emoji(color=color, number=troop.level)

    z = 0
    for x in range(len(troops)):
        troop = troops[x]
        if (troop.is_home_base) and (troop.name not in coc.SIEGE_MACHINE_ORDER) and (troop.name not in SUPER_TROOPS):
            z += 1
            troopList += bot.fetch_emoji(troop.name).emoji_string + ' '
            levelList += str(get_level_emoji(troop))

            if troop.level <= 11:
                levelList += ' '

            if z != 0 and z % 8 == 0:
                troopList += '\n' + levelList + '\n'
                levelList = ''

    troopList += '\n' + levelList

    return troopList


def siegeMachines(player, bot: 'CustomClient'):
    sieges = player.siege_machines
    if not sieges:
        return None
    siegeList = ''
    levelList = ''

    def get_level_emoji(troop: coc.Troop):
        color = 'blue'
        if troop.level == troop.get_max_level_for_townhall(townhall=player.town_hall):
            color = 'gold'
        return bot.get_number_emoji(color=color, number=troop.level)

    z = 0
    for x in range(len(sieges)):
        siegeL = coc.SIEGE_MACHINE_ORDER
        # print(str(regTroop))
        siege = sieges[x]
        if siege.name in siegeL:
            z += 1
            siegeList += bot.fetch_emoji(siege.name).emoji_string + ' '
            levelList += str(get_level_emoji(siege))

            if siege.level <= 10:
                levelList += ' '

    siegeList += '\n' + levelList

    # print(heroList)
    # print(troopList)
    return siegeList


def heroPets(bot, player: coc.Player):
    if not player.pets:
        return None

    def get_level_emoji(pet: coc.Pet):
        color = 'blue'
        if pet.level == pet.max_level:
            color = 'gold'
        return bot.get_number_emoji(color=color, number=pet.level)

    pet_string = ''
    for count, pet in enumerate(player.pets, 1):
        pet_string += f'{bot.fetch_emoji(pet.name)}{get_level_emoji(pet)}'
        if count % 4 == 0:
            pet_string += '\n'

    return pet_string


def hero_gear(bot, player: coc.Player):
    if not player.equipment:
        return None

    gear_string = ''
    for count, gear in enumerate([g for g in player.equipment if g.hero is None], 1):
        color = 'blue'
        if gear.level == gear.max_level:
            color = 'gold'
        emoji = bot.get_number_emoji(color=color, number=gear.level)
        gear_string += f'{bot.fetch_emoji(gear.name)}{emoji}'
        if count % 4 == 0:
            gear_string += '\n'
    return gear_string


def profileSuperTroops(bot: 'CustomClient', player):
    troops = player.troops
    boostedTroops = ''

    for x in range(len(troops)):
        troop = troops[x]
        if troop.is_active:
            emoji = bot.fetch_emoji(troop.name)
            boostedTroops += f'{emoji} {troop.name}' + '\n'

    if len(boostedTroops) > 0:
        boostedTroops = f'\n**Super Troops:**\n{boostedTroops}'
    else:
        boostedTroops = ''
    return boostedTroops








def leagueAndTrophies(bot: 'CustomClient', player):
    league = str(player.league)
    emoji = bot.fetch_emoji(league)
    return emoji.emoji_string + str(player.trophies)


def league_emoji(bot: 'CustomClient', player):
    league = str(player.league)
    return bot.fetch_emoji(league)


def league_to_emoji(bot: 'CustomClient', league: str):

    emoji = bot.fetch_emoji(league)
    if emoji is None:
        league = league.split(' ')[0]
        emoji = bot.fetch_emoji(league)
    if emoji is None:
        emoji = bot.fetch_emoji('unranked')
    return emoji
