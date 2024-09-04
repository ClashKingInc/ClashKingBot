from coc.utils import get_season_end, get_season_start

from utility.clash.other import gen_legend_date, gen_season_date
from .base import BasePlayer
from ..DatabaseClient.Classes.abc import NumChoice


class LegendPlayer(BasePlayer):
    def __init__(self, data, ranking_data, api_player):
        super().__init__(data, api_player)
        self._ranking_data = ranking_data
        self._legend_data = data.get('legends', {})
        self.streak = data.get('legends', {}).get('streak', 0)

    @property
    def trophy_start(self):
        todays_legend_day = self.get_legend_day()
        return self.api_player.trophies - todays_legend_day.net_gain

    @property
    def ranking(self):
        return LegendRanking(ranking_result=self._ranking_data)

    def get_legend_day(self, date=None):
        date = date or gen_legend_date()
        return LegendDay(self._legend_data.get(date, {}))

    def get_legend_season(self, season=None):
        season = season or gen_season_date()
        year, month = season.split('-')

        season_start = get_season_start(month=int(month) - 1, year=int(year))
        season_end = get_season_end(month=int(month) - 1, year=int(year))
        delta = season_end - season_start
        days = [season_start + timedelta(days=i) for i in range(delta.days)]
        days = [day.strftime('%Y-%m-%d') for day in days]

        legend_days = {}
        for day in days:
            legend_days[day] = self.get_legend_day(date=day)
        return legend_days

    def get_legend_season_stats(self, season=None):
        season_stats = self.get_legend_season(season=season)
        return LegendStats(season_stats)


from datetime import datetime, timedelta
from typing import List


class LegendRanking:
    def __init__(self, ranking_result):
        self._ranking_result = ranking_result

    @property
    def country_code(self):
        if self._ranking_result is None:
            return None
        return self._ranking_result.get('country_code')

    @property
    def country(self):
        if self._ranking_result is None:
            return None
        return self._ranking_result.get('country_name')

    @property
    def local_ranking(self):
        if self._ranking_result is None:
            return '<:status_offline:910938138984206347>'
        if self._ranking_result.get('local_rank') is None:
            return '<:status_offline:910938138984206347>'
        return self._ranking_result.get('local_rank')

    @property
    def global_ranking(self):
        if self._ranking_result is None:
            return '<:status_offline:1247040997045829712>'
        if self._ranking_result.get('global_rank') is None:
            return '<:status_offline:1247040997045829712>'
        return self._ranking_result.get('global_rank')

    @property
    def flag(self):
        if self.country is None:
            return '🏳️'
        return f':flag_{self.country_code.lower()}:'


class LegendDay:
    def __init__(self, legend_result):
        self.legend_result = legend_result
        self.net_gain = self.attack_sum - self.defense_sum

    @property
    def attacks(self):
        if self.legend_result.get('new_attacks') is None:
            return []
        new_data: List = self.legend_result.get('new_attacks', [])
        return [LegendAttackInfo(data=data) for data in new_data]

    @property
    def defenses(self):
        if self.legend_result.get('new_defenses') is None:
            return []
        new_data: List = self.legend_result.get('new_defenses', [])
        return [LegendAttackInfo(data=data) for data in new_data]

    @property
    def num_attacks(self):
        if self.legend_result is None:
            return NumChoice(0)
        if self.legend_result.get('num_attacks') is None:
            return NumChoice(0)
        return NumChoice(self.legend_result.get('num_attacks'))

    @property
    def num_defenses(self):
        return NumChoice(len(self.defenses))

    @property
    def finished_trophies(self):
        all_hits = self.attacks + self.defenses
        all_hits = [hit for hit in all_hits if hit.timestamp is not None]
        all_hits.sort(key=lambda x: x.timestamp, reverse=True)
        if all_hits:
            return all_hits[0].trophies
        return None

    @property
    def attack_sum(self):
        return sum([attack.change for attack in self.attacks])

    @property
    def defense_sum(self):
        return sum([defense.change for defense in self.defenses])


class LegendAttackInfo:
    def __init__(self, data):
        self.data = data
        self.timestamp: int = data.get('time')
        self.change: int = data.get('change')
        self.trophies: int = data.get('trophies')

    @property
    def hero_gear(self):
        gears = []
        for gear in self.data.get('hero_gear', []):
            if isinstance(gear, str):
                gears.append({'name': gear, 'level': 1})
            else:
                gears.append(gear)
        return [LegendHeroGear(data=gear) for gear in gears]


class LegendHeroGear:
    def __init__(self, data: dict):
        self.name = data.get('name')
        self.level = data.get('level')

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name


class LegendStats:
    def __init__(self, season_stats):
        self.season_stats = season_stats
        self.offensive_one_star = self._calculate()[0]
        self.offensive_two_star = self._calculate()[1]
        self.offensive_three_star = self._calculate()[2]

        self.defensive_zero_star = self._calculate()[3]
        self.defensive_one_star = self._calculate()[4]
        self.defensive_two_star = self._calculate()[5]
        self.defensive_three_star = self._calculate()[6]

        self.average_offense = self._calculate()[7]
        self.average_defense = self._calculate()[8]
        self.net = self.average_offense - self.average_defense

    def _calculate(self):
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
            if date == self._today():
                break

            if legend_day.num_attacks.integer >= 6:
                sum_hits += legend_day.attack_sum
                hit_days_used += 1

            for hit in legend_day.attacks:
                if 5 <= hit.change <= 15:
                    one_stars += 1
                elif 16 <= hit.change <= 32:
                    two_stars += 1
                elif hit.change == 40:
                    three_stars += 1

            if legend_day.num_defenses.integer >= 6:
                sum_defs += legend_day.defense_sum
                def_days_used += 1
            for hit in legend_day.defenses:
                if 0 <= hit.change <= 4:
                    zero_star_def += 1
                if 5 <= hit.change <= 15:
                    one_stars_def += 1
                elif 16 <= hit.change <= 32:
                    two_stars_def += 1
                elif hit.change == 40:
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

        return [
            one_stars_avg,
            two_stars_avg,
            three_stars_avg,
            zero_stars_avg_def,
            one_stars_avg_def,
            two_stars_avg_def,
            three_stars_avg_def,
            average_offense,
            average_defense,
        ]

    def _today(self):
        now = datetime.utcnow()
        hour = now.hour
        if hour < 5:
            date = (now - timedelta(1)).date()
        else:
            date = now.date()
        return str(date)
