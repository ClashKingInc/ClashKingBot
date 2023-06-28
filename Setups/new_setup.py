import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
import coc
import re

import ast
from utils.general import calculate_time
from main import check_commands
from typing import Union
from utils.discord_utils import interaction_handler


class SetupCommands(commands.Cog , name="Setup"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.color = disnake.Color.dark_theme()

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan



    @commands.slash_command(name="setup")
    async def setup(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()


    #CLAN SETUP
    @setup.sub_command(name="clan-add", description="Add a clan to the server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def addClan(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), category: str = commands.Param(name="category"),
                member_role: disnake.Role = commands.Param(name="member_role"), clan_channel: disnake.TextChannel = commands.Param(name="clan_channel"), leadership_role: disnake.Role = None):
        """
            Parameters
            ----------
            clan_tag: clan to add to server
            category: choose a category or type your own
            member_role: role that all members of this clan receive
            leadership_role: role that co & leaders of this clan would receive
            clan_channel: channel where ban pings & welcome messages should go
        """
        if member_role.is_bot_managed():
            embed = disnake.Embed(description=f"Clan Roles cannot be bot roles.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if leadership_role is not None and leadership_role.is_bot_managed():
            embed = disnake.Embed(description=f"Clan Roles cannot be bot roles.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if member_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(description=f"Member Role cannot be {ctx.guild.default_role.mention}.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if leadership_role is not None and leadership_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(description=f"Leadership Role cannot be {ctx.guild.default_role.mention}.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if leadership_role is not None and member_role.id == leadership_role.id:
            embed = disnake.Embed(description="Member Role & Leadership Role cannot be the same.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await ctx.response.defer()
        # check if clan is already linked
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = disnake.Embed(description=f"{clan.name} is already linked to this server.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        await self.bot.clan_db.insert_one({
            "name": clan.name,
            "tag": clan.tag,
            "generalRole": member_role.id,
            "leaderRole": None if leadership_role is None else leadership_role.id,
            "category": category,
            "server": ctx.guild.id,
            "clanChannel": None if clan_channel is None else clan_channel.id
        })

        tags = await self.bot.clan_db.distinct("tag")
        self.bot.coc_client.add_war_updates(*tags)
        self.bot.clan_list.append(clan.tag)
        embed = disnake.Embed(title=f"{clan.name} successfully added.",
                              description=f"Clan Tag: {clan.tag}\n"
                                          f"General Role: {member_role.mention}\n"
                                          f"Leadership Role: {None if leadership_role is None else leadership_role.mention}\n"
                                          f"Clan Channel: {None if clan_channel is None else clan_channel.mention}\n"
                                          f"Category: {category}",
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        await ctx.edit_original_message(embed=embed)


    @commands.slash_command(name="clan-remove", description="Remove a clan from the server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def removeClan(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: clan to add to server [clan tag, alias, or autocomplete]
        """
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = disnake.Embed(description=f"{clan.name} is not currently set-up as a family clan.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        embed = disnake.Embed(description=f"Are you sure you want to remove {clan.name} [{clan.tag}]?",
                              color=disnake.Color.red())
        embed.set_thumbnail(url=clan.badge.large)

        page_buttons = [
            disnake.ui.Button(label="Yes", emoji="✅", style=disnake.ButtonStyle.green,
                              custom_id="Yes"),
            disnake.ui.Button(label="No", emoji="❌", style=disnake.ButtonStyle.red,
                              custom_id="No")
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)

        await ctx.edit_original_message(embed=embed, components=[buttons])
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        chose = False
        while chose is False:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author.id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", ephemeral=True)
                continue

            chose = res.data.custom_id

            if chose == "No":
                embed = disnake.Embed(description=f"Sorry to hear that. Canceling the command now.",
                                      color=disnake.Color.green())
                embed.set_thumbnail(url=clan.badge.large)
                return await res.response.edit_message(embed=embed,
                                                       components=[])

        await self.bot.clan_db.find_one_and_delete({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})

        tags = await self.bot.clan_db.distinct("tag")
        self.bot.coc_client.add_war_updates(*tags)
        embed = disnake.Embed(
            description=f"{clan.name} removed as a family clan.",
            color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return await msg.edit(embed=embed, components=[])


    #LOG SETUPS
    @setup.sub_command_group(name="log", description="Set a variety of different clan logs for your server!")
    async def set_log(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @set_log.sub_command(name="add", description="Set a variety of different clan logs for your server!")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def set_log_add(self, ctx: disnake.ApplicationCommandInteraction,
                          clan: coc.Clan = commands.Param(converter=clan_converter),
                          channel: Union[disnake.TextChannel, disnake.Thread] = commands.Param(default=None,
                                                                                               name="channel")):
        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.edit_original_message(
                "This clan is not set up on this server. Use `/addclan` to get started.")

        if channel is None:
            channel = ctx.channel

        log_types = ["Clan Capital Log", "Join Log", "Legend Log", "Donation Log", "Clan Log", "War Log - Continuous",
                     "War Log - Panel"]
        type_dict = {"Clan Capital Log": "clan_capital", "Join Log": "joinlog",
                     "War Log - Continuous": "war_log-Continuous Feed", "War Log - Panel": "war_log-Update Feed",
                     "Legend Log": "legend_log", "Donation Log": "donolog", "Clan Log": "upgrade_log"}
        swapped_type_dict = {v: k for k, v in type_dict.items()}
        options = []
        for log_type in log_types:
            options.append(disnake.SelectOption(label=log_type, emoji=self.bot.emoji.clock.partial_emoji,
                                                value=type_dict[log_type]))
        select = disnake.ui.Select(
            options=options,
            placeholder="Select logs!",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        embed = disnake.Embed(
            description=f"Choose the logs that you would like to add for {clan.name} in {channel.mention}\n"
                        f"Use </set log help:1033741922562494569> for more details", color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id and res.author.id == ctx.author.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await ctx.edit_original_message(components=[])
        await res.response.defer()

        if "war_log-Continuous Feed" in res.values and "war_log-Update Feed" in res.values:
            embed = disnake.Embed(description=f"Cannot choose both war log types!", color=disnake.Color.red())
            return await res.edit_original_message(embed=embed, components=[])

        if isinstance(channel, disnake.Thread):
            await channel.add_user(self.bot.user)

        text = ""
        for value in res.values:
            if "war_log" in value:
                log_type = value.split("-")[-1]
                print(log_type)
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan.tag},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"war_log": channel.id, "attack_feed": log_type}})
                text += f"{swapped_type_dict[value]}- {self.bot.emoji.yes}Success\n"
            elif value == "legend_log":
                success = await self.legend_log(ctx, clan, channel)
                if success:
                    text += f"{swapped_type_dict[value]}- {self.bot.emoji.yes}Success\n"
                else:
                    text += f"{swapped_type_dict[value]}- {self.bot.emoji.no}Error\n"
            else:
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan.tag},
                    {"server": ctx.guild.id}
                ]}, {'$set': {f"{value}": channel.id}})
                text += f"{swapped_type_dict[value]}- {self.bot.emoji.yes}Success\n"

        embed = disnake.Embed(title=f"Logs Created for {clan.name}", description=text,
                              color=disnake.Color.green())
        # embed.set_thumbnail(url=clan.badge.medium.url)
        await res.edit_original_message(embed=embed, components=[])

    async def legend_log(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan,
                         channel: Union[disnake.TextChannel, disnake.Thread]):
        # may activate if duplicates becomes an issue
        # clan_webhooks = await self.bot.clan_db.distinct("legend_log.webhook", filter={"server": ctx.guild.id})
        is_thread = False
        try:
            bot_av = self.bot.user.avatar.read().close()
            if isinstance(channel, disnake.Thread):
                webhooks = await channel.parent.webhooks()
            else:
                webhooks = await channel.webhooks()
            webhook = next((w for w in webhooks if w.user.id == self.bot.user.id), None)
            if webhook is None:
                if isinstance(channel, disnake.Thread):
                    webhook = await channel.parent.create_webhook(name="ClashKing", avatar=bot_av,
                                                                  reason="Legends Feed")
                else:
                    webhook = await channel.create_webhook(name="ClashKing", avatar=bot_av, reason="Legends Feed")
        except Exception as e:
            return False

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"legend_log.webhook": webhook.id}})
        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"legend_log.thread": None}})

        if isinstance(channel, disnake.Thread):
            await self.bot.clan_db.update_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]}, {'$set': {"legend_log.thread": ctx.channel.id}})
            await webhook.send("Legend Log Success", username='ClashKing',
                               avatar_url="https://cdn.discordapp.com/attachments/923767060977303552/1033385579091603497/2715c2864c10dc64a848f7d12d1640d0.png",
                               thread=channel)

        else:
            await webhook.send("Legend Log Success", username='ClashKing',
                               avatar_url="https://cdn.discordapp.com/attachments/923767060977303552/1033385579091603497/2715c2864c10dc64a848f7d12d1640d0.png")

        return True

    @set_log.sub_command(name="remove", description="Remove a log for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def set_log_remove(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        type_dict = {"Clan Capital Log": "clan_capital", "Join Log": "joinlog", "War Log": "war_log",
                     "Legend Log": "legend_log", "Donation Log": "donolog", "Clan Log": "upgrade_log"}
        rev_type_dict = {v: k for k, v in type_dict.items()}

        types_setup = []
        for log_type in type_dict.values():
            if results.get(log_type) is not None:
                if log_type == "legend_log":
                    if results.get(f"{log_type}.channel") is not None:
                        types_setup.append(rev_type_dict[log_type])
                else:
                    types_setup.append(rev_type_dict[log_type])

        options = []
        for log_type in types_setup:
            options.append(disnake.SelectOption(label=log_type, emoji=self.bot.emoji.clock.partial_emoji, value=type_dict[log_type]))

        if not options:
            embed = disnake.Embed(description=f"{clan.name} has no logs set up on this server.", color=disnake.Color.red())
            embed.set_thumbnail(url=clan.badge.url)
            return await ctx.edit_original_message(embed=embed)
        select = disnake.ui.Select(
            options=options,
            placeholder="Select logs to remove",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        content = f"Choose the logs that you would like to remove for {clan.name}"
        await ctx.edit_original_message(content=content, components=dropdown)

        res: disnake.MessageInteraction = await self.interaction_handler(ctx=ctx, function=None)

        removed = []
        for log_type in res.values:
            removed.append(rev_type_dict[log_type])
            log_channel = results.get(log_type)
            if log_type == "legend_log" and log_channel is not None:
                log_channel = log_channel.get("webhook")

            if log_type == "legend_log":
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan.tag},
                    {"server": ctx.guild.id}
                ]}, {'$set': {f"{log_type}.thread": None}})
                log_type += ".webhook"

            await self.bot.clan_db.update_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]}, {'$set': {f"{log_type}": None}})

        removed_text = ", ".join(removed)
        embed = disnake.Embed(description=f"`{removed_text}` removed for {clan.name}", color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.url)
        await ctx.edit_original_message(content="", embed=embed, components=[])

    @set_log.sub_command(name="help", description="Overview of common questions & functionality of logs")
    async def set_log_help(self, ctx: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(title="ClashKing Clan Log Overview",
                              description="__Answer to Common Questions__\n"
                                          "- The logs pull updated info about every 4-5 minutes\n"
                                          "- The logs support channels, threads, & forums"
                                          "- Multiple logs can be set in one channel")
        embed.add_field(name="Clan Capital Log",
                        value="- Reports Clan Capital Donations\n"
                              "- Reports Clan Capital Contributions (slightly inaccurate due to the COC API, will be fixed in a future update)\n"
                              "- Will post a overview for the week when Raid Weekend ends\n"
                              "- **Cannot** show what buildings gold is contributed to")
        embed.add_field(name="Join Leave Log",
                        value="- Reports Clan Member Joins\n"
                              "- Reports Clan Member Leaves\n"
                              "- Will show what clan the member left to")
        embed.add_field(name="Legend Log",
                        value="- Reports Legend Attacks & Defenses\n"
                              "- Some inaccuracies, `/faq` covers in more detail")
        embed.add_field(name="War Log",
                        value="- 2 styles\n"
                              "- Panel will post an embed just when the war starts, then update the embed as the war continues\n"
                              "- Continuous will post embeds everytime something happens in war (attack, defense, war start/end)")
        embed.add_field(name="Donation Log",
                        value="- Reports amount of troops donated & received and by which clan members\n"
                              "- **Cannot** show which troops were donated")
        embed.add_field(name="Clan Log",
                        value="- Reports when upgrades are done (townhall, troop, hero, pets, sieges, or spells)\n"
                              "- Reports when a name change is made\n"
                              "- Reports when a super troop is boosted\n"
                              "- Reports when a players league changes\n"
                              "- **Cannot** get building upgrades or when an lab or hero upgrade is started")
        await ctx.edit_original_message(embed=embed)


    #COUNTDOWNS
    @setup.sub_command(name="countdowns", description="Create countdowns for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def voice_setup(self, ctx: disnake.ApplicationCommandInteraction):

        types = ["CWL", "Clan Games", "Raid Weekend", "EOS", "Clan Member Count"]
        emojis = [self.bot.emoji.cwl_medal, self.bot.emoji.clan_games, self.bot.emoji.raid_medal, self.bot.emoji.trophy, self.bot.emoji.person]
        options = []
        for type, emoji in zip(types, emojis):
            options.append(disnake.SelectOption(label=type if type != "EOS" else "EOS (End of Season)", emoji=emoji.partial_emoji, value=type))

        select = disnake.ui.Select(
            options=options,
            placeholder="Select Options",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        await ctx.edit_original_message(content="**Select Countdowns/Statbars to Create Below**", components=dropdown)

        res: disnake.MessageInteraction = await self.interaction_handler(ctx=ctx)


        for countdown_type in res.values:
            try:
                if type == "Clan Games":
                    time_ = await calculate_time(countdown_type)
                    channel = await ctx.guild.create_voice_channel(name=f"CG {time_}")
                elif type == "Raid Weekend":
                    time_ = await calculate_time(countdown_type)
                    channel = await ctx.guild.create_voice_channel(name=f"Raids {time_}")
                elif type == "Clan Member Count":
                    clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
                    results = await self.bot.player_stats.count_documents(filter={"clan_tag": {"$in": clan_tags}})
                    channel = await ctx.guild.create_voice_channel(name=f"{results} Clan Members")
                else:
                    time_ = await calculate_time(countdown_type)
                    channel = await ctx.guild.create_voice_channel(name=f"{type} {time_}")
            except disnake.Forbidden:
                embed = disnake.Embed(description="Bot requires admin to create & set permissions for channel. **Channel will not update**",
                                      color=disnake.Color.red())
                return await ctx.send(embed=embed)

            overwrite = disnake.PermissionOverwrite()
            overwrite.view_channel = True
            overwrite.connect = False
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

            if type == "CWL":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"cwlCountdown": channel.id}})
            elif type == "Clan Games":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"gamesCountdown": channel.id}})
            elif type == "Raid Weekend":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"raidCountdown": channel.id}})
            elif type == "Clan Member Count":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"memberCount": channel.id}})
            else:
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"eosCountdown": channel.id}})


        embed = disnake.Embed(description=f"`{', '.join(res.values)}` Stat Bars Created", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await res.edit_original_message(content="", embed=embed, components=[])

    @setup.sub_command(name="autoboards", description="Create family autoboards for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def autoboard_create(self, ctx: disnake.ApplicationCommandInteraction):
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})

        if not clan_tags:
            embed = disnake.Embed(description="**No clans set up on this server, use `/setup clan-add` to get started.**", color=disnake.Color.red())
            await ctx.edit_original_message(embed=embed)

        content = "**What kind of autoboards would you like to create?**"
        page_buttons = [
            disnake.ui.Button(label="Family", style=disnake.ButtonStyle.grey, custom_id="family"),
            disnake.ui.Button(label="Location", style=disnake.ButtonStyle.grey, custom_id="location"),
            disnake.ui.Button(label="Clan", style=disnake.ButtonStyle.grey, custom_id="clan")
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)
        await ctx.edit_original_message(content=content, components=[buttons])

        res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)

        scope_type = res.data.custom_id

        page_buttons = [
            disnake.ui.Button(label="Save", emoji=self.bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green, custom_id="Save"),
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)

        family_types = ["Troop Donations", "Capital Donations", "Player Trophies", "Clan Trophies", "Loot Leaderboard", "Legend Leaderboard"]
        location_types = ["Player Trophies Lb", "Clan Trophies Lb", "Clan Capital Lb"]
        clan_types = ["Capital Donations", "Player Trophies", "Loot Leaderboard", "Legend Leaderboard"]

        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_options = []
        for day in days:
            day_options.append(disnake.SelectOption(label=day, value=day, emoji=self.bot.emoji.calendar.partial_emoji))

        day_select = disnake.ui.Select(
            options=day_options,
            placeholder="Days to Post",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(day_options),  # the maximum number of options a user can select
        )

        if scope_type == "family":
            options = []
            for type in family_types:
                options.append(disnake.SelectOption(label=type, value=type))
            select = disnake.ui.Select(
                options=options,
                placeholder="Board Type",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            channel = disnake.ui.ChannelSelect(placeholder="Choose Channel", max_values=1, channel_types=[disnake.ChannelType.text, disnake.ChannelType.public_thread])
            dropdown = [disnake.ui.ActionRow(select), disnake.ui.ActionRow(day_select), disnake.ui.ActionRow(channel), buttons]
        elif scope_type == "location":
            clans = await self.bot.get_clans(tags=clan_tags)
            locations = []
            for clan in clans:
                try:
                    locations.append(str(clan.location))
                except:
                    pass

            locations = ["Global"] + list(set(locations))[:24]
            options = []
            for country in locations:
                options.append(disnake.SelectOption(label=f"{country}", value=f"{country}"))
            country_select = disnake.ui.Select(
                options=options,
                placeholder="Locations",
                min_values=1,  # the minimum number of options a user must select
                max_values=1  # the maximum number of options a user can select
            )

            options = []
            for type in location_types:
                options.append(disnake.SelectOption(label=type, value=type))

            select = disnake.ui.Select(
                options=options,
                placeholder="Board Type",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            channel = disnake.ui.ChannelSelect(placeholder="Choose Channel", max_values=1, channel_types=[disnake.ChannelType.text, disnake.ChannelType.public_thread])
            dropdown = [disnake.ui.ActionRow(select), disnake.ui.ActionRow(country_select), disnake.ui.ActionRow(day_select), disnake.ui.ActionRow(channel), buttons]

        elif scope_type == "clan":
            options = []
            for type in clan_types:
                options.append(disnake.SelectOption(label=type, value=type))
            select = disnake.ui.Select(
                options=options,
                placeholder="Board Type",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            clans: list[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            clans = [clan for clan in clans if clan is not None and clan.member_count != 0]
            clans = sorted(clans, key=lambda x: x.member_count, reverse=True)
            options = []
            for clan in clans:
                try:
                    options.append(disnake.SelectOption(label=clan.name, value=clan.tag))
                except:
                    pass
            clan_select = disnake.ui.Select(
                options=options[:25],
                placeholder="Clan",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            channel = disnake.ui.ChannelSelect(placeholder="Choose Channel", max_values=1, channel_types=[disnake.ChannelType.text, disnake.ChannelType.public_thread])
            dropdown = [disnake.ui.ActionRow(select), disnake.ui.ActionRow(clan_select), disnake.ui.ActionRow(day_select), disnake.ui.ActionRow(channel), buttons]

        await ctx.edit_original_message(content="**Choose board type & Settings**\n- All Boards will post between 4:50 - 5:00 am UTC on the days you select, plus end of season regardless of day.", components=dropdown)

        location = None
        board_type = None
        days_to_post = []
        channel = None
        clan = None
        save = False
        while not save:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            if "button" in str(res.data.component_type):
                if channel is None:
                    await res.send(content="Must select a channel", ephemeral=True)
                elif board_type is None:
                    await res.send(content="Must select a board type", ephemeral=True)
                elif scope_type == "clan" and clan is None:
                    await res.send(content="Must select a clan", ephemeral=True)
                elif scope_type == "location" and location is None:
                    await res.send(content="Must select a location", ephemeral=True)
                elif not days_to_post:
                    await res.send(content="Must select days to post this autoboard on", ephemeral=True)
                else:
                    save = True
            elif "string_select" in str(res.data.component_type):
                if res.values[0] in location_types + clan_types + family_types:
                    board_type = res.values[0]
                elif "#" in res.values[0]:
                    clan = res.values[0]
                elif res.values[0] in days:
                    days_to_post = res.values
                else:
                    location = res.values[0]
            else:
                channel = res.values[0]

        await self.bot.autoboard_db.insert_one({
            "scope" : scope_type,
            "board_type" : board_type,
            "location" : location,
            "days" : days_to_post,
            "channel" : channel
        })

        embed= disnake.Embed(description="**Autoboard Successfully Created**", color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=[], content="")

    @setup.sub_command(name="welcome-link", description="Create a custom welcome message that can include linking buttons")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def welcome_message(self, ctx: disnake.ApplicationCommandInteraction, channel: Union[disnake.TextChannel, disnake.Thread], custom_embed: str = None):
        if custom_embed is None:
            embed = disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                                  description=f"To link your account, press the link button below to get started.",
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
        else:
            result = await self.bot.custom_embeds.find_one(
                {"$and": [{"server_id": ctx.guild.id}, {"name": custom_embed}]})
            if result is None:
                return await ctx.send(content=f"Custom Embed - `{custom_embed}` does not exist")
            embed = disnake.Embed.from_dict(data=result.get("embed"))

        stat_buttons = [disnake.ui.Button(label="Link Account", emoji="🔗", style=disnake.ButtonStyle.green, disabled=True,
                                          custom_id="LINKDEMO"),
                        disnake.ui.Button(label="Help", emoji="❓", style=disnake.ButtonStyle.grey, disabled=True,
                                          custom_id="LINKDEMOHELP")]
        await ctx.send(content=f"Welcome Message Set in {channel.mention}\n||(buttons for demo & will work on the live version)||", embed=embed, components=stat_buttons)
        await self.bot.server_db.update_one({"server" : ctx.guild_id}, {"$set" : {"welcome_link_channel" : channel.id, "welcome_link_embed" : embed.to_dict()}})


    @setup.sub_command(name="remove", description="Remove various features")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setup_remove(self, ctx: disnake.ApplicationCommandInteraction):
        pass


    @welcome_message.autocomplete("custom_embed")
    async def embed_names(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        results = await self.bot.custom_embeds.distinct("name", filter={"server_id": ctx.guild.id})
        return_list = []
        for result in results:
            if query.lower() in result.lower():
                return_list.append(result)
                if len(return_list) == 25:
                    break
        return return_list


    @removeClan.autocomplete("clan")
    @set_log_add.autocomplete("clan")
    @set_log_remove.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]

    @addClan.autocomplete("category")
    async def autocomp_names(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        categories = ["General", "Feeder", "War", "Esports"]
        if query != "":
            categories.append(query)
        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if query.lower() in category.lower():
                if category not in categories:
                    categories.append(category)
        return categories[0:24]

def setup(bot: CustomClient):
    bot.add_cog(SetupCommands(bot))