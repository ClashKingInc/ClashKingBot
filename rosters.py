import discord
from discord.ext import commands
from HelperMethods.clashClient import client, getClan

from roster_class import Roster

usafam = client.usafam
clans = usafam.clans
rosters = usafam.rosters


class Roster_Commands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="roster", pass_context=True, invoke_without_command=True)
    async def roster_co(self, ctx, alias):
        pass

    @roster_co.group(name="create", pass_context=True, invoke_without_command=True)
    async def roster_create(self, ctx):

        clan_list = Roster.get_clans(ctx)
        print(clan_list)
        return

        alias = None
        while alias == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            # print(response)
            response = response.lower()

            results = await rosters.find_one({"$and": [
                {"alias": response},
                {"server": ctx.guild.id}
            ]})

            if results != None:
                embed = discord.Embed(title=f"Sorry {response} is already an alias for a roster on this server. Please try again.",
                                      description="What is the alias for this roster?", color=discord.Color.red())
                embed.set_footer(text="Type `cancel` at any point to stop.")
                await msg.edit(embed=embed)

            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)




    @roster_co.group(name="edit", pass_context=True, invoke_without_command=True)
    async def roster_edit(self, ctx):
        pass

    @roster_co.group(name="list", pass_context=True, invoke_without_command=True)
    async def roster_list(self, ctx):
        pass


def setup(bot: commands.Bot):
    bot.add_cog(Roster_Commands(bot))