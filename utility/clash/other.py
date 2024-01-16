import coc
import re
import emoji
from assets.emojiDictionary import emojiDictionary
from collections import defaultdict
from utility.discord_utils import fetch_emoji
from utility.constants import DARK_ELIXIR, SUPER_TROOPS
from pytz import utc
from CustomClasses.CustomPlayer import MyCustomPlayer

from datetime import datetime, timedelta


def gen_season_date():
    end = coc.utils.get_season_end().replace(tzinfo=utc).date()
    month = end.month
    if end.month <= 9:
        month = f"0{month}"
    return f"{end.year}-{month}"


def gen_legend_date():
    now = datetime.utcnow()
    hour = now.hour
    if hour < 5:
        date = (now - timedelta(1)).date()
    else:
        date = now.date()
    return str(date)

async def superTroops(player, asArray=False):
    troops = player.troop_cls
    troops = player.troops

    boostedTroops = []

    for x in range(len(troops)):
        troop = troops[x]
        if (troop.is_active):
            # print (troop.name)
            boostedTroops.append(troop.name)

    if asArray:
        return boostedTroops

    return str(boostedTroops)


def heros(bot, player: MyCustomPlayer):
    def get_emoji(hero: coc.Hero):
        color = "blue"
        if hero.level == hero.get_max_level_for_townhall(townhall=player.town_hall):
            color = "gold"
        return bot.get_number_emoji(color=color, number=hero.level)

    gear_to_hero = defaultdict(list)
    for gear in player.hero_equipment:
        if gear.hero is not None:
            gear_to_hero[gear.hero].append(gear)

    hero_string = ""
    for hero in player.heroes:
        if not hero.is_home_base:
            continue
        gear_text = " | "
        for gear in gear_to_hero.get(hero.name, []):
            color = "blue"
            if gear.level == gear.max_level:
                color = "gold"
            emoji = bot.get_number_emoji(color=color, number=gear.level)
            gear_text += f"{emojiDictionary(gear.name)}{emoji}"
        if gear_text == " | ":
            gear_text = ""
        hero_string += f"{emojiDictionary(hero.name)}{get_emoji(hero)}{gear_text}\n"

    if not hero_string:
        return None

    return "".join(hero_string)


def spells(player, bot=None):
    spells = player.spells
    if not spells:
        return None
    spellList = ""
    levelList = ""

    def get_emoji(spell: coc.Spell):
        color = "blue"
        if spell.level == spell.get_max_level_for_townhall(townhall=player.town_hall):
            color = "gold"
        return bot.get_number_emoji(color=color, number=spell.level)

    for x in range(len(spells)):
        theSpells = coc.SPELL_ORDER
        # print(str(regTroop))
        spell = spells[x]
        if spell.name in theSpells:
            if (spell.name == "Poison Spell"):
                spellList += "\n" + levelList + "\n"
                levelList = ""
            spellList += f"{emojiDictionary(spell.name)} "
            levelList += str(get_emoji(spell))

            if spell.level <= 10:
                levelList += " "

    spellList += "\n" + levelList + "\n"

    return spellList


def troops(player, bot=None):
    troops = player.troops
    if not troops:
        return None
    troopList = ""
    levelList = ""

    def get_emoji(troop: coc.Troop):
        color = "blue"
        if troop.level == troop.get_max_level_for_townhall(townhall=player.town_hall):
            color = "gold"
        return bot.get_number_emoji(color=color, number=troop.level)

    z = 0
    for x in range(len(troops)):
        troop = troops[x]
        if (troop.is_home_base) and (troop.name not in coc.SIEGE_MACHINE_ORDER) and (troop.name not in SUPER_TROOPS):
            z += 1
            troopList += emojiDictionary(troop.name) + " "
            levelList += str(get_emoji(troop))

            if troop.level <= 11:
                levelList += " "

            if (z != 0 and z % 8 == 0):
                troopList += "\n" + levelList + "\n"
                levelList = ""

    troopList += "\n" + levelList

    return troopList

def clean_name(name: str):
    name = emoji.replace_emoji(name)
    name = re.sub('[*_`~/]', '', name)
    return f"\u200e{name}"

