
import coc
import pytz
from coc import utils
from Assets.emojiDictionary import emojiDictionary
from Assets.thPicDictionary import thDictionary
from datetime import datetime, timedelta
from CustomClasses.emoji_class import EmojiType
from collections import defaultdict
from utils.ClanCapital import gen_raid_weekend_datestrings
from utils.constants import SHORT_PLAYER_LINK, HOME_VILLAGE_HEROES
import emoji
import re
from typing import List
from pytz import utc

SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]


class MyCustomPlayer(coc.Player):
    def __init__(self, **kwargs):
        self.troop_cls = MyCustomTroops
        self.hero_cls = MyCustomHeros
        self.spell_cls = MyCustomSpells
        self.pet_cls = MyCustomPets
        super().__init__(**kwargs)
        self.bot = kwargs.pop("bot")
        self.role_as_string = str(self.role)
        self.league_as_string = str(self.league)
        self.streak = 0
        self.results = kwargs.pop("results")
        self.town_hall_cls = CustomTownHall(self.town_hall)
        self.clear_name = self.get_name()

    def get_name(self):
        name = emoji.replace_emoji(self.name)
        name = re.sub('[*_`~/]', '', name)
        return f"\u200e{name}"

    @property
    def share_link(self) -> str:
        return SHORT_PLAYER_LINK + self.tag.replace("#", "")

    def clan_badge_link(self):
        try:
            clan_badge = self.clan.badge.url
        except:
            clan_badge = "https://cdn.discordapp.com/attachments/880895199696531466/911187298513747998/601618883853680653.png"
        return clan_badge

    def clan_name(self):
        try:
            clan_name = self.clan.name
        except:
            clan_name = "No Clan"
        return clan_name

    def clan_tag(self):
        try:
            clan_tag = self.clan.tag
        except:
            clan_tag = "No Tag"
        return clan_tag

    def is_legends(self):
        return str(self.league) == "Legend League"

    def trophy_start(self):
        leg_day = self.legend_day()
        return None if leg_day is None else self.trophies - leg_day.net_gain

    async def ranking(self):
        ranking_result = await self.bot.leaderboard_db.find_one({"tag": self.tag})
        return LegendRanking(ranking_result)

    def legend_day(self, date=None):
        if date is None:
            date = self.bot.gen_legend_date()
        if self.results is None:
            return LegendDay(None)
        legends = self.results.get("legends")
        if legends is None:
            return LegendDay(legends)
        return LegendDay(legends.get(date))

    def season_of_legends(self, season=None):
        if season is None:
            season = self.bot.gen_season_date()
        year = season[:4]
        month = season[-2:]
        season_start = utils.get_season_start(month=int(month) - 1, year=int(year))
        season_end = utils.get_season_end(month=int(month) - 1, year=int(year))
        delta = season_end - season_start
        days = [season_start + timedelta(days=i) for i in range(delta.days)]
        days = [day.strftime("%Y-%m-%d") for day in days]

        try:
            legends = self.results.get("legends")
        except:
            legends = None
        legend_days = {}
        for day in days:
            if legends is None:
                legend_days[day] = LegendDay(legends)
            else:
                legend_days[day] = LegendDay(legends.get(day))
        return legend_days

    def season_legend_stats(self, season=None):
        if season is None:
            season = self.bot.gen_season_date()
        season_stats = self.season_of_legends(season=season)
        return LegendStats(season_stats)

    def attack_wins(self, season=None):
        if season is None:
            season= self.bot.gen_season_data()
        if self.results is None:
            return 0
        season_wins = self.results.get('attack_wins', {}).get(f"{season}", [0])
        return season_wins
    
    def gold_looted(self, season=None):
        if season is None:
            season = self.bot.gen_season_date()
        if self.results is None:
            return 0
        looted = self.results.get("gold_looted")
        if looted is None:
            return 0
        season_looted = looted.get(f"{season}")
        if season_looted is None:
            return 0
        return sum(season_looted)

    def season_pass(self, season=None):
        if season is None:
            season = self.bot.gen_season_date()
        if self.results is None:
            return 0
        season_pass = self.results.get("season_pass")
        if season_pass is None:
            return 0
        season_pass = season_pass.get(f"{season}")
        if season_pass is None:
            return 0
        return season_pass

    def elixir_looted(self, season=None):
        if season is None:
            season = self.bot.gen_season_date()
        if self.results is None:
            return 0
        season_looted = self.results.get("elixir_looted", {}).get(season, [0])
        return sum(season_looted)

    def dark_elixir_looted(self, season=None):
        if season is None:
            season = self.bot.gen_season_date()
        if self.results is None:
            return 0
        looted = self.results.get("dark_elixir_looted")
        if looted is None:
            return 0
        season_looted = looted.get(f"{season}")
        if season_looted is None:
            return 0
        return sum(season_looted)

    def donation_ratio(self, date=None):
        if date is None:
            date = self.bot.gen_season_date()
        donations = self.donos(date).donated
        received = self.donos(date).received
        if received == 0:
            received = 1
        if int(donations/received) >= 1000:
            return int(donations/received)
        elif int(donations/received) >= 100:
            round(donations / received, 1)
        return round(donations / received, 2)

    def clan_capital_stats(self, week = None, start_week = 0, end_week = 0):
        if week is None and start_week== 0 and end_week == 0:
            week = self.bot.gen_raid_date()

        if week is not None:
            if self.results is None:
                return ClanCapitalWeek(None)
            clan_capital_result = self.results.get("capital_gold")
            if clan_capital_result is None:
                return ClanCapitalWeek(None)
            week_result = clan_capital_result.get(week)
            if week_result is None:
                return ClanCapitalWeek(None)
            return ClanCapitalWeek(week_result)
        else:
            weeks = gen_raid_weekend_datestrings(end_week)
            weeks = weeks[start_week:end_week]
            cc_results = []
            for week in weeks:
                if self.results is None:
                    cc_results.append(ClanCapitalWeek(None))
                    continue
                clan_capital_result = self.results.get("capital_gold")
                if clan_capital_result is None:
                    cc_results.append(ClanCapitalWeek(None))
                    continue
                week_result = clan_capital_result.get(week)
                if week_result is None:
                    cc_results.append(ClanCapitalWeek(None))
                    continue
                cc_results.append(ClanCapitalWeek(week_result))
            return cc_results


    def donos(self, date = None):
        if date is None:
            date = self.bot.gen_season_date()
        if self.results is None:
            if date != self.bot.gen_season_date():
                return Donations(donated=0, received=0)
            else:
                return Donations(donated=self.donations, received=self.received)

        donations = self.results.get("donations")
        if donations is None:
            if date != self.bot.gen_season_date():
                return Donations(donated=0, received=0)
            else:
                return Donations(donated=self.donations, received=self.received)

        season_donos = donations.get(f"{date}")
        if season_donos is None:
            if date != self.bot.gen_season_date():
                return Donations(donated=0, received=0)
            else:
                return Donations(donated=self.donations, received=self.received)

        received = season_donos.get("received", 0)
        given = season_donos.get("donated", 0)
        if date == self.bot.gen_season_date():
            given = max(given, self.donations)
            received = max(received, self.received)

        return Donations(donated=given, received=received)

    @property
    def last_online(self):
        return None if self.results is None else self.results.get("last_online")

    @property
    def level_points(self):
        if self.results is None:
            return 0
        return 0 if self.results.get("points") is None else self.results.get("points")

    def season_last_online(self, season_date = None):
        if season_date is None:
            season_date = self.bot.gen_season_date()
        if self.results is None:
            return []
        l_results = self.results.get("last_online_times")
        if l_results is None:
            return []
        if l_results.get(season_date) is None:
            return []
        return l_results.get(season_date)


    async def hit_rate(self, townhall_level:list = [], fresh_type: list = [False, True], start_timestamp:int = 0, end_timestamp: int = 9999999999,
                       war_types: list= ["random", "cwl", "friendly"], war_statuses = ["lost", "losing", "winning", "won"], war_sizes=[]):
        if townhall_level is None:
            townhall_level = self.town_hall
        if townhall_level == []:
            townhall_level = list(range(1, self.town_hall + 1))

        if war_sizes == []:
            war_sizes = [x for x in range(5, 55, 5)]

        results = self.bot.warhits.find({"tag": self.tag})
        count = await self.bot.warhits.count_documents({"tag": self.tag})

        hit_rate_default = {"num_hits" : 0, "total_stars" : 0, "total_destruction" : 0, "total_triples" : 0, "two_stars" : 0, "one_stars" : 0, "zero_stars" : 0}
        if count == 0:
            return [HitRate(hitrate_dict=hit_rate_default, type="All")]
        prev_ = []
        hit_rates = defaultdict(lambda: defaultdict(int))
        async for result in results:
            townhall = result.get("townhall")
            fresh = result.get("fresh")
            time = result.get("_time")
            type = result.get("war_type")
            status = result.get("war_status")
            war_size = result.get("war_size")
            if f"{self.tag}-{result.get('war_start')}-{result.get('defender_tag')}" in prev_:
                continue
            prev_.append(f"{self.tag}-{result.get('war_start')}-{result.get('defender_tag')}")

            if (townhall in townhall_level) and (fresh in fresh_type) and (time >= start_timestamp) and (time <= end_timestamp) and (type in war_types) and (status in war_statuses):
                if len(war_sizes) == 1 and war_size not in war_sizes:
                    continue
                hr_type = f"{townhall}v{result.get('defender_townhall')}"
                hit_rates["All"]["num_hits"] += 1
                hit_rates[hr_type]["num_hits"] += 1

                hit_rates["All"]["total_stars"] += result.get("stars")
                hit_rates[hr_type]["total_stars"] += result.get("stars")

                hit_rates["All"]["total_destruction"] += result.get("destruction")
                hit_rates[hr_type]["total_destruction"] += result.get("destruction")

                if result.get("stars") == 3:
                    hit_rates["All"]["total_triples"] += 1
                    hit_rates[hr_type]["total_triples"] += 1
                elif result.get("stars") == 2:
                    hit_rates["All"]["two_stars"] += 1
                    hit_rates[hr_type]["two_stars"] += 1
                elif result.get("stars") == 1:
                    hit_rates["All"]["one_stars"] += 1
                    hit_rates[hr_type]["one_stars"] += 1
                elif result.get("stars") == 0:
                    hit_rates["All"]["zero_stars"] += 1
                    hit_rates[hr_type]["zero_stars"] += 1

        list_hr = []
        for type, hitrate in hit_rates.items():
            list_hr.append(HitRate(hitrate_dict=hitrate, type=type))
        if list_hr == []:
            list_hr.append(HitRate(hitrate_dict=hit_rate_default, type="All"))

        return list_hr


    async def defense_rate(self, townhall_level: list = [], fresh_type: list = [False, True], start_timestamp: int = 0,
                       end_timestamp: int = 9999999999,
                       war_types: list = ["random", "cwl", "friendly"],
                       war_statuses=["lost", "losing", "winning", "won"], war_sizes = []):
        if townhall_level is None:
            townhall_level = self.town_hall

        if townhall_level == []:
            townhall_level = list(range(1, self.town_hall + 1))

        if war_sizes == []:
            war_sizes = [x for x in range(5, 55, 5)]

        results = self.bot.warhits.find({"defender_tag": self.tag})
        count = await self.bot.warhits.count_documents({"defender_tag": self.tag})

        hit_rate_default = {"num_hits" : 0, "total_stars" : 0, "total_destruction" : 0, "total_triples" : 0, "two_stars" : 0, "one_stars" : 0, "zero_stars" : 0}
        if count == 0:
            return [DefenseRate(hitrate_dict=hit_rate_default, type="All")]
        prev_ = []
        hit_rates = defaultdict(lambda: defaultdict(int))
        async for result in results:
            townhall = result.get("defender_townhall")
            fresh = result.get("fresh")
            time = result.get("_time")
            type = result.get("war_type")
            status = result.get("war_status")
            war_size = result.get("war_size")
            if f"{self.tag}-{result.get('war_start')}-{result.get('defender_tag')}" in prev_:
                continue
            prev_.append(f"{self.tag}-{result.get('war_start')}-{result.get('defender_tag')}")
            if (townhall in townhall_level) and (fresh in fresh_type) and (time >= start_timestamp) and (
                    time <= end_timestamp) and (type in war_types) and (status in war_statuses):
                if len(war_sizes) == 1 and war_size not in war_sizes:
                    continue
                hr_type = f"{townhall}v{result.get('defender_townhall')}"
                hit_rates["All"]["num_hits"] += 1
                hit_rates[hr_type]["num_hits"] += 1

                hit_rates["All"]["total_stars"] += result.get("stars")
                hit_rates[hr_type]["total_stars"] += result.get("stars")

                hit_rates["All"]["total_destruction"] += result.get("destruction")
                hit_rates[hr_type]["total_destruction"] += result.get("destruction")

                if result.get("stars") == 3:
                    hit_rates["All"]["total_triples"] += 1
                    hit_rates[hr_type]["total_triples"] += 1
                elif result.get("stars") == 2:
                    hit_rates["All"]["two_stars"] += 1
                    hit_rates[hr_type]["two_stars"] += 1
                elif result.get("stars") == 1:
                    hit_rates["All"]["one_stars"] += 1
                    hit_rates[hr_type]["one_stars"] += 1
                elif result.get("stars") == 0:
                    hit_rates["All"]["zero_stars"] += 1
                    hit_rates[hr_type]["zero_stars"] += 1

        list_hr = []
        for type, hitrate in hit_rates.items():
            list_hr.append(DefenseRate(hitrate_dict=hitrate, type=type))
        if list_hr == []:
            list_hr.append(DefenseRate(hitrate_dict=hit_rate_default, type="All"))
        return list_hr


    def clan_games(self, date= None):
        if date is None:
            date = self.bot.gen_games_season()

        if self.results is None:
            return 0
        clan_game = self.results.get("clan_games")
        if clan_game is None:
            return 0
        date = clan_game.get(date)
        if date is None:
            return 0
        points = date.get("points")
        if points is None:
            return 0
        if points >= 5000:
            return 5000
        return points

    async def track(self):
        if self.results is None:
            return await self.bot.track_players(players=[self])

    async def verify(self, api_token):
        verified = await self.bot.coc_client.verify_player_token(player_tag=self.tag, token=api_token)
        return verified

    async def linked(self):
        linked_id = await self.bot.link_client.get_link(self.tag)
        return linked_id

    async def add_link(self, member):
        await self.bot.link_client.add_link(self.tag, member.id)

    @property
    def hero_rushed(self):
        rushed_items = []
        not_max_items = []
        locked_items = []
        all_items = []
        for hero_name in coc.HERO_ORDER:
            hero = self.get_hero(name=hero_name)
            if hero is None:
                hero = self.bot.coc_client.get_hero(name=hero_name, townhall=self.town_hall, level=1)
                if not hero.name in HOME_VILLAGE_HEROES:
                    continue
                th_max = hero.get_max_level_for_townhall(self.town_hall)
                if th_max is None:
                    continue
                if self.town_hall >= hero.required_th_level:
                    locked_items.append(hero)
                all_items.append(hero)
            else:
                if not hero.is_home_base:
                    continue
                if hero.required_th_level == self.town_hall:
                    prev_level_max = None
                else:
                    prev_level_max = hero.get_max_level_for_townhall(self.town_hall - 1)
                if prev_level_max is None:
                    prev_level_max = hero.level

                if hero.level < prev_level_max:  # rushed
                    rushed_items.append(hero)
                elif hero.level < hero.get_max_level_for_townhall(self.town_hall):  # not max
                    not_max_items.append(hero)
                all_items.append(self.bot.coc_client.get_hero(name=hero_name, townhall=self.town_hall, level=1))
        return RushedInfo(player=self, rushed_items=rushed_items, not_max_items=not_max_items, locked_items=locked_items, all_items=all_items)

    @property
    def spell_rushed(self):
        rushed_items = []
        not_max_items = []
        locked_items = []
        all_items = []
        for spell_name in coc.SPELL_ORDER:
            spell = self.get_spell(name=spell_name)
            if spell is None:
                spell = self.bot.coc_client.get_spell(name=spell_name, townhall=self.town_hall, level=1)
                th_max = spell.get_max_level_for_townhall(self.town_hall)
                if th_max is None:
                    continue
                if self.town_hall >= spell.required_th_level:
                    locked_items.append(spell)
                all_items.append(spell)
            else:
                if not spell.is_home_base:
                    continue
                if spell.required_th_level == self.town_hall:
                    prev_level_max = None
                else:
                    prev_level_max = spell.get_max_level_for_townhall(self.town_hall - 1)
                if prev_level_max is None:
                    prev_level_max = spell.level

                if spell.level < prev_level_max:  # rushed
                    rushed_items.append(spell)
                elif spell.level < spell.get_max_level_for_townhall(self.town_hall):  # not max
                    not_max_items.append(spell)
                all_items.append(self.bot.coc_client.get_spell(name=spell_name, townhall=self.town_hall, level=1))
        return RushedInfo(player=self, rushed_items=rushed_items, not_max_items=not_max_items,
                          locked_items=locked_items, all_items=all_items)

    @property
    def troop_rushed(self):
        rushed_items = []
        not_max_items = []
        locked_items = []
        all_items = []
        for troop_name in coc.HOME_TROOP_ORDER:
            troop = self.get_troop(name=troop_name)
            if troop is None:
                troop = self.bot.coc_client.get_troop(name=troop_name, townhall=self.town_hall, level=1)
                th_max = troop.get_max_level_for_townhall(self.town_hall)
                if th_max is None:
                    continue
                if self.town_hall >= troop.required_th_level:
                    locked_items.append(troop)
                all_items.append(troop)
            else:
                if not troop.is_home_base:
                    continue
                if troop.required_th_level == self.town_hall:
                    prev_level_max = None
                else:
                    prev_level_max = troop.get_max_level_for_townhall(self.town_hall - 1)
                if prev_level_max is None:
                    prev_level_max = troop.level

                if troop.level < prev_level_max:  # rushed
                    rushed_items.append(troop)
                elif troop.level < troop.get_max_level_for_townhall(self.town_hall):  # not max
                    not_max_items.append(troop)
                all_items.append(self.bot.coc_client.get_troop(name=troop_name, townhall=self.town_hall, level=1))
        return RushedInfo(player=self, rushed_items=rushed_items, not_max_items=not_max_items, locked_items=locked_items, all_items=all_items)


