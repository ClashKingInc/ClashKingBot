
import re

import coc
import emoji

from utility.constants import SHORT_CLAN_LINK


class BaseClan(coc.Clan):
    def __init__(self, *, data, client, **kwargs):
        super().__init__(data=data, client=client, **kwargs)
        self.extra = kwargs.pop('extra', None)

    @property
    def clear_name(self):
        name = emoji.replace_emoji(self.name)
        name = re.sub('[*_`~/]', '', name)
        return f'\u200e{name}'

    @property
    def share_link(self) -> str:
        return SHORT_CLAN_LINK + self.tag.replace('#', '')

    @property
    def member_tags(self) -> set[str]:
        return set(self.members_dict.keys())
