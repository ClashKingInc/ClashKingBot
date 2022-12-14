import disnake
from Assets.emojiDictionary import emojiDictionary, legend_emojis


def partial_emoji_gen(bot, emoji_string, animated=False):
    emoji = ''.join(filter(str.isdigit, emoji_string))
    emoji = bot.get_emoji(int(emoji))
    emoji = disnake.PartialEmoji(
        name=emoji.name, id=emoji.id, animated=animated)
    return emoji


def embed_parse(string):
    return 0


def fetch_emoji(emoji_name):
    emoji = emojiDictionary(emoji_name)
    if emoji is None:
        emoji = legend_emojis(emoji_name)
    return emoji