def siegeMachines(player, bot=None):
    sieges = player.siege_machines
    if not sieges:
        return None
    siegeList = ""
    levelList = ""

    def get_emoji(troop: coc.Troop):
        color = "blue"
        if troop.level == troop.get_max_level_for_townhall(townhall=player.town_hall):
            color = "gold"
        return bot.get_number_emoji(color=color, number=troop.level)

    z = 0
    for x in range(len(sieges)):
        siegeL = coc.SIEGE_MACHINE_ORDER
        # print(str(regTroop))
        siege = sieges[x]
        if siege.name in siegeL:
            z += 1
            siegeList += emojiDictionary(siege.name) + " "
            levelList += str(get_emoji(siege))

            if siege.level <= 10:
                levelList += " "

    siegeList += "\n" + levelList

    # print(heroList)
    # print(troopList)
    return siegeList


def heroPets(bot, player: coc.Player):
    if not player.pets:
        return None

    def get_emoji(pet: coc.Pet):
        color = "blue"
        if pet.level == pet.max_level:
            color = "gold"
        return bot.get_number_emoji(color=color, number=pet.level)

    pet_string = ""
    for count, pet in enumerate(player.pets, 1):
        pet_string += f"{emojiDictionary(pet.name)}{get_emoji(pet)}"
        if count % 4 == 0:
            pet_string += "\n"

    return pet_string

def hero_gear(bot, player: MyCustomPlayer):
    if not player.hero_equipment:
        return None

    gear_string = ""
    for count, gear in enumerate([g for g in player.hero_equipment if g.hero is None], 1):
        color = "blue"
        if gear.level == gear.max_level:
            color = "gold"
        emoji = bot.get_number_emoji(color=color, number=gear.level)
        gear_string += f"{emojiDictionary(gear.name)}{emoji}"
        if count % 4 == 0:
            gear_string += "\n"
    return gear_string


def profileSuperTroops(player):
    troops = player.troops
    boostedTroops = ""

    for x in range(len(troops)):
        troop = troops[x]
        if troop.is_active:
            emoji = emojiDictionary(troop.name)
            boostedTroops += f"{emoji} {troop.name}" + "\n"

    if (len(boostedTroops) > 0):
        boostedTroops = f"\n**Super Troops:**\n{boostedTroops}"
    else:
        boostedTroops = ""
    return boostedTroops


def clan_th_comp(clan_members):
    thcount = defaultdict(int)

    for player in clan_members:
        thcount[player.town_hall] += 1

    th_comp_string = ""
    for th_level, th_count in sorted(thcount.items(), reverse=True):
        th_emoji = fetch_emoji(th_level)
        th_comp_string += f"{th_emoji}`{th_count}` "

    return th_comp_string


def clan_super_troop_comp(clan_members):
    super_troop_comp_dict = defaultdict(int)
    for player in clan_members:
        for troop in player.troops:
            if troop.is_active:
                super_troop_comp_dict[troop.name] += 1

    return_string = ""
    for troop, count in super_troop_comp_dict.items():
        super_troop_emoji = fetch_emoji(emoji_name=troop)
        return_string += f"{super_troop_emoji}`x{count} `"

    if return_string == "":
        return_string = "None"

    return return_string


def leagueAndTrophies(player):
    emoji = ""
    league = str(player.league)
    # print(league)

    if (league == "Bronze League III"):
        emoji = "<:BronzeLeagueIII:601611929311510528>"
    elif (league == "Bronze League II"):
        emoji = "<:BronzeLeagueII:601611942850986014>"
    elif (league == "Bronze League I"):
        emoji = "<:BronzeLeagueI:601611950228635648>"
    elif (league == "Silver League III"):
        emoji = "<:SilverLeagueIII:601611958067920906>"
    elif (league == "Silver League II"):
        emoji = "<:SilverLeagueII:601611965550428160>"
    elif (league == "Silver League I"):
        emoji = "<:SilverLeagueI:601611974849331222>"
    elif (league == "Gold League III"):
        emoji = "<:GoldLeagueIII:601611988992262144>"
    elif (league == "Gold League II"):
        emoji = "<:GoldLeagueII:601611996290613249>"
    elif (league == "Gold League I"):
        emoji = "<:GoldLeagueI:601612010492526592>"
    elif (league == "Crystal League III"):
        emoji = "<:CrystalLeagueIII:601612021472952330>"
    elif (league == "Crystal League II"):
        emoji = "<:CrystalLeagueII:601612033976434698>"
    elif (league == "Crystal League I"):
        emoji = "<:CrystalLeagueI:601612045359775746>"
    elif (league == "Master League III"):
        emoji = "<:MasterLeagueIII:601612064913621002>"
    elif (league == "Master League II"):
        emoji = "<:MasterLeagueII:601612075474616399>"
    elif (league == "Master League I"):
        emoji = "<:MasterLeagueI:601612085327036436>"
    elif (league == "Champion League III"):
        emoji = "<:ChampionLeagueIII:601612099226959892>"
    elif (league == "Champion League II"):
        emoji = "<:ChampionLeagueII:601612113345249290>"
    elif (league == "Champion League I"):
        emoji = "<:ChampionLeagueI:601612124447440912>"
    elif (league == "Titan League III"):
        emoji = "<:TitanLeagueIII:601612137491726374>"
    elif (league == "Titan League II"):
        emoji = "<:TitanLeagueII:601612148325744640>"
    elif (league == "Titan League I"):
        emoji = "<:TitanLeagueI:601612159327141888>"
    elif (league == "Legend League"):
        emoji = "<:LegendLeague:601612163169255436>"
    else:
        emoji = "<:Unranked:601618883853680653>"

    return emoji + str(player.trophies)


