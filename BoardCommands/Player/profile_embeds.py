import disnake
import coc
import aiohttp

from Assets.emojiDictionary import emojiDictionary
from Assets.thPicDictionary import thDictionary
from utils.clash import *
from bs4 import BeautifulSoup
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from numerize import numerize
from CustomClasses.PlayerHistory import StayType

async def create_profile_stats(bot: CustomClient, ctx, player: MyCustomPlayer):

    discord_id = await bot.link_client.get_link(player.tag)
    member = await bot.pingToMember(ctx, str(discord_id))
    super_troop_text = profileSuperTroops(player)

    clan = f"{player.clan.name}, " if player.clan is not None else "None"
    role = player.role if player.role is not None else ""

    if member is not None:
        link_text = f"Linked to {member.mention}"
    elif member is None and discord_id is not None:
        link_text = "*Linked, but not on this server.*"
    else:
        link_text = "Not linked. Owner? Use </link:1033741922180796451>"

    last_online = f"<t:{player.last_online}:R>, {len(player.season_last_online())} times"
    if player.last_online is None:
        last_online = "`Not Seen Yet`"

    loot_text = ""
    if player.gold_looted != 0:
        loot_text += f"- {bot.emoji.gold}Gold Looted: {'{:,}'.format(player.gold_looted)}\n"
    if player.elixir_looted != 0:
        loot_text += f"- {bot.emoji.elixir}Elixir Looted: {'{:,}'.format(player.elixir_looted)}\n"
    if player.dark_elixir_looted != 0:
        loot_text += f"- {bot.emoji.dark_elixir}DE Looted: {'{:,}'.format(player.dark_elixir_looted)}\n"

    capital_stats = player.clan_capital_stats(start_week=0, end_week=4)
    hitrate = (await player.hit_rate())[0]
    profile_text = f"{link_text}\n" \
        f"Tag: [{player.tag}]({player.share_link})\n" \
        f"Clan: {clan} {role}\n" \
        f"Last Seen: {last_online}\n" \
        f"[Clash Of Stats Profile](https://www.clashofstats.com/players/{player.tag.strip('#')})\n\n" \
        f"**Season Stats:**\n" \
        f"__Attacks__\n" \
        f"- {league_emoji(player)}Trophies: {player.trophies}\n" \
        f"- {bot.emoji.thick_sword}Attack Wins: {player.attack_wins}\n" \
        f"- {bot.emoji.brown_shield}Defense Wins: {player.defense_wins}\n" \
        f"{loot_text}" \
        f"__War__\n" \
        f"- {bot.emoji.hitrate}Hitrate: `{round(hitrate.average_triples * 100, 1)}%`\n" \
        f"- {bot.emoji.avg_stars}Avg Stars: `{round(hitrate.average_stars, 2)}`\n" \
        f"- {bot.emoji.war_stars}Total Stars: `{hitrate.total_stars}, {hitrate.num_attacks} atks`\n" \
        f"__Donations__\n" \
        f"- <:warwon:932212939899949176>Donated: {player.donos().donated}\n" \
        f"- <:warlost:932212154164183081>Received: {player.donos().received}\n" \
        f"- <:winrate:932212939908337705>Donation Ratio: {player.donation_ratio()}\n" \
        f"__Event Stats__\n" \
        f"- {bot.emoji.capital_gold}CG Donated: {'{:,}'.format(sum([sum(cap.donated) for cap in capital_stats]))}\n" \
        f"- {bot.emoji.thick_sword}CG Raided: {'{:,}'.format(sum([sum(cap.raided) for cap in capital_stats]))}\n" \
        f"- {bot.emoji.clan_games}Clan Games: {'{:,}'.format(player.clan_games())}\n" \
        f"{super_troop_text}" \
        f"\n**All Time Stats:**\n" \
        f"Best Trophies: {bot.emoji.trophy}{player.best_trophies} | {bot.emoji.versus_trophy}{player.best_versus_trophies}\n" \
        f"War Stars: {bot.emoji.war_star}{player.war_stars}\n" \
        f"CWL Stars: {bot.emoji.war_star} {player.get_achievement('War League Legend').value}\n" \
        f"{bot.emoji.troop}Donations: {'{:,}'.format(player.get_achievement('Friend in Need').value)}\n" \
        f"{bot.emoji.clan_games}Clan Games: {'{:,}'.format(player.get_achievement('Games Champion').value)}\n" \
        f"{bot.emoji.thick_sword}CG Raided: {'{:,}'.format(player.get_achievement('Aggressive Capitalism').value)}\n" \
        f"{bot.emoji.capital_gold}CG Donated: {'{:,}'.format(player.get_achievement('Most Valuable Clanmate').value)}"

    embed = disnake.Embed(title=f"{player.town_hall_cls.emoji} **{player.name}**",
                          description=profile_text,
                          color=disnake.Color.green())
    embed.set_thumbnail(url=player.town_hall_cls.image_url)
    if member is not None:
        embed.set_footer(text=str(member), icon_url=member.display_avatar)

    ban = await bot.banlist.find_one({"$and": [
        {"VillageTag": f"{player.tag}"},
        {"server": ctx.guild.id}
    ]})

    if ban is not None:
        date = ban.get("DateCreated")
        date = date[:10]
        notes = ban.get("Notes")
        if notes == "":
            notes = "No Reason Given"
        embed.add_field(name="__**Banned Player**__",
                        value=f"Date: {date}\nReason: {notes}")
    return embed

