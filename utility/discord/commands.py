import os
from typing import Any, Callable, Dict, List, Tuple, Union

import disnake
from disnake.ext import commands

from classes.exceptions import *

from classes.mongo import MongoClient as mongo_client


def check_commands():
    async def predicate(ctx: disnake.ApplicationCommandInteraction):
        # if dev, allow to run
        if ctx.author.id == 706149153431879760:
            return True

        # check for clashking perms role
        member = await ctx.guild.getch_member(member_id=ctx.author.id)
        server_setup = await mongo_client.server_db.find_one(
            {'server': ctx.guild.id}, {'_id': 0, 'full_whitelist_role': 1}
        )

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

        results = await mongo_client.whitelist.find(
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


# jesus what is this trash lmao, hmm maybe its smart
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


registered_functions: Dict[str, Tuple[Callable[..., None] | None, str, bool, bool, bool]] = {}


def register_button(
    command_name: str, parser: str, ephemeral: bool = False, no_embed: bool = False, pagination: bool = False
):
    def decorator(func: Callable[..., None]) -> Callable[..., None]:
        registered_functions[command_name] = (func, parser, ephemeral, no_embed, pagination)
        return func

    return decorator
