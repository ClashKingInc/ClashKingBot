import disnake
import coc
import aiohttp

from Dictionaries.emojiDictionary import emojiDictionary
from Dictionaries.thPicDictionary import thDictionary
from utils.troop_methods import profileSuperTroops, leagueAndTrophies
from utils.troop_methods import heros, heroPets, troops, deTroops, siegeMachines, spells
from bs4 import BeautifulSoup
from CustomClasses.CustomBot import CustomClient
from numerize import numerize

async def create_profile_stats(bot: CustomClient, ctx, result):

    embed=[]
    player = result
    disnakeID = await bot.link_client.get_link(player.tag)
    #member = await bot.pingToMember(ctx, str(disnakeID))
    try:
        member = await bot.fetch_user(disnakeID)
        print(member.name)
    except:
        member = None

    name = player.name
    link = player.share_link
    donos = player.donations
    received = player.received
    ratio = str(round((donos / (received + 1)), 2))
    bestTrophies = emojiDictionary("trophy") + str(player.best_trophies)
    friendInNeed = player.get_achievement("Friend in Need").value
    friendInNeed = "{:,}".format(friendInNeed)

    clan = ""
    try:
        clan = player.clan.name
        clan = f"{clan},"
    except:
        clan = "None"

    stroops = profileSuperTroops(player)
    # print(stroops)
    if (len(stroops) > 0):
        stroops = "\n**Super Troops:**\n" + stroops + "\n"
    else:
        stroops = ""

    troph = leagueAndTrophies(player)

    th = str(player.town_hall)
    role = str(player.role)
    if role == "None":
        role = ""
    emoji = emojiDictionary(player.town_hall)

    results = await bot.server_db.find_one({"server": ctx.guild.id})
    prefix = results.get("prefix")

    tag = player.tag
    tag = tag.strip("#")
    if member is not None:
        embed = disnake.Embed(title=f'{emoji} **{name}** ',
                              description="Linked to " + member.mention +
                              f"\nTh Level: {player.town_hall}\nTrophies: {troph}\n" +
                                "Tag: " + f'[{player.tag}]({link})' "\n"
                                f"Clan: {clan} {role}\n"
                                f"[Clash Of Stats Profile](https://www.clashofstats.com/players/{tag})",
                              color=disnake.Color.green())
        if member.avatar is None:
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/843624785560993833/961411093622816819/4_1.png")
        else:
            embed.set_thumbnail(url=member.avatar.url)
    elif (member is None) and (disnakeID is not None):
        embed = disnake.Embed(title=f'{emoji} **{name}** ',
                              description=f"*Linked, but not on this server.*"+
                                          f"\nTh Level: {player.town_hall}\nTrophies: {troph}\n" +
                                          "Tag: " + f'[{player.tag}]({link})' "\n"
                                                    f"Clan: {clan} {role}\n"
                                                    f"[Clash Of Stats Profile](https://www.clashofstats.com/players/{tag})"
                              , color=disnake.Color.green())
        if player.town_hall >= 4:
            embed.set_thumbnail(url=thDictionary(player.town_hall))
    else:
        embed = disnake.Embed(title=f'{emoji} **{name}** ',
                              description=f"Not linked. Owner? Use `{prefix}link`" +
                                          f"\nTh Level: {player.town_hall}\nTrophies: {troph}\n" +
                                          "Tag: " + f'[{player.tag}]({link})' "\n"
                                                    f"Clan: {clan} {role}\n"
                                                    f"[Clash Of Stats Profile](https://www.clashofstats.com/players/{tag})"
                              , color=disnake.Color.green())
        if player.town_hall >= 4:
            embed.set_thumbnail(url=thDictionary(player.town_hall))


    embed.add_field(name="**Info:**",
                    value=f"<:warwon:932212939899949176>Donated: {donos} troops\n"
                          f"<:warlost:932212154164183081>Received: {received} troops\n"
                          f"<:winrate:932212939908337705>Donation Ratio: {ratio}\n"
                          f"<:sword:825589136026501160>Attack Wins: {player.attack_wins}\n"
                          f"<:clash:877681427129458739>Defense Wins: {player.defense_wins}\n"
                          f"{stroops}"
                          f"**Stats:**\n"
                          f"Best Trophies: {bestTrophies}\n"
                          f"War Stars: ⭐ {player.war_stars}\n"
                          f"All Time Donos: {friendInNeed}", inline=False)

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

