import asyncio
import io
import os
import re
import textwrap
from contextlib import redirect_stdout
from datetime import datetime

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from classes.bot import CustomClient
from discord import autocomplete, convert

from .utils import fetch_emoji_dict, milestone_embed
from utility.components import button_generator


class OwnerCommands(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.count = 0
        self.model = None

    @commands.command(
        name='reload_all', help='Reload all cogs automatically.', guild_ids=[923764211845312533, 1210616106448978001]
    )
    @commands.is_owner()  # Restrict to the bot owner
    async def reload_all(self, ctx):
        """
        Reloads all cogs found in the `commands` directory with 'commands' in their path.
        """
        disallowed = set()  # Add cogs to ignore here if necessary
        reloaded_cogs = []
        failed_cogs = []

        # Dynamically find all cogs in the `commands` directory
        for root, _, files in os.walk('commands'):
            for filename in files:
                if filename.endswith('.py'):  # Only include Python files
                    path = os.path.join(root, filename)[len('commands/') :][:-3].replace(os.path.sep, '.')

                    # Check if 'commands' is part of the path to filter utils and other submodules
                    if not path.endswith('commands'):
                        continue

                    if path.split('.')[0] in disallowed:  # Exclude disallowed cogs
                        continue

                    cog = f'commands.{path}'
                    try:
                        self.bot.reload_extension(cog)
                        reloaded_cogs.append(cog)
                    except Exception as e:
                        failed_cogs.append((cog, str(e)))

        # Format the response
        success_msg = '\n'.join([f'✅ {cog}' for cog in reloaded_cogs]) or 'No cogs were reloaded.'
        error_msg = '\n'.join([f'❌ {cog}: {error}' for cog, error in failed_cogs]) or 'No errors occurred.'

        embed = disnake.Embed(
            title='🔄 Reload All Cogs',
            description=f'**Reloaded Cogs:**\n{success_msg}\n\n**Errors:**\n{error_msg}',
            color=disnake.Color.blurple(),
        )
        await ctx.send(embed=embed)

    @commands.slash_command(name='dev', guild_ids=[923764211845312533, 1210616106448978001])
    @commands.is_owner()
    async def dev(self, ctx: ApplicationCommandInteraction):
        pass

    @dev.sub_command(name='exec', description='Execute python code')
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

    @dev.sub_command(name='test', description='Arbitrary command')
    async def test(self, ctx: ApplicationCommandInteraction):
        pass

    @dev.sub_command(name='update-emojis', description='Update Emojis across all bots')
    async def update_emojis(self, ctx: ApplicationCommandInteraction):
        await ctx.response.defer()
        asyncio.create_task(fetch_emoji_dict(bot=self.bot))
        await ctx.send('Updating Emojis.')

    @dev.sub_command(name='automation-limit', description='Set a new autoboard limit for a server')
    async def automation_limit(
        self,
        ctx: ApplicationCommandInteraction,
        server: disnake.Guild = commands.Param(converter=convert.server, autocomplete=autocomplete.all_server),
        new_limit: int = commands.Param(),
    ):
        await ctx.response.defer()
        db_server = await self.bot.ck_client.get_server_settings(server_id=server.id)
        await db_server.set_autoboard_limit(limit=new_limit)
        await ctx.send(f'{server.name} autoboard limit set to {new_limit}')

    # GITHUB COMMANDS
    @dev.sub_command_group(name='github', description='Github commands')
    async def github(self, ctx: ApplicationCommandInteraction):
        pass

    @github.sub_command(name='timeline', description='Milestone timeline for github issues')
    async def github_timeline(
        self,
        ctx: ApplicationCommandInteraction,
        repo=commands.Param(choices=['ClashKingBot']),
    ):
        await ctx.response.defer()
        repo = f'ClashKingInc/{repo}'
        embed = await milestone_embed(bot=self.bot, repo=repo)
        components = button_generator(bot=self.bot, button_id=f'githubtimeline:{repo}')
        await ctx.edit_original_response(embed=embed, components=components)


def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))
