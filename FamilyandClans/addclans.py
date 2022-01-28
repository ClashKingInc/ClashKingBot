
import discord
from discord.ext import commands
from HelperMethods.clashClient import getClan, pingToRole, client, pingToChannel
from main import check_commands

from discord_slash.utils.manage_components import wait_for_component, create_select, create_select_option, create_actionrow

from HelperMethods.clashClient import coc_client

usafam = client.usafam
clans = usafam.clans

class addClan(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.color = discord.Color.dark_theme()

    @commands.command(name='addclan', alias =["addclans"])
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def addClan(self, ctx):
        executor = ctx.message.author

        embed = discord.Embed(title="Hello " + executor.display_name + "!",
                              description="First: What is the tag of the clan? (5 minutes to answer)", color=self.color)
        msg = await ctx.send(embed=embed)

        clan = None
        for x in range(5):
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            clan = await getClan(response)

            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)

            if clan is None:
                embed = discord.Embed(title="Sorry that clan tag is invalid. Please try again.",
                                      description="What is the clan tag?", color=discord.Color.red())
                await msg.edit(embed=embed)
                continue
            else:
                break

        if clan is None:
            embed = discord.Embed(description="**Sorry Chief, You tried & failed 5 times. Double check your info & rerun the command.**", color=discord.Color.red())
            return msg.edit(embed=embed)

        results = await clans.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            embed = discord.Embed(description=f"{clan.name} is already linked to this server.",
                                  color=discord.Color.red())
            return await msg.edit(embed=embed)

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

        embed = discord.Embed(title="**Clan Category**",
                              description=f"What category should {clan.name} be listed under?\n"
                                          f"(type a new one or choose an existing from numbers)\n"
                                          f"{categoryTypes}", color=self.color)
        await msg.edit(embed=embed, components=[])

        category = None

        while category == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            #print(response)
            try:
                category=categoryTypesList[int(response)-1]
            except:
                category = response


            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)

        embed = discord.Embed(title="**Clan Alias**",
                              description=f"What is the alias for {clan.name}?\n"
                                          , color=self.color)
        await msg.edit(embed=embed, components=[])

        alias = None

        while alias == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            # print(response)
            alias = response.lower()

            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)


        embed = discord.Embed(title="**General Clan Role**",
                              description=f"What is the general clan role for {clan.name}?", color=self.color)
        await msg.edit(embed=embed)

        generalRole = None

        while generalRole == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            generalRole = await pingToRole(ctx, response)

            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)

            if generalRole is None:
                embed = discord.Embed(title="Sorry that role is invalid. Please try again.",
                                      description=f"What is the general clan role for {clan.name}?", color=discord.Color.red())
                await msg.edit(embed=embed)
                continue
            else:
                break


        embed = discord.Embed(title="**Leadership Clan Role**",
                              description=f"What is the leadership role for {clan.name}?", color=self.color)
        await msg.edit(embed=embed)
        leaderRole = None

        while leaderRole == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            leaderRole = await pingToRole(ctx, response)

            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)

            if leaderRole is None:
                embed = discord.Embed(title="Sorry that role is invalid. Please try again.",
                                      description=f"What is the leadership role for {clan.name}?",
                                      color=discord.Color.red())
                await msg.edit(embed=embed)
                continue
            else:
                break

        embed = discord.Embed(title="**Clan Channel**",
                              description=f"What is the clan channel for {clan.name}?", color=self.color)
        await msg.edit(embed=embed)
        clanChannel = None

        while clanChannel == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            clanChannel = await pingToChannel(ctx, response)

            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)

            if clanChannel is None:
                embed = discord.Embed(title="Sorry that channel is invalid. Please try again.",
                                      description=f"What is the clan channel for {clan.name}?",
                                      color=discord.Color.red())
                await msg.edit(embed=embed)
                continue
            else:
                break

        await clans.insert_one({
            "name" : clan.name,
            "tag" : clan.tag,
            "generalRole" : generalRole.id,
            "leaderRole" : leaderRole.id,
            "category" : category,
            "alias" : alias,
            "server" : ctx.guild.id,
            "clanChannel" : clanChannel.id
        })
        coc_client.add_clan_updates(clan.tag)

        embed = discord.Embed(title=f"{clan.name} successfully added.",
                              description=f"Clan Tag: {clan.tag}\n"
                                          f"General Role: {generalRole.mention}\n"
                                          f"Leadership Role: {leaderRole.mention}\n"
                                          f"Alias: {alias}\n"
                                          f"Clan Channel: {clanChannel.mention}\n"
                                          f"Category: {category}",
                              color=discord.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        await msg.edit(embed=embed)


    @commands.command(name= "removeclan", alias=["removeclans"])
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def removeClan(self, ctx, *, tag):
        tag = tag.lower()
        results = await clans.find_one({"$and": [
            {"alias": tag},
            {"server": ctx.guild.id}
        ]})

        if results is not None:
            tag = results.get("tag")
            clan = await getClan(tag)
        else:
            clan = await getClan(tag)
        if clan == None:
            embed = discord.Embed(description=f"{tag} is not a valid clan.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)
        results = await clans.find_one({"$and": [
            {"tag": clan.tag},
            {"server": ctx.guild.id}
        ]})
        if results is None:
            embed = discord.Embed(description=f"{clan.name} is not currently set-up as a family clan.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        embed = discord.Embed(description=f"Are you sure you want to remove {clan.name} [{clan.tag}]?",
                              color=discord.Color.red())
        embed.set_thumbnail(url=clan.badge.large)

        select1 = create_select(
            options=[
                create_select_option("Yes", value=f"Yes"),
                create_select_option("No", value=f"No")
            ],
            placeholder="Choose your option",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = create_actionrow(select1)
        msg = await ctx.send(embed=embed, components=[action_row])

        chose = False
        while chose == False:
            try:
                res = await wait_for_component(self.bot, components=action_row, messages=msg, timeout=600)
            except:
                return await msg.edit(components=[])

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            chose = res.values[0]
            # print(chose)

            if chose == "No":
                embed = discord.Embed(description=f"Sorry to hear that. Canceling the command now.",
                                      color=discord.Color.green())
                embed.set_thumbnail(url=clan.badge.large)
                return await msg.edit(embed=embed,
                                      components=[])

        await clans.find_one_and_delete({"tag": clan.tag})

        embed = discord.Embed(
            description=f"{clan.name} removed as a family clan.",
            color=discord.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        coc_client.remove_clan_updates(clan.tag)
        return await msg.edit(embed=embed, components=[])



def setup(bot: commands.Bot):
    bot.add_cog(addClan(bot))
