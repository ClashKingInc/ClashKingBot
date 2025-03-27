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


async def army_embed(
    bot: CustomClient,
    nick: str,
    link: str,
    notes: str = None,
    embed_color: disnake.Color = EMBED_COLOR_CLASS,
):
    recipe = bot.coc_client.parse_army_link(link=link)

    if (not recipe.heroes_loadout
            and not recipe.troops
            and not recipe.spells
            and not recipe.clan_castle_troops
            and not recipe.clan_castle_spells):
        raise MessageException('Not a valid army link')

    troops = super_troops = spells = siege_machines = clan_castle = ''
    troop_space = spell_space = minimum_th = cc_space = 0

    for troop, quantity in recipe.troops:   # type: coc.Troop, int
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

    for spell, quantity in recipe.spells:   # type: coc.Spell, int
        emoji = bot.fetch_emoji(spell.name)
        spells += f'{emoji}`x {str(quantity)}` {spell.name}\n'
        minimum_th = max(minimum_th, spell.required_th_level[1])
        spell_space += spell.housing_space * quantity

    for troop, quantity in recipe.clan_castle_troops:   # type: coc.Troop, int
        emoji = bot.fetch_emoji(troop.name)
        if not troop.is_siege_machine:
            cc_space += troop.housing_space * quantity
        clan_castle += f'{emoji}`x {str(quantity)}` {troop.name}\n'

    for spell, quantity in recipe.clan_castle_spells:  # type: coc.Spell, int
        emoji = bot.fetch_emoji(spell.name)
        clan_castle += f'{emoji}`x {str(quantity)}` {spell.name}\n'

    minimum_th = max(minimum_th, army_camp_size(troop_space))
    description =\
    f'-# {bot.fetch_emoji(minimum_th)}Minimum Required Townhall: {minimum_th}\n'\

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

    hero_loadout = ""
    for loadout in recipe.heroes_loadout: # type: coc.HeroLoadout
        hero_loadout += f"{bot.fetch_emoji(loadout.hero.name)} `{loadout.hero.name}` "
        if loadout.pet:
            hero_loadout += f"\n- {bot.fetch_emoji(loadout.pet.name)} `{loadout.pet.name}`"
        hero_loadout += "\n"
        for equipment in loadout.equipment:
            hero_loadout += f"- {bot.fetch_emoji(equipment.name)} `{equipment.name}`\n"

    if hero_loadout:
        if recipe.clan_castle_troops or recipe.clan_castle_spells:
            hero_loadout += f'­'
        embed.add_field(name='Heroes Loadout', value=f'{hero_loadout}', inline=False)

    if clan_castle:
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
    elif size <= 320:
        return 15
    else:
        return 17


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
