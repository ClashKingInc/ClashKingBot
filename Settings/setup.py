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
from operator import attrgetter
from Exceptions.CustomExceptions import *
from datetime import datetime
from utils.discord_utils import permanent_image

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

    @setup.sub_command(name="autoeval", description="Turn autoeval on/off")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def autoeval(self, ctx: disnake.ApplicationCommandInteraction, option=commands.Param(choices=["On", "Off"]),
                       log: disnake.TextChannel = commands.Param(default=None, name="log")):

        await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"autoeval": option == "On"}})

        log_text = ""
        if log is not None:
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"autoeval_log": log.id}})
            log_text = f"and will log in {log.mention}"
        await ctx.edit_original_message(f"**Autoeval is now turned {option} {log_text}**",
                                        allowed_mentions=disnake.AllowedMentions.none())



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
                modal_inter, embed = await self.basic_embed_modal(ctx=ctx)
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
            embed = disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                                  description=f"To link your account, press the link button below to get started.",
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)


        stat_buttons = [disnake.ui.Button(label="Link Account", emoji="🔗", style=disnake.ButtonStyle.green, disabled=True,
                                          custom_id="LINKDEMO"),
                        disnake.ui.Button(label="Help", emoji="❓", style=disnake.ButtonStyle.grey, disabled=True,
                                          custom_id="LINKDEMOHELP")]
        await ctx.send(content=f"Welcome Message Set in {channel.mention}\n||(buttons for demo & will work on the live version)||", embed=embed, components=stat_buttons)
        await self.bot.server_db.update_one({"server" : ctx.guild_id}, {"$set" : {"link_channel" : channel.id, "welcome_link_embed" : embed.to_dict()}})




    @setup.sub_command(name="remove", description="Remove various features")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setup_remove(self, ctx: disnake.ApplicationCommandInteraction):
        pass




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



    async def basic_embed_modal(self, ctx: disnake.ApplicationCommandInteraction, previous_embed=None):
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
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            return None

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

        embed = await self.generate_embed(our_embed=our_embed, embed=previous_embed)
        await modal_inter.response.defer()

        return (modal_inter, embed)


    async def generate_embed(self, our_embed: dict, embed=None):
        if embed is None:
            embed = disnake.Embed()
        for attribute, embed_field in our_embed.items():
            if embed_field is None or embed_field == "":
                continue
            attribute: str
            if "field" in attribute:
                if embed_field["name"] is None or embed_field == "":
                    continue
                embed.insert_field_at(index=int(attribute.split("_")[1]) - 1, name=embed_field["name"],
                                      value=embed_field["value"], inline=embed_field["inline"])
            elif "image" in attribute:
                if embed_field != "" and embed_field != "None":
                    embed_field = await permanent_image(self.bot, embed_field)
                if embed_field == "None":
                    embed._image = None
                else:
                    embed.set_image(url=embed_field)
            elif "thumbnail" in attribute:
                if embed_field != "" and embed_field != "None":
                    embed_field = await permanent_image(self.bot, embed_field)
                if embed_field == "None":
                    embed._thumbnail = None
                else:
                    embed.set_thumbnail(url=embed_field)
            elif "footer" in attribute:
                if embed_field["text"] is None:
                    continue
                embed.set_footer(icon_url=embed_field["icon"], text=embed_field["text"])
            elif "author" in attribute:
                if embed_field["text"] is None:
                    continue
                embed.set_author(icon_url=embed_field["icon"], name=embed_field["text"])
            else:
                if len(attribute.split(".")) == 2:
                    obj = attrgetter(attribute.split(".")[0])(embed)
                    setattr(obj, attribute.split(".")[1], embed_field)
                else:
                    setattr(embed, attribute, embed_field)

        return embed

def setup(bot: CustomClient):
    bot.add_cog(SetupCommands(bot))