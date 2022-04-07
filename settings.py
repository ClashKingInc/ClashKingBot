import disnake
from disnake.ext import commands
from utils.clash import client, pingToChannel


usafam = client.usafam
clans = usafam.clans
server = usafam.server



class misc(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="set")
    async def set(self, ctx):
        pass

    @set.sub_command(name="banlist-channel")
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


    @set.sub_command(name="greeting")
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




def setup(bot: commands.Bot):
    bot.add_cog(misc(bot))