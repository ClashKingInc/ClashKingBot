from typing import Union, List
import emoji
import re
from utils.constants import SHORT_PLAYER_LINK
from datetime import datetime
from Commands.graph import comparison_bar_graph

class Response():
    def __init__(self, data: dict):
        self.__data = data
        self.average_townhall: float = data.get("totals").get("average_townhall")
        self.sort_order: str = data.get("metadata").get("sort_order")
        self.sort_field: str = data.get("metadata").get("sort_field")
        self.season:str = data.get("metadata").get("season")
        self.clan_length: int = len(data.get("clan_totals", []))

    @property
    def comparison_graph(self):
        return comparison_bar_graph(full_totals=self.__data.get("totals"), clan_totals=self.__data.get("clan_totals"))

class DonationResponse(Response):
    def __init__(self, data: dict):
        super().__init__(data)
        self.total_donations: int = data.get("totals").get("donations")
        self.total_received: int = data.get("totals").get("donationsReceived")
        self.players: List[MemberDonation] = [MemberDonation(d) for d in data.get("items")]

class ActivityResponse(Response):
    def __init__(self, data: dict):
        super().__init__(data)
        self.total_activity: int = data.get("totals").get("activity")
        self.median_activity: float = data.get("totals").get("median_activity")
        self.players: List[MemberActivity] = [MemberActivity(d) for d in data.get("items")]

class ClanGamesResponse(Response):
    def __init__(self, data: dict):
        super().__init__(data)
        self.total_points: int = data.get("totals").get("points")
        self.average_points: float = data.get("totals").get("average_points")
        self.players: List[MemberClanGames] = [MemberClanGames(d) for d in data.get("items")]

class Member():
    def __init__(self, data: dict):
        self.name: str = data.get("name")
        self.tag: str = data.get("tag")
        self.townhall: Union[int, None] = data.get("townhall")
        self.rank:int  = data.get("rank")
        self.share_link: str = f"{SHORT_PLAYER_LINK}{self.tag.strip('#')}"
        self.clan_tag: str = data.get("clan_tag")

    @property
    def clear_name(self):
        name = emoji.replace_emoji(self.name)
        name = re.sub('[*_`~/]', '', name)
        return f"\u200e{name}"

class MemberClanGames(Member):
    def __init__(self, data: dict):
        super().__init__(data)
        self.points: int = data.get("points")
        self.time_taken: int = data.get("time_taken")

    @property
    def time_taken_text(self):
        if self.time_taken != 0:
            seconds = self.time_taken
            intervals = (
                ('w', 604800),  # 60 * 60 * 24 * 7
                ('d', 86400),  # 60 * 60 * 24
                ('h', 3600),  # 60 * 60
                ('m', 60),
                ('s', 1),
            )
            result = []
            for name, count in intervals:
                value = seconds // count
                if value:
                    seconds -= value * count
                    if value == 1:
                        name = name.rstrip('s')
                    result.append("{}{}".format(value, name))
            return ' '.join(result[:2])
        return "N/A"

class MemberActivity(Member):
    def __init__(self, data: dict):
        super().__init__(data)
        self.activity: int = data.get("activity")
        self.last_online: int = data.get("last_online")

    @property
    def last_online_timestamp(self):
        if self.last_online != 0:
            return f"<t:{self.last_online}:R>"
        return "N/A"

    @property
    def last_online_text(self):
        if self.last_online != 0:
            now = int(datetime.now().timestamp())
            seconds = now - self.last_online
            intervals = (
                ('w', 604800),  # 60 * 60 * 24 * 7
                ('d', 86400),  # 60 * 60 * 24
                ('h', 3600),  # 60 * 60
                ('m', 60),
                ('s', 1),
            )
            result = []
            for name, count in intervals:
                value = seconds // count
                if value:
                    seconds -= value * count
                    if value == 1:
                        name = name.rstrip('s')
                    result.append("{}{}".format(value, name))
            return ' '.join(result[:2])
        return "N/A"


class MemberDonation(Member):
    def __init__(self, data: dict):
        super().__init__(data)
        self.donations: int = data.get("donations")
        self.donations_received: int = data.get("donationsReceived")





