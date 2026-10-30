class WarPlan:
    def __init__(self, data):
        self.data = data
        self.name: str = data.get('name')
        self.player_tag: str = data.get('player_tag')
        self.townhall_level: int = data.get('townhall_level')
        self.notes = data.get('notes')
        self.stars = data.get('stars')
        self.targets = data.get('targets')
        self.map_position: int = data.get('map_position')
        self.plan_one: str = data.get('plan', 'No Plan')
        self.plan_two: str = data.get('plan_two', 'No Plan')

    @property
    def plan_text(self):
        text = f'▸ 1. {self.plan_one}'
        if self.plan_two != 'No Plan' and self.plan_two != '':
            text += f'\n▸ 2. {self.plan_two}'
        return text
