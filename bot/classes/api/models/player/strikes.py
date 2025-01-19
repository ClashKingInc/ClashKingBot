import coc
import pendulum as pend


class StrikedPlayer(coc.Player):
    def __init__(self, *, data, client, **kwargs):
        super().__init__(data=data, client=client, **kwargs)
        self._results: dict = kwargs.pop('results')
        self.reason: str = self._results.get('reason')
        self.date_created: str = self._results.get('date_created')
        self.added_by: int | None = self._results.get('added_by')
        self.strike_id: str = self._results.get('strike_id')

    @property
    def rollover_date(self) -> None | pend.DateTime:
        if not self._results.get('rollover_date'):
            return None
        return pend.from_timestamp(timestamp=self._results.get('rollover_date'), tz=pend.UTC)
