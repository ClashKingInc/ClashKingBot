import ast
from collections import defaultdict
from typing import Dict, List

import coc
import disnake
import openai
import pendulum as pd

from classes.bot import CustomClient
from exceptions.CustomExceptions import MessageException
from utility.constants import EMBED_COLOR_CLASS
from utility.discord_utils import iter_embed_creation
from utility.time import format_time

async def generate_dictionary(bot: CustomClient, context: str, user_prompt: str):
    try:
        openai.api_key = bot._config.open_ai_key
        response = await openai.ChatCompletion.acreate(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': context},
                {'role': 'user', 'content': user_prompt}
            ],
            max_tokens=2000,  # Adjust token limit as needed
            temperature=0.7,  # Adjust creativity level
        )
        response_content = response['choices'][0]['message']['content']
        return ast.literal_eval(response_content)
    except Exception:
        return {}

async def generate_equipment(bot: CustomClient, equipment: str) -> str:
    try:
        context = """
                You are an assistant designed to help users turn their clash of clans 
                equipment selections into a python readable dictionary
                """
        user_prompt = f"""
                These are the current equipment: {str(coc.enums.EQUIPMENT)}, these are my equipment: {equipment}.
                Give me a python readable dictionary like equipment: quantity, using the closest available options.
                If there is no available close and accurate option, please skip. Return ONLY a dictionary and nothing else,
                even if empty. Do NOT return in a code block, please.
                """
        equip_dict = await generate_dictionary(bot=bot, context=context, user_prompt=user_prompt)
        equipment = ''
        for hero_name in coc.enums.HOME_BASE_HERO_ORDER:
            heroes_equipment = ''
            for name, _ in equip_dict.items():
                gear = bot.coc_client.get_equipment(name=name)
                if gear.hero == hero_name:
                    emoji = bot.fetch_emoji(gear.name)
                    heroes_equipment += f'- {emoji} {gear.name}\n'
            if heroes_equipment:
                emoji = bot.fetch_emoji(hero_name)
                equipment += f'{emoji} {hero_name} \n{heroes_equipment}'
    except Exception:
        pass

    return equipment


async def generate_pets(bot: CustomClient, pets: str) -> str:
    try:
        context = """
                You are an assistant designed to help users turn their clash of clans 
                pet selections into a python readable dictionary
                """
        user_prompt = f"""
                These are the current pets: {str(coc.enums.PETS_ORDER)}, these are my pets: {pets}.
                Give me a python readable list like [pet1, pet2, pet3], using the closest available options.
                If there is no available close and accurate option, please skip. Return ONLY a list and nothing else,
                even if empty. Do NOT return in a code block, please.
                """
        pet_list = await generate_dictionary(bot=bot, context=context, user_prompt=user_prompt)
        pets = ''
        for pet in pet_list:
            emoji = bot.fetch_emoji(pet)
            pets += f'{emoji}'
    except Exception:
        pass

    return pets

async def generate_clan_castle(bot: CustomClient, clan_castle: str) -> tuple[str, int]:
    cc_space = 0
    try:
        context = """
                You are an assistant designed to help users turn their clash of clans clan castle - troop & spell
                selections into a python readable dictionary
                """
        user_prompt = f"""
                        These are the current troops & spells: {str(coc.enums.HOME_TROOP_ORDER + coc.enums.SPELL_ORDER)}, 
                        these are my spells and troops: {clan_castle}.
                        Give me a python readable dictionary like troop/spell: quantity, using the closest available options.
                        If there is no available close and accurate option, please skip. Return ONLY a dictionary and nothing else,
                        even if empty. Do NOT return in a code block, please.
                        """

        castle_dict = await generate_dictionary(bot=bot, context=context, user_prompt=user_prompt)
        troops = spells = ''
        for name, quantity in castle_dict.items():  # type: str, int
            item = bot.coc_client.get_troop(name=name)
            if item is None:
                item = bot.coc_client.get_spell(name=name)
            if not item:
                continue
            emoji = bot.fetch_emoji(item.name)
            if item.name in coc.enums.SPELL_ORDER:
                spells += f'{emoji}`x {str(quantity)}` {item.name}\n'
            elif item.name in coc.enums.HOME_TROOP_ORDER:
                troops += f'{emoji}`x {str(quantity)}` {item.name}\n'
                if not item.is_siege_machine:
                    cc_space += item.housing_space * int(quantity)
        clan_castle = troops + spells
    except Exception as e:
        pass
    return clan_castle, cc_space

