import asyncio
from typing import List

import disnake
import pendulum as pend
from numerize import numerize

from classes.clashofstats import StayType
from classes.database.models.player.stats import StatsPlayer
from exceptions.CustomExceptions import NoLinkedAccounts
from utility.clash.capital import is_raids, weekend_to_cocpy_timestamp
from utility.clash.other import *
from utility.discord_utils import interaction_handler, register_button
from utility.general import create_superscript


async def basic_player_board(bot: CustomClient, player: coc.Player, embed_color: disnake.Color):
    clan = player.clan.name if player.clan else 'No Clan'
    hero = heros(bot=bot, player=player)
    pets = heroPets(bot=bot, player=player)

    hero = f'**Heroes:**\n{hero}\n' if hero is None else ''
    pets = f'**Pets:**\n{pets}\n' if pets is None else ''

    embed = disnake.Embed(
        title=f'**Invite {player.name} to your clan:**',
        description=f'{player.name} - TH{player.town_hall}\n'
        + f'Tag: {player.tag}\n'
        + f'Clan: {clan}\n'
        + f'Trophies: {player.trophies}\n'
        f'War Stars: {player.war_stars}\n'
        f'{hero}{pets}',
        color=embed_color,
    ).set_thumbnail(url=f'https://assets.clashk.ing/home-base/town-hall-pics/town-hall-{player.town_hall}.png')

    return embed


async def history(bot: CustomClient, player):

    clan_history = await bot.get_player_history(player_tag=player.tag)
    previous_clans = clan_history.previous_clans(limit=5)
    clan_summary = clan_history.summary(limit=5)

    top_5 = ''
    if previous_clans == 'Private History':
        return disnake.Embed(
            title=f'{player.name} Clan History',
            description='This player has made their clash of stats history private.',
            color=disnake.Color.green(),
        )
    embed = disnake.Embed(
        title=f'{player.name} Clan History',
        description=f'This player has been seen in a total of {clan_history.num_clans} different clans\n'
        f"[Full History](https://www.clashofstats.com/players/{player.tag.strip('#')}/history/)",
        color=disnake.Color.green(),
    )

    for clan in clan_summary:
        years = clan.duration.days // 365
        # Calculating months
        months = (clan.duration.days - years * 365) // 30
        # Calculating days
        days = clan.duration.days - years * 365 - months * 30
        date_text = []
        if years >= 1:
            date_text.append(f'{years} Years')
        if months >= 1:
            date_text.append(f'{months} Months')
        if days >= 1:
            date_text.append(f'{days} Days')
        if date_text:
            date_text = ', '.join(date_text)
        else:
            date_text = 'N/A'
        top_5 += f'[{clan.clan_name}]({clan.share_link}) - {date_text}\n'

    if top_5 == '':
        top_5 = 'No Clans Found'
    embed.add_field(name='**Top 5 Clans Player has stayed the most:**', value=top_5, inline=False)

    last_5 = ''
    for clan in previous_clans:
        if clan.stay_type == StayType.unknown:
            continue
        last_5 += f'[{clan.clan_name}]({clan.share_link}), {clan.role.in_game_name}'
        if clan.stay_type == StayType.stay:
            last_5 += f', {clan.stay_length.days} days' if clan.stay_length.days >= 1 else ''
            last_5 += (
                f'\n<t:{int(clan.start_stay.time.timestamp())}:D> to <t:{int(clan.end_stay.time.timestamp())}:D>\n'
            )
        elif clan.stay_type == StayType.seen:
            last_5 += f'\nSeen on <t:{int(clan.seen_date.time.timestamp())}:D>\n'

    if last_5 == '':
        last_5 = 'No Clans Found'
    embed.add_field(name='**Last 5 Clans Player has been seen at:**', value=last_5, inline=False)

    embed.set_footer(text='Data from ClashofStats.com')
    return embed


async def create_profile_troops(
    bot: CustomClient,
    result: StatsPlayer,
    embed_color: disnake.Color = disnake.Color.green(),
):
    player = result
    hero = heros(bot=bot, player=player)
    pets = heroPets(bot=bot, player=player)
    troop = troops(bot=bot, player=player)
    siege = siegeMachines(bot=bot, player=player)
    spell = spells(bot=bot, player=player)
    gears = hero_gear(bot=bot, player=player)

    troop_embed_text = ''
    if troop:
        troop_embed_text += f'{bot.emoji.elixir}**Troops**\n{troop}\n\n'

    if spell:
        troop_embed_text += f'{bot.emoji.spells}**Spells**\n{spell}\n'

    if siege:
        troop_embed_text += f'{bot.emoji.heart}**Siege Machines**\n{siege}'

    troop_embed = disnake.Embed(description=troop_embed_text, color=embed_color)
    troop_embed.set_author(name=f'{player.name}', icon_url=player.town_hall_cls.image_url)

    hero_embed_text = ''
    if hero:
        hero_embed_text += f'{bot.emoji.up_green_arrow}**Heroes**\n{hero}\n'

    if pets:
        hero_embed_text += f'{bot.emoji.pet_paw}**Pets**\n{pets}\n'

    if gears:
        hero_embed_text += f'{bot.emoji.gear}**Other Hero Gear**\n{gears}'

    hero_embed = disnake.Embed(description=hero_embed_text, color=embed_color)

    if hero_embed_text != '':
        hero_embed.timestamp = datetime.now()
        return [troop_embed, hero_embed]
    else:
        troop_embed.timestamp = datetime.now()
        return [troop_embed]


