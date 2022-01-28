from discord.ext import commands
from HelperMethods.clashClient import client, pingToRole
import discord
usafam = client.usafam
linkrole = usafam.linkrole

from main import check_commands


class linkroles(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="linkroles", pass_context=True, invoke_without_command=True)
    async def linkroles_co(self, ctx):
        embed = discord.Embed(
            description=f"**{ctx.prefix}linkroles add @RoleName**\n"
                        "Adds a role to remove when a player is linked to a family clan.\n"
                        f"**{ctx.prefix}linkroles delete @RoleName**\n"
                        "Deletes a role from the list of roles to remove when a player is linked to a family clan.\n"
                        f"**{ctx.prefix}linkroles list**\n"
                        "Displays the list of roles to remove when a player is linked to a family clan.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @linkroles_co.group(name="add", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def linkroles_add(self, ctx, ping=None):
        if ping == None:
            return await ctx.reply(f"Role argument missing. `{ctx.prefix}linkroles add @Role`")

        role = await pingToRole(ctx, ping)
        if role == None:
            return await ctx.reply("Not a valid role.")

        results = await linkrole.find_one({"$and": [
            {"role": role.id},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = discord.Embed(description=f"{role.mention} is already in the link-remove roles list.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        await linkrole.insert_one({
            "server": ctx.guild.id,
            "role": role.id
        })

        embed = discord.Embed(
            description=f"{role.mention} added to the link-remove role list.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @linkroles_co.group(name="remove", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def linkroles_remove(self, ctx, ping=None):
        if ping == None:
            return await ctx.reply(f"Role argument missing. `{ctx.prefix}linkroles remove @Role`")

        if (ping.startswith('<@') and ping.endswith('>')):
            ping = ping[2:len(ping) - 1]

        if (ping.startswith('&')):
            ping = ping[1:len(ping)]

        try:
            ping = int(ping)
        except:
            return await ctx.reply("Not a valid role.")

        results = await linkrole.find_one({"$and": [
            {"role": ping},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = discord.Embed(description=f"<@&{ping}> is not currently in the link-remove roles list.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        await linkrole.find_one_and_delete({"role": ping})

        embed = discord.Embed(
            description=f"<@&{ping}> removed from the link-remove roles list.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @linkroles_co.group(name="list", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def linkroles_list(self, ctx):
        text = ""
        all = linkrole.find()
        limit = await linkrole.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            text += f"<@&{r}>\n"

        if text == "":
            text = "No linkroles."

        embed = discord.Embed(title=f"Link-Remove Roles",
                              description=text,
                              color=discord.Color.green())

        await ctx.reply(embed=embed, mention_author=False)


def setup(bot: commands.Bot):
    bot.add_cog(linkroles(bot))