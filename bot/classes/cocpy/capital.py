import coc
import math

from functools import cached_property


class CustomRaidLogEntry(coc.RaidLogEntry):
    def __init__(self, *, data, client, **kwargs):
        super().__init__(data=data, client=client, **kwargs)


    @cached_property
    def calculated_offensive_raid_medals(self):
        district_dict = {1: 135, 2: 225, 3: 350, 4: 405, 5: 460}
        capital_dict = {
            2: 180,
            3: 360,
            4: 585,
            5: 810,
            6: 1115,
            7: 1240,
            8: 1260,
            9: 1375,
            10: 1450,
        }
        """
        TODO: this should be moved to constants eventually
        """

        total_medals = 0
        attacks_done = 0
        for raid_clan in self.attack_log:
            attacks_done += raid_clan.attack_count
            for district in raid_clan.districts:
                if int(district.destruction) == 100:
                    if district.id == 70000000:
                        total_medals += capital_dict[int(district.hall_level)]
                    else:
                        total_medals += district_dict[int(district.hall_level)]

        if total_medals != 0:
            total_medals = math.ceil(total_medals / attacks_done) * 6
        return total_medals
