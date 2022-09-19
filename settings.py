import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import CustomServer, ServerClan

class misc(commands.Cog, name="Settings"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="set")
    async def set(self, ctx):
        pass

    @set.sub_command(name="banlist-channel", description="Set channel to post banlist in")
    async def setbanlist(self, ctx: disnake.ApplicationCommandInteraction, channel:disnake.TextChannel):
        """
            Parameters
            ----------
            channel: channel to post & update banlist in when changes are made
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"banlist": channel.id}})
        await ctx.send(f"Banlist channel switched to {channel.mention}")

    @set.sub_command(name="greeting", description="Set a custom clan greeting message")
    async def setgreeting(self, ctx: disnake.ApplicationCommandInteraction, greet):
        """
            Parameters
            ----------
            greet: text for custom new member clan greeting
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"greeting": greet}})

        await ctx.send(f"Greeting is now:\n\n"
                        f"{ctx.author.mention}, welcome to {ctx.guild.name}! {greet}",
                         allowed_mentions=disnake.AllowedMentions.none())

    @set.sub_command(name="clan-channel", description="Set a new clan channel for a clan")
    async def channel(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: disnake.TextChannel):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            channel: New channel to switch to
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan_search = clan.lower()
        first_clan = clan
        results = await self.bot.clan_db.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await self.bot.getClan(tag)
        else:
            clan = await self.bot.getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await self.bot.getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"clanChannel": channel.id}})

        await ctx.send(f"Clan channel switched to {channel.mention}")

    @set.sub_command(name="member-role", description="Set a new member role for a clan")
    async def role(self, ctx: disnake.ApplicationCommandInteraction, clan: str, role: disnake.Role):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            role: New role to switch to
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan_search = clan.lower()
        first_clan = clan
        results = await self.bot.clan_db.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await self.bot.getClan(tag)
        else:
            clan = await self.bot.getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await self.bot.getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"generalRole": role.id}})

        embed = disnake.Embed(
            description=f"General role switched to {role.mention}",
            color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="leader-role", description="Set a new leader role for a clan")
    async def leaderrole(self, ctx: disnake.ApplicationCommandInteraction, clan: str, role: disnake.Role):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            role: New role to switch to
        """

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan_search = clan.lower()
        first_clan = clan
        results = await self.bot.clan_db.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await self.bot.getClan(tag)
        else:
            clan = await self.bot.getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await self.bot.getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"leaderRole": role.id}})

        embed = disnake.Embed(
            description=f"Leader role switched to {role.mention}",
            color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="clan-category", description="Set a new category for a clan")
    async def category(self, ctx: disnake.ApplicationCommandInteraction, clan: str, new_category: str):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            new_category: new category to use for this clan (type one or choose from autocomplete)
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan_search = clan.lower()
        first_clan = clan
        results = await self.bot.clan_db.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await self.bot.getClan(tag)
        else:
            clan = await self.bot.getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await self.bot.getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"category": new_category}})

        embed = disnake.Embed(description=f"Category for {clan.name} changed to {new_category}.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="clan-abbreviation", description="Set a new abbreviation for a clan (used for auto nicknames)")
    async def abbreviation(self, ctx: disnake.ApplicationCommandInteraction, clan: str, new_abbreviation: str):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            new_abbreviation: Maximum of 4 characters
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan_search = clan.lower()
        first_clan = clan
        results = await self.bot.clan_db.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await self.bot.getClan(tag)
        else:
            clan = await self.bot.getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await self.bot.getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        if len(new_abbreviation) >= 5:
            return await ctx.send("Abbreviation must be 1 to 4 characters.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"abbreviation": new_abbreviation.upper()}})

        embed = disnake.Embed(description=f"Abbreviation for {clan.name} changed to {new_abbreviation.upper()}.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="join-log", description="Set up a join & leave log for a clan")
    async def joinleavelog(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: disnake.TextChannel):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            channel: channel to set the join/leave log to
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan_search = clan.lower()
        first_clan = clan
        results = await self.bot.clan_db.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await self.bot.getClan(tag)
        else:
            clan = await self.bot.getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await self.bot.getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"joinlog": channel.id}})

        embed = disnake.Embed(description=f"Join/Leave Log set in {channel.mention} for {clan.name}",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="clancapital-log", description="Set up a clan capital log for a clan")
    async def clancapitallog(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: disnake.TextChannel):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            channel: channel to set the join/leave log to
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan_search = clan.lower()
        first_clan = clan
        results = await self.bot.clan_db.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await self.bot.getClan(tag)
        else:
            clan = await self.bot.getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await self.bot.getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"clan_capital": channel.id}})

        embed = disnake.Embed(description=f"Clan Capital Log set in {channel.mention} for {clan.name}",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="war-log-beta", description="Set up a war log for a clan. in beta.")
    async def warlog(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: disnake.TextChannel):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the war log to
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan = await self.bot.getClan(clan)

        if clan is None:
            return await ctx.send("Not a valid clan tag")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"war_log": channel.id}})

        embed = disnake.Embed(description=f"War Log set in {channel.mention} for {clan.name}",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="legend-log", description="Set up a legend log for a clan")
    async def legend_log(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: disnake.TextChannel):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the legend log to
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan = await self.bot.getClan(clan)

        if clan is None:
            return await ctx.send("Not a valid clan tag")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"legend_log.channel": channel.id}})

        embed = disnake.Embed(description=f"Legend Log set in {channel.mention} for {clan.name}",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="leadership-eval", description="Have eval assign leadership role to clan coleads & leads (on default)")
    async def leadership_eval(self, ctx: disnake.ApplicationCommandInteraction, option=commands.Param(choices=["On", "Off"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        await server.change_leadership_eval(option=(option == "On"))
        embed = disnake.Embed(description=f"Leadership Eval turned {option}.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="auto-nickname",
                     description="Have linking change discord name to name | clan (on default)")
    async def auto_nickname(self, ctx: disnake.ApplicationCommandInteraction,
                              option=commands.Param(choices=["On", "Off"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        await server.change_auto_nickname(option=(option == "On"))
        embed = disnake.Embed(description=f"Auto Nickname turned {option}.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)


    @set.sub_command(name="reddit-recruit-feed", description="Feed of searching for a clan posts on the recruiting subreddit")
    async def reddit_recruit(self, ctx: disnake.ApplicationCommandInteraction, role_to_ping: disnake.Role, channel: disnake.TextChannel, remove=commands.Param(default=None, choices=["Remove Feed"])):
        """
            Parameters
            ----------
            channel: channel to set the feed to
            role_to_ping: role to ping when a new recruit appears
            remove: option to remove this feed
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.", color=disnake.Color.red())

            return await ctx.send(embed=embed)
        await ctx.response.defer()
        if remove is None:
            role_id = None if role_to_ping is None else role_to_ping.id
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {"$set": {"reddit_feed": channel.id, "reddit_role": role_id}})

            embed = disnake.Embed(description=f"**Reddit Recruit feed set to {channel.mention}**", color=disnake.Color.green())

        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {"$set": {"reddit_feed": None, "reddit_role": None}})

            embed = disnake.Embed(description="**Reddit Recruit feed removed**", color=disnake.Color.green())

        return await ctx.edit_original_message(embed=embed)

    @set.sub_command(name="ytbase-feed",
                     description="Feed of yt base links from new yt videos")
    async def ytbase_feed(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel,
                             remove=commands.Param(default=None, choices=["Remove Feed"])):
        """
            Parameters
            ----------
            channel: channel to set the feed to
            remove: option to remove this feed
        """
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())

            return await ctx.send(embed=embed)
        await ctx.response.defer()
        if remove is None:
            await self.bot.server_db.update_one({"server": ctx.guild.id},
                                                {"$set": {"yt_feed": channel.id}})

            embed = disnake.Embed(description=f"**YT base feed set to {channel.mention}**",
                                  color=disnake.Color.green())

        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id},
                                                {"$set": {"yt_feed": None}})

            embed = disnake.Embed(description="**YT Base feed removed**", color=disnake.Color.green())

        return await ctx.edit_original_message(embed=embed)

    @set.sub_command(name="remove", description="Remove a setup")
    async def remove_setup(self, ctx: disnake.ApplicationCommandInteraction, clan: str,
                           log_to_remove=commands.Param(choices=["Clan Capital Log", "Join Log", "War Log", "Legend Log"])):
        type_dict = {"Clan Capital Log": "clan_capital", "Join Log": "joinlog", "War Log": "war_log", "Legend Log" : "legend_log"}
        log_type = type_dict[log_to_remove]

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan = await self.bot.getClan(clan)

        if clan is None:
            return await ctx.send("Not a valid clan tag")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")


        log_channel = results.get(log_type)
        if log_type == "legend_log" and log_channel is not None:
            log_channel = log_channel.get("channel")

        if log_channel is None:
            embed = disnake.Embed(description=f"This clan does not have a {log_to_remove} set up on this server.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if log_type == "legend_log":
            log_type += ".channel"

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {f"{log_type}": None}})

        channel = await self.bot.fetch_channel(log_channel)

        embed = disnake.Embed(description=f"{log_to_remove} in {channel.mention} removed for {clan.name}",
                              color=disnake.Color.green())

        await ctx.send(embed=embed)

    @commands.slash_command(name="server-settings", description="Complete list of channels & roles set up on server")
    async def server_info(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        await server.initialize_server()
        embed = disnake.Embed(title=f"{ctx.guild.name} Server Settings",
                              color=disnake.Color.green())
        embed.add_field(name="Banlist Channel:", value=f"{server.banlist_channel}", inline=True)
        embed.add_field(name="Reddit Feed:", value=f"{server.reddit_feed}", inline=True)
        embed.add_field(name="Leadership Eval:", value=f"{server.leadership_eval}", inline=True)
        embed.add_field(name="Clan Greeting Message:", value=f"{server.clan_greeting}", inline=False)

        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embeds = [embed]
        clans = server.server_clans
        for clan in clans:
            clan: ServerClan
            got_clan = await self.bot.getClan(clan.tag)
            embed = disnake.Embed(title=f"{clan.name}", color=disnake.Color.green())
            embed.set_thumbnail(url=got_clan.badge.url)
            embed.add_field(name="Member Role:", value=f"{clan.member_role}", inline=True)
            embed.add_field(name="Leadership Role:", value=f"{clan.leader_role}", inline=True)
            embed.add_field(name="Clan Channel:", value=f"{clan.clan_channel}", inline=True)
            embed.add_field(name="War Log:", value=f"{clan.war_log}", inline=True)
            embed.add_field(name="Join Log:", value=f"{clan.join_log}", inline=True)
            embed.add_field(name="Clan Capital Log:", value=f"{clan.capital_log}", inline=True)
            embeds.append(embed)

        chunk_embeds = [embeds[i:i + 10] for i in range(0, len(embeds), 10)]

        for embeds in chunk_embeds:
            if embeds == chunk_embeds[0]:
                await ctx.edit_original_message(embeds=embeds)
            else:
                await ctx.followup.send(embeds=embeds)


    @channel.autocomplete("clan")
    @role.autocomplete("clan")
    @leaderrole.autocomplete("clan")
    @category.autocomplete("clan")
    @joinleavelog.autocomplete("clan")
    @clancapitallog.autocomplete("clan")
    @warlog.autocomplete("clan")
    @remove_setup.autocomplete("clan")
    @legend_log.autocomplete("clan")
    @abbreviation.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[:25]

    @category.autocomplete("new_category")
    async def autocomp_category(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        categories = []
        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if query.lower() in category.lower() and category not in categories:
                categories.append(category)
        return categories[:25]


def setup(bot: CustomClient):
    bot.add_cog(misc(bot))