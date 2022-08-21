import disnake
from disnake.ext import commands
from utils.clash import coc_client, client, getClan

usafam = client.usafam
banlist = usafam.banlist
server = usafam.server
clans = usafam.clans
clancapital = usafam.clancapital

import motor.motor_asyncio
new_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")

clan_tags = ["#2P0JJQGUJ"]
known_streak = []
count = 0
list_size = 0
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient

class OwnerCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
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



    @commands.command(name="testraid")
    async def testraid(self, ctx, tag):

        text = ""
        clan = await getClan(tag)

        tracked = clans.find({"tag": f"{clan.tag}"})
        limit = await clans.count_documents(filter={"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await self.bot.fetch_guild(server)
            except:
                continue
            clancapital_channel = cc.get("clan_capital")
            if clancapital_channel is None:
                continue

            try:
                clancapital_channel = await server.fetch_channel(clancapital_channel)
                if clancapital_channel is None:
                    continue
            except:
                continue

            embed = disnake.Embed(
                description=f"Test Player donated <:capitalgold:987861320286216223>1000"
                , color=disnake.Color.green())

            embed.set_footer(icon_url=clan.badge.url, text=clan.name)

            try:
                member = await server.getch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send =ow.send_messages
                await clancapital_channel.send(embed=embed)
                text += f"{server.name} : Successful\n> Send Messages Perm: {send}\n"
            except Exception as e:
                member = await server.getch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send = ow.send_messages
                text += f"{server.name} : Not Successful\n> Send Messages Perm: {send}\n> {str(e)[0:1000]}\n"

        embed = disnake.Embed(title=f"Test Raid {clan.name}", description=text, color=disnake.Color.green())
        await ctx.send(embed=embed)

    @commands.command(name='leave')
    @commands.is_owner()
    async def leaveg(self,ctx, *, guild_name):
        guild = disnake.utils.get(self.bot.guilds, name=guild_name)  # Get the guild by name
        if guild is None:
            await ctx.send("No guild with that name found.")  # No guild found
            return
        await guild.leave()  # Guild found
        await ctx.send(f"I left: {guild.name}!")


    @commands.command(name="testy")
    @commands.is_owner()
    async def testy(self, ctx, date):
        tag = "#20LLYQYQ2"
        results = await self.bot.player_stats.find_one({"tag" : tag})
        player: MyCustomPlayer = await coc_client.get_player(player_tag=tag, cls=MyCustomPlayer, bot=self.bot, results=results)
        print(player.town_hall.emoji)



    async def get_warlog(self,clan, channel):
        global clan_tags
        try:
            warlog = await coc_client.get_warlog(clan_tag=clan.tag)
        except:
            return
        for war in warlog:
            try:
                clan = await coc_client.get_clan(tag=war.opponent.tag)
                if war.opponent.tag not in clan_tags:
                    if clan.war_win_streak >= 35:
                        if clan.member_count >= 10:
                            if str(clan.chat_language) == "English" or str(clan.chat_language) == "None":
                                description = clan.description
                                rest = ""
                                if "discord.gg" in description:
                                    rest = description.partition("discord.gg")[2]
                                location = ""
                                try:
                                    location = str(clan.location)
                                except:
                                    pass

                                await channel.send(f"{clan.name} | {clan.tag} | ({clan.member_count}/50) - {clan.war_win_streak} wins | {location} | {rest}")
                    clan_tags.append(war.opponent.tag)
            except:
                continue




def setup(bot: commands.Bot):
    bot.add_cog(OwnerCommands(bot))