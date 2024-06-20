from typing import Dict, List

import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from discord.options import autocomplete
from exceptions.CustomExceptions import MessageException
from utility.discord_utils import interaction_handler

from .utils import get_all_commands, get_command_permissions


class HelpCommands(commands.Cog, name='Help'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(
        name='help',
        description='List of commands & descriptions for ClashKing',
        extras={'Example Usage': '`/help command: help`'},
    )
    async def help(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        command: str = commands.Param(default=None, autocomplete=autocomplete.command_autocomplete),
        category: str = commands.Param(default=None, autocomplete=autocomplete.command_category_autocomplete),
    ):
        """
        Parameters
        ----------
        command: (optional) command to get details about
        category: (optional) category of commands to view
        """
        await ctx.response.defer()
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)

        all_commands: Dict[str, List[disnake.ext.commands.InvokableSlashCommand]] = get_all_commands(bot=self.bot)
        if category:
            all_commands = {category: all_commands.get(category)}

        embeds = []
        if not command:
            for cog, commands in all_commands.items():
                text = ''
                for command in commands:
                    api_command: disnake.APISlashCommand = self.bot.get_global_command_named(name=command.qualified_name.split(' ')[0])
                    permissions = get_command_permissions(command=command)
                    if permissions:
                        permissions = f"**({', '.join(permissions)})**".replace('Guild', 'Server')
                    else:
                        permissions = ''

                    text += f'</{command.qualified_name}:{api_command.id}> {permissions}\n{command.description}\n\n'
                embed = disnake.Embed(description=text, color=embed_color)
                embed.set_author(
                    name=f'{self.bot.user.name} {cog} Commands',
                    icon_url=self.bot.user.avatar.url,
                )
                embeds.append(embed)
        else:
            command = [c for command_list in all_commands.values() for c in command_list if command == c.qualified_name]
            if not command:
                raise MessageException('Command Not Found')
            command = command[0]
            api_command: disnake.APISlashCommand = self.bot.get_global_command_named(name=command.qualified_name.split(' ')[0])
            mention = f'</{command.qualified_name}:{api_command.id}>'

            embed = disnake.Embed(
                title='Slash Command Details',
                description=f'{mention}\n{command.description}',
                color=embed_color,
            )
            permissions = get_command_permissions(command=command)

            if permissions:
                permissions = ', '.join(permissions)
                embed.add_field(name='Required Permissions', value=permissions, inline=True)

            embed.set_footer(text='[ required ] | ( optional )')

            if command.body.options:
                args: str = ''
                for option in command.body.options:
                    if option.type in (
                        disnake.OptionType.sub_command,
                        disnake.OptionType.sub_command_group,
                    ):
                        continue
                    name = f'**[{option.name}]**' if option.required else f'**({option.name})**'
                    args += f'{name}: *{option.description}*\n'

                embed.add_field(name='Parameters', value=args, inline=False)
            else:
                embed.add_field(name='Parameters', value='None', inline=True)

            if command.extras:
                for title, text in command.extras.items():
                    embed.add_field(name=title, value=text, inline=False)

            embeds = [embed]

        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])

        select_options = []
        page_names = list(all_commands.keys())
        for cog_name in page_names:
            select_options.append(
                disnake.SelectOption(
                    label=cog_name,
                    emoji=self.bot.emoji.gear.partial_emoji,
                    value=cog_name,
                )
            )
        select_options.append(disnake.SelectOption(label='Print', emoji='🖨️', value='Print'))
        select = disnake.ui.Select(
            options=select_options,
            placeholder='Help Modules',  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        await ctx.edit_original_message(embed=embeds[0], components=dropdown)

        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            if res.values[0] == 'Print':
                await res.delete_original_message()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)
            else:
                await res.edit_original_message(embed=embeds[page_names.index(res.values[0])])


def setup(bot: CustomClient):
    bot.add_cog(HelpCommands(bot))
