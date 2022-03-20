import discord
from discord.ext import commands
from HelperMethods.clashClient import getPlayer, client, getClan, pingToChannel, pingToRole

from discord_slash.utils.manage_components import create_button, wait_for_component, create_actionrow
from discord_slash.model import ButtonStyle

from main import check_commands
import time
from datetime import timedelta

usafam = client.usafam
clans = usafam.clans
server = usafam.server

from HelperMethods.troop_methods import heros, heroPets

from Dictionaries.thPicDictionary import thDictionary

class misc(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.up = time.time()

    @commands.Cog.listener()
    async def on_message(self, message : discord.Message):
        if "https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=" in message.content:
            m = message.content.replace("\n", " ")
            spots = m.split(" ")
            s = ""
            for spot in spots:
                if "https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=" in spot:
                    s = spot
                    break
            tag = s.replace("https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=", "")
            if "%23" in tag:
                tag = tag.replace("%23", "")
            player = await getPlayer(tag)

            clan = ""
            try:
                clan = player.clan.name
                clan = f"{clan}"
            except:
                clan = "None"
            hero = heros(player)
            pets = heroPets(player)
            if hero == None:
                hero = ""
            else:
                hero = f"**Heroes:**\n{hero}\n"

            if pets == None:
                pets = ""
            else:
                pets = f"**Pets:**\n{pets}\n"

            embed = discord.Embed(title=f"Invite {player.name} to your clan:",
                                  description=f"{player.name} - TH{player.town_hall}\n" +
                                              f"Tag: {player.tag}\n" +
                                              f"Clan: {clan}\n" +
                                              f"Trophies: {player.trophies}\n"
                                              f"War Stars: {player.war_stars}\n"
                                              f"{hero}{pets}"
                                              f'[View Stats](https://www.clashofstats.com/players/{player.tag}) | [Open in Game]({player.share_link})',
                                  color=discord.Color.green())
            embed.set_thumbnail(url=thDictionary(player.town_hall))

            channel = message.channel
            await channel.send(embed=embed)


    @commands.command(name="invite")
    async def invite(self, ctx, tag=None):
        if tag == None:
            return await ctx.reply(f"#playerTag argument is missing. `{ctx.prefix}invite #playerTag`")

        player = await getPlayer(tag)
        if player is None:
            return await ctx.reply("Not a valid playerTag.")

        clan = ""
        try:
            clan = player.clan.name
            clan = f"{clan}"
        except:
            clan = "None"
        hero = heros(player)
        pets = heroPets(player)
        if hero == None:
            hero = ""
        else:
            hero = f"**Heroes:**\n{hero}\n"

        if pets == None:
            pets = ""
        else:
            pets = f"**Pets:**\n{pets}\n"

        embed = discord.Embed(title=f"Invite {player.name} to your clan:",
                              description=f"{player.name} - TH{player.town_hall}\n" +
                                          f"Tag: {player.tag}\n" +
                                          f"Clan: {clan}\n" +
                                          f"Trophies: {player.trophies}\n"
                                          f"War Stars: {player.war_stars}\n"
                                          f"{hero}{pets}"
                                          f'[View Stats](https://www.clashofstats.com/players/{player.tag}) | [Open in Game]({player.share_link})',
                              color=discord.Color.green())
        embed.set_thumbnail(url=thDictionary(player.town_hall))

        await ctx.send(embed=embed)

    @commands.command(name="setprefix")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setprefix(self, ctx, prefix=None):
        if prefix is None:
            return await ctx.reply("Provide a prefix to switch to",
                            mention_author=False)

        results = await server.find_one({"server": ctx.guild.id})
        old_prefix = results.get("prefix")
        if prefix == "do":
            prefix = "do "

        await server.update_one({"server": ctx.guild.id},{'$set': {"prefix": prefix}})

        await ctx.reply(f"Prefix switched from {old_prefix} to {prefix}",
                        mention_author=False)

    @commands.command(name="alias")
    async def alias(self, ctx):
        prefix = ctx.prefix
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("No clans linked to this server.")
        categoryTypesList = []
        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if category not in categoryTypesList:
                categoryTypesList.append(category)

        embeds = []
        text = ""
        for category in categoryTypesList:
            results = clans.find({"$and": [
                {"category": category},
                {"server": ctx.guild.id}
            ]})
            limit = await clans.count_documents(filter={"$and": [
                {"category": category},
                {"server": ctx.guild.id}
            ]})
            text+= f"\n__**{category} Clans**__\n"
            for result in await results.to_list(length=limit):
                tag = result.get("tag")
                clan = await getClan(tag)
                alias = result.get("alias")
                text+=f"{clan.name}-`{prefix}{alias}`\n"


        embed = discord.Embed(title=f"{ctx.guild.name} Clan Aliases",
                              description=text,
                              color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon_url_as())

        await ctx.reply(embed=embed,
                        mention_author=False)

    @commands.command(name="setbanlist")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setbanlist(self, ctx, ban=None):
        if ban is None:
            return await ctx.reply("Provide a channel to switch banlist to.",
                                   mention_author=False)

        channel = await pingToChannel(ctx, ban)
        if channel is None:
            return await ctx.reply("Invalid Channel.",
                                   mention_author=False)

        await server.update_one({"server": ctx.guild.id}, {'$set': {"banlist": channel.id}})

        await ctx.reply(f"Banlist channel switched to {channel.mention}",
                        mention_author=False)

    @commands.command(name="roleusers")
    async def roleusers(self, ctx, ping=None):
        if ping == None:
            return await ctx.reply("Role is a required argument.")

        role = await pingToRole(ctx, ping)
        if role == None:
            return await ctx.reply("Not a valid role.")

        embeds = []
        text = ""
        num = 0
        for member in role.members:
            text += f"{member.display_name} [{member.mention}]\n"
            num+=1
            if num == 25:
                embed = discord.Embed(title=f"Users in {role.name}",
                                      description=text,
                                      color=discord.Color.green())
                embed.set_thumbnail(url=ctx.guild.icon_url_as())
                embeds.append(embed)
                num = 0
                text=""

        if text != "":
            embed = discord.Embed(title=f"Users in {role.name}",
                                  description=text,
                                  color=discord.Color.green())
            embed.set_thumbnail(url=ctx.guild.icon_url_as())
            embeds.append(embed)

        current_page = 0
        limit = len(embeds)

        msg = await ctx.send(embed=embeds[0], components=self.create_components(current_page, limit),
                             mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=self.create_components(current_page, limit),
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()

            # print(res.custom_id)
            if res.custom_id == "Previous":
                current_page -= 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Next":
                current_page += 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

    @commands.command(name="setgreeting")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setgreeting(self, ctx, *, greet=None):
        if greet is None:
            return await ctx.reply("Provide a greeting message.",
                                   mention_author=False)

        await server.update_one({"server": ctx.guild.id}, {'$set': {"greeting": greet}})

        await ctx.reply(f"Greeting is now:\n\n"
                        f"{ctx.author.mention}, welcome to {ctx.guild.name}! {greet}",
                        mention_author=False, allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name="stats", aliases=["stat"])
    async def stat(self, ctx):

        uptime = time.time() - self.up
        uptime = time.strftime("%H hours %M minutes %S seconds", time.gmtime(uptime))

        msg = await ctx.send("<a:loading:862934416137781248> Loading data...")
        bp = msg.created_at - ctx.message.created_at
        bp = (bp / timedelta(milliseconds=1))
        meping = bp

        me = self.bot.user.mention

        before = time.time()
        await getPlayer("#P2PQDW")
        after = time.time()
        cocping = round(((after - before) * 1000), 2)

        inservers = len(self.bot.guilds)
        members = 0
        for guild in self.bot.guilds:
            members += guild.member_count - 1

        embed = discord.Embed(title='MagicBot Stats',
                              description=f"<:bot:862911608140333086> Bot: {me}\n" +
                                          f"<:discord:840749695466864650> Discord Api Ping: {round(self.bot.latency * 1000, 2)} ms\n" +
                                          f"<a:ping:862916971711168562> Bot Ping: {round(meping, 2)} ms\n" +
                                          f"<:clash:855491735488036904> COC Api Ping: {cocping} ms\n" +
                                          f"<:server:863148364006031422> In {str(inservers)} servers\n" +
                                          f"<a:num:863149480819949568> Watching {members} users\n" +
                                          f"🕐 Uptime: {uptime}\n",
                              color=discord.Color.blue())

        await msg.edit(content="", embed=embed)

    @commands.command(name='servers')
    @commands.is_owner()
    async def servers(self, ctx):
        text = ""
        guilds = self.bot.guilds
        for guild in guilds:
            id = guild.member_count
            # owner = await self.bot.fetch_user(id)
            text += guild.name + f" | {id} members\n"

        embed = discord.Embed(description=text,
                              color=discord.Color.green())

        await ctx.send(embed=embed)

    @commands.command(name='serverm')
    @commands.is_owner()
    async def serversmm(self, ctx, *, sname):
        text = ""
        guilds = self.bot.guilds
        for guild in guilds:
            name = guild.name
            if name == sname:
                for member in guild.members:
                    text += member.name + "\n"

        embed = discord.Embed(description=text,
                              color=discord.Color.green())

        await ctx.send(embed=embed)

    @commands.command(name='leave')
    @commands.is_owner()
    async def leaveg(self, ctx, *, guild_name):
        guild = discord.utils.get(self.bot.guilds, name=guild_name)  # Get the guild by name
        if guild is None:
            await ctx.send("No guild with that name found.")  # No guild found
            return
        await guild.leave()  # Guild found
        await ctx.send(f"I left: {guild.name}!")

    @commands.command(name="addrole")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def addroleperms(self, ctx, role:discord.Role):
        channel = ctx.message.channel
        overwrite = discord.PermissionOverwrite()
        overwrite.view_channel = True
        overwrite.read_messages = True
        overwrite.send_messages = True
        await channel.set_permissions(role, overwrite=overwrite)
        embed = discord.Embed(description=f"{role.mention} added to channel.",
                              color=discord.Color.green())

        await ctx.send(embed=embed)


    def create_components(self, current_page, length):
        if length == 1:
            return []

        page_buttons = [create_button(label="", emoji="◀️", style=ButtonStyle.blue, disabled=(current_page == 0),
                                      custom_id="Previous"),
                        create_button(label=f"Page {current_page + 1}/{length}", style=ButtonStyle.grey,
                                      disabled=True),
                        create_button(label="", emoji="▶️", style=ButtonStyle.blue,
                                      disabled=(current_page == length - 1), custom_id="Next")]
        page_buttons = create_actionrow(*page_buttons)

        return [page_buttons]




def setup(bot: commands.Bot):
    bot.add_cog(misc(bot))