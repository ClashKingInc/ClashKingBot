from main import check_commands
from discord.ext import commands # Again, we need this imported
import discord
from HelperMethods.clashClient import getClan, getPlayer, verifyPlayer, link_client, pingToMember, getTags, client

link_open=[]

usafam = client.usafam
clans = usafam.clans
server = usafam.server

class Linking(commands.Cog):
    """A couple of simple commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="refresh")
    async def refresh(self, ctx):
        tags = await getTags(ctx, str(ctx.message.author.id))
        if tags !=[]:
            evalua = self.bot.get_cog("eval")
            changes = await evalua.eval_member(ctx, ctx.message.author, False)
            embed = discord.Embed(
                description=f"Refreshed your roles {ctx.author.mention}.\n"
                            f"Added: {changes[0]}\n"
                            f"Removed: {changes[1]}", color=discord.Color.green())
            return await ctx.reply(embed=embed, mention_author=False)
        else:
            embed = discord.Embed(
                description=f"You have no accounts linked.", color=discord.Color.red())
            return await ctx.reply(embed=embed, mention_author=False)


    @commands.command(name='link')
    async def link(self, ctx, playerTag=None):

        member = ctx.author

        if member in link_open:
            return await ctx.send(
                content="You already have a link command open, please finish linking there or type `cancel` to cancel the command.", delete_after=30)

        executor = ctx.author
        link_open.append(member)

        messagesSent = []

        cancel = False
        correctTag = False

        embed = discord.Embed(description="<a:loading:884400064313819146> Starting link...",
                              color=discord.Color.green())

        msg = await ctx.reply(embed=embed, mention_author=False)

        if playerTag == None:
            playerTag = ""
            playerToken = ""
            embed = discord.Embed(
                title="Hello, " + ctx.author.display_name + "!",
                description="Let's get started:" +
                            "\nPlease respond in the chat with the player tag of __**your**__ account.\n(Example: #PC2UJVVU)\nYou have 10 minutes to reply.\nSee image below for help finding your player tag.",
                color=discord.Color.green())

            embed.set_footer(text="Type `cancel` at any point to quit")
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
            await msg.edit(embed=embed)
            x = 0
            while (correctTag == False):
                x += 1
                if x == 4:
                    return

                def check(message):
                    ctx.message.content = message.content
                    return message.content != "" and message.author == executor

                # LETS SEEE WHAT HAPPENS

                try:
                    m = await self.bot.wait_for("message", check=check, timeout=600)
                    await m.delete()
                except:
                    link_open.remove(member)
                    embed = discord.Embed(
                        description=f"Command Timed-out please run again.",
                        color=discord.Color.red())
                    return await msg.edit(embed=embed)
                playerTag = ctx.message.content
                player = await getPlayer(playerTag)
                clan = await getClan(playerTag)

                if (playerTag.lower() == "cancel"):
                    cancel = True
                    link_open.remove(member)
                    canceled = discord.Embed(
                        description="Command Canceled",
                        color=0xf30000)
                    return await msg.edit(embed=canceled)

                if (player == None):
                    if clan is not None:
                        embed = discord.Embed(
                            title=f"Sorry, `{playerTag}` is invalid and it also appears to be the **clan** tag for " + clan.name,
                            description="Player tags only, What is the correct player tag? (Image below for reference)",
                            color=0xf30000)
                        embed.set_image(
                            url="https://media.discordapp.net/attachments/815832030084333628/845542691411853312/image0.jpg")
                        embed.set_footer(text="Type `cancel` at any point to quit")
                        await msg.edit(embed=embed)
                    else:
                        embed = discord.Embed(
                            title=f"Sorry, `{playerTag}` is an invalid player tag. Please try again.",
                            description="What is the correct player tag? (Image below for reference)", color=0xf30000)
                        embed.set_image(
                            url="https://media.discordapp.net/attachments/815832030084333628/845542691411853312/image0.jpg")
                        embed.set_footer(text="Type `cancel` at any point to quit")
                        await msg.edit(embed=embed)
                    continue
                else:
                    correctTag = True

        player = await getPlayer(playerTag)
        if player == None:
            link_open.remove(member)
            embed = discord.Embed(
                title=playerTag + " is an invalid playertag. Try again. Reference image below & try linking again.",
                color=discord.Color.red())
            embed.set_image(
                url="https://media.discordapp.net/attachments/815832030084333628/845542691411853312/image0.jpg")
            return await msg.edit(embed=embed, mention_author=False)
        linked = await link_client.get_link(player.tag)

        if (linked != member.id) and (linked != None):
            link_open.remove(member)
            embed = discord.Embed(
                description=f"[{player.name}]({player.share_link}) is already linked to another discord user.",
                color=discord.Color.red())
            return await msg.edit(embed=embed, mention_author=False)
        elif linked == member.id:
            link_open.remove(member)
            evalua = self.bot.get_cog("eval")
            changes = await evalua.eval_member(ctx, member, False)

            embed = discord.Embed(
                description=f"You're already linked {executor.mention}! Updating your roles.\n"
                            f"Added: {changes[0]}\n"
                            f"Removed: {changes[1]}", color=discord.Color.green())
            return await msg.edit(embed=embed, mention_author=False)

        playerToken = None
        if cancel is not True:

            embed = discord.Embed(
                title="What is your api token? ",
                description=f"- Reference below for help finding your api token.\n- Open COC and navigate to Settings > More Settings - OR use the below link:\nhttps://link.clashofclans.com/?action=OpenMoreSettings" +
                            "\n- Scroll down to the bottom and copy the api token.\n- View the picture below for reference.",
                color=discord.Color.green())
            embed.set_footer(text="Type `cancel` at any point to quit\n(API Token is one-time use.)")
            embed.set_image(
                url="https://media.discordapp.net/attachments/822599755905368095/826178477023166484/image0.png?width=1806&height=1261")
            await msg.edit(embed=embed)

            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == executor

            try:
                m = await self.bot.wait_for("message", check=check, timeout=600)
                await m.delete()
            except:
                link_open.remove(member)
                embed = discord.Embed(
                    description=f"Command Timed-out please run again.",
                    color=discord.Color.red())
                return await msg.edit(embed=embed)
            playerToken = ctx.message.content
            if playerToken.lower() == "cancel":
                cancel = True
                link_open.remove(member)
                canceled = discord.Embed(
                    description="Command Canceled",
                    color=0xf30000)
                return await msg.edit(embed=canceled)

        if cancel is not True:
            try:
                playerVerified = await verifyPlayer(player.tag, playerToken)
                linked = await link_client.get_link(player.tag)

                if (linked is None) and (playerVerified == True):
                    link_open.remove(member)
                    await link_client.add_link(player.tag, member.id)
                    evalua = self.bot.get_cog("eval")
                    changes = await evalua.eval_member(ctx, member, False)
                    embed = discord.Embed(
                        description=f"[{player.name}]({player.share_link}) successfully linked to {member.mention}.\n"
                                    f"Added: {changes[0]}\n"
                                    f"Removed: {changes[1]}", color=discord.Color.green())

                    await msg.edit(embed=embed, mention_author=False)
                    greet = changes[2]
                    if greet:
                        results = await server.find_one({"server": ctx.guild.id})
                        greeting = results.get("greeting")
                        if greeting == None:
                            greeting = ""

                        results = await clans.find_one({"$and": [
                            {"alias": player.clan},
                            {"server": ctx.guild.id}
                        ]})
                        channel = results.get("clanChannel")
                        channel = self.bot.get_channel(channel)
                        await channel.send(f"{ctx.author.mention}, welcome to {ctx.guild.name}! {greet}")


                elif (linked is None) and (playerVerified == False):
                    link_open.remove(member)
                    embed = discord.Embed(
                        description="Hey " + member.display_name + f"! The player you are looking for is [{player.name}]({player.share_link})  however it appears u may have made a mistake. \nDouble check your player tag and/or api token again.",
                        color=discord.Color.red())
                    await msg.edit(embed=embed)

            except:
                link_open.remove(member)
                embed = discord.Embed(title="Something went wrong " + member.display_name + " :(",
                                      description="Take a second glance at your player tag and/or token, one is completely invalid.",
                                      color=discord.Color.red())
                await msg.edit(embed=embed)


    @commands.command(name="modlink")
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def modlink(self, ctx, user, *, playerTags):
        user = await pingToMember(ctx, user)
        if user is None:
            embed = discord.Embed(description="Invalid Discord User", color=discord.Color.red())
            return await ctx.reply(embed=embed, mention_author=False)

        playerTags = playerTags.split()
        for playerTag in playerTags:
            player = await getPlayer(playerTag)
            if player is None:
                embed = discord.Embed(description="Invalid Player Tag", color=discord.Color.red())
                return await ctx.reply(embed=embed, mention_author=False)

            linked = await link_client.get_link(player.tag)
            if linked is not None:
                embed = discord.Embed(
                    title=player.name + " is already linked to a discord user.",
                    color=discord.Color.red())
                return await ctx.reply(embed=embed, mention_author=False)

            await link_client.add_link(player.tag, user.id)

            evalua = self.bot.get_cog("eval")
            changes = await evalua.eval_member(ctx, user, False)

            embed = discord.Embed(description=f"[{player.name}]({player.share_link}) has been linked to {user.mention}.\n"
                                              f"Added: {changes[0]}\n"
                                                  f"Removed: {changes[1]}", color=discord.Color.green())
            await ctx.reply(embed=embed, mention_author=False)
            greet = changes[2]
            if greet:
                results = await server.find_one({"server": ctx.guild.id})
                greeting = results.get("greeting")
                if greeting == None:
                    greeting = ""

                results = await clans.find_one({"$and": [
                    {"tag": player.clan.tag},
                    {"server": ctx.guild.id}
                ]})
                channel = results.get("clanChannel")
                channel = self.bot.get_channel(channel)
                await channel.send(f"{user.mention}, welcome to {ctx.guild.name}! {greeting}")

    @commands.command(name="unlink")
    @commands.check_any(commands.has_permissions(manage_roles=True), check_commands())
    async def unlink(self, ctx, playerTag):
        player = await getPlayer(playerTag)
        if player is None:
            embed = discord.Embed(description="Invalid Player Tag", color=discord.Color.red())
            return await ctx.reply(embed=embed, mention_author=False)

        linked = await link_client.get_link(player.tag)
        if linked is None:
            embed = discord.Embed(
                title=player.name + " is not linked to a discord user.",
                color=discord.Color.red())
            return await ctx.reply(embed=embed, mention_author=False)

        member = await pingToMember(ctx, linked)
        is_member = (member != None)
        if ctx.guild.id == 328997757048324101:
            is_member = True

        if is_member == False:
            embed = discord.Embed(description=f"[{player.name}]({player.share_link}), cannot unlink players not on this server.",
                                  color=discord.Color.green())
            await ctx.reply(embed=embed, mention_author=False)

        await link_client.delete_link(player.tag)

        embed = discord.Embed(description=f"[{player.name}]({player.share_link}) has been unlinked from discord.",
                              color=discord.Color.green())
        await ctx.reply(embed=embed, mention_author=False)




def setup(bot: commands.Bot):
    bot.add_cog(Linking(bot))