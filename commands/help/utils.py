import disnake

from classes.bot import CustomClient
from collections import defaultdict
from disnake.ext import commands
from typing import Dict, List


def get_all_commands(bot: CustomClient):
    command_list: Dict[str, List[disnake.ext.commands.InvokableSlashCommand]] = defaultdict(list)
    for command in bot.slash_commands:
        if command.guild_ids is not None:
            continue
        if command.cog_name == "OwnerCommands":
            continue
        if not command.children:
            command_list[command.cog_name].append(command)
        else:
            for child in command.children.keys():
                sub_command = bot.get_slash_command(name=f"{command.name} {child}")
                command_list[command.cog_name].append(sub_command)

    return dict(command_list)


def get_command_permissions(command: disnake.ext.commands.InvokableSlashCommand):
    permissions = []

    for check in command.checks:
        name = check.__qualname__.split(".")[0]
        if "bot" in name or not check.__closure__:
            continue
        try:
            closure = check.__closure__[0]

            for c in closure.cell_contents:
                if c.__closure__ is not None:
                    try:
                        permissions.extend([p.replace("_", " ").title() for p, v in closure.cell_contents.items() if v])
                    except:
                        permissions.extend(
                            [
                                p.replace("_", " ").title()
                                for p, v in closure.cell_contents[0]
                                .__closure__[0]
                                .cell_contents.__closure__[0]
                                .cell_contents.items()
                                if v
                            ]
                        )
        except AttributeError:
            return []
    return permissions