def league_emoji(player):
    league = str(player.league)

    if league == "Bronze League I":
        return "<:BronzeLeagueI:601611950228635648>"
    elif league == "Bronze League II":
        return "<:BronzeLeagueII:601611942850986014>"
    elif league == "Bronze League III":
        return "<:BronzeLeagueIII:601611929311510528>"
    elif league == "Champion League I":
        return "<:ChampionLeagueI:601612124447440912>"
    elif league == "Champion League II":
        return "<:ChampionLeagueII:601612113345249290>"
    elif league == "Champion League III":
        return "<:ChampionLeagueIII:601612099226959892>"
    elif league == "Crystal League I":
        return "<:CrystalLeagueI:601612045359775746>"
    elif league == "Crystal League II":
        return "<:CrystalLeagueII:601612033976434698>"
    elif league == "Crystal League III":
        return "<:CrystalLeagueIII:601612021472952330>"
    elif league == "Gold League I":
        return "<:GoldLeagueI:601612010492526592>"
    elif league == "Gold League II":
        return "<:GoldLeagueII:601611996290613249>"
    elif league == "Gold League III":
        return "<:GoldLeagueIII:601611988992262144>"
    elif league == "Legend League":
        return "<:LegendLeague:601612163169255436>"
    elif league == "Master League I":
        return "<:MasterLeagueI:601612085327036436>"
    elif league == "Master League II":
        return "<:MasterLeagueII:601612075474616399>"
    elif league == "Master League III":
        return "<:MasterLeagueIII:601612064913621002>"
    elif league == "Silver League I":
        return "<:SilverLeagueI:601611974849331222>"
    elif league == "Silver League II":
        return "<:SilverLeagueII:601611965550428160>"
    elif league == "Silver League III":
        return "<:SilverLeagueIII:601611958067920906>"
    elif league == "Titan League I":
        return "<:TitanLeagueI:601612159327141888>"
    elif league == "Titan League II":
        return "<:TitanLeagueII:601612148325744640>"
    elif league == "Titan League III":
        return "<:TitanLeagueIII:601612137491726374>"
    else:
        return "<:Unranked:601618883853680653>"


