import lightbulb
import requests

from classes.config import Config

APPLICATION_EMOJI_CACHE = {}


import hikari


class EmojiType:
    def __init__(self, emoji_string):
        self.emoji_string = emoji_string
        self.str = emoji_string

    def __str__(self):
        return self.emoji_string

    @property
    def partial_emoji(self):
        emoji = self.emoji_string.split(':')
        animated = '<a:' in self.emoji_string
        emoji = hikari.CustomEmoji(
            name=emoji[1][1:],
            id=hikari.Snowflake(int(str(emoji[2])[:-1])),
            is_animated=animated,
        )
        return emoji


class Emojis:
    def __init__(self, emoji_dict: dict[str | int, str]):
        self.animated_clash_swords = EmojiType(emoji_dict.get('animated_clash_swords'))
        self.average = EmojiType(emoji_dict.get('average'))
        self.back = EmojiType(emoji_dict.get('back'))
        self.blank = EmojiType(emoji_dict.get('blank'))
        self.broken_sword = EmojiType(emoji_dict.get('broken_sword'))
        self.brown_shield = EmojiType(emoji_dict.get('brown_shield'))
        self.calendar = EmojiType(emoji_dict.get('calendar'))
        self.capital_gold = EmojiType(emoji_dict.get('capital_gold'))
        self.capital_trophy = EmojiType(emoji_dict.get('capital_trophy'))
        self.clan_castle = EmojiType(emoji_dict.get('clan_castle'))
        self.clan_games = EmojiType(emoji_dict.get('clan_games'))
        self.clash_sword = EmojiType(emoji_dict.get('clash_sword'))
        self.clock = EmojiType(emoji_dict.get('clock'))
        self.cwl_medal = EmojiType(emoji_dict.get('cwl_medal'))
        self.dark_elixir = EmojiType(emoji_dict.get('dark_elixir'))
        self.discord = EmojiType(emoji_dict.get('discord'))
        self.double_up_arrow = EmojiType(emoji_dict.get('double_up_arrow'))
        self.down_red_arrow = EmojiType(emoji_dict.get('down_red_arrow'))
        self.earth = EmojiType(emoji_dict.get('earth'))
        self.elixir = EmojiType(emoji_dict.get('elixir'))
        self.excel = EmojiType(emoji_dict.get('excel'))
        self.eye = EmojiType(emoji_dict.get('eye'))
        self.forward = EmojiType(emoji_dict.get('forward'))
        self.gear = EmojiType(emoji_dict.get('gear'))
        self.gold = EmojiType(emoji_dict.get('gold'))
        self.green_check = EmojiType(emoji_dict.get('green_check'))
        self.green_circle = EmojiType(emoji_dict.get('green_circle'))
        self.grey_circle = EmojiType(emoji_dict.get('grey_circle'))
        self.grey_dash = EmojiType(emoji_dict.get('grey_dash'))
        self.hand_coins = EmojiType(emoji_dict.get('hand_coins'))
        self.hashmark = EmojiType(emoji_dict.get('hashmark'))
        self.heart = EmojiType(emoji_dict.get('heart'))
        self.no_star = EmojiType(emoji_dict.get('no_star'))
        self.opt_in = EmojiType(emoji_dict.get('opt_in'))
        self.opt_out = EmojiType(emoji_dict.get('opt_out'))
        self.people = EmojiType(emoji_dict.get('people'))
        self.pet_paw = EmojiType(emoji_dict.get('pet_paw'))
        self.pin = EmojiType(emoji_dict.get('pin'))
        self.raid_medal = EmojiType(emoji_dict.get('raid_medal'))
        self.ratio = EmojiType(emoji_dict.get('ratio'))
        self.red_circle = EmojiType(emoji_dict.get('red_circle'))
        self.red_tick = EmojiType(emoji_dict.get('red_tick'))
        self.red_x = EmojiType(emoji_dict.get('red_x'))
        self.reddit_icon = EmojiType(emoji_dict.get('reddit_icon'))
        self.refresh = EmojiType(emoji_dict.get('refresh'))
        self.search = EmojiType(emoji_dict.get('search'))
        self.shield = EmojiType(emoji_dict.get('shield'))
        self.spells = EmojiType(emoji_dict.get('spells'))
        self.square_sum_box = EmojiType(emoji_dict.get('square_sum_box'))
        self.square_x_deny = EmojiType(emoji_dict.get('square_x_deny'))
        self.terminal = EmojiType(emoji_dict.get('terminal'))
        self.thick_capital_sword = EmojiType(emoji_dict.get('thick_capital_sword'))
        self.time = EmojiType(emoji_dict.get('time'))
        self.toggle_off = EmojiType(emoji_dict.get('toggle_off'))
        self.toggle_on = EmojiType(emoji_dict.get('toggle_on'))
        self.trashcan = EmojiType(emoji_dict.get('trashcan'))
        self.troop = EmojiType(emoji_dict.get('troop'))
        self.trophy = EmojiType(emoji_dict.get('trophy'))
        self.unranked = EmojiType(emoji_dict.get('unranked'))
        self.up_green_arrow = EmojiType(emoji_dict.get('up_green_arrow'))
        self.user_search = EmojiType(emoji_dict.get('user_search'))
        self.versus_trophy = EmojiType(emoji_dict.get('versus_trophy'))
        self.war_star = EmojiType(emoji_dict.get('war_star'))
        self.warning = EmojiType(emoji_dict.get('warning'))
        self.wood_swords = EmojiType(emoji_dict.get('wood_swords'))
        self.wrench = EmojiType(emoji_dict.get('wrench'))
        self.xp = EmojiType(emoji_dict.get('xp'))


emojis = Emojis(emoji_dict={})


@lightbulb.di.with_di
async def fetch_emoji_dict(bot: hikari.GatewayBot = lightbulb.di.INJECTED, config: Config = lightbulb.di.INJECTED):

    # Fetch the desired emoji definitions
    response = requests.get(config.emoji_url).json()
    original_name_map = {}
    full_emoji_dict = {}

    # Convert keys to a normalized form, just like your original code
    for emoji_type, emoji_dict in response.items():
        hold_dict = emoji_dict.copy()
        for key, value in emoji_dict.items():
            prev_value = hold_dict.pop(key)
            prev_key = key.replace('.', '').replace(' ', '').lower()
            if prev_key.isnumeric():
                prev_key = f'{prev_key}xx'
            original_name_map[prev_key] = key
            hold_dict[prev_key] = prev_value
        full_emoji_dict = full_emoji_dict | hold_dict

    application = await bot.rest.fetch_my_user()
    current_emoji = await bot.rest.fetch_application_emojis(application=application.id)

    combined_emojis = {}
    for emoji in current_emoji:
        start = '<:' if not emoji.is_animated else '<a:'
        # Map back to original name if available
        real_name = original_name_map.get(emoji.name, emoji.name)

        # Convert numeric name to int if needed
        if isinstance(real_name, str) and real_name.isnumeric():
            real_name = int(real_name)

        combined_emojis[real_name] = f'{start}{emoji.name}:{emoji.id}>'

    global APPLICATION_EMOJI_CACHE
    APPLICATION_EMOJI_CACHE = combined_emojis
    global emojis
    emojis = Emojis(emoji_dict=APPLICATION_EMOJI_CACHE)
    return APPLICATION_EMOJI_CACHE


def fetch_emoji(name: str | int):

    if name == 'CWL_Unranked':
        name = 'unranked'

    if name == 'Unranked':
        name = 'unranked'
    emoji = APPLICATION_EMOJI_CACHE.get(name)
    if emoji is None:
        return None
    return EmojiType(emoji_string=emoji)
