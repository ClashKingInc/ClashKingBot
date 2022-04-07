import disnake
from disnake.ext import commands

class OwnerCommands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='reload', hidden=True)
    async def _reload(self,ctx, *, module: str):
        """Reloads a module."""
        if ctx.message.author.id == 706149153431879760:
            try:
                self.bot.unload_extension(module)
                self.bot.load_extension(module)
            except:
                await ctx.send('<a:no:862552093324083221> Could not reload module.')
            else:
                await ctx.send('<a:check:861157797134729256> Reloaded module successfully')
        else:
            await ctx.send("You aren't magic. <:PS_Noob:783126177970782228>")

    @commands.command(name='leave')
    @commands.is_owner()
    async def leaveg(self,ctx, *, guild_name):
        guild = disnake.utils.get(self.bot.guilds, name=guild_name)  # Get the guild by name
        if guild is None:
            await ctx.send("No guild with that name found.")  # No guild found
            return
        await guild.leave()  # Guild found
        await ctx.send(f"I left: {guild.name}!")

    @commands.command(name='servers')
    @commands.is_owner()
    async def serversmm(self, ctx):
        text = ""
        guilds = self.bot.guilds
        for guild in guilds:
            name = guild.name
            text += f"{name} | {len(guild.members)}\n"

        embed = disnake.Embed(title=f"{len(guilds)} servers", description=text,
                              color=disnake.Color.green())

        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(OwnerCommands(bot))