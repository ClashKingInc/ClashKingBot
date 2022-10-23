import disnake
from disnake.ext import commands
from datetime import datetime
clan_tags = ["#2P0JJQGUJ"]
known_streak = []
count = 0
list_size = 0
from utils.clash import weekend_timestamps
import asyncio
from CustomClasses.CustomBot import CustomClient
from pymongo import UpdateOne

class OwnerCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="emoji_to_json")
    async def emoji_json(self, ctx: disnake.ApplicationCommandInteraction):
        emojis = ctx.guild.emojis
        text = ""
        for emoji in emojis:
            text += f'"{emoji.name}" : "<{emoji.name}:{emoji.id}>",\n'
        text = "```{\n" + f"{text}" + "}```"
        await ctx.send(text)


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

    @commands.slash_command(name="owner_anniversary", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def anniversary(self, ctx: disnake.ApplicationCommandInteraction):
        guild = ctx.guild
        await ctx.send(content="Edited 0 members")
        x = 0
        for member in guild.members:
            year = member.joined_at.year
            month = member.joined_at.month
            n_year = datetime.now().year
            n_month = datetime.now().month
            num_months = (n_year - year) * 12 + (n_month - month)
            if num_months >= 12:
                r = disnake.utils.get(ctx.guild.roles, id=1029249316981833748)
                await member.add_roles(*[r])
            elif num_months >= 9:
                r = disnake.utils.get(ctx.guild.roles, id=1029249365858062366)
                await member.add_roles(*[r])
            elif num_months >= 6:
                r = disnake.utils.get(ctx.guild.roles, id=1029249360178987018)
                await member.add_roles(*[r])
            elif num_months >= 3:
                r = disnake.utils.get(ctx.guild.roles, id=1029249480261906463)
                await member.add_roles(*[r])
            x += 1
            if x % 5 == 0:
                await ctx.edit_original_message(content=f"Edited {x} members")
        await ctx.edit_original_message(content="Done")


    @commands.command(name="testraid")
    @commands.is_owner()
    async def testraid(self, ctx, tag):

        text = ""
        clan = await self.bot.getClan(tag)

        tracked = self.bot.clan_db.find({"tag": f"{clan.tag}"})
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan.tag}"})
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
                member = await server.fetch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send =ow.send_messages
                embed_link = ow.embed_links
                await clancapital_channel.send(embed=embed)
                text += f"{server.name} : Successful\n> Send Messages Perm: {send}\nEmbed Link Perm: {embed_link}\n"
            except Exception as e:
                member = await server.getch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send = ow.send_messages
                embed_link = ow.embed_links
                text += f"{server.name} : Not Successful\n> Send Messages Perm: {send}\nEmbed Link Perm: {embed_link}\n> {str(e)[0:1000]}\n"

        embed = disnake.Embed(title=f"Test Raid {clan.name}", description=text, color=disnake.Color.green())
        await ctx.send(embed=embed)

    @commands.command(name="testreddit")
    @commands.is_owner()
    async def testraid(self, ctx, server_id):

        text = ""
        server_id = int(server_id)

        server = await self.bot.server_db.find_one({"server" : server_id})
        reddit_channel = server.get("reddit_feed")
        if reddit_channel is None:
            await ctx.send("No channel set up")

        server = server.get("server")

        server = await self.bot.fetch_guild(server)



        reddit_channel = await server.fetch_channel(reddit_channel)
        if reddit_channel is None:
            await ctx.send("Invalid channel")


        embed = disnake.Embed(
            description=f"Test Reddit Feed"
            , color=disnake.Color.green())

        try:
            member = await server.fetch_member(self.bot.user.id)
            ow = reddit_channel.overwrites_for(member)
            send = ow.send_messages
            embed_link = ow.embed_links
            await reddit_channel.send(embed=embed)
            text += f"{server.name} : Successful\n> Send Messages Perm: {send}\nEmbed Link Perm: {embed_link}\n"
        except Exception as e:
            member = await server.getch_member(self.bot.user.id)
            ow = reddit_channel.overwrites_for(member)
            send = ow.send_messages
            embed_link = ow.embed_links
            text += f"{server.name} : Not Successful\n> Send Messages Perm: {send}\nEmbed Link Perm: {embed_link}\n> {str(e)[0:1000]}\n"

        embed = disnake.Embed(title=f"Test Reddit Feed for {server.name}", description=text, color=disnake.Color.green())
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






def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))