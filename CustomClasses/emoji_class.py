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
        self.pin = EmojiType("<:pin:989362628361072650>")
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
        self.deny_mark = EmojiType("<:not_clan:1045915201037422683>")
        self.raid_medal = EmojiType("<:raidmedal:1032108724552224798>")
        self.clan_games = EmojiType("<:cg:1033805598518677604>")
        self.time = EmojiType("<:time:1033909938281529386>")
        self.no_star = EmojiType("<:no_star:1033914094824198174>")
        self.yes = EmojiType("<:yes:1033915430198333500>")
        self.no = EmojiType("<:no:1033915481335275621>")
        self.gear = EmojiType("<:gear:1035416941646594118>")
        self.ratio = EmojiType("<:winrate:932212939908337705>")
        self.switch = EmojiType("<:switch:1037530447665704980>")
        self.menu = EmojiType("<:menu:1037531977324167219>")
        self.elixir = EmojiType("<:elixir:1043616874446999602>")
        self.dark_elixir = EmojiType("<:delixir:1043616963815022612>")
        self.gold = EmojiType("<:gold:1043616714874687578>")
        self.brown_shield = EmojiType("<:shield:1045920451165159525>")
        self.thick_sword = EmojiType("<:thick_sword:1045921321990754305>")
        self.hitrate = EmojiType("<:hitrate:1046114606151630918>")
        self.avg_stars = EmojiType("<:avg_stars:1046114668139270234>")
        self.war_stars = EmojiType("<:war_stars:1046114735059378236>")
        self.versus_trophy = EmojiType("<:versustrophy:1046117900907450399>")
        self.up_green_arrow = EmojiType("<:warwon:932212939899949176>")
        self.down_red_arrow = EmojiType("<:warlost:932212154164183081>")
        self.capital_trophy = EmojiType("<:capital_trophy:1054056202864177232>")







