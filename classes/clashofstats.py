from enum import Enum
from coc.enums import Role
from coc.miscmodels import Timestamp
import datetime
from datetime import datetime as dt


class COSPlayerHistory:
    def __init__(self, data):
        self._data = data

    @property
    def num_clans(self):
        return len(list(set([clandata.get("tag") for clandata in self._data["log"]])))

    def previous_clans(self, limit=5):
        if self._data.get("error") is not None:
            return "Private History"

        clans = [
            COSClan(full_data=self._data, clan_data=clan_data)
            for clan_data in self._data["log"]
        ]
        clans = [clan for clan in clans if clan.tag != ""][:limit]
        return clans

    def summary(self, limit=5):
        if self._data.get("error") is not None:
            return "Private History"

        return [
            SummaryClans(full_data=self._data, clan_data=clan_data)
            for clan_data in self._data["summary"][:limit]
        ]


class SummaryClans:
    def __init__(self, full_data, clan_data):
        self._data = full_data
        self._clandata = clan_data

    @property
    def duration(self):
        return datetime.timedelta(milliseconds=self._clandata["duration"])

    @property
    def roles(self):
        role_list: list = self._clandata["roles"]
        role_enum = [Role.member, Role.elder, Role.co_leader, Role.leader]
        return [role_enum[count] for count, role in enumerate(role_list) if role != 0]

    @property
    def count(self):
        return self._clandata["count"]

    @property
    def days_per_stay(self):
        return datetime.timedelta(
            milliseconds=int((self._clandata["duration"] / self.count))
        )

    @property
    def tag(self):
        return self._clandata["tag"]

    @property
    def clan_badge(self):
        return self._data["clansMap"][self.tag]["badge"]

    @property
    def clan_name(self):
        try:
            return self._data["clansMap"][self.tag]["name"]
        except:
            return None

    @property
    def share_link(self):
        return f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{self.tag.strip('#')}"


class COSClan:
    def __init__(self, full_data, clan_data):
        self._data = full_data
        self._clandata = clan_data

    @property
    def data(self):
        return self._clandata

    @property
    def stay_type(self):
        if self._clandata["type"] == "STAY":
            return StayType.stay
        elif self._clandata["type"] == "SEEN":
            return StayType.seen
        else:
            return StayType.unknown

    @property
    def tag(self):
        if self.stay_type != StayType.unknown:
            return self._clandata["tag"]
        else:
            return None

    @property
    def role(self) -> Role:
        if self.stay_type != StayType.unknown:
            return Role(value=self._clandata["role"])
        else:
            return None

    @property
    def start_stay(self):
        _ = dt.strptime(self._clandata["start"].split(".")[0], "%Y-%m-%dT%H:%M:%S")
        return Timestamp(data=_.strftime("%Y%m%dT%H%M%S.000Z"))

    @property
    def end_stay(self):
        _ = dt.strptime(self._clandata["end"].split(".")[0], "%Y-%m-%dT%H:%M:%S")
        return Timestamp(data=_.strftime("%Y%m%dT%H%M%S.000Z"))

    @property
    def seen_date(self):
        if self.stay_type != StayType.unknown:
            _ = dt.strptime(self._clandata["date"].split(".")[0], "%Y-%m-%dT%H:%M:%S")
            return Timestamp(data=_.strftime("%Y%m%dT%H%M%S.000Z"))
        else:
            return None

    @property
    def stay_length(self):
        if self.stay_type == StayType.seen:
            return datetime.timedelta(seconds=self._clandata["duration"])
        else:
            return self.end_stay.time.date() - self.start_stay.time.date()

    @property
    def clan_badge(self):
        if self.stay_type != StayType.unknown:
            return self._data["clansMap"][self.tag]["badge"]
        else:
            return None

    @property
    def clan_name(self):
        if self.stay_type != StayType.unknown:
            return self._data["clansMap"][self.tag]["name"]
        else:
            return None

    @property
    def share_link(self):
        if self.stay_type != StayType.unknown:
            return f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{self.tag.strip('#')}"
        else:
            return None


class StayType(Enum):
    stay = "STAY"
    seen = "SEEN"
    unknown = "UNKNOWN"