async def upgrade_embed(bot: CustomClient, player: StatsPlayer):
    areas = [
        player.troop_rushed,
        player.hero_rushed,
        player.spell_rushed,
        player.pets_rushed,
    ]

    total_time = sum([area.total_time for area in areas])
    total_time_done = sum([area.time_done for area in areas])
    total_time_remaining = sum([area.total_time_left for area in areas])

    total_elixir = sum([area.total_loot.elixir for area in areas])
    total_elixir_done = sum([area.loot_done.elixir for area in areas])
    total_elixir_remaining = sum([area.total_loot_left.elixir for area in areas])

    total_de = sum([area.total_loot.dark_elixir for area in areas])
    total_de_done = sum([area.loot_done.dark_elixir for area in areas])
    total_de_remaining = sum([area.total_loot_left.dark_elixir for area in areas])

    total_levels = sum([area.total_levels for area in areas])
    total_levels_done = sum([area.levels_done for area in areas])
    total_levels_remaining = sum([area.total_levels_left for area in areas])

    total_h_levels = sum([area.total_levels for area in [player.hero_rushed]])
    total_h_levels_done = sum([area.levels_done for area in [player.hero_rushed]])
    total_h_levels_remaining = sum([area.total_levels_left for area in [player.hero_rushed]])

    def seconds_convert(secs: int):
        day = secs // (24 * 3600)
        secs = secs % (24 * 3600)
        hour = secs // 3600
        return f'{day}D'

    embed2 = disnake.Embed(title='Totals', color=disnake.Color.green())
    embed2.add_field(
        name=f'{bot.emoji.clock}Time',
        value=f'- Percent Done: {round(total_time_done/total_time * 100, 2)}%\n'
        f'- Done: {seconds_convert(total_time_done)}\n'
        f'- Total: {seconds_convert(total_time)}\n'
        f'- Remaining: {seconds_convert(total_time_remaining)}',
    )
    embed2.add_field(
        name=f'{bot.emoji.elixir}Elixir',
        value=f'- Percent Done: {round(total_elixir_done/total_elixir * 100, 2)}%\n'
        f'- Done: {total_elixir_done:,}\n'
        f'- Total: {total_elixir:,}\n'
        f'- Remaining: {total_elixir_remaining:,}',
    )
    if player.heroes:
        embed2.add_field(
            name=f'{bot.emoji.dark_elixir}Dark Elixir',
            value=f'- Percent Done: {round(total_de_done / total_de * 100, 2)}%\n'
            f'- Done: {total_de_done:,}\n'
            f'- Total: {total_de:,}\n'
            f'- Remaining: {total_de_remaining:,}',
        )
    embed2.add_field(
        name=f'{bot.emoji.up_green_arrow}All Levels',
        value=f'- Percent Done: {round(total_levels_done / total_levels * 100, 2)}%\n'
        f'- Done: {total_levels_done:,}\n'
        f'- Total: {total_levels:,}\n'
        f'- Remaining: {total_levels_remaining:,}',
    )
    if player.heroes:
        embed2.add_field(
            name=f"{bot.fetch_emoji(name='Barbarian King')}Hero Levels",
            value=f'- Percent Done: {round(total_h_levels_done / total_h_levels * 100, 2)}%\n'
            f'- Done: {total_h_levels_done:,}\n'
            f'- Total: {total_h_levels:,}\n'
            f'- Remaining: {total_h_levels_remaining:,}',
        )

    not_unlocked = []
    home_elixir_troops = ''
    for troop in player.troop_rushed.rushed_items + player.troop_rushed.not_max_items:  # type: coc.Troop
        if not troop.is_elixir_troop:
            continue
        th_max = troop.get_max_level_for_townhall(player.town_hall)
        th_max = f'{th_max}'.ljust(2)
        level = f'{troop.level}'.rjust(2)
        days = f'{int(troop.upgrade_time.hours / 24)}'.rjust(2)
        hours = f'{(int(troop.upgrade_time.hours % 24 / 24 * 10))}H'.ljust(3)
        time = f'{days}D {hours}'
        cost = f'{numerize.numerize(troop.upgrade_cost)}'.ljust(5)
        home_elixir_troops += f'{bot.fetch_emoji(name=troop.name)} `{level}/{th_max}` `{time}` `{cost}`'
        if troop in player.troop_rushed.rushed_items:
            home_elixir_troops += '✗'
        home_elixir_troops += '\n'

    home_de_troops = ''
    for troop in player.troop_rushed.rushed_items + player.troop_rushed.not_max_items:  # type: coc.Troop
        if not troop.is_dark_troop:
            continue
        th_max = troop.get_max_level_for_townhall(player.town_hall)
        th_max = f'{th_max}'.ljust(2)
        level = f'{troop.level}'.rjust(2)
        days = f'{int(troop.upgrade_time.hours / 24)}'.rjust(2)
        hours = f'{(int(troop.upgrade_time.hours % 24 / 24 * 10))}H'.ljust(3)
        time = f'{days}D {hours}'
        cost = f'{numerize.numerize(troop.upgrade_cost)}'.ljust(5)
        home_de_troops += f'{bot.fetch_emoji(name=troop.name)} `{level}/{th_max}` `{time}` `{cost}`'
        if troop in player.troop_rushed.rushed_items:
            home_de_troops += '✗'
        home_de_troops += '\n'

    siege_machines = ''
    for troop in player.troop_rushed.rushed_items + player.troop_rushed.not_max_items:  # type: coc.Troop
        if not troop.is_siege_machine:
            continue
        th_max = troop.get_max_level_for_townhall(player.town_hall)
        th_max = f'{th_max}'.ljust(2)
        level = f'{troop.level}'.rjust(2)
        days = f'{int(troop.upgrade_time.hours / 24)}'.rjust(2)
        hours = f'{(int(troop.upgrade_time.hours % 24 / 24 * 10))}H'.ljust(3)
        time = f'{days}D {hours}'
        cost = f'{numerize.numerize(troop.upgrade_cost)}'.ljust(5)
        siege_machines += f'{bot.fetch_emoji(name=troop.name)} `{level}/{th_max}` `{time}` `{cost}`'
        if troop in player.troop_rushed.rushed_items:
            siege_machines += '✗'
        siege_machines += '\n'

    hero_text = ''
    for hero in player.hero_rushed.rushed_items + player.hero_rushed.not_max_items:  # type: coc.hero.Hero
        if not hero.is_home_base:
            continue
        th_max = hero.get_max_level_for_townhall(player.town_hall)
        th_max = f'{th_max}'.ljust(2)
        level = f'{hero.level}'.rjust(2)
        days = f'{int(hero.upgrade_time.hours / 24)}'.rjust(2)
        hours = f'{(int(hero.upgrade_time.hours % 24 / 24 * 10))}H'.ljust(3)
        time = f'{days}D {hours}'
        cost = f'{numerize.numerize(hero.upgrade_cost)}'.ljust(5)
        hero_text += f'{bot.fetch_emoji(name=hero.name)} `{level}/{th_max}` `{time}` `{cost}`'
        if hero in player.hero_rushed.rushed_items:
            hero_text += '✗'
        hero_text += '\n'

    pet_text = ''
    for pet in player.pets_rushed.rushed_items + player.pets_rushed.not_max_items:  # type: coc.Pet
        if player.town_hall == 14:
            prev_level_max = 0
            max = 10
        else:
            if pet.name in ['L.A.S.S.I', 'Mighty Yak', 'Electro Owl', 'Unicorn']:
                if pet.name in ['L.A.S.S.I', 'Mighty Yak']:
                    max = 15
                else:
                    max = 10
                prev_level_max = 10
            else:
                prev_level_max = 0
                max = 10

        th_max = max
        th_max = f'{th_max}'.ljust(2)
        level = f'{pet.level}'.rjust(2)
        days = f'{int(pet.upgrade_time.hours / 24)}'.rjust(2)
        hours = f'{(int(pet.upgrade_time.hours % 24 / 24 * 10))}H'.ljust(3)
        time = f'{days}D {hours}'
        cost = f'{numerize.numerize(pet.upgrade_cost)}'.ljust(5)
        pet_text += f'{bot.fetch_emoji(name=pet.name)} `{level}/{th_max}` `{time}` `{cost}`'
        if pet in player.pets_rushed.rushed_items:
            pet_text += '✗'
        pet_text += '\n'

    elixir_spells = ''
    for spell in player.spell_rushed.rushed_items + player.spell_rushed.not_max_items:  # type: coc.Spell
        if spell.is_dark_spell:
            continue
        th_max = spell.get_max_level_for_townhall(player.town_hall)
        th_max = f'{th_max}'.ljust(2)
        level = f'{spell.level}'.rjust(2)
        days = f'{int(spell.upgrade_time.hours / 24)}'.rjust(2)
        hours = f'{(int(spell.upgrade_time.hours % 24 / 24 * 10))}H'.ljust(3)
        time = f'{days}D {hours}'
        cost = f'{numerize.numerize(spell.upgrade_cost)}'.ljust(5)
        elixir_spells += f'{bot.fetch_emoji(name=spell.name)} `{level}/{th_max}` `{time}` `{cost}`'
        if spell in player.spell_rushed.rushed_items:
            elixir_spells += '✗'
        elixir_spells += '\n'

    de_spells = ''
    for spell in player.spell_rushed.rushed_items + player.spell_rushed.not_max_items:  # type: coc.Spell
        if not spell.is_dark_spell:
            continue
        th_max = spell.get_max_level_for_townhall(player.town_hall)
        th_max = f'{th_max}'.ljust(2)
        level = f'{spell.level}'.rjust(2)
        days = f'{int(spell.upgrade_time.hours / 24)}'.rjust(2)
        hours = f'{(int(spell.upgrade_time.hours % 24 / 24 * 10))}H'.ljust(3)
        time = f'{days}D {hours}'
        cost = f'{numerize.numerize(spell.upgrade_cost)}'.ljust(5)
        de_spells += f'{bot.fetch_emoji(name=spell.name)} `{level}/{th_max}` `{time}` `{cost}`'
        if spell in player.spell_rushed.rushed_items:
            de_spells += '✗'
        de_spells += '\n'

    full_text = ''
    if home_elixir_troops != '':
        full_text += f'**Elixir Troops**\n{home_elixir_troops}\n'
    if home_de_troops != '':
        full_text += f'**Dark Elixir Troops**\n{home_de_troops}\n'
    if hero_text != '':
        full_text += f'**Heros**\n{hero_text}\n'
    if pet_text != '':
        full_text += f'**Hero Pets**\n{pet_text}\n'
    if elixir_spells != '':
        full_text += f'**Elixir Spells**\n{elixir_spells}\n'
    if de_spells != '':
        full_text += f'**Dark Elixir Spells**\n{de_spells}\n'
    if siege_machines != '':
        full_text += f'**Siege Machines**\n{siege_machines}\n'
    if full_text == '':
        full_text = 'No Heros, Pets, Spells, or Troops left to upgrade\n'

    embed = disnake.Embed(
        title=f'{player.name} | TH{player.town_hall}',
        description=full_text[:4000],
        colour=disnake.Color.green(),
    )

    embeds = [embed, embed2]
    embeds[0].set_footer(text='✗ = rushed for th level')
    return embeds


