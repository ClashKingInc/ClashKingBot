import disnake
import coc

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from utils.general import calculate_time
from main import check_commands
from typing import Union
from utils.discord_utils import get_webhook_for_channel
from Exceptions.CustomExceptions import *
from utils.discord_utils import  interaction_handler, basic_embed_modal
from CustomClasses.CustomServer import DatabaseClan

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
        pass

    @setup.sub_command(name="autoeval", description="Turn autoeval on/off")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def autoeval(self, ctx: disnake.ApplicationCommandInteraction, option=commands.Param(choices=["On", "Off"]),
                       log: disnake.TextChannel = commands.Param(default=None, name="log")):
        await ctx.response.defer()

        await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"autoeval": option == "On"}})

        log_text = ""
        if log is not None:
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"autoeval_log": log.id}})
            log_text = f"and will log in {log.mention}"
        await ctx.edit_original_message(f"**Autoeval is now turned {option} {log_text}**", allowed_mentions=disnake.AllowedMentions.none())

    @setup.sub_command(name="logs", description="Set a variety of different clan logs for your server!")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def set_log_add(self, ctx: disnake.ApplicationCommandInteraction,
                          clan: coc.Clan = commands.Param(converter=clan_converter), mode:str = commands.Param(choices=["Add/Edit", "Remove"]),
                          channel: Union[disnake.TextChannel, disnake.Thread] = commands.Param(default=None)):
        await ctx.response.defer()

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            raise ThingNotFound("**This clan is not set up on this server. Use `/addclan` to get started.**")

        db_clan = DatabaseClan(bot=self.bot, data=results)
        channel = ctx.channel if channel is None else channel

        log_types = {"Member Join" : db_clan.join_log, "Member Leave" : db_clan.leave_log, "War Log" : db_clan.war_log, "War Panel" : db_clan.war_panel,
                     "Capital Donations" : db_clan.capital_donations, "Capital Attacks" : db_clan.capital_attacks, "Capital Panel" : db_clan.raid_panel,
                     "Capital Weekly Summary" : db_clan.capital_weekly_summary, "Donation Log" : db_clan.donation_log, "Super Troop Boosts" : db_clan.super_troop_boost_log,
                     "Role Change" : db_clan.role_change, "Troop Upgrade" : db_clan.troop_upgrade, "Townhall Upgrade" : db_clan.th_upgrade, "League Change" : db_clan.league_change,
                     "Spell Upgrade" : db_clan.spell_upgrade, "Hero Upgrade" : db_clan.hero_upgrade, "Name Change" : db_clan.name_change,
                     "Legend Attacks" : db_clan.legend_log_attacks, "Legend Defenses" : db_clan.legend_log_defenses}

        if mode == "Remove":
            for log_type, log in log_types.copy().items():
                if log.webhook is None:
                    del log_types[log_type]

        options = []
        for log_type in log_types.keys():
            options.append(disnake.SelectOption(label=log_type, emoji=self.bot.emoji.clock.partial_emoji, value=log_type))

        select = disnake.ui.Select(
            options=options,
            placeholder="Select logs!",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(options),  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        channel_text = "" if mode == "Remove" else f"in {channel.mention}"
        embed = disnake.Embed(
            description=f"Choose the logs that you would like to {mode.lower()} for {clan.name} {channel_text}\n"
                        f"Visit https://docs.clashking.xyz/clan-setups/log-setup for more info", color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=dropdown)

        res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
        if mode == "Add/Edit":
            webhook = await get_webhook_for_channel(channel=channel, bot=self.bot)
            thread = None
            if isinstance(channel, disnake.Thread):
                await channel.add_user(self.bot.user)
                thread = channel.id


        text = ""
        for value in res.values:
            log = log_types[value]
            if mode == "Add/Edit":
                await log.set_webhook(id=webhook.id)
                await log.set_thread(id=thread)
                mention = webhook.channel.mention if thread is None else f"<#{thread}>"
                text += f'{self.bot.emoji.yes}{value} | {mention}\n'
            elif mode == "Remove":
                await log.set_webhook(id=None)
                await log.set_thread(id=None)
                text += f'{self.bot.emoji.yes}{value} Removed\n'


        embed = disnake.Embed(title=f"Logs for {clan.name}", description=text, color=disnake.Color.green())
        await res.edit_original_message(embed=embed, components=[])


    @setup.sub_command(name="reddit-recruit-feed", description="Feed of searching for a clan posts on the recruiting subreddit")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def reddit_recruit(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel,
                             role_to_ping: disnake.Role = None,
                             remove=commands.Param(default=None, choices=["Remove Feed"])):
        """
            Parameters
            ----------
            channel: channel to set the feed to
            role_to_ping: role to ping when a new recruit appears
            remove: option to remove this feed
        """
        await ctx.response.defer()

        if remove is None:
            role_id = None if role_to_ping is None else role_to_ping.id
            await self.bot.server_db.update_one({"server": ctx.guild.id},
                                                {"$set": {"reddit_feed": channel.id, "reddit_role": role_id}})

            embed = disnake.Embed(description=f"**Reddit Recruit feed set to {channel.mention}**",
                                  color=disnake.Color.green())

        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id},
                                                {"$set": {"reddit_feed": None, "reddit_role": None}})

            embed = disnake.Embed(description="**Reddit Recruit feed removed**", color=disnake.Color.green())

        return await ctx.edit_original_message(embed=embed)


    @setup.sub_command(name="countdowns", description="Create countdowns for your server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def voice_setup(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(default=None, converter=clan_converter)):
        """
            Parameters
            ----------
            clan: for war countdowns
        """
        await ctx.response.defer()

        types = ["CWL", "Clan Games", "Raid Weekend", "EOS", "Clan Member Count", "War"]
        emojis = [self.bot.emoji.cwl_medal, self.bot.emoji.clan_games, self.bot.emoji.raid_medal, self.bot.emoji.trophy, self.bot.emoji.person, self.bot.emoji.war_star]
        if clan is None:
            types = types[:-1]
            emojis = emojis[:-1]
        else:
            types = types[-1:]
            emojis = emojis[-1:]
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

        res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)


        results_list = []
        for type in res.values:
            try:
                if type == "Clan Games":
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f"CG {time_}")
                elif type == "Raid Weekend":
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f"Raids {time_}")
                elif type == "Clan Member Count":
                    clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
                    results = await self.bot.player_stats.count_documents(filter={"clan_tag": {"$in": clan_tags}})
                    channel = await ctx.guild.create_voice_channel(name=f"{results} Clan Members")
                elif type == "EOS":
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f"EOS {time_}")
                elif type == "War":
                    war = await self.bot.get_clanwar(clanTag=clan.tag)
                    time_ = await calculate_time(type, war=war)
                    channel = await ctx.guild.create_voice_channel(name=f"{clan.name}: {time_}")
                else:
                    time_ = await calculate_time(type)
                    channel = await ctx.guild.create_voice_channel(name=f"{type} {time_}")

                overwrite = disnake.PermissionOverwrite()
                overwrite.view_channel = True
                overwrite.connect = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                results_list.append((type, channel))
            except disnake.Forbidden:
                embed = disnake.Embed(description="Bot requires admin to create & set permissions for channel. **Channel will not update**",
                                      color=disnake.Color.red())
                return await ctx.send(embed=embed)

        for type, channel in results_list:
            if type == "CWL":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"cwlCountdown": channel.id}})
            elif type == "Clan Games":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"gamesCountdown": channel.id}})
            elif type == "Raid Weekend":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"raidCountdown": channel.id}})
            elif type == "Clan Member Count":
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"memberCount": channel.id}})
            elif type == "War":
                await self.bot.clan_db.update_one({"$and": [{"tag": clan.tag}, {"server": ctx.guild.id}]}, {"$set" : {"warCountdown" : channel.id}})
            else:
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"eosCountdown": channel.id}})


        embed = disnake.Embed(description=f"`{', '.join(res.values)}` Stat Bars Created", color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await res.edit_original_message(content="", embed=embed, components=[])


    '''@setup.sub_command(name="autoboards", description="Create family autoboards for your server")
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

        family_types = ["Troop Donations", "Capital Donations", "Player Trophies", "Clan Trophies", "Summary Leaderboard", "Legend Leaderboard"]
        location_types = ["Player Trophies Lb", "Clan Trophies Lb", "Clan Capital Lb"]
        clan_types = ["Capital Donations", "Player Trophies", "Summary Leaderboard", "Legend Leaderboard", "Clan Games"]

        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Clan Games End", "EOS"]
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

        await ctx.edit_original_message(content="**Choose board type & Settings**\n- All Boards will post between 4:50 - 5:00 am UTC on the days you select", components=dropdown)

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
        await ctx.edit_original_message(embed=embed, components=[], content="")'''

    @setup.sub_command(name="welcome-link", description="Create a custom welcome message that can include linking buttons")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def welcome_message(self, ctx: disnake.ApplicationCommandInteraction, channel: Union[disnake.TextChannel, disnake.Thread], custom_embed = commands.Param(default="False", choices=["True", "False"]), embed_link: str = None):
        if custom_embed != "False":
            if embed_link is None:
                modal_inter, embed = await basic_embed_modal(bot=self.bot, ctx=ctx)
                ctx = modal_inter
            else:
                await ctx.response.defer()
                try:
                    if "discord.com" not in embed_link:
                        return await ctx.send(content="Not a valid message link", ephemeral=True)
                    link_split = embed_link.split("/")
                    message_id = link_split[-1]
                    channel_id = link_split[-2]

                    channel = await self.bot.getch_channel(channel_id=int(channel_id))
                    if channel is None:
                        return await ctx.send(content="Cannot access the channel this embed is in", ephemeral=True)
                    message = await channel.fetch_message(int(message_id))
                    if not message.embeds:
                        return await ctx.send(content="Message has no embeds", ephemeral=True)
                    embed = message.embeds[0]
                except:
                    return await ctx.send(content=f"Something went wrong :/ An error occured with the message link.", ephemeral=True)
        else:
            await ctx.response.defer()
            embed = None



        stat_buttons = [disnake.ui.Button(label="Link Account", emoji="🔗", style=disnake.ButtonStyle.green, disabled=True,
                                          custom_id="LINKDEMO"),
                        disnake.ui.Button(label="Help", emoji="❓", style=disnake.ButtonStyle.grey, disabled=True,
                                          custom_id="LINKDEMOHELP")]
        if embed is not None:
            await self.bot.server_db.update_one({"server" : ctx.guild_id}, {"$set" : {"welcome_link_channel" : channel.id, "welcome_link_embed" : embed.to_dict()}})
        else:
            await self.bot.server_db.update_one({"server": ctx.guild_id}, {"$set": {"welcome_link_channel": channel.id, "welcome_link_embed": None}})
        if embed is None:
            embed = disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                          description=f"To link your account, press the link button below to get started.",
                          color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.edit_original_message(content=f"Welcome Message Set in {channel.mention}\n||(buttons for demo & will work on the live version)||", embed=embed, components=stat_buttons)




    @set_log_add.autocomplete("clan")
    @voice_setup.autocomplete("clan")
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




def setup(bot: CustomClient):
    bot.add_cog(SetupCommands(bot))