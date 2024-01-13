from utility.constants import SHORT_PLAYER_LINK


class BasicPlayer():
    def __init__(self, data, client):
        self.client = client
        self.name = data.get("name")
        self.tag = data.get("tag")
        self.share_link = SHORT_PLAYER_LINK + self.tag.replace("#", "")
        self.townhall = data.get("townhall")