class RushedInfo():
    def __init__(self, player, rushed_items: List, not_max_items: List, locked_items: List, all_items: List):
        self.player: coc.Player = player
        self.rushed_items = rushed_items
        self.not_max_items = not_max_items
        self.locked_items = locked_items
        self.all_items = all_items
        self.together = self.rushed_items + self.not_max_items + self.locked_items

    @property
    def total_time_left(self):
        time = 0
        for item in self.together:
            og_level = item.level
            while item.level < item.get_max_level_for_townhall(self.player.town_hall):
                time += item.upgrade_time.total_seconds()
                item.level += 1
            item.level = og_level
        return time


    @property
    def total_loot_left(self):
        elixir = 0
        dark_elixir = 0
        builder_elixir = 0
        for item in self.together:
            og_level = item.level
            while item.level < item.get_max_level_for_townhall(self.player.town_hall):
                if (item.name in ["Barbarian King", "Archer Queen", "Royal Champion"] and item.is_home_base) or \
                    (item.name in coc.HOME_TROOP_ORDER and item.is_dark_troop) or (item.name in coc.SPELL_ORDER and item.is_dark_spell):
                    dark_elixir += item.upgrade_cost
                elif (item.name in ["Battle Machine", "Battle Copter"] and item.is_builder_base) or (item.is_builder_base):
                    builder_elixir += item.upgrade_cost
                else:
                    elixir += item.upgrade_cost
                item.level += 1
            item.level = og_level
        return LootObject(elixir=elixir, dark_elixir=dark_elixir, builder_elixir=builder_elixir)

    @property
    def total_levels_left(self):
        levels_left = 0
        for item in self.together:
            og_level = item.level
            while item.level < item.get_max_level_for_townhall(self.player.town_hall):
                levels_left += 1
                item.level += 1
            item.level = og_level
        return levels_left


    @property
    def total_time(self):
        time = 0
        for item in self.all_items:
            og_level = item.level
            while item.level < item.get_max_level_for_townhall(self.player.town_hall):
                time += item.upgrade_time.total_seconds()
                item.level += 1
            item.level = og_level
        return time

    @property
    def total_loot(self):
        elixir = 0
        dark_elixir = 0
        builder_elixir = 0
        for item in self.all_items:
            og_level = item.level
            while item.level < item.get_max_level_for_townhall(self.player.town_hall):
                if (item.name in ["Barbarian King", "Archer Queen", "Royal Champion"] and item.is_home_base) or (
                        item.name not in coc.HERO_ORDER and (item.is_dark_spell or item.is_dark_troop)):
                    dark_elixir += item.upgrade_cost
                elif (item.name in ["Battle Machine", "Battle Copter"] and item.is_builder_base) or (
                item.is_builder_base):
                    builder_elixir += item.upgrade_cost
                else:
                    elixir += item.upgrade_cost
                item.level += 1
            item.level = og_level
        return LootObject(elixir=elixir, dark_elixir=dark_elixir, builder_elixir=builder_elixir)

    @property
    def total_levels(self):
        levels_left = 0
        for item in self.all_items:
            og_level = item.level
            while item.level < item.get_max_level_for_townhall(self.player.town_hall):
                levels_left += 1
                item.level += 1
            item.level = og_level
        return levels_left


