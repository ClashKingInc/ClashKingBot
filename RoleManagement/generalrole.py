from disnake.ext import commands
from utils.clash import client, pingToRole
import disnake

from main import check_commands

usafam = client.usafam
generalrole = usafam.generalrole


class generalroles(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="generalrole", pass_context=True, invoke_without_command=True)
    async def generalrole_co(self, ctx):
        prefix = ctx.prefix
        embed = disnake.Embed(
            description=f"**{prefix}generalrole add @RoleName**\n"
                        "Adds a role to add when a player is linked to a family clan.\n"
                        f"**{prefix}generalrole remove @RoleName**\n"
                        "Deletes a role from the list of roles to add when a player is linked to a family clan.\n"
                        f"**{prefix}generalrole list**\n"
                        "Displays the list of roles to add when a player is linked to a family clan.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @generalrole_co.group(name="add", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def linkroles_add(self, ctx, ping=None):
        prefix = ctx.prefix
        if ping == None:
            return await ctx.reply(f"Role argument missing. `{prefix}generalrole add @Role`")

        role = await pingToRole(ctx, ping)
        if role == None:
            return await ctx.reply("Not a valid role.")

        results = await generalrole.find_one({"$and": [
            {"role": role.id},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = disnake.Embed(description=f"{role.mention} is already in the general-link roles list.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await generalrole.insert_one({
            "server": ctx.guild.id,
            "role": role.id
        })

        embed = disnake.Embed(
            description=f"{role.mention} added to the general-link role list.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @generalrole_co.group(name="remove", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def linkaddroles_remove(self, ctx, ping=None):
        prefix = ctx.prefix
        if ping == None:
            return await ctx.reply(f"Role argument missing. `{prefix}generalrole remove @Role`")

        if (ping.startswith('<@') and ping.endswith('>')):
            ping = ping[2:len(ping) - 1]

        if (ping.startswith('&')):
            ping = ping[1:len(ping)]

        try:
            ping = int(ping)
        except:
            return await ctx.reply("Not a valid role.")

        results = await generalrole.find_one({"$and": [
            {"role": ping},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = disnake.Embed(description=f"<@&{ping}> is not currently in the general-link roles list.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await generalrole.find_one_and_delete({"role": ping})

        embed = disnake.Embed(
            description=f"<@&{ping}> removed from the general-link roles list.",
            color=disnake.Color.green())
        return await ctx.send(embed=embed)

    @generalrole_co.group(name="list", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def linkaddroles_list(self, ctx):
        text = ""
        all = generalrole.find()
        limit = await generalrole.count_documents(filter={"server": ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            text += f"<@&{r}>\n"

        if text == "":
            text = "No General-Link roles."

        embed = disnake.Embed(title=f"General-Link Roles",
                              description=text,
                              color=disnake.Color.green())

        await ctx.reply(embed=embed, mention_author=False)


def setup(bot: commands.Bot):
    bot.add_cog(generalroles(bot))