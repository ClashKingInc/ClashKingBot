import disnake

class EmojiType():
    def __init__(self, emoji_string):
        self.emoji_string = emoji_string

    def __str__(self):
        return self.emoji_string

    @property
    def partial_emoji(self):
        emoji = self.emoji_string.split(":")
        animated = "<a:" in self.emoji_string
        emoji = disnake.PartialEmoji(name=emoji[1][1:], id=int(str(emoji[2])[:-1]), animated=animated)
        return emoji

class Emojis():
    def __init__(self):
        self.clan_castle = EmojiType("<:clan_castle:855688168816377857>")
        self.shield = EmojiType("<:sh:948845842809360424>")
        self.trophy = EmojiType("<:trophyy:849144172698402817>")
        self.capital_gold = EmojiType("<:capitalgold:987861320286216223>")
        self.legends_shield = EmojiType("<:legends:881450752109850635>")
        self.sword = EmojiType("<:cw:948845649229647952>")
        self.previous_days = EmojiType("<:cal:989351376146530304>")
        self.legends_overview = EmojiType("<:list:989351376796680213>")
        self.graph_and_stats = EmojiType("<:graph:989351375349624832>")
        self.history = EmojiType("<:history:989351374087151617>")
        self.quick_check = EmojiType("<:plusminus:989351373608980490>")
        self.gear = EmojiType("<:gear:989351372711399504>")
        self.pin = EmojiType("<:magnify:944914253171810384>")
        self.back = EmojiType("<:back_arrow:989399022156525650>")
        self.forward = EmojiType("<:forward_arrow:989399021602877470>")
        self.print = EmojiType("<:print:989400875766251581>")
        self.refresh = EmojiType("<:refresh:989399023087652864>")
        self.trashcan = EmojiType("<:trashcan:989534332425232464>")
        self.alphabet = EmojiType("<:alphabet:989649421564280872>")
        self.start = EmojiType("<:start:989649420742176818>")
        self.blue_shield = EmojiType("<:blueshield:989649418665996321>")
        self.blue_sword = EmojiType("<:bluesword:989649419878166558>")
        self.blue_trophy = EmojiType("<:bluetrophy:989649417760018483>")
        self.grey_circle = EmojiType("<:status_offline:910938138984206347>")
        self.earth = EmojiType("<a:earth:861321402909327370>")
        self.sword_clash = EmojiType("<a:swords:944894455633297418>")
        self.war_star = EmojiType("<:war_star:1013159341395816618>")
        self.blank = EmojiType("<:blanke:838574915095101470>")
        self.clock = EmojiType("<:clock:1013161445833326653>")
        self.troop = EmojiType("<:troop:861797310224400434>")
        self.reddit_icon = EmojiType("<:reddit:1015107963536539688>")
        self.xp = EmojiType("<:xp:991965062703095938>")
        self.deny_mark = EmojiType("<:deny_mark:892770746034704384>")
        self.raid_medal = EmojiType("<:raidmedal:1032108724552224798>")
        self.clan_games = EmojiType("<:cg:1033805598518677604>")
        self.time = EmojiType("<:time:1033909938281529386>")
        self.no_star = EmojiType("<:no_star:1033914094824198174>")
        self.yes = EmojiType("<:yes:1033915430198333500>")
        self.no = EmojiType("<:no:1033915481335275621>")







