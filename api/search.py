class ClanSearchResult:
    def __init__(self, data):
        self.tag: str = data['tag']
        self.name: str = data['name']
        self.result_type: str = data['type']
        self.member_count = data['memberCount']
        self.level = data['level']
        self.war_league = data['warLeague']


class Group:
    def __init__(self, data):
        self.group_id: str = data['group_id']
        self.tags: list[str] = data['tags']
        self.type: str = data['type']
