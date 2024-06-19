import disnake

from disnake.ext import commands
from exceptions.CustomExceptions import *
from classes.bot import CustomClient
from utility.discord_utils import (
    get_webhook_for_channel,
    check_commands,
    interaction_handler,
)

mapping = {
    "clandetailed": "Clan Detailed",
    "clanbasic": "Clan Basic",
    "clanmini": "Clan Minimalistic",
    "clancompo": "Clan Composition",
    "clanhero": "Clan Hero Progress",
    "clantroops": "Clan Troops Progress",
    "clansorted": "Clan Sorted",
    "clandonos": "Clan Donations",
    "clanwarpref": "Clan War Preference",
    "clanactivity": "Clan Activity",
    "clancapoverview": "Clan Capital Overview",
    "clancapdonos": "Clan Capital Donations",
    "clancapraids": "Clan Capital Raids",
    "clanwarlog": "Clan War Log",
    "clancwlperf": "Clan CWL Performance",
    "clansummary": "Clan Summary",
    "clangames": "Clan Games",
    "familycompo": "Family Composition",
    "familysummary": "Family Summary",
    "familyoverview": "Family Overview",
    "familyheroprogress": "Family Hero Progress",
    "familytroopprogress": "Family Troop Progress",
    "familysorted": "Family Sorted",
    "familydonos": "Family Donations",
    "familygames": "Family Games",
    "familyactivity": "Family Activity",
    "legendday": "Legend Day",
    "legendseason": "Legend Season",
    "legendhistory": "Legend History",
    "legendclan": "Legend Clan",
    "legendcutoff": "Legend Cutoff",
    "legendstreaks": "Legend Streaks",
    "legendbuckets": "Legend Buckets",
    "legendeosfinishers": "Legend EOS Finishers",
    "discordlinks": "Discord Links",
}


class MessageCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.message_command(name="Refresh Board", dm_permission=False)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def refresh_board(self, ctx: disnake.MessageCommandInteraction, message: disnake.Message):
        check = await self.bot.white_list_check(ctx, "setup server-settings")
        await ctx.response.defer(ephemeral=True)
        if not check and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(
                content="You cannot use this command. Missing Permissions. Must have `Manage Server` permissions or be whitelisted for `/setup server-settings`",
                ephemeral=True,
            )
        if not message.components:
            raise MessageException("This message has no components")

        options = []
        for child in message.components[0].children:
            if child.custom_id is None:
                continue
            name = child.custom_id.split(":")[0]
            if mapping.get(name) is not None:
                options.append(disnake.SelectOption(label=mapping.get(name), value=child.custom_id))

        if not options:
            raise MessageException("This command does not support auto refreshing currently")

        if len(options) >= 2:
            option_select = disnake.ui.Select(
                options=options,
                placeholder=f"Select Board Type",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            await ctx.edit_original_message(
                content="Choose which button to make an auto refreshing board for",
                components=[disnake.ui.ActionRow(option_select)],
            )
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, ephemeral=True)
            custom_id = res.values[0]
        else:
            custom_id = options[0].value

        webhook = await get_webhook_for_channel(channel=message.channel, bot=self.bot)
        thread = None
        if isinstance(message.channel, disnake.Thread):
            await message.channel.add_user(self.bot.user)
            thread = message.channel.id

        placeholder = disnake.Embed(
            description="Placeholder Embed, will update momentarily!",
            color=disnake.Color.green(),
        )
        if thread is not None:
            thread = await self.bot.getch_channel(thread)
            webhook_message = await webhook.send(embed=placeholder, thread=thread, wait=True)
            thread = thread.id
        else:
            webhook_message = await webhook.send(embed=placeholder, wait=True)
        await self.bot.button_store.update_one(
            {"$and": [{"button_id": custom_id}, {"server": ctx.guild_id}]},
            {
                "$set": {
                    "webhook_id": webhook.id,
                    "thread_id": thread,
                    "message_id": webhook_message.id,
                }
            },
            upsert=True,
        )
        await message.delete()
        await ctx.edit_original_message("Refresh Board Created", components=[])

    @commands.message_command(name="Auto Board", dm_permission=False)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def auto_board(self, ctx: disnake.MessageCommandInteraction, message: disnake.Message):
        check = await self.bot.white_list_check(ctx, "setup server-settings")
        await ctx.response.defer(ephemeral=True)
        if not check and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send(
                content="You cannot use this command. Missing Permissions. Must have `Manage Server` permissions or be whitelisted for `/setup server-settings`",
                ephemeral=True,
            )
        if not message.components:
            raise MessageException("This message has no components")

        options = []
        for child in message.components[0].children:
            if child.custom_id is None:
                continue
            name = child.custom_id.split(":")[0]
            if mapping.get(name) is not None:
                options.append(disnake.SelectOption(label=mapping.get(name), value=child.custom_id))

        if not options:
            raise MessageException("This command does not support auto refreshing currently")

        if len(options) >= 2:
            option_select = disnake.ui.Select(
                options=options,
                placeholder=f"Select Board Type",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            await ctx.edit_original_message(
                content="Choose which button to make an auto refreshing board for",
                components=[disnake.ui.ActionRow(option_select)],
            )
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, ephemeral=True)
            custom_id = res.values[0]
        else:
            custom_id = options[0].value

        webhook = await get_webhook_for_channel(channel=message.channel, bot=self.bot)
        thread = None
        if isinstance(message.channel, disnake.Thread):
            await message.channel.add_user(self.bot.user)
            thread = message.channel.id

        placeholder = disnake.Embed(
            description="Placeholder Embed, will update momentarily!",
            color=disnake.Color.green(),
        )
        if thread is not None:
            thread = await self.bot.getch_channel(thread)
            webhook_message = await webhook.send(embed=placeholder, thread=thread, wait=True)
            thread = thread.id
        else:
            webhook_message = await webhook.send(embed=placeholder, wait=True)
        await self.bot.button_store.update_one(
            {"$and": [{"button_id": custom_id}, {"server": ctx.guild_id}]},
            {
                "$set": {
                    "webhook_id": webhook.id,
                    "thread_id": thread,
                    "message_id": webhook_message.id,
                }
            },
            upsert=True,
        )
        await message.delete()
        await ctx.edit_original_message("Refresh Board Created", components=[])


def setup(bot: CustomClient):
    bot.add_cog(MessageCommands(bot))