async def army_embed(
    bot: CustomClient,
    nick: str,
    link: str,
    clan_castle: str = None,
    equipment: str = None,
    pets: str = None,
    notes: str = None,
    embed_color: disnake.Color = EMBED_COLOR_CLASS,
):
    troops_list, spell_list = bot.coc_client.parse_army_link(link=link)
    if not troops_list and not spell_list:
        raise MessageException('Not a valid army link')

    troops = super_troops = spells = siege_machines = ''
    troop_space = spell_space = minimum_th = cc_space = 0
    troop_train_time = spell_train_time = 0

    for troop, quantity in troops_list:   # type: coc.Troop, int
        emoji = bot.fetch_emoji(troop.name)
        if troop.is_super_troop:
            super_troops += f'{emoji}`x {str(quantity)}` {troop.name}\n'
        elif troop.is_siege_machine:
            siege_machines += f'{emoji}`x {str(quantity)}` {troop.name}\n'
        else:
            troops += f'{emoji}`x {str(quantity)}` {troop.name}\n'
        minimum_th = max(minimum_th, troop.required_th_level[1])
        if not troop.is_siege_machine:
            troop_space += troop.housing_space * quantity
            troop_train_time += troop.training_time.total_seconds() * quantity

    for spell, quantity in spell_list:   # type: coc.Spell, int
        emoji = bot.fetch_emoji(spell.name)
        spells += f'{emoji}`x {str(quantity)}` {spell.name}\n'
        minimum_th = max(minimum_th, spell.required_th_level[1])
        spell_space += spell.housing_space * quantity
        spell_train_time += spell.training_time.total_seconds() * quantity

    minimum_th = max(minimum_th, army_camp_size(troop_space))
    description =\
    f'-# {bot.fetch_emoji(minimum_th)}Minimum Required Townhall: {minimum_th}\n'\
    f'-# {bot.emoji.clock} Training Time: {format_time(max(troop_train_time, spell_train_time))}\n'

    if notes:
        description += f"-# {bot.emoji.pin} Notes: {notes}\n"
    embed = disnake.Embed(
        title=nick,
        description=description,
        color=embed_color,
    )
    for field, content in zip(['Troops', 'Super Troops', 'Spells', 'Siege Machines'], [troops, super_troops, spells, siege_machines]):
        if content:
            embed.add_field(name=field, value=content + '­', inline=False)

    if equipment or pets:
        equipment = await generate_equipment(bot=bot, equipment=equipment)
        if clan_castle:
            equipment += f'­'
        embed.add_field(name='Heroes & Equipment', value=f'{equipment}', inline=False)

    if pets:
        pets = await generate_pets(bot=bot, pets=pets)
        if clan_castle:
            pets += f'\n­'
        embed.add_field(name='Pets', value=f'{pets}', inline=False)

    if clan_castle:
        clan_castle, cc_space = await generate_clan_castle(bot=bot, clan_castle=clan_castle)
        embed.add_field(name='Clan Castle', value=f'{clan_castle}', inline=False)

    embed.set_footer(text=f'{troop_space} Troop Space | {spell_space} Spell Space | {cc_space} CC Troop')
    return embed


def army_camp_size(size: int):
    if size <= 20:
        return 1
    elif size <= 30:
        return 2
    elif size <= 70:
        return 3
    elif size <= 80:
        return 4
    elif size <= 135:
        return 5
    elif size <= 150:
        return 6
    elif size <= 200:
        return 7
    elif size <= 220:
        return 9
    elif size <= 240:
        return 10
    elif size <= 260:
        return 11
    elif size <= 280:
        return 12
    elif size <= 300:
        return 13
    else:
        return 15


async def super_troop_embed(
    bot: CustomClient,
    clans: List[coc.Clan],
    super_troop: str,
    embed_color: disnake.Color = EMBED_COLOR_CLASS,
) -> List[disnake.Embed]:
    player_tags = [m.tag for clan in clans for m in clan.members]
    players = await bot.get_players(tags=player_tags, custom=False)
    players = [p for p in players if p.get_troop(name=super_troop) is not None and p.get_troop(name=super_troop).is_active]
    base_embed = disnake.Embed(title=f'Players with {super_troop}', color=embed_color)
    embeds = iter_embed_creation(
        base_embed=base_embed,
        iter=players,
        scheme='{x.clan.name} - {x.name} [{x.tag}]\n',
        brk=50,
    )
    return embeds


async def clan_boost_embeds(
    bot: CustomClient,
    clans: List[coc.Clan],
    embed_color: disnake.Color = EMBED_COLOR_CLASS,
) -> List[disnake.Embed]:
    player_tags = [m.tag for clan in clans for m in clan.members]
    players = await bot.get_players(tags=player_tags, custom=False)
    player_dict: Dict[coc.Clan, List[coc.Player]] = {}
    for clan in clans:
        player_dict[clan] = []
        for player in players.copy():
            if player.clan is not None and player.clan.tag == clan.tag:
                player_dict[clan].append(player)

    embeds = []
    for clan, players in player_dict.items():
        clan_boosted = defaultdict(list)
        for player in players:
            for troop in [t for t in player.troops if t.is_active and t.is_super_troop]:
                clan_boosted[troop.name].append(player.name)

        if bool(clan_boosted):
            embed = disnake.Embed(title=f'Boosted Troops', color=embed_color)
            for troop, members in clan_boosted.items():
                text = ''.join([f'- {member}\n' for member in members])
                embed.add_field(
                    name=f'{bot.fetch_emoji(troop)} {troop}',
                    value=text,
                    inline=False,
                )
                embed.timestamp = pd.now(pd.UTC)
                embed.set_footer(icon_url=clan.badge.url, text=clan.name)
            embeds.append(embed)

    if not embeds:
        raise MessageException('No Super Troops Boosted')
    return embeds