class LootObject():
    def __init__(self, elixir= 0, dark_elixir= 0, builder_elixir= 0):
        self.elixir = elixir
        self.dark_elixir = dark_elixir
        self.builder_elixir = builder_elixir


class ClanCapitalWeek():
    def __init__(self, clan_capital_result):
        self.clan_capital_result = clan_capital_result

    @property
    def raid_clan(self):
        if self.clan_capital_result is None:
            return None
        return self.clan_capital_result.get("raided_clan")

    @property
    def donated(self):
        if self.clan_capital_result is None:
            return []
        donations = self.clan_capital_result.get("donate")
        return [] if donations is None else donations

    @property
    def raided(self):
        if self.clan_capital_result is None:
            return []
        raids = self.clan_capital_result.get("raid")
        return [] if raids is None else raids

class LegendRanking():
    def __init__(self, ranking_result):
        self.ranking_result = ranking_result

    @property
    def country_code(self):
        if self.ranking_result is None:
            return None
        return self.ranking_result.get("country_code")

    @property
    def country(self):
        if self.ranking_result is None:
            return None
        return self.ranking_result.get("country_name")

    @property
    def local_ranking(self):
        if self.ranking_result is None:
            return "<:status_offline:910938138984206347>"
        if self.ranking_result.get("local_rank") is None:
            return "<:status_offline:910938138984206347>"
        return self.ranking_result.get("local_rank")

    @property
    def global_ranking(self):
        if self.ranking_result is None:
            return "<:status_offline:910938138984206347>"
        if self.ranking_result.get("global_rank") is None:
            return "<:status_offline:910938138984206347>"
        return self.ranking_result.get("global_rank")

    @property
    def flag(self):
        if self.country is None:
            return "🏳️"
        return f":flag_{self.country_code.lower()}:"

