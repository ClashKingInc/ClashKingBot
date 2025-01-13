import coc


class BannedPlayer(coc.Player):
    def __init__(self, *, data, client, **kwargs):
        super().__init__(data=data, client=client, **kwargs)
        self._results: dict = kwargs.pop('results')
        self.notes: str = self._results.get('Notes')
        self.date_created: str = self._results.get('DateCreated')
        self.added_by: int = self._results.get('added_by')
