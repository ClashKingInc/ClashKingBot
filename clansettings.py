from discord.ext import commands
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle
import discord
from HelperMethods.clashClient import pingToChannel, client, pingToRole
from main import check_commands
usafam = client.usafam
clans = usafam.clans


class ClanSettings(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="set", pass_context=True, invoke_without_command=True)
    async def set(self, ctx):
        pass

    @set.group(name="channel")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def channel(self, ctx, channel=None, *, alias=None):
        if channel is None:
            return await ctx.reply("Channel argument required.",
                                   mention_author=False)
        if alias is None:
            return await ctx.reply("Provide an alias for a clan to switch general channel on.",
                                   mention_author=False)

        channel = await pingToChannel(ctx, channel)
        if channel is None:
            return await ctx.reply("Invalid Channel.",
                                   mention_author=False)

        alias = alias.lower()
        results = await clans.find_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]})

        if results is None:
            return await ctx.reply("Invalid alias.",
                                   mention_author=False)

        await clans.update_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]}, {'$set': {"clanChannel": channel.id}})

        await ctx.reply(f"Clan channel switched to {channel.mention}",
                        mention_author=False)

    @set.group(name="warchannel")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def warchannel(self, ctx, channel=None, *, alias=None):
        if channel is None:
            return await ctx.reply("Channel argument required.",
                                   mention_author=False)
        if alias is None:
            return await ctx.reply("Provide an alias for a clan to switch warchannel on.",
                                   mention_author=False)

        channel = await pingToChannel(ctx, channel)
        if channel is None:
            return await ctx.reply("Invalid Channel.",
                                   mention_author=False)

        alias = alias.lower()
        results = await clans.find_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]})

        if results is None:
            return await ctx.reply("Invalid alias.",
                                   mention_author=False)

        await clans.update_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]}, {'$set': {"warChannel": channel.id}})

        await ctx.reply(f"War channel switched to {channel.mention}",
                        mention_author=False)

    @set.group(name="role")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def role(self, ctx, role=None, *, alias=None):
        if role is None:
            return await ctx.reply("Role argument required.",
                                   mention_author=False)
        if alias is None:
            return await ctx.reply("Provide an alias for a clan to switch general role on.",
                                   mention_author=False)

        role = await pingToRole(ctx, role)
        if role is None:
            return await ctx.reply("Invalid role.",
                                   mention_author=False)

        alias = alias.lower()
        results = await clans.find_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]})

        if results is None:
            return await ctx.reply("Invalid alias.",
                                   mention_author=False)

        await clans.update_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]}, {'$set': {"generalRole": role.id}})

        embed = discord.Embed(
            description=f"General role switched to {role.mention}",
            color=discord.Color.green())
        await ctx.reply(embed=embed, mention_author=False)

    @set.group(name="leaderrole")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def leaderrole(self, ctx, role=None, *, alias=None):
        if role is None:
            return await ctx.reply("Role argument required.",
                                   mention_author=False)
        if alias is None:
            return await ctx.reply("Provide an alias for a clan to switch leader role on.",
                                   mention_author=False)

        role = await pingToRole(ctx, role)
        if role is None:
            return await ctx.reply("Invalid role.",
                                   mention_author=False)

        alias = alias.lower()
        results = await clans.find_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]})

        if results is None:
            return await ctx.reply("Invalid alias.",
                                   mention_author=False)

        await clans.update_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]}, {'$set': {"leaderRole": role.id}})

        embed = discord.Embed(
            description=f"Leader role switched to {role.mention}",
            color=discord.Color.green())
        await ctx.reply(embed=embed, mention_author=False)

    @set.group(name="clanalias")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def clanalias(self, ctx, alias=None, *, newalias=None):
        if alias is None:
            return await ctx.reply("Alias argument required.",
                                   mention_author=False)
        if newalias is None:
            return await ctx.reply("Provide an newalias for a clan to switch to.",
                                   mention_author=False)

        alias = alias.lower()
        results = await clans.find_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]})

        if results is None:
            return await ctx.reply("Invalid alias.",
                                   mention_author=False)

        await clans.update_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]}, {'$set': {"alias": newalias.lower()}})

        embed = discord.Embed(
            description=f"Clan alias switched to {newalias.lower()}",
            color=discord.Color.green())
        await ctx.reply(embed=embed, mention_author=False)

    @set.group(name="category")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def leaderrole(self, ctx, alias=None):
        if alias is None:
            return await ctx.reply("Provide an alias for a clan to switch category on.",
                                   mention_author=False)

        alias = alias.lower()
        results = await clans.find_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]})

        if results is None:
            return await ctx.reply("Invalid alias.",
                                   mention_author=False)

        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        categoryTypes = ""
        categoryTypesList = []
        num = 1
        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if category not in categoryTypesList:
                categoryTypesList.append(category)
                categoryTypes += f"{num}. {category}\n"
                num += 1

        if categoryTypes == "":
            categoryTypes = "**No previous existing categories.**"

        name = results.get("name")
        embed = discord.Embed(title="**Clan Category**",
                              description=f"What category should {name} be listed under?\n"
                                          f"(type a new one or choose an existing from numbers)\n"
                                          f"{categoryTypes}", color=discord.Color.green())
        msg = await ctx.send(embed=embed)

        category = None

        while category == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == ctx.message.author

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)

            try:
                category = categoryTypesList[int(response) - 1]
            except:
                category = response

        await clans.update_one({"$and": [
            {"alias": alias},
            {"server": ctx.guild.id}
        ]}, {'$set': {"category": category}})

        embed = discord.Embed(description=f"Category for {name} changed to {category}.", color=discord.Color.green())
        await msg.edit(embed=embed)










def setup(bot: commands.Bot):
    bot.add_cog(ClanSettings(bot))