class LegendDay():
    def __init__(self, legend_result):
        self.legend_result = legend_result
        self.net_gain = self.attack_sum - self.defense_sum

    @property
    def attacks(self):
        if self.legend_result is None:
            return []
        if self.legend_result.get("attacks") is None:
            return []
        return self.legend_result.get("attacks")

    @property
    def defenses(self):
        if self.legend_result is None:
            return []
        if self.legend_result.get("defenses") is None:
            return []
        return self.legend_result.get("defenses")

    @property
    def num_attacks(self):
        if self.legend_result is None:
            return NumChoice(0)
        if self.legend_result.get("num_attacks") is None:
            return NumChoice(0)
        return NumChoice(self.legend_result.get("num_attacks"))

    @property
    def num_defenses(self):
        return NumChoice(len(self.defenses))

    @property
    def attack_sum(self):
        return sum(self.attacks)

    @property
    def defense_sum(self):
        return sum(self.defenses)

class LegendStats():
    def __init__(self, season_stats):
        self.season_stats = season_stats
        self.offensive_one_star = self.calculate()[0]
        self.offensive_two_star = self.calculate()[1]
        self.offensive_three_star = self.calculate()[2]

        self.defensive_zero_star = self.calculate()[3]
        self.defensive_one_star = self.calculate()[4]
        self.defensive_two_star = self.calculate()[5]
        self.defensive_three_star = self.calculate()[6]

        self.average_offense = self.calculate()[7]
        self.average_defense = self.calculate()[8]
        self.net = self.average_offense - self.average_defense

    def calculate(self):
        one_stars = 0
        two_stars = 0
        three_stars = 0

        zero_star_def = 0
        one_stars_def = 0
        two_stars_def = 0
        three_stars_def = 0

        sum_hits = 0
        hit_days_used = 0
        sum_defs = 0
        def_days_used = 0

        for date, legend_day in self.season_stats.items():
            legend_day: LegendDay
            if date == self.today():
                break
            if legend_day.num_attacks.integer >= 6:
                sum_hits += legend_day.attack_sum
                hit_days_used += 1
            for hit in legend_day.attacks:
                if hit >= 5 and hit <= 15:
                    one_stars += 1
                elif hit >= 16 and hit <= 32:
                    two_stars += 1
                elif hit == 40:
                    three_stars += 1

            if legend_day.num_defenses.integer >= 6:
                sum_defs += legend_day.defense_sum
                def_days_used += 1
            for hit in legend_day.defenses:
                if 0 <= hit <= 4:
                    zero_star_def += 1
                if 5 <= hit <= 15:
                    one_stars_def += 1
                elif 16 <= hit <= 32:
                    two_stars_def += 1
                elif hit == 40:
                    three_stars_def += 1


        total = one_stars + two_stars + three_stars
        total_def = zero_star_def + one_stars_def + two_stars_def + three_stars_def

        try:
            one_stars_avg = int(round((one_stars / total), 2) * 100)
        except:
            one_stars_avg = 0
        try:
            two_stars_avg = int(round((two_stars / total), 2) * 100)
        except:
            two_stars_avg = 0
        try:
            three_stars_avg = int(round((three_stars / total), 2) * 100)
        except:
            three_stars_avg = 0

        try:
            zero_stars_avg_def = int(round((zero_star_def / total_def), 2) * 100)
        except:
            zero_stars_avg_def = 0
        try:
            one_stars_avg_def = int(round((one_stars_def / total_def), 2) * 100)
        except:
            one_stars_avg_def = 0
        try:
            two_stars_avg_def = int(round((two_stars_def / total_def), 2) * 100)
        except:
            two_stars_avg_def = 0
        try:
            three_stars_avg_def = int(round((three_stars_def / total_def), 2) * 100)
        except:
            three_stars_avg_def = 0

        if hit_days_used == 0:
            average_offense = 0
        else:
            average_offense = int(sum_hits / hit_days_used)

        if def_days_used == 0:
            average_defense = 0
        else:
            average_defense = int(sum_defs / def_days_used)
        average_net = average_offense - average_defense

        return [one_stars_avg, two_stars_avg, three_stars_avg, zero_stars_avg_def, one_stars_avg_def, two_stars_avg_def,
                three_stars_avg_def, average_offense, average_defense]

    def today(self):
        now = datetime.utcnow()
        hour = now.hour
        if hour < 5:
            date = (now - timedelta(1)).date()
        else:
            date = now.date()
        return str(date)