async def create_player_hr(bot: CustomClient, player: StatsPlayer, start_date, end_date):
    embed = disnake.Embed(title=f'{player.name} War Stats', colour=disnake.Color.green())
    time_range = f"{datetime.fromtimestamp(start_date).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_date).strftime('%m/%d/%y')}"
    embed.set_footer(icon_url=player.town_hall_cls.image_url, text=time_range)
    hitrate = await player.hit_rate(start_timestamp=start_date, end_timestamp=end_date)
    hr_text = ''
    for hr in hitrate:
        hr_type = f'{hr.type}'.ljust(5)
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        hr_text += f'`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n'
    if hr_text == '':
        hr_text = 'No war hits tracked.\n'
    embed.add_field(name='**Triple Hit Rate**', value=hr_text + '­\n', inline=False)

    defrate = await player.defense_rate(start_timestamp=start_date, end_timestamp=end_date)
    def_text = ''
    for hr in defrate:
        hr_type = f'{hr.type}'.ljust(5)
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        def_text += f'`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n'
    if def_text == '':
        def_text = 'No war defenses tracked.\n'
    embed.add_field(name='**Triple Defense Rate**', value=def_text + '­\n', inline=False)

    text = ''
    hr = hitrate[0]
    footer_text = f'Avg. Off Stars: `{round(hr.average_stars, 2)}`'
    if hr.total_zeros != 0:
        hr_nums = f'{hr.total_zeros}/{hr.num_attacks}'.center(5)
        text += f'`Off 0 Stars` | `{hr_nums}` | {round(hr.average_zeros * 100, 1)}%\n'
    if hr.total_ones != 0:
        hr_nums = f'{hr.total_ones}/{hr.num_attacks}'.center(5)
        text += f'`Off 1 Stars` | `{hr_nums}` | {round(hr.average_ones * 100, 1)}%\n'
    if hr.total_twos != 0:
        hr_nums = f'{hr.total_twos}/{hr.num_attacks}'.center(5)
        text += f'`Off 2 Stars` | `{hr_nums}` | {round(hr.average_twos * 100, 1)}%\n'
    if hr.total_triples != 0:
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        text += f'`Off 3 Stars` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n'

    hr = defrate[0]
    footer_text += f'\nAvg. Def Stars: `{round(hr.average_stars, 2)}`'
    if hr.total_zeros != 0:
        hr_nums = f'{hr.total_zeros}/{hr.num_attacks}'.center(5)
        text += f'`Def 0 Stars` | `{hr_nums}` | {round(100 - (hr.average_zeros * 100), 1)}%\n'
    if hr.total_ones != 0:
        hr_nums = f'{hr.total_ones}/{hr.num_attacks}'.center(5)
        text += f'`Def 1 Stars` | `{hr_nums}` | {round(100 - (hr.average_ones * 100), 1)}%\n'
    if hr.total_twos != 0:
        hr_nums = f'{hr.total_twos}/{hr.num_attacks}'.center(5)
        text += f'`Def 2 Stars` | `{hr_nums}` | {round(100 - (hr.average_twos * 100), 1)}%\n'
    if hr.total_triples != 0:
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        text += f'`Def 3 Stars` | `{hr_nums}` | {round(100 - (hr.average_triples * 100), 1)}%\n'

    if text == '':
        text = 'No attacks/defenses yet.\n'
    embed.add_field(name="**Star Count %'s**", value=text + '­\n', inline=False)

    fresh_hr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
    nonfresh_hr = await player.hit_rate(fresh_type=[False], start_timestamp=start_date, end_timestamp=end_date)
    fresh_dr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
    nonfresh_dr = await player.defense_rate(fresh_type=[False], start_timestamp=start_date, end_timestamp=end_date)
    hitrates = [fresh_hr, nonfresh_hr, fresh_dr, nonfresh_dr]
    names = ['Fresh HR', 'Non-Fresh HR', 'Fresh DR', 'Non-Fresh DR']
    text = ''
    for count, hr in enumerate(hitrates):
        hr = hr[0]
        if hr.num_attacks == 0:
            continue
        hr_type = f'{names[count]}'.ljust(12)
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        text += f'`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n'
    if text == '':
        text = 'No attacks/defenses yet.\n'
    embed.add_field(name='**Fresh/Not Fresh**', value=text + '­\n', inline=False)

    random = await player.hit_rate(war_types=['random'], start_timestamp=start_date, end_timestamp=end_date)
    cwl = await player.hit_rate(war_types=['cwl'], start_timestamp=start_date, end_timestamp=end_date)
    friendly = await player.hit_rate(war_types=['friendly'], start_timestamp=start_date, end_timestamp=end_date)
    random_dr = await player.defense_rate(war_types=['random'], start_timestamp=start_date, end_timestamp=end_date)
    cwl_dr = await player.defense_rate(war_types=['cwl'], start_timestamp=start_date, end_timestamp=end_date)
    friendly_dr = await player.defense_rate(war_types=['friendly'], start_timestamp=start_date, end_timestamp=end_date)
    hitrates = [random, cwl, friendly, random_dr, cwl_dr, friendly_dr]
    names = ['War HR', 'CWL HR', 'Friendly HR', 'War DR', 'CWL DR', 'Friendly DR']
    text = ''
    for count, hr in enumerate(hitrates):
        hr = hr[0]
        if hr.num_attacks == 0:
            continue
        hr_type = f'{names[count]}'.ljust(11)
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        text += f'`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n'
    if text == '':
        text = 'No attacks/defenses yet.\n'
    embed.add_field(name='**War Type**', value=text + '­\n', inline=False)

    war_sizes = list(range(5, 55, 5))
    hitrates = []
    for size in war_sizes:
        hr = await player.hit_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
        hitrates.append(hr)
    for size in war_sizes:
        hr = await player.defense_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
        hitrates.append(hr)

    text = ''
    names = [f'{size}v{size} HR' for size in war_sizes] + [f'{size}v{size} DR' for size in war_sizes]
    for count, hr in enumerate(hitrates):
        hr = hr[0]
        if hr.num_attacks == 0:
            continue
        hr_type = f'{names[count]}'.ljust(8)
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        text += f'`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n'
    if text == '':
        text = 'No attacks/defenses yet.\n'
    embed.add_field(name='**War Size**', value=text + '­\n', inline=False)

    lost_hr = await player.hit_rate(
        war_statuses=['lost', 'losing'],
        start_timestamp=start_date,
        end_timestamp=end_date,
    )
    win_hr = await player.hit_rate(
        war_statuses=['winning', 'won'],
        start_timestamp=start_date,
        end_timestamp=end_date,
    )
    lost_dr = await player.defense_rate(
        war_statuses=['lost', 'losing'],
        start_timestamp=start_date,
        end_timestamp=end_date,
    )
    win_dr = await player.defense_rate(
        war_statuses=['winning', 'won'],
        start_timestamp=start_date,
        end_timestamp=end_date,
    )
    hitrates = [lost_hr, win_hr, lost_dr, win_dr]
    names = ['Losing HR', 'Winning HR', 'Losing DR', 'Winning DR']
    text = ''
    for count, hr in enumerate(hitrates):
        hr = hr[0]
        if hr.num_attacks == 0:
            continue
        hr_type = f'{names[count]}'.ljust(11)
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        text += f'`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n'
    if text == '':
        text = 'No attacks/defenses yet.\n'
    embed.add_field(name='**War Status**', value=text + '­\n', inline=False)
    embed.description = footer_text

    return embed


