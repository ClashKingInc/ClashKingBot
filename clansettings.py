from discord.ext import commands
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle
import discord
from HelperMethods.clashClient import pingToChannel, client, pingToRole

usafam = client.usafam
clans = usafam.clans


class ClanSettings(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="set", pass_context=True, invoke_without_command=True)
    async def set(self, ctx):
        pass

    @set.group(name="channel")
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

def setup(bot: commands.Bot):
    bot.add_cog(ClanSettings(bot))