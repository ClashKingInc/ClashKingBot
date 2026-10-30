from typing import TYPE_CHECKING

import disnake


if TYPE_CHECKING:
    from classes.bot import CustomClient


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
    def __init__(self, bot: 'CustomClient'):
        self.animated_clash_swords = EmojiType(bot.loaded_emojis.get('animated_clash_swords'))
        self.average = EmojiType(bot.loaded_emojis.get('average'))
        self.back = EmojiType(bot.loaded_emojis.get('back'))
        self.blank = EmojiType(bot.loaded_emojis.get('blank'))
        self.broken_sword = EmojiType(bot.loaded_emojis.get('broken_sword'))
        self.brown_shield = EmojiType(bot.loaded_emojis.get('brown_shield'))
        self.calendar = EmojiType(bot.loaded_emojis.get('calendar'))
        self.capital_gold = EmojiType(bot.loaded_emojis.get('capital_gold'))
        self.capital_trophy = EmojiType(bot.loaded_emojis.get('capital_trophy'))
        self.clan_castle = EmojiType(bot.loaded_emojis.get('clan_castle'))
        self.clan_games = EmojiType(bot.loaded_emojis.get('clan_games'))
        self.clash_sword = EmojiType(bot.loaded_emojis.get('clash_sword'))
        self.clock = EmojiType(bot.loaded_emojis.get('clock'))
        self.cwl_medal = EmojiType(bot.loaded_emojis.get('cwl_medal'))
        self.dark_elixir = EmojiType(bot.loaded_emojis.get('dark_elixir'))
        self.discord = EmojiType(bot.loaded_emojis.get('discord'))
        self.double_up_arrow = EmojiType(bot.loaded_emojis.get('double_up_arrow'))
        self.down_red_arrow = EmojiType(bot.loaded_emojis.get('down_red_arrow'))
        self.earth = EmojiType(bot.loaded_emojis.get('earth'))
        self.elixir = EmojiType(bot.loaded_emojis.get('elixir'))
        self.excel = EmojiType(bot.loaded_emojis.get('excel'))
        self.eye = EmojiType(bot.loaded_emojis.get('eye'))
        self.forward = EmojiType(bot.loaded_emojis.get('forward'))
        self.gear = EmojiType(bot.loaded_emojis.get('gear'))
        self.gold = EmojiType(bot.loaded_emojis.get('gold'))
        self.green_check = EmojiType(bot.loaded_emojis.get('green_check'))
        self.green_circle = EmojiType(bot.loaded_emojis.get('green_circle'))
        self.grey_circle = EmojiType(bot.loaded_emojis.get('grey_circle'))
        self.grey_dash = EmojiType(bot.loaded_emojis.get('grey_dash'))
        self.hand_coins = EmojiType(bot.loaded_emojis.get('hand_coins'))
        self.hashmark = EmojiType(bot.loaded_emojis.get('hashmark'))
        self.heart = EmojiType(bot.loaded_emojis.get('heart'))
        self.no_star = EmojiType(bot.loaded_emojis.get('no_star'))
        self.opt_in = EmojiType(bot.loaded_emojis.get('opt_in'))
        self.opt_out = EmojiType(bot.loaded_emojis.get('opt_out'))
        self.people = EmojiType(bot.loaded_emojis.get('people'))
        self.pet_paw = EmojiType(bot.loaded_emojis.get('pet_paw'))
        self.pin = EmojiType(bot.loaded_emojis.get('pin'))
        self.raid_medal = EmojiType(bot.loaded_emojis.get('raid_medal'))
        self.ratio = EmojiType(bot.loaded_emojis.get('ratio'))
        self.red_circle = EmojiType(bot.loaded_emojis.get('red_circle'))
        self.red_tick = EmojiType(bot.loaded_emojis.get('red_tick'))
        self.red_x = EmojiType(bot.loaded_emojis.get('red_x'))
        self.reddit_icon = EmojiType(bot.loaded_emojis.get('reddit_icon'))
        self.refresh = EmojiType(bot.loaded_emojis.get('refresh'))
        self.search = EmojiType(bot.loaded_emojis.get('search'))
        self.shield = EmojiType(bot.loaded_emojis.get('shield'))
        self.spells = EmojiType(bot.loaded_emojis.get('spells'))
        self.square_sum_box = EmojiType(bot.loaded_emojis.get('square_sum_box'))
        self.square_x_deny = EmojiType(bot.loaded_emojis.get('square_x_deny'))
        self.terminal = EmojiType(bot.loaded_emojis.get('terminal'))
        self.thick_capital_sword = EmojiType(bot.loaded_emojis.get('thick_capital_sword'))
        self.time = EmojiType(bot.loaded_emojis.get('time'))
        self.toggle_off = EmojiType(bot.loaded_emojis.get('toggle_off'))
        self.toggle_on = EmojiType(bot.loaded_emojis.get('toggle_on'))
        self.trashcan = EmojiType(bot.loaded_emojis.get('trashcan'))
        self.troop = EmojiType(bot.loaded_emojis.get('troop'))
        self.trophy = EmojiType(bot.loaded_emojis.get('trophy'))
        self.unranked = EmojiType(bot.loaded_emojis.get('unranked'))
        self.up_green_arrow = EmojiType(bot.loaded_emojis.get('up_green_arrow'))
        self.user_search = EmojiType(bot.loaded_emojis.get('user_search'))
        self.versus_trophy = EmojiType(bot.loaded_emojis.get('versus_trophy'))
        self.war_star = EmojiType(bot.loaded_emojis.get('war_star'))
        self.warning = EmojiType(bot.loaded_emojis.get('warning'))
        self.wood_swords = EmojiType(bot.loaded_emojis.get('wood_swords'))
        self.wrench = EmojiType(bot.loaded_emojis.get('wrench'))
        self.xp = EmojiType(bot.loaded_emojis.get('xp'))