async def detailed_player_board(bot: CustomClient, custom_player: StatsPlayer, server: disnake.Guild):
    player = custom_player

    discord_id = await bot.link_client.get_link(player.tag)
    member = await bot.getch_user(discord_id)
    super_troop_text = profileSuperTroops(player=player, bot=bot)

    clan_text = (
        f'[{player.clan.name}]({player.clan.share_link}), {player.role.in_game_name}'
        if player.clan is not None
        else 'Not in a Clan'
    )

    if member is not None:
        link_text = f'{bot.emoji.green_check}Linked to {member.mention}'
    elif member is None and discord_id is not None:
        link_text = f'{bot.emoji.green_check}*Linked, but not on this server.*'
    else:
        link_text = f"{bot.emoji.square_x_deny}Not linked. Owner? Use {bot.get_command_mention('link')}"

    last_online = f'<t:{player.last_online}:R>, {len(player.season_last_online())} times'
    if player.last_online is None:
        last_online = '`Not Seen Yet`'

    loot_text = ''
    if player.gold_looted() != 0:
        loot_text += f"- {bot.emoji.gold}Gold Looted: {'{:,}'.format(player.gold_looted())}\n"
    if player.elixir_looted() != 0:
        loot_text += f"- {bot.emoji.elixir}Elixir Looted: {'{:,}'.format(player.elixir_looted())}\n"
    if player.dark_elixir_looted() != 0:
        loot_text += f"- {bot.emoji.dark_elixir}DE Looted: {'{:,}'.format(player.dark_elixir_looted())}\n"

    capital_stats = player.clan_capital_stats(start_week=0, end_week=4)
    hitrate = (await player.hit_rate())[0]
    profile_text = (
        f'{link_text}\n'
        f"[Open In-Game]({player.share_link}), [Clash Of Stats](https://www.clashofstats.com/players/{player.tag.strip('#')})\n"
        f'Clan: {clan_text}\n'
        f'Seen: {last_online}\n\n'
        f'**Season Stats:**\n'
        f'- {bot.fetch_emoji(player.league.name)}Trophies: {player.trophies}\n'
        f'- {bot.emoji.brown_shield}Attack Wins: {player.attack_wins}\n'
        f'- {bot.emoji.shield}Defense Wins: {player.defense_wins}\n'
        f'{loot_text}'
        f'**War**\n'
        f'- {bot.emoji.ratio}Hitrate: `{round(hitrate.average_triples * 100, 1)}%`\n'
        f'- {bot.emoji.average}Avg Stars: `{round(hitrate.average_stars, 2)}`\n'
        f'- {bot.emoji.war_star}Total Stars: `{hitrate.total_stars}, {hitrate.num_attacks} atks`\n'
        f'**Donations**\n'
        f'- {bot.emoji.up_green_arrow}Donated: {player.donos().donated}\n'
        f'- {bot.emoji.down_red_arrow}Received: {player.donos().received}\n'
        f'- {bot.emoji.ratio}Donation Ratio: {player.donation_ratio()}\n'
        f'**Event Stats**\n'
        f"- {bot.emoji.capital_gold}CG Donated: {'{:,}'.format(sum([sum(cap.donated) for cap in capital_stats]))}\n"
        f"- {bot.emoji.thick_capital_sword}CG Raided: {'{:,}'.format(sum([sum(cap.raided) for cap in capital_stats]))}\n"
        f"- {bot.emoji.clan_games}Clan Games: {'{:,}'.format(player.clan_games())}\n"
        f'{super_troop_text}'
        f'\n**All Time Stats**\n'
        f'- Best: {bot.emoji.trophy}{player.best_trophies} | {bot.emoji.versus_trophy}{player.best_builder_base_trophies}\n'
        f'- War: {bot.emoji.war_star}{player.war_stars}\n'
        f"- CWL: {bot.emoji.war_star} {player.get_achievement('War League Legend').value}\n"
        f"- {bot.emoji.troop}Donos: {'{:,}'.format(player.get_achievement('Friend in Need').value)}\n"
        f"- {bot.emoji.clan_games}Clan Games: {'{:,}'.format(player.get_achievement('Games Champion').value)}\n"
        f"- {bot.emoji.thick_capital_sword}CG Raided: {'{:,}'.format(player.get_achievement('Aggressive Capitalism').value)}\n"
        f"- {bot.emoji.capital_gold}CG Donated: {'{:,}'.format(player.get_achievement('Most Valuable Clanmate').value)}"
    )

    embed = disnake.Embed(
        title=f'{player.name} ({player.tag})',
        description=profile_text,
        color=disnake.Color.green(),
    ).set_thumbnail(url=player.town_hall_cls.image_url)
    if member is not None:
        embed.set_footer(text=str(member), icon_url=member.display_avatar)

    ban = await bot.banlist.find_one(
        {'$and': [{'VillageTag': f'{player.tag}'}, {'server': server.id if server else None}]}
    )

    if ban is not None:
        date = ban.get('DateCreated')
        date = date[:10]
        notes = ban.get('Notes')
        if notes == '':
            notes = 'No Reason Given'
        embed.add_field(name=f'**{bot.emoji.warning}Banned Player**', value=f'Date: {date}\nReason: {notes}')
    return embed


