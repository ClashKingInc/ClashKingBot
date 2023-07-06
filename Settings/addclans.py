import disnake
import coc
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from main import check_commands

class addClan(commands.Cog, name="Clan Setup"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.color = disnake.Color.dark_theme()

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan


    @commands.slash_command(name="addclan", description="Add a clan to the server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def addClan(self, ctx: disnake.ApplicationCommandInteraction,
                      clan: coc.Clan = commands.Param(converter=clan_converter),
                      category: str = commands.Param(name="category"),
                      member_role: disnake.Role = commands.Param(name="member_role"),
                      clan_channel: disnake.TextChannel = commands.Param(name="clan_channel"),
                      leadership_role: disnake.Role = None):
        """
            Parameters
            ----------
            clan_tag: clan to add to server
            category: choose a category or type your own
            member_role: role that all members of this clan receive
            leadership_role: role that co & leaders of this clan would receive
            clan_channel: channel where ban pings & welcome messages should go
        """
        await ctx.response.defer()
        if member_role.is_bot_managed():
            embed = disnake.Embed(description=f"Clan Roles cannot be bot roles.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if leadership_role is not None and leadership_role.is_bot_managed():
            embed = disnake.Embed(description=f"Clan Roles cannot be bot roles.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if member_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(description=f"Member Role cannot be {ctx.guild.default_role.mention}.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if leadership_role is not None and leadership_role.id == ctx.guild.default_role.id:
            embed = disnake.Embed(description=f"Leadership Role cannot be {ctx.guild.default_role.mention}.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if leadership_role is not None and member_role.id == leadership_role.id:
            embed = disnake.Embed(description="Member Role & Leadership Role cannot be the same.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)


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

        embed = disnake.Embed(title=f"{clan.name} successfully added.",
                              description=f"Clan Tag: {clan.tag}\n"
                                          f"General Role: {member_role.mention}\n"
                                          f"Leadership Role: {None if leadership_role is None else leadership_role.mention}\n"
                                          f"Clan Channel: {None if clan_channel is None else clan_channel.mention}\n"
                                          f"Category: {category}",
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        await ctx.edit_original_message(embed=embed)


    @commands.slash_command(name="removeclan", description="Remove a clan from the server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def removeClan(self, ctx: disnake.ApplicationCommandInteraction,
                         clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: clan to add to server [clan tag, alias, or autocomplete]
        """
        await ctx.response.defer()
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

        embed = disnake.Embed(
            description=f"{clan.name} removed as a family clan.",
            color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return await msg.edit(embed=embed, components=[])


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


    @removeClan.autocomplete("clan")
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
    bot.add_cog(addClan(bot))
