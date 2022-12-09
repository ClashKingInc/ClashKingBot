import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import CustomServer, ServerClan
from main import check_commands
from typing import Union

class misc(commands.Cog, name="Settings"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="set")
    async def set(self, ctx):
        pass

    @set.sub_command(name="banlist-channel", description="Set channel to post banlist in")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setbanlist(self, ctx: disnake.ApplicationCommandInteraction, channel:disnake.TextChannel):
        """
            Parameters
            ----------
            channel: channel to post & update banlist in when changes are made
        """
        await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"banlist": channel.id}})
        await ctx.send(f"Banlist channel switched to {channel.mention}")

    @set.sub_command(name="greeting", description="Set a custom clan greeting message")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setgreeting(self, ctx: disnake.ApplicationCommandInteraction, greet):
        """
            Parameters
            ----------
            greet: text for custom new member clan greeting
        """

        await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"greeting": greet}})

        await ctx.send(f"Greeting is now:\n\n"
                        f"{ctx.author.mention}, welcome to {ctx.guild.name}! {greet}",
                         allowed_mentions=disnake.AllowedMentions.none())

    @set.sub_command(name="clan-channel", description="Set a new clan channel for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def channel(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: disnake.TextChannel):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            channel: New channel to switch to
        """

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
        ]}, {'$set': {"clanChannel": channel.id}})

        await ctx.send(f"Clan channel switched to {channel.mention}")

    @set.sub_command(name="member-role", description="Set a new member role for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def role(self, ctx: disnake.ApplicationCommandInteraction, clan: str, role: disnake.Role):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            role: New role to switch to
        """

        clan = await self.bot.getClan(clan_tag=clan)

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
        ]}, {'$set': {"generalRole": role.id}})

        embed = disnake.Embed(
            description=f"General role switched to {role.mention}",
            color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="leadership-role", description="Set a new leadership role for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def leaderrole(self, ctx: disnake.ApplicationCommandInteraction, clan: str, role: disnake.Role):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            role: New role to switch to
        """

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
        ]}, {'$set': {"leaderRole": role.id}})

        embed = disnake.Embed(
            description=f"Leader role switched to {role.mention}",
            color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="clan-category", description="Set a new category for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def category(self, ctx: disnake.ApplicationCommandInteraction, clan: str, new_category: str):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            new_category: new category to use for this clan (type one or choose from autocomplete)
        """

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
        ]}, {'$set': {"category": new_category}})

        embed = disnake.Embed(description=f"Category for {clan.name} changed to {new_category}.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="ban-alert-channel", description="Set a new channel for ban alerts")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_alert(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: disnake.TextChannel):
        """
                    Parameters
                    ----------
                    clan: Use clan tag, alias, or select an option from the autocomplete
                    channel: New channel to switch to
                """

        clan = await self.bot.getClan(clan_tag=clan)

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
        ]}, {'$set': {"ban_alert_channel": channel.id}})

        await ctx.send(f"Ban alert channel for {clan.tag} switched to {channel.mention}")

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
            return await ctx.send(f"No category - **{category}** - on this server")

        await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {f"category_roles.{category}": role.id}})

        embed = disnake.Embed(
            description=f"Category role set to {role.mention}",
            color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="nickname-labels", description="Set new abreviations for a clan or labels for family members (used for auto nicknames)")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def abbreviation(self, ctx: disnake.ApplicationCommandInteraction, type: str, new_label: str):
        """
            Parameters
            ----------
            type: clan or family
            new_label: label that goes after a player's nickname on discord
        """

        if type != "Family":
            clan = await self.bot.getClan(type)
            if clan is None:
                return await ctx.send("Not a valid clan tag or alias.")
            results = await self.bot.clan_db.find_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")
            if len(new_label) >= 16 or len(new_label) < 2:
                return await ctx.send("Clan Abbreviation must be 2 to 15 characters (this is to minimize name length's being too long).")

            await self.bot.clan_db.update_one({"$and": [
                {"tag": clan.tag},
                {"server": ctx.guild.id}
            ]}, {'$set': {"abbreviation": new_label.upper()}})
            embed = disnake.Embed(description=f"Abbreviation for {clan.name} changed to {new_label.upper()}.",
                                  color=disnake.Color.green())
        else:
            server = CustomServer(guild=ctx.guild, bot=self.bot)
            await server.set_family_label(new_label)
            embed = disnake.Embed(description=f"Family label changed to {new_label}.",
                                  color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="join-log", description="Set up a join & leave log for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def joinleavelog(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: Union[disnake.TextChannel, disnake.Thread]):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            channel: channel to set the join/leave log to
        """

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

    @set.sub_command(name="donation-log", description="Set up a donation log for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def donolog(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: Union[disnake.TextChannel, disnake.Thread]):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            channel: channel to set the donation log to
        """

        clan = await self.bot.getClan(clan)

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
        ]}, {'$set': {"donolog": channel.id}})

        embed = disnake.Embed(description=f"Donation Log set in {channel.mention} for {clan.name}",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="clan-log", description="Set up a clan log for a clan - name, upgrade, & league changes")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def player_upgrades_log(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: Union[disnake.TextChannel, disnake.Thread]):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            channel: channel to set the clan log to
        """

        clan = await self.bot.getClan(clan)

        if clan is None:
            return await ctx.send("Not a valid clan tag.")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"upgrade_log": channel.id}})

        embed = disnake.Embed(description=f"Player Clan Log set in {channel.mention} for {clan.name}. It will receive updates when player troops, spells, heros, or townhall level or league or name changes.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="clancapital-log", description="Set up a clan capital log for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clancapitallog(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: Union[disnake.TextChannel, disnake.Thread]):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            channel: channel to set the join/leave log to
        """

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

    @set.sub_command(name="war-log", description="Set up a war log for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def warlog(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: Union[disnake.TextChannel, disnake.Thread], log_type = commands.Param(choices=["Continuous Feed", "Update Panel"])):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the war log to
            attack_feed: Continuous - log of every attack, Update - silently update the war panel
        """

        clan = await self.bot.getClan(clan)

        if clan is None:
            return await ctx.send("Not a valid clan tag")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        #legacy naming
        if log_type == "Update Panel":
            log_type = "Update Feed"
        await self.bot.clan_db.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"war_log": channel.id, "attack_feed" : log_type}})

        embed = disnake.Embed(description=f"War Log set in {channel.mention} for {clan.name}",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="legend-log", description="Set up a legend log for a clan")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def legend_log(self, ctx: disnake.ApplicationCommandInteraction, clan: str, channel: Union[disnake.TextChannel, disnake.Thread]):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            channel: channel to set the legend log to
        """

        clan = await self.bot.getClan(clan)

        if clan is None:
            return await ctx.send("Not a valid clan tag")

        results = await self.bot.clan_db.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            return await ctx.send("This clan is not set up on this server. Use `/addclan` to get started.")

        #may activate if duplicates becomes an issue
        #clan_webhooks = await self.bot.clan_db.distinct("legend_log.webhook", filter={"server": ctx.guild.id})
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
                    webhook = await channel.parent.create_webhook(name="ClashKing", avatar=bot_av, reason="Legends Feed")
                else:
                    webhook = await channel.create_webhook(name="ClashKing", avatar=bot_av, reason="Legends Feed")
        except Exception as e:
            e = str(e)[:1000]
            embed = disnake.Embed(title="Error",
                                  description="Likely Missing Permissions\nEnsure the bot has both `Manage Webhooks` and `Send Messages` Perms for this channel.\nError Output: " + e,
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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

        embed = disnake.Embed(
            description="Legend Log Successfully Created",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @set.sub_command(name="leadership-eval", description="Have eval assign leadership role to clan coleads & leads (on default)")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def leadership_eval(self, ctx: disnake.ApplicationCommandInteraction, option=commands.Param(choices=["On", "Off"])):
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        await server.change_leadership_eval(option=(option == "On"))
        embed = disnake.Embed(description=f"Leadership Eval turned {option}.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="nickname-label-type", description="Have linking change discord name to name | clan or name | family")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def auto_nickname(self, ctx: disnake.ApplicationCommandInteraction, type=commands.Param(choices=["Clan Abbreviations", "Family Name", "Off"])):
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        await server.change_auto_nickname(type)
        embed = disnake.Embed(description=f"Auto Nickname set to {type}.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="reddit-recruit-feed", description="Feed of searching for a clan posts on the recruiting subreddit")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def reddit_recruit(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, role_to_ping: disnake.Role = None, remove=commands.Param(default=None, choices=["Remove Feed"])):
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
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {"$set": {"reddit_feed": channel.id, "reddit_role": role_id}})

            embed = disnake.Embed(description=f"**Reddit Recruit feed set to {channel.mention}**", color=disnake.Color.green())

        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {"$set": {"reddit_feed": None, "reddit_role": None}})

            embed = disnake.Embed(description="**Reddit Recruit feed removed**", color=disnake.Color.green())

        return await ctx.edit_original_message(embed=embed)

    @set.sub_command(name="category-order", description="Change the order family categories display on /family-clans")
    @commands.has_permissions(manage_guild=True)
    async def family_cat_order(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
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

    @set.sub_command(name="remove", description="Remove a setup")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def remove_setup(self, ctx: disnake.ApplicationCommandInteraction, clan: str,
                           log_to_remove=commands.Param(choices=["Clan Capital Log", "Join Log", "War Log", "Legend Log", "Donation Log", "Clan Log"])):
        type_dict = {"Clan Capital Log": "clan_capital", "Join Log": "joinlog", "War Log": "war_log", "Legend Log" : "legend_log",  "Donation Log" : "donolog",  "Clan Log" : "upgrade_log"}
        log_type = type_dict[log_to_remove]

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
            log_channel = log_channel.get("webhook")

        if log_channel is None:
            embed = disnake.Embed(description=f"This clan does not have a {log_to_remove} set up on this server.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

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

        if log_to_remove != "Legend Log":
            channel = await self.bot.fetch_channel(log_channel)

            embed = disnake.Embed(description=f"{log_to_remove} in {channel.mention} removed for {clan.name}",
                                  color=disnake.Color.green())
        else:
            embed = disnake.Embed(description=f"{log_to_remove} removed for {clan.name}",
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
            ll_log = await clan.legend_log
            got_clan = await self.bot.getClan(clan.tag)
            embed = disnake.Embed(title=f"{clan.name}", color=disnake.Color.green())
            embed.set_thumbnail(url=got_clan.badge.url)
            embed.add_field(name="Member Role:", value=f"{clan.member_role}", inline=True)
            embed.add_field(name="Leadership Role:", value=f"{clan.leader_role}", inline=True)
            embed.add_field(name="Clan Channel:", value=f"{clan.clan_channel}", inline=True)
            embed.add_field(name="War Log:", value=f"{clan.war_log}", inline=True)
            embed.add_field(name="Join Log:", value=f"{clan.join_log}", inline=True)
            embed.add_field(name="Clan Capital Log:", value=f"{clan.capital_log}", inline=True)
            embed.add_field(name="Legend Log:", value=f"{ll_log}", inline=True)
            embeds.append(embed)

        chunk_embeds = [embeds[i:i + 10] for i in range(0, len(embeds), 10)]

        for embeds in chunk_embeds:
            if embeds == chunk_embeds[0]:
                await ctx.edit_original_message(embeds=embeds)
            else:
                await ctx.followup.send(embeds=embeds)

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

    @channel.autocomplete("clan")
    @role.autocomplete("clan")
    @leaderrole.autocomplete("clan")
    @category.autocomplete("clan")
    @joinleavelog.autocomplete("clan")
    @clancapitallog.autocomplete("clan")
    @warlog.autocomplete("clan")
    @remove_setup.autocomplete("clan")
    @legend_log.autocomplete("clan")
    @ban_alert.autocomplete("clan")
    @donolog.autocomplete("clan")
    @player_upgrades_log.autocomplete("clan")
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

    @abbreviation.autocomplete("type")
    async def autocomp_type(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = ["Family"]
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[:25]

    @category.autocomplete("new_category")
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