@register_button('playeraccounts', parser='_:discord_user')
async def player_accounts(bot: CustomClient, discord_user: disnake.Member, embed_color: disnake.Color):
    linked_accounts = await bot.link_client.get_linked_players(discord_id=discord_user.id)

    players = await bot.get_players(tags=linked_accounts, custom=True, use_cache=True)
    if not players:
        raise NoLinkedAccounts

    players.sort(key=lambda x: (x.town_hall, x.trophies), reverse=True)
    total_stats = {
        'donos': 0,
        'rec': 0,
        'war_stars': 0,
        'th': 0,
        'attacks': 0,
        'trophies': 0,
        'total_donos': 0,
    }
    text = ''
    for count, player in enumerate(players):
        if count < 20:
            opt_emoji = bot.emoji.opt_in if player.war_opted_in else bot.emoji.opt_out

            text += (
                f'{opt_emoji}**[{player.clear_name}{create_superscript(player.town_hall)}]({player.share_link})**\n'
                f'{bot.fetch_emoji(player.league_as_string)}{player.trophies}'
            )

            if player.clan:
                text += f' | {player.clan.name} ({player.role_as_string})'

            text += '\n'
    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(
        name=f'{discord_user.display_name} Accounts ({len(players)})',
        icon_url=discord_user.display_avatar,
    )
    if len(players) > 20:
        embed.set_footer(text='Only top 20 accounts are shown due to character limitations')
    return embed


