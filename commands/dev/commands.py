import io
import re
import textwrap
import time
import traceback
from contextlib import redirect_stdout
from datetime import datetime

import disnake
from disnake.ext import commands
from disnake import ApplicationCommandInteraction
import pendulum as pend
import aiohttp
import uuid
import random
from classes.bot import CustomClient
from discord import convert, autocomplete
from utility.constants import EMBED_COLOR_CLASS

class OwnerCommands(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.count = 0
        self.model = None

    @commands.slash_command(name="dev", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def dev(self, ctx: ApplicationCommandInteraction):
        pass

    @dev.sub_command(name='exec', description="Execute python code")
    async def exec(self, ctx: ApplicationCommandInteraction):
        def cleanup_code(content: str) -> str:
            """Automatically removes code blocks from the code and reformats linebreaks"""

            # remove ```py\n```
            if content.startswith('```') and content.endswith('```'):
                return '\n'.join(content.split('\n')[1:-1])

            return '\n'.join(content.split(';'))

        def e_(msg: str) -> str:
            """unescape discord markdown characters
            Parameters
            ----------
                msg: string
                    the text to remove escape characters from
            Returns
            -------
                the message excluding escape characters
            """

            return re.sub(r'\\(\*|~|_|\||`)', r'\1', msg)

        components = [
            disnake.ui.TextInput(
                label=f'Code',
                custom_id=f'code',
                required=False,
                style=disnake.TextInputStyle.paragraph,
                max_length=750,
            )
        ]
        t_ = int(datetime.now().timestamp())
        await ctx.response.send_modal(title='Code', custom_id=f'basicembed-{t_}', components=components)

        def check(res: disnake.ModalInteraction):
            return ctx.author.id == res.author.id and res.custom_id == f'basicembed-{t_}'

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                'modal_submit',
                check=check,
                timeout=300,
            )
        except:
            return None, None

        code = modal_inter.text_values.get('code')

        embed = disnake.Embed(title='Query', description=f'```py\n{code}```')
        await modal_inter.send(embed=embed)

        stmts = cleanup_code(e_(code))
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(stmts, "  ")}'

        env = {'self': self, 'ctx': ctx}
        env.update(globals())

        exec(to_compile, env)

        func = env['func']

        with redirect_stdout(stdout):
            ret = await func()

        value = stdout.getvalue()
        values = value.split('\n')
        buf = f'{len(values)} lines output\n'
        buffer = []
        for v in values:
            if len(v) < 4000:
                if len(buf) + len(v) < 500:
                    buf += v + '\n'
                else:
                    buffer.append(buf)
                    buf = v + '\n'
            else:
                for x in range(0, len(v), 4000):
                    if x + 4000 < len(v):
                        buffer.append(v[x : x + 4000])
                    else:
                        buffer.append(v[x:])
        buffer.append(buf)
        for i, b in enumerate(buffer):
            await ctx.followup.send(embed=disnake.Embed(description=f'```py\n{b}```'))
        if ret is not None:
            ret = ret.split('\n')
            buf = f'{len(ret)} lines output\n'
            buffer = []
            for v in ret:
                if len(buf) + len(v) < 500:
                    buf += v + '\n'
                else:
                    buffer.append(buf)
                    buf = v + '\n'
            buffer.append(buf)
            for i, b in enumerate(buffer):
                await ctx.followup.send(embed=disnake.Embed(description=f'```py\n{b}```'))


    @dev.sub_command(name='test', description="Arbitrary command")
    async def test(self, ctx: ApplicationCommandInteraction):
        pass


    @dev.sub_command(name='automation-limit', description="Set a new autoboard limit for a server")
    async def automation_limit(self, ctx: ApplicationCommandInteraction,
                              server: disnake.Guild =commands.Param(converter=convert.server, autocomplete=autocomplete.all_server),
                              new_limit: int = commands.Param()):
        await ctx.response.defer()
        db_server = await self.bot.ck_client.get_server_settings(server_id=server.id)
        await db_server.set_autoboard_limit(limit=new_limit)
        await ctx.send(f"{server.name} autoboard limit set to {new_limit}")







def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))
