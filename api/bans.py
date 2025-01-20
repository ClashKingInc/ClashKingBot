import pendulum as pend


class BanResponse:
    def __init__(self, data: dict):
        self.status: str = data['status']
        self.player_tag: str = data['player_tag']
        self.server_id: int = data['server_id']


class BanListEdit:
    def __init__(self, data: dict):
        self.user: int = data['user']
        self.reason: str = data['previous']['reason']
        self.rollover_days: int | None = data['previous']['rollover_days']


class BanListItem:
    def __init__(self, data: dict):
        self.name: str | None = data.get('name')
        self.tag: str = data['VillageTag']
        self._date_created: str = data['DateCreated']
        self.date_created = pend.parse(self._date_created)
        self.added_by: int | None = data.get('added_by')
        self.server_id: int = data['server']
        self._edits: list = data.get('edited_by', [])
        self.edits: list[BanListEdit] = []
        self.rollover_date: None = data.get('rollover_date')
        self.notes: str = data['Notes']

        if self._edits:
            move_user = self.added_by
            for edit in self._edits:
                """
                we do this because the first given previous edit was actually authored by the original author, and
                there is a sort of staggered effect here to the edit history
                """
                hold_user = edit['user']
                edit['user'] = move_user
                move_user = hold_user
                self.edits.append(BanListEdit(edit))

        self.last_edited_by: int | None = self.edits[-1].user if self.edits else self.added_by

    def __repr__(self):
        return f'{self.__class__.__name__}(name={self.name}, tag={self.tag})'