@register_button('playertodo', parser='_:discord_user')
async def to_do_embed(bot: CustomClient, discord_user: disnake.Member, embed_color: disnake.Color):

    user_settings = await bot.user_settings.find_one({'discord_id': discord_user.id})
    if user_settings:
        linked_accounts = user_settings.get('to_do_accounts')
    else:
        linked_accounts = await bot.link_client.get_linked_players(discord_id=discord_user.id)

    linked_accounts = await bot.get_players(tags=linked_accounts, custom=True, use_cache=True)
    if not linked_accounts:
        raise NoLinkedAccounts

    embed = disnake.Embed(title=f'{discord_user.display_name} To-Do List', color=embed_color)

    war_hits_to_do = await get_war_hits(bot=bot, linked_accounts=linked_accounts)
    if war_hits_to_do != '':
        embed.add_field(name='War Hits', value=war_hits_to_do, inline=False)

    legend_hits_to_do = await get_legend_hits(linked_accounts=linked_accounts)
    if legend_hits_to_do != '':
        embed.add_field(name='Legend Hits', value=legend_hits_to_do, inline=False)

    if is_raids():
        raid_hits_to_do = await get_raid_hits(bot=bot, linked_accounts=linked_accounts)
        if raid_hits_to_do != '':
            embed.add_field(name='Raid Hits', value=raid_hits_to_do, inline=False)

    clangames_to_do = await get_clan_games(linked_accounts=linked_accounts)
    if clangames_to_do != '':
        embed.add_field(name='Clan Games', value=clangames_to_do, inline=False)

    pass_to_do = await get_pass(bot=bot, linked_accounts=linked_accounts)
    if pass_to_do != '':
        embed.add_field(name='Season Pass (Top 10)', value=pass_to_do, inline=False)

    inactive_to_do = await get_inactive(linked_accounts=linked_accounts)
    if inactive_to_do != '':
        embed.add_field(name='Inactive Accounts (48+ hr)', value=inactive_to_do, inline=False)

    donation_to_do = await get_last_donated(bot=bot, linked_accounts=linked_accounts)
    if donation_to_do != '':
        embed.add_field(name='Capital Dono (24+ hr)', value=donation_to_do, inline=False)

    if len(embed.fields) == 0:
        embed.description = "You're all caught up chief!"
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed


