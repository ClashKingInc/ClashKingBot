import disnake
from disnake.ext import commands
import time
from CustomClasses.CustomBot import CustomClient



from utils.components import create_components

class misc(commands.Cog, name="Other"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.up = time.time()

    @commands.slash_command(name="support-server", description="Invite to bot support server")
    async def support(self, ctx):
        embed = disnake.Embed(title="Support Server & Github",
                              description="Support Server: [here](https://discord.gg/gChZm3XCrS)\n"
                                          "Github: [here](https://github.com/MagicTheDev/MagicBot)",
                              color=disnake.Color.blue())
        await ctx.send(embed=embed)

    @commands.slash_command(name="bot-invite", description="Invite bot to other servers!")
    async def invitebot(self, ctx):
        embed = disnake.Embed(title="Bot Invite",
                              description="Invite Link: [here](https://discord.com/api/oauth2/authorize?client_id=824653933347209227&permissions=8&scope=bot%20applications.commands)",
                              color=disnake.Color.blue())
        await ctx.send(embed=embed)

    @commands.slash_command(name="role-users", description="Get a list of users in a role")
    async def roleusers(self, ctx, role:disnake.Role):
        embeds = []
        text = ""
        num = 0
        for member in role.members:
            text += f"{member.display_name} [{member.mention}]\n"
            num+=1
            if num == 25:
                embed = disnake.Embed(title=f"Users in {role.name}",
                                      description=text,
                                      color=disnake.Color.green())
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                embeds.append(embed)
                num = 0
                text=""

        if text != "":
            embed = disnake.Embed(title=f"Users in {role.name}",
                                  description=text,
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)

        current_page = 0
        await ctx.send(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)

    @commands.slash_command(name="bot-stats", description="Stats about bots uptime & ping")
    async def stat(self, ctx):
        uptime = time.time() - self.up
        uptime = time.strftime("%H hours %M minutes %S seconds", time.gmtime(uptime))

        me = self.bot.user.mention

        before = time.time()
        await self.bot.getPlayer("#P2PQDW")
        after = time.time()
        cocping = round(((after - before) * 1000), 2)

        inservers = len(self.bot.guilds)
        members = 0
        for guild in self.bot.guilds:
            members += guild.member_count - 1

        embed = disnake.Embed(title=f'{self.bot.user.name} Stats',
                              description=f"<:bot:862911608140333086> Bot: {me}\n" +
                                          f"<:discord:840749695466864650> Discord Api Ping: {round(self.bot.latency * 1000, 2)} ms\n" +
                                          f"<:clash:855491735488036904> COC Api Ping: {cocping} ms\n" +
                                          f"<:server:863148364006031422> In {str(inservers)} servers\n" +
                                          f"<a:num:863149480819949568> Watching {members} users\n" +
                                          f"🕐 Uptime: {uptime}\n",
                              color=disnake.Color.blue())

        await ctx.send(embed=embed)





def setup(bot: CustomClient):
    bot.add_cog(misc(bot))