class NumChoice():
    def __init__(self, num):
        self.integer = num

    @property
    def superscript(self):
        if self.integer >= 8:
            return SUPER_SCRIPTS[8]
        return SUPER_SCRIPTS[self.integer]

class MyCustomTroops(coc.Troop):
    @property
    def emoji(self):
        return EmojiType(emojiDictionary(self.name))

class MyCustomHeros(coc.Hero):
    @property
    def emoji(self):
        return EmojiType(emojiDictionary(self.name))

class MyCustomSpells(coc.Spell):
    @property
    def emoji(self):
        return EmojiType(emojiDictionary(self.name))

class MyCustomPets(coc.Pet):
    @property
    def emoji(self):
        return EmojiType(emojiDictionary(self.name))

class CustomTownHall():
    def __init__(self, th_level):
        self.level = th_level
        self.str_level = str(th_level)
    @property
    def emoji(self):
        return EmojiType(emojiDictionary(self.level))

    @property
    def image_url(self):
        if self.level <= 4:
            self.level = 5
        return thDictionary(self.level)


class Donations():
    def __init__(self, donated, received):
        self._donated = donated
        self._received = received

    @property
    def donated(self):
        return self._donated


    @property
    def received(self):
        return self._received


class HitRate():
    def __init__(self, hitrate_dict, type):
        self.hitrate_dict = hitrate_dict
        self.type = type

    #{"num_hits" : 0, "total_stars" : 0, "total_destruction" : 0, "total_triples" : 0, "two_stars" : 0, "one_stars" : 0, "zero_stars" : 0}

    @property
    def num_attacks(self):
        return self.hitrate_dict["num_hits"]

    @property
    def average_stars(self):
        try:
            return self.hitrate_dict["total_stars"] / self.hitrate_dict["num_hits"]
        except:
            return 0.00

    @property
    def total_stars(self):
        return self.hitrate_dict["total_stars"]

    @property
    def total_destruction(self):
        return self.hitrate_dict["total_destruction"]

    @property
    def average_destruction(self):
        try:
            return self.hitrate_dict["total_destruction"] / self.hitrate_dict["num_hits"]
        except:
            return 0.00

    @property
    def total_triples(self):
        return self.hitrate_dict["total_triples"]

    @property
    def average_triples(self):
        try:
            return self.hitrate_dict["total_triples"] / self.hitrate_dict["num_hits"]
        except:
            return 0.00

    @property
    def total_twos(self):
        return self.hitrate_dict["two_stars"]

    @property
    def average_twos(self):
        try:
            return self.hitrate_dict["two_stars"] / self.hitrate_dict["num_hits"]
        except:
            return 0.00

    @property
    def total_ones(self):
        return self.hitrate_dict["one_stars"]

    @property
    def average_ones(self):
        try:
            return self.hitrate_dict["one_stars"] / self.hitrate_dict["num_hits"]
        except:
            return 0.00

    @property
    def total_zeros(self):
        return self.hitrate_dict["zero_stars"]

    @property
    def average_zeros(self):
        try:
            return self.hitrate_dict["zero_stars"] / self.hitrate_dict["num_hits"]
        except:
            return 0.00