async def get_war_hits(bot: CustomClient, linked_accounts: List[StatsPlayer]):
    async def get_clan_wars(clan_tag, player):
        war = await bot.get_clanwar(clanTag=clan_tag)
        if war is not None and str(war.state) == 'notInWar':
            war = None
        if war is not None and war.end_time is None:
            war = None
        if war is not None and war.end_time.seconds_until <= 0:
            war = None
        return (player, war)

    tasks = []
    for player in linked_accounts:
        if player.clan is not None:
            task = asyncio.ensure_future(get_clan_wars(clan_tag=player.clan.tag, player=player))
            tasks.append(task)
    wars = await asyncio.gather(*tasks)

    war_hits = ''
    for player, war in wars:
        if war is None:
            continue
        war: coc.ClanWar
        our_player = coc.utils.get(war.members, tag=player.tag)
        if our_player is None:
            continue
        attacks = our_player.attacks
        required_attacks = war.attacks_per_member
        if len(attacks) < required_attacks:
            war_hits += f'({len(attacks)}/{required_attacks}) | <t:{int(war.end_time.time.replace(tzinfo=pend.UTC).timestamp())}:R> - {player.name}\n'
    return war_hits


@register_button('playertodosettings', parser='_:ctx', ephemeral=True, no_embed=True)
async def player_todo_settings(bot: CustomClient, ctx: disnake.MessageInteraction):

    user_accounts = await bot.link_client.get_linked_players(discord_id=ctx.user.id)
    user_accounts = await bot.get_players(tags=user_accounts, use_cache=True, custom=False)
    if not user_accounts:
        raise NoLinkedAccounts

    def player_component(bot: CustomClient, all_players: List[coc.Player]):
        all_players.sort(key=lambda x: (x.town_hall, x.trophies), reverse=True)
        all_players = all_players[:100]
        player_chunked = [all_players[i : i + 25] for i in range(0, len(all_players), 25)]

        dropdown = []
        for chunk_list in player_chunked:
            player_options = []
            for player in chunk_list:
                player_options.append(
                    disnake.SelectOption(
                        label=f'{player.name} ({player.tag})',
                        emoji=bot.fetch_emoji(player.town_hall).partial_emoji,
                        value=f'{player.tag}',
                    )
                )

            player_select = disnake.ui.Select(
                options=player_options,
                placeholder=f'Select Player(s)',  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(player_options),  # the maximum number of options a user can select
            )
            dropdown.append(disnake.ui.ActionRow(player_select))

        dropdown.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label='Save',
                    emoji=bot.emoji.green_check.partial_emoji,
                    style=disnake.ButtonStyle.green,
                    custom_id='Save',
                )
            )
        )
        return dropdown

    msg = await ctx.followup.send(
        content='Choose which account you want visible on your to-do list (max 15)\n',
        components=player_component(bot=bot, all_players=user_accounts),
        ephemeral=True,
        wait=True,
    )
    clicked_save = False
    players = set()
    while not clicked_save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, msg=msg)
        if res.component.type == disnake.ComponentType.button:
            break
        for value in res.values:
            players.add(value)
            if len(players) == 15:
                break

    await bot.user_settings.update_one(
        {'discord_id': ctx.author.id},
        {'$set': {'to_do_accounts': list(players)}},
        upsert=True,
    )
    await msg.edit(content='Player To-Do Accounts Updated!', components=None)


