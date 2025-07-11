import coc
import pendulum as pend

from classes.cocpy.capital import CustomRaidLogEntry

"""return {
    'player',
    'war',
    'clan',
    'capital',
    'reminder',
    'reddit',
    'giveaway',
}"""


class EventType:
    def __init__(self, string: str = None):
        self.string = string
        self.owner_class = None
        self.name = None

    def __set_name__(self, owner, name):
        # This method is called when the class is created
        self.owner_class = owner
        self.name = name

    def __str__(self):
        # if no string is passed, use the name of the Event Type itself
        return f'{self.owner_class.topic}:{self.string or self.name}'


class BaseEvent:
    __slots__ = ('types', '_data', 'timestamp', 'event_type')

    def __init__(self, data: dict):
        self._data = data
        self.types: list[str] = self._data.get('types', [self._data.get('type')])
        self.timestamp = pend.from_timestamp(self._data.get('timestamp', 0), tz=pend.UTC)
        self.event_type: str = self._data.get('event_type')


class PlayerEvent(BaseEvent):
    topic = 'player'
    __slots__ = ('old_player', 'new_player')

    def __init__(self, data: dict):
        super().__init__(data)
        self.old_player = coc.Player(data=self._data.get('old_player'), client=coc_client)
        self.new_player = coc.Player(data=self._data.get('new_player'), client=coc_client)


class ClanEvent(BaseEvent):
    topic = 'clan'
    """
    string representation of the available event types
    the classes double as an enum to check against
    """
    join_leave = EventType('members_join_leave')

    __slots__ = ('old_clan', 'new_clan', 'clan')

    def __init__(self, data: dict):
        super().__init__(data)
        self.old_clan = coc.Clan(data=self._data.get('old_clan'), client=coc_client)
        self.new_clan = coc.Clan(data=self._data.get('new_clan'), client=coc_client)
        self.clan = self.new_clan   # alias for new_clan


class ClanJoinLeaveEvent(ClanEvent):
    __slots__ = ('__joined', 'members_joined', '__left', 'members_left')

    def __init__(self, data: dict):
        super().__init__(data)
        self.__joined = self._data.get('joined', [])
        self.members_joined = [coc.ClanMember(data=d, client=coc_client, clan=self.new_clan) for d in self.__joined]
        self.__left = self._data.get('left', [])
        self.members_left = [coc.ClanMember(data=d, client=coc_client, clan=self.new_clan) for d in self.__left]


class CapitalEvent(BaseEvent):
    topic = 'capital'
    """
    string representation of the available event types
    """
    attack_log = EventType('raid_attacks')

    __slots__ = ('old_raid', 'new_raid', 'clan')

    def __init__(self, data: dict):
        super().__init__(data)
        self.old_raid = CustomRaidLogEntry(
            data=self._data['old_raid'],
            client=coc_client,
            clan_tag=self._data['clan_tag'],
        )
        self.new_raid = CustomRaidLogEntry(data=self._data['raid'], client=coc_client, clan_tag=self._data['clan_tag'])
        self.clan = coc.Clan(data=self._data.get('clan', {}), client=coc_client)


class CapitalAttacksEvent(CapitalEvent):
    __slots__ = ('_attackers_tags', 'attackers')

    def __init__(self, data: dict):
        super().__init__(data)
        self._attackers_tags: list[str] = data['attacked']   # list of player tags
        self.attackers: list[tuple[coc.RaidMember, coc.RaidMember]] = [
            (self.old_raid.get_member(tag), self.new_raid.get_member(tag)) for tag in self._attackers_tags
        ]
