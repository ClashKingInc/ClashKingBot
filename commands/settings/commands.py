import disnake
import coc
from disnake.ext import commands
from classes.bot import CustomClient
from classes.server import CustomServer, ServerClan, DatabaseClan
from exceptions.CustomExceptions import ThingNotFound
from utility.discord_utils import check_commands
from typing import Union
from utility.general import calculate_time
from utility.discord_utils import interaction_handler

class misc(commands.Cog, name="Settings"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    @commands.slash_command(name="set")
    async def set(self, ctx):
        await ctx.response.defer()
        pass





    @set.sub_command(name="member-count-warning", description="Set a warning when member count gets to a certain level")
    async def member_count_warning(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                                   below: int = commands.Param(), above: int = commands.Param(), ping: disnake.Role = None, channel: Union[disnake.TextChannel, disnake.Thread] = None):
        if channel is None:
            channel = ctx.channel
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            raise ThingNotFound("**This clan is not set up on this server. Use `/addclan` to get started.**")
        db_clan = DatabaseClan(bot=self.bot, data=results)
        await db_clan.member_count_warning.set_above(num=above)
        await db_clan.member_count_warning.set_below(num=below)
        await db_clan.member_count_warning.set_channel(id=channel.id)
        if ping is not None:
            await db_clan.member_count_warning.set_role(id=ping.id)

        text = f"Member Count Warning for {clan.name}({clan.tag}) set in {channel.id}. Will warn when reaching {below} & {above}."
        if ping is not None:
            text += f" Will ping {ping.mention}."
        embed = disnake.Embed(description=text, color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.url)
        await ctx.edit_original_message(embed=embed)





    @set.sub_command(name="webhook-info", description="Set the profile pictures/name for all CK webhooks in server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def set_pfps(self, ctx: disnake.ApplicationCommandInteraction, picture: disnake.Attachment, name:str):
        await ctx.edit_original_message(content="<a:loading:948121999526461440> Updating, this can take several minutes.")
        db_server = await self.bot.get_custom_server(guild_id=ctx.guild_id)
        for clan in db_server.clans:
            logs = [clan.join_log, clan.leave_log, clan.capital_attacks, clan.capital_donations, clan.capital_weekly_summary, clan.raid_panel, clan.donation_log, clan.super_troop_boost_log,
                    clan.role_change, clan.donation_log, clan.troop_upgrade, clan.th_upgrade, clan.league_change, clan.spell_upgrade, clan.hero_upgrade, clan.name_change, clan.war_log, clan.war_panel,
                    clan.legend_log_defenses, clan.legend_log_attacks]
            real_logs = set()
            for log in logs:
                if log.webhook is not None:
                    real_logs.add(log.webhook)

            for log in real_logs:
                webhook = await self.bot.getch_webhook(log)
                await webhook.edit(name=name, avatar=(await picture.read()))
        await ctx.edit_original_message(content=f"All logs profile pictures set to {name} with the following image:", file=(await picture.to_file()))

    @set.sub_command(name="bot-status", description="Set the bot status for a custom bot (only works if you have one)")
    @commands.is_owner()
    async def set_status(self, ctx: disnake.ApplicationCommandInteraction, activity_type = commands.Param(choices=["Playing", "Listening", "Watching", "Competing"]),
                                activity_text: str = commands.Param(name="activity_text"),
                                status: str= commands.Param(choices=["Online", "Offline", "Idle", "DND"])):

        type_convert = {"Playing" : disnake.ActivityType.playing, "Listening" : disnake.ActivityType.listening,
                        "Watching" : disnake.ActivityType.watching, "Competing" : disnake.ActivityType.competing}
        status_convert = {"Online" : disnake.Status.online, "Offline" : disnake.Status.offline, "Idle" : disnake.Status.idle, "DND" : disnake.Status.do_not_disturb}
        await self.bot.change_presence(activity=disnake.Activity(name=activity_text ,type=type_convert.get(activity_type)), status=status_convert.get(status))
        await ctx.edit_original_message("Status changed")


    @set.sub_command(name="category-role", description="Set a new category role for a server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def category_role(self, ctx: disnake.ApplicationCommandInteraction, category: str, role: disnake.Role):
        """
            Parameters
            ----------
            category: category to set role for
            role: New role to switch to
        """

        results = await self.bot.clan_db.find_one({"$and": [
            {"category": category},
            {"server": ctx.guild.id}
        ]})

        if results is None:
            return await ctx.edit_original_message(f"No category - **{category}** - on this server")

        await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {f"category_roles.{category}": role.id}})

        embed = disnake.Embed(
            description=f"Category role set to {role.mention}",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)


    @set.sub_command(name="category-order", description="Change the order family categories display on /family-clans")
    @commands.has_permissions(manage_guild=True)
    async def family_cat_order(self, ctx: disnake.ApplicationCommandInteraction):
        categories = await self.bot.clan_db.distinct("category", filter={"server": ctx.guild.id})
        select_options = []
        for category in categories:
            select_options.append(disnake.SelectOption(label=category, value=category))
        select = disnake.ui.Select(
            options=select_options,
            placeholder="Categories",  # the placeholder text to show when no options have been chosen
            min_values=len(select_options),  # the minimum number of options a user must select
            max_values=len(select_options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        embed= disnake.Embed(description="**Select from the categories below in the order you would like them to be in**", color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=dropdown)
        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                      timeout=600)
        except:
            return await msg.edit(components=[])
        await res.response.defer()
        await self.bot.server_db.update_one({"server" : ctx.guild.id}, {"$set" : {"category_order" : res.values}})
        new_order = ", ".join(res.values)
        embed= disnake.Embed(description=f"New Category Order: `{new_order}`", color=disnake.Color.green())
        await res.edit_original_message(embed=embed)



    @commands.slash_command(name="whitelist")
    async def whitelist(self, ctx):
        pass

    @whitelist.sub_command(name="add", description="Adds a role that can run a specific command.")
    @commands.has_permissions(manage_guild=True)
    async def whitelist_add(self, ctx, ping: Union[disnake.Member, disnake.Role], command: str):

        list_commands = []
        for command_ in self.bot.slash_commands:
            base_command = command_.name
            children = command_.children
            if children != {}:
                for child in children:
                    command_l = children[child]
                    full_name = f"{base_command} {command_l.name}"
                    command_l = self.bot.get_slash_command(name=full_name)
                    if command_l.checks != []:
                        list_commands.append(full_name)
            else:
                full_name = base_command
                if command_.checks != []:
                    list_commands.append(full_name)

        is_command = command in list_commands

        if "whitelist" in command:
            is_command = False

        if is_command == False:
            return await ctx.reply("Not a valid command or command cannot be whitelisted.")

        results = await self.bot.whitelist.find_one({"$and": [
            {"command": command},
            {"server": ctx.guild.id},
            {"role_user": ping.id}
        ]})

        if results is not None:
            embed = disnake.Embed(description=f"{ping.mention} is already whitelisted for `{command}`.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.whitelist.insert_one({
            "command": command,
            "server": ctx.guild.id,
            "role_user": ping.id,
            "is_role" : isinstance(ping, disnake.Role)
        })

        embed = disnake.Embed(
            description=f"{ping.mention} added to `{command}` whitelist.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @whitelist.sub_command(name="remove", description="Deletes a role/user that can run a specific command")
    @commands.has_permissions(manage_guild=True)
    async def whitelist_remove(self, ctx, ping: Union[disnake.Member, disnake.Role], command: str):

        list_commands = []
        for command_ in self.bot.slash_commands:
            base_command = command_.name
            children = command_.children
            if children != {}:
                for child in children:
                    command_l = children[child]
                    full_name = f"{base_command} {command_l.name}"
                    command_l = self.bot.get_slash_command(name=full_name)
                    if command_l.checks != []:
                        list_commands.append(full_name)
            else:
                full_name = base_command
                if command_.checks != []:
                    list_commands.append(full_name)

        is_command = command in list_commands

        if "whitelist" in command:
            is_command = False

        if is_command == False:
            return await ctx.reply("Not a valid command or command cannot be whitelisted.")

        results = await self.bot.whitelist.find_one({"$and": [
            {"command": command},
            {"server": ctx.guild.id},
            {"role_user": ping.id}
        ]})

        if results is None:
            embed = disnake.Embed(description=f"{ping.mention} has no active whitelist for `{command}`.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.whitelist.find_one_and_delete({
            "command": command,
            "server": ctx.guild.id,
            "role_user": ping.id
        })

        embed = disnake.Embed(
            description=f"{ping.mention} removed from `{command}` whitelist.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @whitelist.sub_command(name="list", description="Displays the list of commands that have whitelist overrides.")
    async def whitelist_list(self, ctx):
        text = ""
        results = self.bot.whitelist.find({"server": ctx.guild.id})
        limit = await self.bot.whitelist.count_documents(filter={"server": ctx.guild.id})
        for role in await results.to_list(length=limit):
            r = role.get("role_user")
            command = role.get("command")
            if role.get("is_role") :
                text += f"<@&{r}> | `{command}`\n"
            else:
                text += f"<@{r}> | `{command}`\n"

        if text == "":
            text = "Whitelist is empty."

        embed = disnake.Embed(title=f"Command Whitelist",
                              description=text,
                              color=disnake.Color.green())

        await ctx.send(embed=embed)


    @category_role.autocomplete("category")
    async def autocomp_category(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        categories = []
        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if query.lower() in category.lower() and category not in categories:
                categories.append(category)
        return categories[:25]

    @whitelist_add.autocomplete("command")
    @whitelist_remove.autocomplete("command")
    async def autocomp_comamnds(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        commands = []
        for command_ in self.bot.slash_commands:
            base_command = command_.name
            if "whitelist" in base_command:
                continue
            children = command_.children
            if children != {}:
                for child in children:
                    command = children[child]
                    full_name = f"{base_command} {command.name}"
                    command = self.bot.get_slash_command(name=full_name)
                    if query.lower() in full_name.lower() and command.checks != []:
                        commands.append(full_name)
            else:
                full_name = base_command
                if query.lower() in full_name.lower() and command_.checks != []:
                    commands.append(full_name)
        return commands[:25]


def setup(bot: CustomClient):
    bot.add_cog(misc(bot))