async def get_legend_hits(linked_accounts: List[StatsPlayer]):
    legend_hits_remaining = ''
    for player in linked_accounts:
        if player.is_legends():
            if player.legend_day().num_attacks.integer < 8:
                legend_hits_remaining += f'({player.legend_day().num_attacks.integer}/8) - {player.name}\n'
    return legend_hits_remaining


async def get_raid_hits(bot: CustomClient, linked_accounts: List[StatsPlayer]):

    current_week = bot.gen_raid_date()

    # only pull current raid weekends, in case somehow old ones get stuck there
    """raids_in = await bot.capital_cache.find({"$and" : [
        {"data.members.tag": {"$in": [p.tag for p in linked_accounts]}},
        {"data.startTime" : weekend_to_cocpy_timestamp(weekend=current_week)}
    ]})"""

    linked_tags = [p.tag for p in linked_accounts]  # Assume this list is already computed
    weekend_timestamp = weekend_to_cocpy_timestamp(weekend=current_week)

    raids_in = await bot.capital_cache.aggregate(
        [
            {
                '$match': {
                    '$and': [
                        {'data.members.tag': {'$in': linked_tags}},
                        {'data.startTime': weekend_timestamp.time.strftime('%Y%m%dT%H%M%S.000Z')},
                    ]
                }
            },
            {
                '$project': {
                    'data': {
                        'startTime': 1,
                        'members': {
                            '$filter': {
                                'input': '$data.members',
                                'as': 'member',
                                'cond': {'$in': ['$$member.tag', linked_tags]},
                            }
                        },
                    },
                    'tag': 1,
                }
            },
            {'$match': {'data.members': {'$not': {'$size': 0}}}},
        ]
    ).to_list(length=None)
    raid_hits = ''

    for raw_raid in raids_in:
        clan_tag = raw_raid.get('tag')
        members = raw_raid.get('data', {}).get('members', [])
        members = [coc.raid.RaidMember(data=m, raid_log_entry=None, client=None) for m in members]

        for member in members:
            linked_tags.remove(member.tag)
            attacks = member.attack_count
            required_attacks = member.attack_limit + member.bonus_attack_limit
            if attacks < required_attacks:
                raid_hits += f'({attacks}/{required_attacks}) - {member.name}\n'

    for player in linked_accounts:
        if player.tag in linked_tags and player.clan is not None:
            raid_hits += f'({0}/{5}) - {player.name}\n'
    return raid_hits


async def get_inactive(linked_accounts: List[StatsPlayer]):
    now = int(pend.now(tz=pend.UTC).timestamp())
    inactive_text = ''
    for player in linked_accounts:
        last_online = player.last_online
        # 48 hours in seconds
        if last_online is None:
            continue
        if now - last_online >= (48 * 60 * 60):
            inactive_text += f'<t:{last_online}:R> - {player.name}\n'
    return inactive_text


async def get_clan_games(linked_accounts: List[StatsPlayer]):
    missing_clan_games = ''
    zeros = ''
    num_zeros = 0
    if is_clan_games():
        for player in linked_accounts:
            points = player.clan_games()
            if points < 4000:
                if points == 0:
                    zeros += f'({points}/4000) - {player.name}\n'
                    num_zeros += 1
                else:
                    missing_clan_games += f'({points}/4000) - {player.name}\n'

    if num_zeros == len(linked_accounts):
        missing_clan_games = '(0/4000) on All Accounts '
    elif num_zeros >= 5:
        missing_clan_games += '(0/4000) on All Other Accounts'
    else:
        missing_clan_games += zeros

    return missing_clan_games


async def get_pass(bot: CustomClient, linked_accounts: List[StatsPlayer]):
    pass_text = ''
    points = 3000 if bot.gen_games_season() == '2023-06' else 4000
    l = sorted(linked_accounts, key=lambda x: x.season_pass(), reverse=True)[:10]
    for player in l:
        season_pass_points = player.season_pass()
        if season_pass_points < points and season_pass_points != 0:
            pass_text += f'({season_pass_points}/{points}) - {player.name}\n'
    return pass_text


async def get_last_donated(bot: CustomClient, linked_accounts: List[StatsPlayer]):
    pass_text = ''
    now = int(pend.now(tz=pend.UTC).timestamp())
    pipeline = [
        {
            '$match': {
                '$and': [
                    {'tag': {'$in': [p.tag for p in linked_accounts]}},
                    {'type': 'clanCapitalContributions'},
                ]
            }
        },
        {'$group': {'_id': '$tag', 'last_change': {'$last': '$time'}}},
        {'$sort': {'last_change': -1}},
    ]
    results = await bot.player_history.aggregate(pipeline=pipeline).to_list(length=None)
    tag_to_player = {p.tag: p for p in linked_accounts}
    for result in results:
        time = result.get('last_change')
        if now - time >= (24 * 60 * 60):
            pass_text += f"<t:{time}:R> - {tag_to_player.get(result.get('_id')).name}\n"
    return pass_text


def is_clan_games():
    now = pend.now(tz=pend.UTC)
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    first = pend.datetime(year, month, 22, hour=8, tz=pend.UTC)
    end = pend.datetime(year, month, 28, hour=8, tz=pend.UTC)
    if day >= 22 and day <= 28:
        if (day == 22 and hour < 8) or (day == 28 and hour >= 8):
            is_games = False
        else:
            is_games = True
    else:
        is_games = False
    return is_games
