import discord
from discord.ext import commands
from HelperMethods.clashClient import client, pingToRole

usafam = client.usafam
whitelist = usafam.whitelist



class whiteList(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="whitelist", pass_context=True, invoke_without_command=True)
    async def whitelist_co(self, ctx):
        embed = discord.Embed(
            description=f"**{ctx.prefix}whitelist add @RoleName command**\n"
                        "Adds a role that can run a specific command.\n"
                        f"**{ctx.prefix}whitelist remove @RoleName command**\n"
                        "Deletes a role that can run a specific command.\n"
                        f"**{ctx.prefix}whitelist list**\n"
                        "Displays the list of commands/roles that have whitelist overrides.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @whitelist_co.group(name= "add", pass_context=True, invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def evalignore_add(self, ctx, ping=None, *, command=None):
        if ping == None or command == None:
            return await ctx.reply("Please specify a user or role to evaluate.")

        role = await pingToRole(ctx, ping)
        if role == None:
            return await ctx.reply("Not a valid role.")

        is_command =False

        for subcommand in self.bot.walk_commands():
            command_name = subcommand.qualified_name
            #print(command_name)
            has_checks = subcommand.checks
            has_checks = (has_checks != [])
            if (command == command_name) and (has_checks):
                #print(subcommand.checks)
                #print(command_name)
                is_command=True
                break

        if is_command == False:
            return await ctx.reply("Not a valid command or command cannot be whitelisted.")

        results = await whitelist.find_one({"$and": [
            {"command": command},
            {"server": ctx.guild.id},
            {"role" : role.id}
        ]})

        if results is not None:
            embed = discord.Embed(description=f"{role.mention} is already whitelisted for `{command}`.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        await whitelist.insert_one({
            "command" : command,
            "server": ctx.guild.id,
            "role" : role.id
        })

        embed = discord.Embed(
            description=f"{role.mention} added to `{command}` whitelist.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @whitelist_co.group(name="remove", pass_context=True, invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def evalignore_remove(self, ctx, ping=None, *, command=None):
        if ping == None or command == None:
            return await ctx.reply("Please specify a user or role to evaluate.")

        role = await pingToRole(ctx, ping)
        if role == None:
            return await ctx.reply("Not a valid role.")

        is_command = False

        for subcommand in self.bot.walk_commands():
            command_name = subcommand.qualified_name
            # print(command_name)
            has_checks = subcommand.checks
            has_checks = (has_checks != [])
            if (command == command_name) and (has_checks):
                # print(subcommand.checks)
                # print(command_name)
                is_command = True
                break

        if is_command == False:
            return await ctx.reply("Not a valid command or command cannot be whitelisted.")

        results = await whitelist.find_one({"$and": [
            {"command": command},
            {"server": ctx.guild.id},
            {"role": role.id}
        ]})

        if results is None:
            embed = discord.Embed(description=f"{role.mention} has no active whitelist for `{command}`.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        await whitelist.find_one_and_delete({
            "command": command,
            "server": ctx.guild.id,
            "role": role.id
        })

        embed = discord.Embed(
            description=f"{role.mention} removed from `{command}` whitelist.",
            color=discord.Color.green())
        return await ctx.send(embed=embed)

    @whitelist_co.group(name="list", pass_context=True, invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def evalignore_list(self, ctx):
        text = ""
        results = whitelist.find({"server": ctx.guild.id})
        limit = await whitelist.count_documents(filter={"server": ctx.guild.id})
        for role in await results.to_list(length=limit):
            r = role.get("role")
            command = role.get("command")
            text += f"<@&{r}> | `{command}`\n"

        if text == "":
            text = "Whitelist is empty."

        embed = discord.Embed(title=f"Whitelist command/role list",
                              description=text,
                              color=discord.Color.green())

        await ctx.reply(embed=embed, mention_author= False)



def setup(bot: commands.Bot):
    bot.add_cog(whiteList(bot))