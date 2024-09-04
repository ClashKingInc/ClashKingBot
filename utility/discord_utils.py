import os
from typing import Callable, List, Union

import disnake
import motor.motor_asyncio
from disnake.ext import commands
from exceptions.CustomExceptions import *


db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('STATIC_MONGODB'))
whitelist = db_client.usafam.whitelist
server_settings = db_client.usafam.server


def check_commands():
    async def predicate(ctx: disnake.ApplicationCommandInteraction):
        # if owner, allow to run
        if ctx.author.id == 706149153431879760:
            return True

        # check for clashking perms role
        member = await ctx.guild.getch_member(member_id=ctx.author.id)
        server_setup = await server_settings.find_one({'server': ctx.guild.id}, {'_id': 0, 'full_whitelist_role': 1})

        if server_setup is not None and server_setup.get('full_whitelist_role') is not None:
            if disnake.utils.get(member.roles, id=server_setup.get('full_whitelist_role')) is not None:
                return True
        else:
            if disnake.utils.get(member.roles, name='ClashKing Perms') is not None:
                return True

        full_command_name = ctx.application_command.qualified_name
        # idk why this is, find out later
        if full_command_name == 'unlink':
            return True

        base_command_name = full_command_name.split(' ')[0]

        results = await whitelist.find(
            {
                '$and': [
                    {
                        '$or': [
                            {'command': full_command_name},
                            {'command': base_command_name},
                        ]
                    },
                    {'server': ctx.guild.id},
                ]
            }
        ).to_list(length=None)

        if not results:
            return False

        for result in results:
            if result.get('is_role'):
                if disnake.utils.get(member.roles, id=int(result.get('role_user'))) is not None:
                    return True
            else:
                if member.id == result.get('role_user'):
                    return True

        return False

    return commands.check(predicate)


def partial_emoji_gen(bot, emoji_string, animated=False):
    emoji = ''.join(filter(str.isdigit, emoji_string))
    emoji = bot.emoji_holder.all_emojis.get(int(emoji))
    emoji = disnake.PartialEmoji(name=emoji.name, id=emoji.id, animated=animated)
    return emoji


def embed_parse(string):
    return 0


async def interaction_handler(
    bot,
    ctx: Union[disnake.ApplicationCommandInteraction, disnake.MessageInteraction],
    msg: disnake.Message = None,
    function: Callable = None,
    no_defer=False,
    ephemeral=False,
    any_run=False,
    timeout=600,
):
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
            res: disnake.MessageInteraction = await bot.wait_for('message_interaction', check=check, timeout=timeout)
        except Exception:
            raise ExpiredComponents

        if any_run is False and res.author.id != ctx.author.id:
            await res.send(
                content='You must run the command to interact with components.',
                ephemeral=True,
            )
            continue

        if not no_defer and 'modal' not in res.data.custom_id:
            if ephemeral:
                await res.response.defer(ephemeral=True)
            else:
                if not res.response.is_done():
                    await res.response.defer()
        valid_value = await function(res=res)

    return valid_value


"""async def basic_embed_modal(bot, ctx: disnake.ApplicationCommandInteraction, previous_embed=None):
    components = [
        disnake.ui.TextInput(
            label=f"Embed Title",
            custom_id=f"title",
            required=False,
            style=disnake.TextInputStyle.single_line,
            max_length=75,
        ),
        disnake.ui.TextInput(
            label=f"Embed Description",
            custom_id=f"desc",
            required=False,
            style=disnake.TextInputStyle.paragraph,
            max_length=500,
        ),
        disnake.ui.TextInput(
            label=f"Embed Thumbnail",
            custom_id=f"thumbnail",
            placeholder="Must be a valid url",
            required=False,
            style=disnake.TextInputStyle.single_line,
            max_length=200,
        ),
        disnake.ui.TextInput(
            label=f"Embed Image",
            custom_id=f"image",
            placeholder="Must be a valid url",
            required=False,
            style=disnake.TextInputStyle.single_line,
            max_length=200,
        ),
        disnake.ui.TextInput(
            label=f"Embed Color (Hex Color)",
            custom_id=f"color",
            required=False,
            style=disnake.TextInputStyle.short,
            max_length=10,
        )
    ]
    t_ = int(datetime.now().timestamp())
    await ctx.response.send_modal(
        title="Basic Embed Creator ",
        custom_id=f"basicembed-{t_}",
        components=components)

    def check(res: disnake.ModalInteraction):

        return ctx.author.id == res.author.id and res.custom_id == f"basicembed-{t_}"

    try:
        modal_inter: disnake.ModalInteraction = await bot.wait_for(
            "modal_submit",
            check=check,
            timeout=300,
        )
    except:
        return None, None

    color = disnake.Color.dark_grey()
    if modal_inter.text_values.get("color") != "":
        try:
            r, g, b = tuple(
                int(modal_inter.text_values.get("color").replace("#", "")[i:i + 2], 16) for i in (0, 2, 4))
            color = disnake.Color.from_rgb(r=r, g=g, b=b)
        except:
            raise InvalidHexCode

    our_embed = {"title": modal_inter.text_values.get("title"), "description": modal_inter.text_values.get("desc"),
                 "image.url": modal_inter.text_values.get("image"),
                 "thumbnail.url": modal_inter.text_values.get("thumbnail"), "color": color}

    embed = await generate_embed(bot=bot, our_embed=our_embed, embed=previous_embed)
    await modal_inter.response.defer()

    return (modal_inter, embed)"""


def iter_embed_creation(base_embed: disnake.Embed, iter: List, scheme: str, brk: int = 50) -> List[disnake.Embed]:

    embeds = []
    text = ''
    for count, x in enumerate(iter, 1):
        text += scheme.format(**locals())
        if count % brk == 0:
            embed = base_embed
            embed.description = text
            embeds.append(embed)
            text = ''
    if text != '':
        embed = base_embed
        embed.description = text
        embeds.append(embed)
    return embeds


registered_functions = {}


def register_button(
    command_name: str,
    parser: str,
    ephemeral: bool = False,
    no_embed: bool = False,
    components: Callable = None,
):
    def decorator(func):
        registered_functions[command_name] = (func, parser, ephemeral, no_embed)
        return func

    return decorator


async def get_webhook_for_channel(bot, channel: Union[disnake.TextChannel, disnake.Thread]) -> disnake.Webhook:
    try:
        if isinstance(channel, disnake.Thread):
            webhooks = await channel.parent.webhooks()
        else:
            webhooks = await channel.webhooks()
        webhook = next((w for w in webhooks if w.user.id == bot.user.id), None)
        if webhook is None:
            if isinstance(channel, disnake.Thread):
                webhook = await channel.parent.create_webhook(name=bot.user.name, avatar=bot.user.avatar, reason='Log Creation')
            else:
                webhook = await channel.create_webhook(name=bot.user.name, avatar=bot.user.avatar, reason='Log Creation')
        return webhook
    except Exception:
        raise MissingWebhookPerms


class Holder:
    def __init__(self):
        self.tag = None
        self.id = None
