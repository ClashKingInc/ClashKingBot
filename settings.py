import disnake
from disnake.ext import commands
from utils.clash import client, getClan


usafam = client.usafam
clans = usafam.clans
server = usafam.server



class misc(commands.Cog):

    def __init__(self, bot: commands.Bot):
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

        await server.update_one({"server": ctx.guild.id}, {'$set': {"banlist": channel.id}})
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

        await server.update_one({"server": ctx.guild.id}, {'$set': {"greeting": greet}})

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
        results = await clans.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await getClan(tag)
        else:
            clan = await getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        await clans.update_one({"$and": [
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
        results = await clans.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await getClan(tag)
        else:
            clan = await getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        await clans.update_one({"$and": [
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
        results = await clans.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await getClan(tag)
        else:
            clan = await getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        await clans.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"leaderRole": role.id}})

        embed = disnake.Embed(
            description=f"Leader role switched to {role.mention}",
            color=disnake.Color.green())
        await ctx.send(embed=embed)

    @set.sub_command(name="clan-alias", description="Set a new alias for a clan")
    async def clanalias(self, ctx: disnake.ApplicationCommandInteraction, clan: str, new_alias: str):
        """
            Parameters
            ----------
            clan: Use clan tag, alias, or select an option from the autocomplete
            new_alias: new alias to use for this clan
        """

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        clan_search = clan.lower()
        first_clan = clan
        results = await clans.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await getClan(tag)
        else:
            clan = await getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        results = await clans.find_one({"$and": [
            {"alias": new_alias.lower()},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = disnake.Embed(description=f"{new_alias} is already used as an alias on this server.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await clans.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"alias": new_alias.lower()}})

        embed = disnake.Embed(
            description=f"Clan alias switched to {new_alias.lower()}",
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
        results = await clans.find_one({"$and": [
            {"alias": clan_search},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await getClan(tag)
        else:
            clan = await getClan(clan)

        if clan is None:
            if "|" in first_clan:
                search = first_clan.split("|")
                tag = search[1]
                clan = await getClan(tag)

        if clan is None:
            return await ctx.send("Not a valid clan tag or alias.")

        await clans.update_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]}, {'$set': {"category": new_category}})

        embed = disnake.Embed(description=f"Category for {clan.name} changed to {new_category}.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @channel.autocomplete("clan")
    @role.autocomplete("clan")
    @leaderrole.autocomplete("clan")
    @clanalias.autocomplete("clan")
    @category.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]

    @category.autocomplete("new_category")
    async def autocomp_category(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        categories = []
        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if query.lower() in category.lower():
                if category not in categories:
                    categories.append(category)
        return categories[0:25]


def setup(bot: commands.Bot):
    bot.add_cog(misc(bot))