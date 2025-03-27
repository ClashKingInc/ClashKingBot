


class ClanSearchResult:
    def __init__(self, data):
        self.tag: str = data["tag"]
        self.name: str = data["name"]
        self.result_type: str = data["type"]
        self.member_count = data["memberCount"]
        self.level = data["level"]
        self.war_league = data["warLeague"]