def league_to_emoji(league: str):

    if league == "Bronze League I":
        return "<:BronzeLeagueI:601611950228635648>"
    elif league == "Bronze League II":
        return "<:BronzeLeagueII:601611942850986014>"
    elif league == "Bronze League III":
        return "<:BronzeLeagueIII:601611929311510528>"
    elif league == "Champion League I":
        return "<:ChampionLeagueI:601612124447440912>"
    elif league == "Champion League II":
        return "<:ChampionLeagueII:601612113345249290>"
    elif league == "Champion League III":
        return "<:ChampionLeagueIII:601612099226959892>"
    elif league == "Crystal League I":
        return "<:CrystalLeagueI:601612045359775746>"
    elif league == "Crystal League II":
        return "<:CrystalLeagueII:601612033976434698>"
    elif league == "Crystal League III":
        return "<:CrystalLeagueIII:601612021472952330>"
    elif league == "Gold League I":
        return "<:GoldLeagueI:601612010492526592>"
    elif league == "Gold League II":
        return "<:GoldLeagueII:601611996290613249>"
    elif league == "Gold League III":
        return "<:GoldLeagueIII:601611988992262144>"
    elif league == "Legend League":
        return "<:LegendLeague:601612163169255436>"
    elif league == "Master League I":
        return "<:MasterLeagueI:601612085327036436>"
    elif league == "Master League II":
        return "<:MasterLeagueII:601612075474616399>"
    elif league == "Master League III":
        return "<:MasterLeagueIII:601612064913621002>"
    elif league == "Silver League I":
        return "<:SilverLeagueI:601611974849331222>"
    elif league == "Silver League II":
        return "<:SilverLeagueII:601611965550428160>"
    elif league == "Silver League III":
        return "<:SilverLeagueIII:601611958067920906>"
    elif league == "Titan League I":
        return "<:TitanLeagueI:601612159327141888>"
    elif league == "Titan League II":
        return "<:TitanLeagueII:601612148325744640>"
    elif league == "Titan League III":
        return "<:TitanLeagueIII:601612137491726374>"
    elif "Wood" in league:
        return "<:wood_league:1109716152709566524>"
    elif "Clay" in league:
        return "<:clay_league:1109716160561291274>"
    elif "Stone" in league:
        return "<:stone_league:1109716159126843403>"
    elif "Copper" in league:
        return "<:copper_league:1109716157440720966>"
    elif "Brass" in league:
        return "<:brass_league:1109716155876249620>"
    elif "Iron" in league:
        return "<:iron_league:1109716154257264670>"
    elif "Steel" in league:
        return "<:steel_league:1109716168375279616>"
    elif "Titanium" in league:
        return "<:titanium_league:1109716170208198686>"
    elif "Platinum" in league:
        return "<:platinum_league:1109716172330512384>"
    elif "Emerald" in league:
        return "<:emerald_league:1109716179121094707>"
    elif "Ruby" in league:
        return "<:ruby_league:1109716183269265501>"
    elif "Diamond" in league:
        return "<:diamond_league:1109716180983369768>"
    else:
        return "<:Unranked:601618883853680653>"


def cwl_league_emojis(league: str):
    cwl_emojis =  {
        "Bronze League I" : "<:WarBronzeI:1116151829617705000>",
        "Bronze League II" : "<:WarBronzeII:1116151836035006464>",
        "Bronze League III" : "<:WarBronzeIII:1116151838136356895>",
        "Silver League I" : "<:WarSilverI:1116151826870456420>",
        "Silver League II" : "<:WarSilverII:1116151831542907011>",
        "Silver League III" : "<:WarSilverIII:1116151833891704953>",
        "Gold League I" : "<:WarGoldI:1116151792904966154>",
        "Gold League II" : "<:WarGoldII:1116151794721103912>",
        "Gold League III" : "<:WarGoldIII:1116151824471293954>",
        "Crystal League I" : "<:WarCrystalI:1116151785476866109>",
        "Crystal League II" : "<:WarCrystalII:1116151788895211682>",
        "Crystal League III" : "<:WarCrystalIII:1116151790946230312>",
        "Master League I" : "<:WarMasterI:1116151777813868596>",
        "Master League II" : "<:WarMasterII:1116151780074598421>",
        "Master League III" : "<:WarMasterIII:1116151784059191347>",
        "Champion League I" : "<:WarChampionI:1116151613795598407>",
        "Champion League II" : "<:WarChampionII:1116151615506894858>",
        "Champion League III" : "<:WarChampionIII:1116151617922809947>"
    }
    return cwl_emojis.get(league, "<:Unranked:601618883853680653>")



def is_cwl():
    now = datetime.utcnow().replace(tzinfo=utc)
    current_dayofweek = now.weekday()
    if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
            current_dayofweek == 0 and now.hour < 7):
        if current_dayofweek == 0:
            current_dayofweek = 7
        is_raids = True
    else:
        is_raids = False
    return is_raids

def is_games():
    is_games = True
    now = datetime.utcnow().replace(tzinfo=utc)
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    first = datetime(year, month, 22, hour=8, tzinfo=utc)
    end = datetime(year, month, 28, hour=8, tzinfo=utc)
    if (day >= 22 and day <= 28):
        if (day == 22 and hour < 8) or (day == 28 and hour >= 8):
            is_games = False
        else:
            is_games = True
    else:
        is_games = False
    return is_games