def upgrade_embed(bot, player: coc.Player):
    home_elixir_troops = ""
    home_de_troops = ""
    siege_machines = ""
    bb_troops = ""
    for troop in player.troops:
        if troop.is_super_troop:
            continue
        troop_emoji = bot.fetch_emoji(name=troop.name)

        prev_level_max = troop.get_max_level_for_townhall(player.town_hall - 1)
        if prev_level_max is None:
            prev_level_max = troop.level

        th_max = troop.get_max_level_for_townhall(player.town_hall)
        th_max = f"{th_max}".ljust(2)
        level = f"{troop.level}".rjust(2)
        days = f"{int(troop.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(troop.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(troop.upgrade_cost)}".ljust(5)
        if troop.level < prev_level_max:  # rushed
            if troop.is_siege_machine:
                siege_machines += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✓\n"
            elif troop.is_elixir_troop:
                home_elixir_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✓\n"
            elif troop.is_dark_troop:
                home_de_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✓\n"
            elif troop.is_builder_base:
                bb_troops += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✓\n"

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

    elixir_spells = ""
    de_spells = ""
    for spell in player.spells:
        troop_emoji = bot.fetch_emoji(name=spell.name)

        prev_level_max = spell.get_max_level_for_townhall(player.town_hall - 1)
        if prev_level_max is None:
            prev_level_max = spell.level

        th_max = spell.get_max_level_for_townhall(player.town_hall)
        th_max = f"{th_max}".ljust(2)
        level = f"{spell.level}".rjust(2)
        days = f"{int(spell.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(spell.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(spell.upgrade_cost)}".ljust(5)
        if spell.level < prev_level_max:  # rushed
            if spell.is_elixir_spell:
                elixir_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✓\n"
            elif spell.is_dark_spell:
                de_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✓\n"
        elif spell.level < spell.get_max_level_for_townhall(player.town_hall):  # not max
            if spell.is_elixir_spell:
                elixir_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"
            elif spell.is_dark_spell:
                de_spells += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`\n"

    hero_text = ""
    for hero in player.heroes:
        troop_emoji = bot.fetch_emoji(name=hero.name)

        prev_level_max = hero.get_max_level_for_townhall(player.town_hall - 1)
        if prev_level_max is None:
            prev_level_max = hero.level

        th_max = hero.get_max_level_for_townhall(player.town_hall)
        th_max = f"{th_max}".ljust(2)
        level = f"{hero.level}".rjust(2)
        days = f"{int(hero.upgrade_time.hours / 24)}".rjust(2)
        hours = f"{(int(hero.upgrade_time.hours % 24 / 24 * 10))}H".ljust(3)
        time = f"{days}D {hours}"
        cost = f"{numerize.numerize(hero.upgrade_cost)}".ljust(5)
        if hero.level < prev_level_max:  # rushed
            hero_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✓\n"

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
        if pet.level < 10 and pet.name not in new_pets:  # rushed
            pet_text += f"{troop_emoji} `{level}/{th_max}` `{time}` `{cost}`✓\n"
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
    if bb_troops != "":
        full_text += f"**Builder Base Troops**\n{bb_troops}\n"

    if full_text == "":
        full_text = "No Heros, Pets, Spells, or Troops left to upgrade\n"

    full_text += "✓ = rushed for th level"

    embed = disnake.Embed(title=f"{player.name}", description=full_text, colour=disnake.Color.green())
    return embed