async def history(bot: CustomClient, ctx, player):

    clan_history = await bot.get_player_history(player_tag=player.tag)
    previous_clans = clan_history.previous_clans(limit=5)
    clan_summary = clan_history.summary(limit=5)

    top_5 = ""
    if previous_clans == "Private History":
        return disnake.Embed(title=f"{player.name} Clan History",description="This player has made their clash of stats history private.", color=disnake.Color.green())
    embed = disnake.Embed(title=f"{player.name} Clan History", description=f"This player has been seen in a total of {clan_history.num_clans} different clans\n"
                                        f"[Full History](https://www.clashofstats.com/players/{player.tag.strip('#')}/history/)", color=disnake.Color.green())

    for clan in clan_summary:
        years = clan.duration.days // 365
        # Calculating months
        months = (clan.duration.days - years * 365) // 30
        # Calculating days
        days = (clan.duration.days - years * 365 - months * 30)
        date_text = []
        if years >= 1:
            date_text.append(f"{years} Years")
        if months >= 1:
            date_text.append(f"{months} Months")
        if days >= 1:
            date_text.append(f"{days} Days")
        if date_text:
            date_text = ', '.join(date_text)
        else:
            date_text = "N/A"
        top_5 += f"[{clan.clan_name}]({clan.share_link}) - {date_text}\n"

    if top_5 == "":
        top_5 = "No Clans Found"
    embed.add_field(name="**Top 5 Clans Player has stayed the most:**",
                        value=top_5, inline=False)

    last_5 = ""
    for clan in previous_clans:
        if clan.stay_type == StayType.unknown:
            continue
        last_5 += f"[{clan.clan_name}]({clan.share_link}), {clan.role.in_game_name}"
        if clan.stay_type == StayType.stay:
            last_5 += f", {clan.stay_length.days} days" if clan.stay_length.days >= 1 else ""
            last_5 += f"\n<t:{int(clan.start_stay.time.timestamp())}:D> to <t:{int(clan.end_stay.time.timestamp())}:D>\n"
        elif clan.stay_type == StayType.seen:
            last_5 += f"\nSeen on <t:{int(clan.seen_date.time.timestamp())}:D>\n"

    if last_5 == "":
        last_5 = "No Clans Found"
    embed.add_field(name="**Last 5 Clans Player has been seen at:**", value=last_5, inline=False)

    embed.set_footer(text="Data from ClashofStats.com")
    return embed


async def create_profile_troops(bot, result):
    player = result
    hero = heros(bot=bot, player=player)
    pets = heroPets(bot=bot, player=player)
    troop = troops(bot=bot, player=player)
    deTroop = deTroops(bot=bot, player=player)
    siege = siegeMachines(bot=bot, player=player)
    spell = spells(bot=bot, player=player)

    embed = disnake.Embed(title="You are looking at " + player.name,
                           description="Troop, hero, & spell levels for this account.",
                           color=disnake.Color.green())
    embed.add_field(name=f'__**{player.name}** (Th{player.town_hall})__ {player.trophies}', value="Profile: " + f'[{player.tag}]({player.share_link})',
                     inline=False)

    if (hero is not None):
        embed.add_field(name="**Heroes:** ", value=hero, inline=False)

    if (pets is not None):
        embed.add_field(name="**Pets:** ", value=pets, inline=False)

    if (troop is not None):
        embed.add_field(name="**Elixir Troops:** ", value=troop, inline=False)

    if (deTroop is not None):
        embed.add_field(name="**Dark Elixir Troops:** ", value=deTroop, inline=False)

    if (siege is not None):
        embed.add_field(name="**Siege Machines:** ", value=siege, inline=False)

    if (spell is not None):
        embed.add_field(name="**Spells:** ", value=spell, inline=False)

    return embed

