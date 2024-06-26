import disnake

from assets.emojis import SharedEmojis


class EmojiType:
    def __init__(self, emoji_string):
        self.emoji_string = emoji_string

    def __str__(self):
        return self.emoji_string

    @property
    def partial_emoji(self):
        emoji = self.emoji_string.split(':')
        animated = '<a:' in self.emoji_string
        emoji = disnake.PartialEmoji(name=emoji[1][1:], id=int(str(emoji[2])[:-1]), animated=animated)
        return emoji


class Emojis:
    def __init__(self):
        self.win_streak = EmojiType(SharedEmojis.all_emojis.get('win_streak'))
        self.broken_sword = EmojiType(SharedEmojis.all_emojis.get('broken_sword'))
        self.discord = EmojiType(SharedEmojis.all_emojis.get('discord'))
        self.clan_castle = EmojiType(SharedEmojis.all_emojis.get('clan_castle'))
        self.shield = EmojiType(SharedEmojis.all_emojis.get('shield'))
        self.trophy = EmojiType(SharedEmojis.all_emojis.get('trophy'))
        self.capital_gold = EmojiType(SharedEmojis.all_emojis.get('capital_gold'))
        self.legends_shield = EmojiType(SharedEmojis.all_emojis.get('legends_shield'))
        self.sword = EmojiType(SharedEmojis.all_emojis.get('sword'))
        self.previous_days = EmojiType(SharedEmojis.all_emojis.get('previous_days'))
        self.legends_overview = EmojiType(SharedEmojis.all_emojis.get('legends_overview'))
        self.graph_and_stats = EmojiType(SharedEmojis.all_emojis.get('graph_and_stats'))
        self.history = EmojiType(SharedEmojis.all_emojis.get('history'))
        self.quick_check = EmojiType(SharedEmojis.all_emojis.get('quick_check'))
        self.gear = EmojiType(SharedEmojis.all_emojis.get('gear'))
        self.pin = EmojiType(SharedEmojis.all_emojis.get('pin'))
        self.back = EmojiType(SharedEmojis.all_emojis.get('back'))
        self.forward = EmojiType(SharedEmojis.all_emojis.get('forward'))
        self.print = EmojiType(SharedEmojis.all_emojis.get('print'))
        self.refresh = EmojiType(SharedEmojis.all_emojis.get('refresh'))
        self.trashcan = EmojiType(SharedEmojis.all_emojis.get('trashcan'))
        self.alphabet = EmojiType(SharedEmojis.all_emojis.get('alphabet'))
        self.start = EmojiType(SharedEmojis.all_emojis.get('start'))
        self.blue_shield = EmojiType(SharedEmojis.all_emojis.get('blue_shield'))
        self.blue_sword = EmojiType(SharedEmojis.all_emojis.get('blue_sword'))
        self.blue_trophy = EmojiType(SharedEmojis.all_emojis.get('blue_trophy'))
        self.grey_circle = EmojiType(SharedEmojis.all_emojis.get('grey_circle'))
        self.earth = EmojiType(SharedEmojis.all_emojis.get('earth'))
        self.sword_clash = EmojiType(SharedEmojis.all_emojis.get('sword_clash'))
        self.war_star = EmojiType(SharedEmojis.all_emojis.get('war_star'))
        self.blank = EmojiType(SharedEmojis.all_emojis.get('blank'))
        self.clock = EmojiType(SharedEmojis.all_emojis.get('clock'))
        self.troop = EmojiType(SharedEmojis.all_emojis.get('troop'))
        self.reddit_icon = EmojiType(SharedEmojis.all_emojis.get('reddit_icon'))
        self.xp = EmojiType(SharedEmojis.all_emojis.get('xp'))
        self.deny_mark = EmojiType(SharedEmojis.all_emojis.get('deny_mark'))
        self.raid_medal = EmojiType(SharedEmojis.all_emojis.get('raid_medal'))
        self.clan_games = EmojiType(SharedEmojis.all_emojis.get('clan_games'))
        self.time = EmojiType(SharedEmojis.all_emojis.get('time'))
        self.no_star = EmojiType(SharedEmojis.all_emojis.get('no_star'))
        self.yes = EmojiType(SharedEmojis.all_emojis.get('yes'))
        self.no = EmojiType(SharedEmojis.all_emojis.get('no'))
        self.gear = EmojiType(SharedEmojis.all_emojis.get('gear'))
        self.ratio = EmojiType(SharedEmojis.all_emojis.get('ratio'))
        self.switch = EmojiType(SharedEmojis.all_emojis.get('switch'))
        self.menu = EmojiType(SharedEmojis.all_emojis.get('menu'))
        self.elixir = EmojiType(SharedEmojis.all_emojis.get('elixir'))
        self.dark_elixir = EmojiType(SharedEmojis.all_emojis.get('dark_elixir'))
        self.gold = EmojiType(SharedEmojis.all_emojis.get('gold'))
        self.brown_shield = EmojiType(SharedEmojis.all_emojis.get('brown_shield'))
        self.thick_sword = EmojiType(SharedEmojis.all_emojis.get('thick_sword'))
        self.hitrate = EmojiType(SharedEmojis.all_emojis.get('hitrate'))
        self.avg_stars = EmojiType(SharedEmojis.all_emojis.get('avg_stars'))
        self.war_stars = EmojiType(SharedEmojis.all_emojis.get('war_stars'))
        self.versus_trophy = EmojiType(SharedEmojis.all_emojis.get('versus_trophy'))
        self.up_green_arrow = EmojiType(SharedEmojis.all_emojis.get('up_green_arrow'))
        self.down_red_arrow = EmojiType(SharedEmojis.all_emojis.get('down_red_arrow'))
        self.capital_trophy = EmojiType(SharedEmojis.all_emojis.get('capital_trophy'))
        self.cwl_medal = EmojiType(SharedEmojis.all_emojis.get('cwl_medal'))
        self.person = EmojiType(SharedEmojis.all_emojis.get('person'))
        self.excel = EmojiType(SharedEmojis.all_emojis.get('excel'))
        self.magnify_glass = EmojiType(SharedEmojis.all_emojis.get('magnify_glass'))
        self.right_green_arrow = EmojiType(SharedEmojis.all_emojis.get('right_green_arrow'))
        self.calendar = EmojiType(SharedEmojis.all_emojis.get('calendar'))
        self.red_status = EmojiType(SharedEmojis.all_emojis.get('red_status'))
        self.green_status = EmojiType(SharedEmojis.all_emojis.get('green_status'))
        self.toggle_on = EmojiType(SharedEmojis.all_emojis.get('toggle_on'))
        self.toggle_off = EmojiType(SharedEmojis.all_emojis.get('toggle_off'))
        self.unranked = EmojiType(SharedEmojis.all_emojis.get('unranked'))
        self.hashmark = EmojiType(SharedEmojis.all_emojis.get('hashmark'))
        self.red_tick = EmojiType(SharedEmojis.all_emojis.get('red_tick'))
        self.green_tick = EmojiType(SharedEmojis.all_emojis.get('green_tick'))
        self.opt_in = EmojiType(SharedEmojis.all_emojis.get('opt_in'))
        self.opt_out = EmojiType(SharedEmojis.all_emojis.get('opt_out'))
        self.globe = EmojiType(SharedEmojis.all_emojis.get('globe'))
        self.wood_swords = EmojiType(SharedEmojis.all_emojis.get('wood_swords'))
        self.red_pin = EmojiType(SharedEmojis.all_emojis.get('red_pin'))
        self.wbb_red = EmojiType(SharedEmojis.all_emojis.get('wbb_red'))
        self.spells = EmojiType(SharedEmojis.all_emojis.get('spells'))
        self.heart = EmojiType(SharedEmojis.all_emojis.get('heart'))
        self.pet_paw = EmojiType(SharedEmojis.all_emojis.get('pet_paw'))
