import discord
from discord.ext import commands
from HelperMethods.clashClient import client, pingToRole
from main import check_commands

usafam = client.usafam
evalignore = usafam.evalignore


class evalignores(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="evalignore", pass_context=True, invoke_without_command=True)
    async def evalignore_co(self, ctx):
        prefix = ctx.prefix
        embed = discord.Embed(
            description=f"**{prefix}evalignore add @RoleName**\n"
                        "Adds a role to ignore when a user or role is evaluated.\n"
                        f"**{prefix}evalignore remove @RoleName**\n"
                        "Deletes a role to ignore when a user or role is evaluated.\n"
                        f"**{prefix}evalignore list**\n"
                        "Displays the list of roles to ignore when a user or role is evaluated.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @evalignore_co.group(name= "add", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def evalignore_add(self, ctx, ping=None):
        if ping == None:
            return await ctx.reply("Please specify a user or role to evaluate.")

        role = await pingToRole(ctx, ping)
        if role == None:
            return await ctx.reply("Not a valid role.")

        results = await evalignore.find_one({"$and": [
            {"role": role.id},
            {"server": ctx.guild.id}
        ]})
        if results is not None:
            embed = discord.Embed(description=f"{role.mention} role is already ignored during eval.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        await evalignore.insert_one({
            "server": ctx.guild.id,
            "role" : role.id
        })

        embed = discord.Embed(
            description=f"{role.mention} added as a role to ignore during evaluation.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @evalignore_co.group(name="remove", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def evalignore_remove(self, ctx, ping=None):
        if ping == None:
            return await ctx.reply("Please specify a user or role to evaluate.")

        if (ping.startswith('<@') and ping.endswith('>')):
            ping = ping[2:len(ping) - 1]

        if (ping.startswith('&')):
            ping = ping[1:len(ping)]

        try:
            ping = int(ping)
        except:
            return await ctx.reply("Not a valid role.")

        results = await evalignore.find_one({"$and": [
            {"role": ping},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = discord.Embed(description=f"<@&{ping}> is not currently evalignored.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        await evalignore.find_one_and_delete({"role" : ping})

        embed = discord.Embed(
            description=f"<@&{ping}> removed as a role to ignore during evaluation.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @evalignore_co.group(name="list", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def evalignore_list(self, ctx):
        text = ""
        all = evalignore.find({"server" : ctx.guild.id})
        limit = await evalignore.count_documents(filter={"server" : ctx.guild.id})
        for role in await all.to_list(length=limit):
            r = role.get("role")
            text += f"<@&{r}>\n"

        if text == "":
            text = "No evalignored roles."

        embed = discord.Embed(title=f"Eval ignore roles",
                              description=text,
                              color=discord.Color.green())

        await ctx.reply(embed=embed, mention_author= False)



def setup(bot: commands.Bot):
    bot.add_cog(evalignores(bot))