def upgrade_embed(bot: CustomClient, player: coc.Player):
    home_elixir_troops = ""
    home_de_troops = ""
    siege_machines = ""
    bb_troops = ""

    troops_found = []
    troop_levels = 0
    troop_levels_missing = 0
    for troop in player.troops:
        if troop.is_super_troop:
            continue
        troops_found.append(troop.name)
        troop_emoji = bot.fetch_emoji(name=troop.name)

        prev_level_max = troop.get_max_level_for_townhall(player.town_hall - 1)
        if prev_level_max is None:
            prev_level_max = troop.level

        th_max = troop.get_max_level_for_townhall(player.town_hall)
        troop_levels += th_max
        troop_levels_missing += (th_max - troop.level)
        th_max = f"{th_max}".ljust(2)
        level = f"{troop.level}".rjust(2)
        days = f"{int(troop.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(troop.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(troop.upgrade_cost)}".ljust(5)
        if troop.level < prev_level_max:  # rushed
            if troop.is_siege_machine:
                siege_machines += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
            elif troop.is_elixir_troop:
                home_elixir_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
            elif troop.is_dark_troop:
                home_de_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
            elif troop.is_builder_base:
                bb_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"

        elif troop.level < troop.get_max_level_for_townhall(player.town_hall):  # not max
            if troop.is_elixir_troop:
                if troop.is_siege_machine:
                    siege_machines += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"
                else:
                    home_elixir_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"
            elif troop.is_dark_troop:
                home_de_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"
            elif troop.is_builder_base:
                bb_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"

    for troop in coc.HOME_TROOP_ORDER:
        if troop not in troops_found:
            troop: coc.Troop = bot.coc_client.get_troop(name=troop, is_home_village=True, townhall=player.town_hall)
            troop_emoji = bot.fetch_emoji(name=troop.name)
            th_max = troop.get_max_level_for_townhall(player.town_hall)
            troop_unlock = troop.lab_level[2]
            convert_lab = troop.lab_to_townhall
            troop_unlock = convert_lab[troop_unlock]
            if player.town_hall >= troop_unlock:
                troop_levels += th_max
                troop_levels_missing += (th_max)
                th_max = f"{th_max}".ljust(2)
                level = f"0".rjust(2)
                if troop.is_siege_machine:
                    siege_machines += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"
                elif troop.is_elixir_troop:
                    home_elixir_troops += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"
                elif troop.is_dark_troop:
                    home_de_troops += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"

    elixir_spells = ""
    de_spells = ""
    found_spells = []
    spell_levels= 0
    spell_levels_missing = 0
    for spell in player.spells:
        troop_emoji = bot.fetch_emoji(name=spell.name)
        found_spells.append(spell.name)
        prev_level_max = spell.get_max_level_for_townhall(player.town_hall - 1)
        if prev_level_max is None:
            prev_level_max = spell.level


        th_max = spell.get_max_level_for_townhall(player.town_hall)
        spell_levels += th_max
        spell_levels_missing += (th_max - spell.level)
        th_max = f"{th_max}".ljust(2)
        level = f"{spell.level}".rjust(2)
        days = f"{int(spell.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(spell.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(spell.upgrade_cost)}".ljust(5)
        if spell.level < prev_level_max:  # rushed
            if spell.is_elixir_spell:
                elixir_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
            elif spell.is_dark_spell:
                de_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
        elif spell.level < spell.get_max_level_for_townhall(player.town_hall):  # not max
            if spell.is_elixir_spell:
                elixir_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"
            elif spell.is_dark_spell:
                de_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"


    for spell in coc.SPELL_ORDER:
        if spell not in found_spells:
            spell: coc.Spell = bot.coc_client.get_spell(name=spell, townhall=player.town_hall)
            troop_emoji = bot.fetch_emoji(name=spell.name)
            th_max = spell.get_max_level_for_townhall(player.town_hall)
            if th_max is None:
                continue
            spell_levels += th_max
            spell_levels_missing += (th_max)
            troop_unlock = spell.lab_level[2]
            convert_lab = spell.lab_to_townhall
            troop_unlock = convert_lab[troop_unlock]
            if player.town_hall >= troop_unlock:
                th_max = f"{th_max}".ljust(2)
                level = f"0".rjust(2)
                if spell.is_elixir_spell:
                    elixir_spells += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"
                elif spell.is_dark_spell:
                    de_spells += f"{troop_emoji} `{level}/{th_max}` `Not Unlocked`\n"

    hero_levels = 0
    hero_levels_missing = 0
    hero_text = ""
    for hero in player.heroes:
        troop_emoji = bot.fetch_emoji(name=hero.name)
        hero_levels += hero.level
        if hero.required_th_level == player.town_hall:
            prev_level_max = None
        else:
            prev_level_max = hero.get_max_level_for_townhall(player.town_hall - 1)
        if prev_level_max is None:
            prev_level_max = hero.level


        th_max = hero.get_max_level_for_townhall(player.town_hall)
        hero_levels_missing += (th_max - hero.level)
        th_max = f"{th_max}".ljust(2)
        level = f"{hero.level}".rjust(2)
        days = f"{int(hero.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(hero.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(hero.upgrade_cost)}".ljust(5)
        if hero.level < prev_level_max:  # rushed
            hero_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"

        elif hero.level < hero.get_max_level_for_townhall(player.town_hall):  # not max
            hero_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"

    pet_text = ""

    for pet in player.pets:
        troop_emoji = bot.fetch_emoji(name=pet.name)

        new_pets = ["Diggy", "Frosty", "Phoenix", "Poison Lizard"]

        th_max = f"{10}".ljust(2)
        level = f"{pet.level}".rjust(2)
        days = f"{int(pet.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(pet.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(pet.upgrade_cost)}".ljust(5)
        if pet.level < 10 and pet.name not in new_pets and player.town_hall == 15:  # rushed
            pet_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✗\n"
        elif pet.level < 10:  # not max
            pet_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"


    full_text = ""
    if home_elixir_troops != "":
        full_text += f"**Elixir Troops**\n{home_elixir_troops}\n"
    if home_de_troops != "":
        full_text += f"**Dark Elixir Troops**\n{home_de_troops}\n"
    if hero_text != "":
        full_text += f"**Heros**\n{hero_text}\n"
    if pet_text != "":
        full_text += f"**Hero Pets**\n{pet_text}\n"
    if elixir_spells != "":
        full_text += f"**Elixir Spells**\n{elixir_spells}\n"
    if de_spells != "":
        full_text += f"**Dark Elixir Spells**\n{de_spells}\n"
    if siege_machines != "":
        full_text += f"**Siege Machines**\n{siege_machines}\n"

    embed2 = False
    if bb_troops != "":
        embed2 = disnake.Embed(description=f"**Builder Base Troops**\n{bb_troops}\n",colour=disnake.Color.green())

    if full_text == "":
        full_text = "No Heros, Pets, Spells, or Troops left to upgrade\n"

    if hero_levels_missing == 0:
        hero_levels_missing = "0.00%"
    else:
        hero_levels_missing = f"{round((hero_levels_missing/(hero_levels+hero_levels_missing)) * 100, 2)}%"

    if troop_levels_missing == 0:
        troop_levels_missing = "0.00%"
    else:
        troop_levels_missing = f"{round((troop_levels_missing / (troop_levels)) * 100, 2)}%"

    if spell_levels_missing == 0:
        spell_levels_missing = "0.00%"
    else:
        spell_levels_missing = f"{round((spell_levels_missing / (spell_levels)) * 100, 2)}%"

    #print(full_text)
    embed = disnake.Embed(title=f"{player.name} | TH{player.town_hall}", description=full_text, colour=disnake.Color.green())
    if embed2 is not False:
        embeds = [embed, embed2]
    else:
        embeds = [embed]
    embeds[-1].set_footer(text="✗ = rushed for th level")
    embeds[-1].description += f"Hero Lvl Left: {hero_levels_missing}\n" \
                 f"Troop Lvl Left: {troop_levels_missing}\n" \
                 f"Spell Lvl Left: {spell_levels_missing}\n"
    return embeds