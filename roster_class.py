import discord
from HelperMethods.clashClient import client, getClan


class Roster():
    def __init__(self, bot):
        self.bot = bot
        self.clans = None
        self.alias = None
        self.members = None


    async def get_clans(self, ctx):
        executor = ctx.message.author

        embed = discord.Embed(title="Hello " + executor.display_name + "!",
                              description="First: What is the tag(s) of the clan or clans, whose members you are adding to this roster?",
                              color=discord.Color.green())
        embed.set_footer(text="Type `cancel` at any point to stop.")
        msg = await ctx.send(embed=embed)

        clan_list = []
        for x in range(5):
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor and message.channel == ctx.message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            response = response.split()
            for r in response:
                clan = await getClan(r)
                if clan is None:
                    embed = discord.Embed(title=f"Sorry {r} is an invalid clan tag. Please try again.",
                                          description="What is/are the clan tag(s)?", color=discord.Color.red())
                    await msg.edit(embed=embed)
                    embed.set_footer(text="Type `cancel` at any point to stop.")
                    continue
                clan_list.append(clan)

            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)

        if clan_list == []:
            embed = discord.Embed(
                description="**Sorry Chief, You tried & failed 5 times. Double check your info & rerun the command.**",
                color=discord.Color.red())
            return msg.edit(embed=embed)

        self.clans = clan_list
        return self.clans