class DefenseRate():
    def __init__(self, hitrate_dict, type):
        self.hitrate_dict = hitrate_dict
        self.type = type

    #{"num_hits" : 0, "total_stars" : 0, "total_destruction" : 0, "total_triples" : 0, "two_stars" : 0, "one_stars" : 0, "zero_stars" : 0}

    @property
    def num_attacks(self):
        return self.hitrate_dict["num_hits"]

    @property
    def average_stars(self):
        try:
            return self.hitrate_dict["total_stars"] / self.hitrate_dict["num_hits"]
        except:
            return 0.00

    @property
    def total_stars(self):
        return self.hitrate_dict["total_stars"]

    @property
    def total_destruction(self):
        return self.hitrate_dict["total_destruction"]

    @property
    def average_destruction(self):
        try:
            return 1 - self.hitrate_dict["total_destruction"] / self.hitrate_dict["num_hits"]
        except:
            return 1 - 0.00

    @property
    def total_triples(self):
        return self.hitrate_dict["total_triples"]

    @property
    def average_triples(self):
        try:
            return 1 - self.hitrate_dict["total_triples"] / self.hitrate_dict["num_hits"]
        except:
            return 1 - 0.00

    @property
    def total_twos(self):
        return self.hitrate_dict["two_stars"]

    @property
    def average_twos(self):
        try:
            return 1 - self.hitrate_dict["two_stars"] / self.hitrate_dict["num_hits"]
        except:
            return 1 - 0.00

    @property
    def total_ones(self):
        return self.hitrate_dict["one_stars"]

    @property
    def average_ones(self):
        try:
            return 1 - self.hitrate_dict["one_stars"] / self.hitrate_dict["num_hits"]
        except:
            return 1 - 0.00

    @property
    def total_zeros(self):
        return self.hitrate_dict["zero_stars"]

    @property
    def average_zeros(self):
        try:
            return 1 - self.hitrate_dict["zero_stars"] / self.hitrate_dict["num_hits"]
        except:
            return 1 - 0.00




