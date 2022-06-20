import coc
from coc import utils
import motor.motor_asyncio
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://45.33.3.218:27017/admin?readPreference=primary&appname=MongoDB%20Compass&directConnection=true&ssl=false")
legends_stats = client.legends_stats
ongoing_stats = legends_stats.ongoing_stats
from datetime import datetime
import pytz
utc = pytz.utc

class DB_Player():
    def __init__(self, player):
        self.player = player
        self.name = self.names()
        self.tag = self.tags()
        self.league = self.leagues()
        self.clan_name = self.clan_names()
        self.clan_tag = self.clan_tags()
        self.town_hall = self.th_lvls()
        self.link = self.links()
        self.trophies = self.trophiess()
        self.clan_badge_link = self.clan_badge_links()
        self.todays_hits = self.todays_hitss()
        self.today_defs = self.today_defss()
        self.previous_hits = self.previous_hitss()
        self.previous_defs = self.previous_defss()
        self.num_season_hits = self.num_season_hitss()
        self.num_season_defs = self.num_season_defss()
        self.last_update = self.last_updates()
        self.location = self.locations()
        self.location_code = self.location_codes()
        self.current_streak = self.current_streaks()
        self.highest_streak = self.highest_streaks()
        self.num_hits = self.num_hitss()
        self.num_def = self.num_defs()
        self.sum_hits = self.sum_hitss()
        self.sum_defs = self.sum_defss()
        self.todays_net = self.todays_nets()
        self.stats = self.season_hit_stats()
        self.one_star_avg_off = self.stats[0]
        self.two_star_avg_off = self.stats[1]
        self.three_star_avg_off = self.stats[2]
        self.one_star_avg_def = self.stats[3]
        self.two_star_avg_def = self.stats[4]
        self.three_star_avg_def = self.stats[5]
        self.average_off = self.stats[6]
        self.average_def = self.stats[7]
        self.average_net = self.stats[8]
        self.season_hits_len = self.stats[9]
        self.season_defs_len = self.stats[10]
        self.length = self.stats[11]

    ##STRAIGHT DB VALUES
    def names(self):
        return self.player.get("name")

    def tags(self):
        return self.player.get("tag")

    def leagues(self):
        return self.player.get("league")

    def clan_names(self):
        return self.player.get("clan")

    def clan_tags(self):
        return self.player.get("clan_tag")

    def th_lvls(self):
        return self.player.get("th")

    def links(self):
        return self.player.get("link")

    def trophiess(self):
        return self.player.get("trophies")

    def clan_badge_links(self):
        return self.player.get("badge")

    def todays_hitss(self):
        return self.player.get("today_hits")

    def today_defss(self):
        return self.player.get("today_defenses")

    def previous_hitss(self):
        return self.player.get("previous_hits")

    def previous_defss(self):
        return self.player.get("previous_defenses")

    def num_season_hitss(self):
        return int(self.player.get("num_season_hits"))

    def num_season_defss(self):
        return int(self.player.get("num_season_defenses"))

    def last_updates(self):
        return self.player.get("last_update")

    def locations(self):
        return self.player.get("location")

    def location_codes(self):
        return self.player.get("location_code")

    def current_streaks(self):
        return self.player.get("row_triple")

    def highest_streaks(self):
        highest_streak = self.player.get("highest_streak")
        if highest_streak is None:
            highest_streak = 0
        return highest_streak

    # PURE DB EXTENSION METHODS
    def num_hitss(self):
        return self.player.get("num_today_hits")

    def num_defs(self):
        defs = self.player.get("today_defenses")
        return (len(defs))


    def sum_hitss(self):
        h = self.player.get("today_hits")
        return sum(h)

    def sum_defss(self):
        d= self.player.get("today_defenses")
        return sum(d)


    def todays_nets(self):
        sum_hits = self.sum_hits
        sum_defs = self.sum_defs
        return sum_hits - sum_defs

    async def ranks(self):
        day = 0
        rankings = []
        tracked = ongoing_stats.find()
        limit = await ongoing_stats.count_documents(filter={})
        for document in await tracked.to_list(length=limit):
            tag = document.get("tag")
            if day == 0:
                trophy = document.get("trophies")
            else:
                record = day + 1
                eod = document.get("end_of_day")
                if record > len(eod):
                    continue
                trophy = eod[-record]
            rr = []
            rr.append(tag)
            rr.append(trophy)
            rankings.append(rr)

        ranking = sorted(rankings, key=lambda l: l[1], reverse=True)

        async def get_rank(tag, ranking):
            for i, x in enumerate(ranking):
                if tag in x:
                    return i

        ranking = await get_rank(self.tag, ranking)
        return str(ranking + 1)

    # hitratees
    def season_hit_stats(self):
        start = utils.get_season_start().replace(tzinfo=utc).date()
        now = datetime.utcnow().replace(tzinfo=utc).date()
        now_ = datetime.utcnow().replace(tzinfo=utc)
        current_season_progress = now - start
        current_season_progress = current_season_progress.days
        if now_.hour <= 5:
            current_season_progress -= 1
        first_record = 0
        last_record = current_season_progress
        y = self.player.get("end_of_day")

        len_y = len(y)
        if last_record == len_y:
            last_record -= 1
        if last_record > len_y:
            last_record = len(y) - 1

        if first_record >= len_y - 2:
            return [0, 0, 0, 0, 0,
                    0, None, None, None, 0, 0, 0]

        one_stars = 0
        two_stars = 0
        three_stars = 0

        zero_star_def = 0
        one_stars_def = 0
        two_stars_def = 0
        three_stars_def = 0

        hits = self.player.get("previous_hits")
        defs = self.player.get("previous_defenses")
        hits = hits[len(hits) - last_record:len(hits) - first_record]
        defs = defs[len(defs) - last_record:len(defs) - first_record]
        length = len(hits)

        l_hit = 0
        sum_hits = 0
        for day in hits:
            if len(day) >= 6:
                sum_hits += sum(day)
                l_hit += 1
            for hit in day:
                if hit >= 5 and hit <= 15:
                    one_stars += 1
                elif hit >= 16 and hit <= 32:
                    two_stars += 1
                elif hit >= 40:
                    if hit % 40 == 0:
                        three_stars += (hit // 40)

        total = one_stars + two_stars + three_stars
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

        l_defs = 0
        sum_defs = 0
        for day in defs:
            if len(day) >= 6:
                sum_defs += sum(day)
                l_defs+=1
            for hit in day:
                if hit >= 0 and hit <= 4:
                    zero_star_def += 1
                if hit >= 5 and hit <= 15:
                    one_stars_def += 1
                elif hit >= 16 and hit <= 32:
                    two_stars_def += 1
                elif hit >= 40:
                    if hit % 40 == 0:
                        three_stars_def += (hit // 40)

        total_def = zero_star_def + one_stars_def + two_stars_def + three_stars_def
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

        if l_hit == 0:
            average_offense = l_hit
        else:
            average_offense = int(sum_hits/l_hit)

        if l_defs == 0:
            average_defense = l_defs
        else:
            average_defense = int(sum_defs/l_defs)
        average_net = average_offense - average_defense

        return [one_stars_avg, two_stars_avg, three_stars_avg, one_stars_avg_def, two_stars_avg_def,
                three_stars_avg_def, average_offense, average_defense, average_net, len(hits), len(defs), length]


