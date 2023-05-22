import disnake
import calendar
import coc
from numerize import numerize
from utils.clash import heros, heroPets
from disnake.ext import commands
from typing import TYPE_CHECKING, List
from utils.search import search_results
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient
from utils.discord_utils import interaction_handler
from Exceptions.CustomExceptions import *
if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    cog_class = BoardCog
else:
    cog_class = commands.Cog

class PlayerEmbeds(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def create_search(self, clan, townhall, trophies, war_stars, clan_capital_donos, league, attacks):
        queries = {}
        queries['$and'] = []
        if clan == "No Clan":
            queries['$and'].append({'data.clan.tag': {"$eq": None}})
        elif clan == "In Clan":
            queries['$and'].append({'data.clan.tag': {"$ne": None}})

        if league == "No League":
            queries['$and'].append({'data.league.name': {"$eq": None}})
        elif league == "Has League":
            queries['$and'].append({'data.league.name': {"$ne": None}})

        if townhall is not None:
            queries['$and'].append({"data.townHallLevel" : int(townhall)})

        if trophies is not None:
            queries['$and'].append({"data.trophies" : {"$gte": int(trophies)}})

        if attacks is not None:
            queries['$and'].append({"data.attackWins" : {"$gte": int(attacks)}})

        if war_stars is not None:
            queries['$and'].append({"data.warStars" : {"$gte": int(war_stars)}})

        if clan_capital_donos is not None:
            queries['$and'].append({"data.clanCapitalContributions" : {"$gte": int(clan_capital_donos)}})

        if queries["$and"] == []:
            queries = {}

        player = []
        tries = 0
        while player == []:
            pipeline = [{"$match": queries}, {"$sample": {"size": 3}}]
            player_list = await self.bot.player_cache.aggregate(pipeline).to_list(length=3)
            if player_list == [] or tries == 3:
                return disnake.Embed(description="**No Results Found**", color=disnake.Color.red()), []
            players = await self.bot.get_players(tags=[player.get("tag") for player in player_list], custom=True, use_cache=False)
            player = [player for player in players if player.results is not None]
            if player == []:
                tries += 1
        player = player[:1][0]
        #players = [MyCustomPlayer(data=data.get("data"), client=self.bot.coc_client, bot=self.bot, results=None) for data in player_list]
        player_links = await self.bot.link_client.get_links(*[player.tag])
        player_link_dict = dict(player_links)

        hero = heros(bot=self.bot, player=player)
        pets = heroPets(bot=self.bot, player=player)
        if hero is None:
            hero = ""
        else:
            hero = f"**Heroes:**\n{hero}\n"

        if pets is None:
            pets = ""
        else:
            pets = f"**Pets:**\n{pets}\n"

        if player.last_online is not None:
            lo = f"<t:{player.last_online}:R>"
        else:
            lo = "`N/A`"

        discord = self.bot.emoji.green_status if player_link_dict.get(player.tag) is not None else self.bot.emoji.red_status

        embed = disnake.Embed(title=f"**Invite {player.name} to your clan:**",
                              description=f"{player.town_hall_cls.emoji}{player.name} - TH{player.town_hall}\n" +
                                          f"{self.bot.emoji.hashmark}Tag: {player.tag}\n" +
                                          f"{self.bot.emoji.clan_castle}Clan: {player.clan_name()}\n" +
                                          f"{self.bot.emoji.trophy}Trophies: {player.trophies} | Attacks: {player.attack_wins}\n"
                                          f"{self.bot.emoji.war_star}War Stars: {player.war_stars}\n"
                                          f"{self.bot.emoji.capital_gold}Capital Donos: {player.clan_capital_contributions}\n"
                                          f"{self.bot.emoji.clock}{lo} {self.bot.emoji.discord}{discord}\n"
                                          f"{hero}{pets}",
                              color=disnake.Color.green())
        if str(player.league) != "Unranked":
            embed.set_thumbnail(url=player.league.icon.url)
        else:
            embed.set_thumbnail(url=self.bot.emoji.unranked.partial_emoji.url)

        stat_buttons = [
            disnake.ui.Button(label=f"Open In-Game",
                              url=player.share_link),
            disnake.ui.Button(label=f"Clash of Stats",
                              url=f"https://www.clashofstats.com/players/{player.tag.strip('#')}/summary"),
            disnake.ui.Button(label=f"Next", emoji=self.bot.emoji.right_green_arrow.partial_emoji, custom_id="NextSearch")]
        buttons = disnake.ui.ActionRow()
        for button in stat_buttons:
            buttons.append_item(button)

        return embed, [buttons]


    def create_upgrade_embed(self, player: coc.Player):
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
            troop_emoji = self.bot.fetch_emoji(name=troop.name)
            prev_level_max = troop.get_max_level_for_townhall(player.town_hall - 1)
            if prev_level_max is None:
                prev_level_max = troop.level

            th_max = troop.get_max_level_for_townhall(player.town_hall)
            troop_levels += th_max
            troop_levels_missing += (th_max - troop.level)
            th_max = f"{th_max}".ljust(2)
            level = f"{troop.level}".rjust(2)
            print(troop.name)
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
        spell_levels = 0
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
        '''
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
        '''

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
            embed2 = disnake.Embed(description=f"**Builder Base Troops**\n{bb_troops}\n", colour=disnake.Color.green())

        if full_text == "":
            full_text = "No Heros, Pets, Spells, or Troops left to upgrade\n"

        if hero_levels_missing == 0:
            hero_levels_missing = "0.00%"
        else:
            hero_levels_missing = f"{round((hero_levels_missing / (hero_levels + hero_levels_missing)) * 100, 2)}%"

        if troop_levels_missing == 0:
            troop_levels_missing = "0.00%"
        else:
            troop_levels_missing = f"{round((troop_levels_missing / (troop_levels)) * 100, 2)}%"

        if spell_levels_missing == 0:
            spell_levels_missing = "0.00%"
        else:
            spell_levels_missing = f"{round((spell_levels_missing / (spell_levels)) * 100, 2)}%"

        # print(full_text)
        embed = disnake.Embed(title=f"{player.name} | TH{player.town_hall}", description=full_text,
                              colour=disnake.Color.green())
        if embed2 is not False:
            embeds = [embed, embed2]
        else:
            embeds = [embed]
        embeds[-1].set_footer(text="✗ = rushed for th level")
        embeds[-1].description += f"Hero Lvl Left: {hero_levels_missing}\n" \
                                  f"Troop Lvl Left: {troop_levels_missing}\n" \
                                  f"Spell Lvl Left: {spell_levels_missing}\n"
        return embeds