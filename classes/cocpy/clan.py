import re

import coc
import emoji

from utility.constants import SHORT_CLAN_LINK, SHORT_PLAYER_LINK


class CustomClanMember(coc.ClanMember):
    def __init__(self, *, data, clan, client, **kwargs):
        super().__init__(data=data, client=client, clan=clan, **kwargs)

    @property
    def donation_ratio(self) -> float:
        if self.received == 0:
            return self.donations  # we can't divide by 0!
        return self.donations / self.received

    @property
    def share_link(self) -> str:
        return SHORT_PLAYER_LINK + self.tag.replace('#', '')


class CustomClan(coc.Clan):
    def __init__(self, *, data, client, **kwargs):
        super().__init__(data=data, client=client, **kwargs)
        self.member_cls = CustomClanMember

        print(f'After super(): {self.member_cls}')
        # ✅ Rebuild members_dict immediately after initialization
        self._iter_members = (
            self.member_cls(data=mdata, client=self._client, clan=self) for mdata in data.get('memberList', [])
        )

        # ✅ Force clear and reset the cached properties
        self.__dict__.pop('_cs_members_dict', None)
        self.__dict__.pop('_cs_members', None)

    @property
    def clear_name(self):
        name = emoji.replace_emoji(self.name)
        name = re.sub('[*_`~/]', '', name)
        return f'\u200e{name}'

    @property
    def share_link(self) -> str:
        return SHORT_CLAN_LINK + self.tag.replace('#', '')

    @property
    def member_tags(self) -> list[str]:
        return list(self.members_dict.keys())

    @property
    def total_donations(self) -> int:
        return sum([m.donations for m in self.members])
