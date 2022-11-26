import disnake
import coc
import aiohttp

from Assets.emojiDictionary import emojiDictionary
from Assets.thPicDictionary import thDictionary
from utils.troop_methods import profileSuperTroops, league_emoji
from utils.troop_methods import heros, heroPets, troops, deTroops, siegeMachines, spells
from bs4 import BeautifulSoup
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from numerize import numerize

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
        f"- <:warwon:932212939899949176>Donated: {player.donos.donated}\n" \
        f"- <:warlost:932212154164183081>Received: {player.donos.received}\n" \
        f"- <:winrate:932212939908337705>Donation Ratio: {player.donation_ratio}\n" \
        f"__Event Stats__\n" \
        f"- {bot.emoji.capital_gold}CG Donated: {'{:,}'.format(sum([sum(cap.donated) for cap in capital_stats]))}\n" \
        f"- {bot.emoji.thick_sword}CG Raided: {'{:,}'.format(sum([sum(cap.raided) for cap in capital_stats]))}\n" \
        f"- {bot.emoji.clan_games}Clan Games: {'{:,}'.format(player.clan_games)}\n" \
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

async def history(bot, ctx, result):
    player = result
    discordID = await bot.link_client.get_link(player.tag)
    member = await bot.pingToMember(ctx, str(discordID))
    join = None
    try:
        join = member.joined_at
        day = str(join.day)
        month = str(join.month)
        year = str(join.year)
    except:
        pass

    result = player.tag.strip("#")
    url = f'https://www.clashofstats.com/players/{result}/history/'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            soup = BeautifulSoup(await response.text(), 'lxml')
            clans = soup.find_all("a", class_="v-list-item v-list-item--link theme--dark")
            test = soup.find_all("div", class_="subsection-title")
            num_clans = test[1].text.strip()
            text = ""
            x = 0
            for clan in clans:
                try:
                    #title_element = clan.find("div", class_="subsection-title")
                    company_element = clan.find("span", class_="text--secondary caption")
                    location_element = clan.find("div", class_="v-list-item__subtitle")
                    #print(title_element.text.strip())
                    #print(company_element.text.strip())
                    t = company_element.text.strip()
                    t = t.strip("-")
                    c = await bot.getClan(t)
                    t = f"[{c.name}]({c.share_link}), - "
                    lstay = None
                    for d in location_element.find_all("br"):
                        lstay = "".join(d.previous_siblings)
                    # print(location_element.text.strip())
                    lstay = " ".join(lstay.split())
                    lstay = lstay.strip("Total ")
                    text += f"\u200e{t} \u200e{lstay}\n"
                    x+=1
                    if x == 5:
                        break
                except:
                    pass

        embed = disnake.Embed(title=f"{player.name} History",
                              description=f"{num_clans}",
                              color=disnake.Color.green())
        embed.add_field(name="**Top 5 Clans Player has stayed the most:**",
                        value=text, inline=False)


        result = result.strip("#")
        url = f'https://www.clashofstats.com/players/{result}/history/log'
        async with session.get(url) as response:
            soup = BeautifulSoup(await response.text(), 'lxml')
            clans = soup.find_all("a", class_="v-list-item v-list-item--link theme--dark")
            text = ""
            x = 0
            types = ["Member", "Elder", "Co-leader", "Leader"]
            for clan in clans:
                try:
                    title_element = clan.find("div", class_="v-list-item__title")
                    location_element = clan.find("div", class_="v-list-item__subtitle text--secondary")
                    t = title_element.text.strip()
                    t = " ".join(t.split())
                    ttt = t.split("#", 1)
                    clan = await bot.getClan(ttt[1])
                    type = "No Role"
                    for ty in types:
                        if ty in t:
                            type = ty

                    t = f"\u200e[{clan.name}]({clan.share_link}), \u200e{type}"

                    lstay = location_element.text.strip()
                    lstay = " ".join(lstay.split())
                    text += f"{t} \n{lstay}\n"
                    x += 1
                    if x == 5:
                        break
                except:
                    pass

        embed.add_field(name="**Last 5 Clans Player has been seen at:**",
                        value=text, inline=False)

        if join is not None:
            embed.add_field(name="**Tenure:**", value=(f"{member.display_name} has been in this server since {month}/{day}/{year}"), inline=False)


        embed.set_footer(text="Data from ClashofStats.com")
        return embed


async def create_profile_troops(bot, result):
    player = result
    hero = heros(player)
    pets = heroPets(player)
    troop = troops(player)
    deTroop = deTroops(player)
    siege = siegeMachines(player)
    spell = spells(player)

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
    for pet in player.hero_pets:
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

    print(spell_levels)
    print(spell_levels_missing)
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