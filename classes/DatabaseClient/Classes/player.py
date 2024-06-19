from .abc import BasePlayer
from .legends import LegendDay, LegendRanking, LegendStats
from utility.clash.other import gen_legend_date, gen_season_date
from coc.utils import get_season_end, get_season_start
from datetime import timedelta


class LegendPlayer(BasePlayer):
    def __init__(self, data, ranking_data, api_player):
        super().__init__(data, api_player)
        self._ranking_data = ranking_data
        self._legend_data = data.get("legends", {})
        self.streak = data.get("legends", {}).get("streak", 0)

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
        year, month = season.split("-")

        season_start = get_season_start(month=int(month) - 1, year=int(year))
        season_end = get_season_end(month=int(month) - 1, year=int(year))
        delta = season_end - season_start
        days = [season_start + timedelta(days=i) for i in range(delta.days)]
        days = [day.strftime("%Y-%m-%d") for day in days]

        legend_days = {}
        for day in days:
            legend_days[day] = self.get_legend_day(date=day)
        return legend_days

    def get_legend_season_stats(self, season=None):
        season_stats = self.get_legend_season(season=season)
        return LegendStats(season_stats)
