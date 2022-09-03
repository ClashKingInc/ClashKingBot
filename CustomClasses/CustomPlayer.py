
import coc
import pytz
from coc import utils
from Dictionaries.emojiDictionary import emojiDictionary
from Dictionaries.thPicDictionary import thDictionary
from datetime import datetime, timedelta
from pymongo import MongoClient
from CustomClasses.emoji_class import EmojiType

sync_client = MongoClient("mongodb://localhost:27017")
new_looper = sync_client.new_looper
player_stats = new_looper.player_stats

utc = pytz.utc
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
        days = [season_start + timedelta(days=i) for i in range(delta.days + 1)]
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

    async def donation_ratio(self):
        return self.donations if self.received == 0 else self.donations / self.received

    def clan_capital_stats(self, week=None):
        if week is None:
            week = self.bot.gen_raid_date()
        if self.results is None:
            return ClanCapitalWeek(None)
        clan_capital_result = self.results.get("capital_gold")
        if clan_capital_result is None:
            return ClanCapitalWeek(None)
        week_result = clan_capital_result.get(week)
        if week_result is None:
            return ClanCapitalWeek(None)
        return ClanCapitalWeek(week_result)

    async def track(self):
        if self.results is None:
            return await self.bot.track_players(players=[self])

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
        return thDictionary(self.level)



