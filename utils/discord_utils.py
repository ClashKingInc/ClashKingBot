import disnake
from Assets.emojiDictionary import emojiDictionary, legend_emojis
from typing import Callable, Union
from Exceptions.CustomExceptions import ExpiredComponents
from urllib.request import Request, urlopen
import io

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


async def permanent_image(bot, url: str):
    def request(url):
        req = Request(url=url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'})
        f = io.BytesIO(urlopen(req).read())
        file = disnake.File(fp=f, filename="pic.png")
        return file
    file = request(url)
    pic_channel = await bot.getch_channel(884951195406458900)
    msg = await pic_channel.send(file=file)
    pic = msg.attachments[0].url
    return pic


async def interaction_handler(bot, ctx: Union[disnake.ApplicationCommandInteraction, disnake.MessageInteraction], msg:disnake.Message = None,
                              function: Callable = None, no_defer = False, ephemeral= False):
    if msg is None:
        msg = await ctx.original_message()

    async def return_res(res):
        return res

    if function is None:
        function = return_res

    def check(res: disnake.MessageInteraction):
        return res.message.id == msg.id

    valid_value = None
    while valid_value is None:
        try:
            res: disnake.MessageInteraction = await bot.wait_for("message_interaction", check=check, timeout=600)
        except Exception:
            raise ExpiredComponents

        if res.author.id != ctx.author.id:
            await res.send(content="You must run the command to interact with components.", ephemeral=True)
            continue

        if not no_defer and "modal" not in res.data.custom_id:
            if ephemeral:
                await res.response.defer(ephemeral=True)
            else:
                await res.response.defer()
        valid_value = await function(res=res)

    return valid_value



