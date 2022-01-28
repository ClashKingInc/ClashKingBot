from discord.ext import commands
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle
import discord

from HelperMethods.clashClient import getClan, getPlayer, verifyPlayer, link_client

from HelperMethods.clashClient import client
usafam = client.usafam
clans = usafam.clans
server = usafam.server

link_open=[]

class joinstuff(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 328997757048324101:
            memId = member.mention
            channel = self.bot.get_channel(739597294474625034)

            emoji = "<a:redflame:932469862633181194>"
            arrowleft = "<a:6270_Arrow_1_Gif:932470483205644300>"
            arrowright =  "<a:rightarrow:932470092883722271>"
            clash = "<:clash:855491735488036904>"

            results = await server.find_one({"server": member.guild.id})
            prefix = results.get("prefix")

            embed = discord.Embed(title="Enjoy your stay!",description=f"{emoji}**Welcome to {member.guild.name}!**{emoji}\n"
                                                                       f"Thank you for joining the mighty U.S.A Family! If you are **looking for a clan**, please open a ticket in <#936477949803233320>."
                                                                       f" If you are **already** in a U.S.A Family clan, head over to <#803774459659681822> and follow the instructions to link your account.\n\n"
                                                                       f"{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                                  color=discord.Color.green())
            #embed.set_thumbnail(
                #url="https://media.discordapp.net/attachments/815832030084333628/854623578532216862/ezgif.com-gif-maker_1.gif")
            embed.set_thumbnail(url=member.avatar_url)
            #embed.set_footer(text="Feel free to message in #new-people if you need help.")

            stat_buttons = [
                create_button(label="Looking for a Clan", emoji="🔍", style=ButtonStyle.URL,  url="https://discord.com/channels/328997757048324101/936477949803233320"),
                create_button(label="Link Yourself", emoji="🔗", style=ButtonStyle.URL, url="https://discord.com/channels/328997757048324101/803774459659681822"),
                create_button(label="Rules & Info", emoji="📚", style=ButtonStyle.URL, url="https://discord.com/channels/328997757048324101/596905919581913101")]
            buttons = create_actionrow(*stat_buttons)
            await channel.send(content=member.mention,embed=embed, components= [buttons])

            channel = self.bot.get_channel(803774459659681822)
            embed = discord.Embed(title=f"**Welcome to {member.guild.name}!**",
                                  description=f"To link your account, press the button below & follow the step by step instructions.",
                                  color=discord.Color.green())
            stat_buttons = [
                create_button(label="Link Account", emoji="🔗", style=ButtonStyle.blue, custom_id="Start Link", disabled=False)]
            stat_buttons = create_actionrow(*stat_buttons)
            embed.set_thumbnail(url=member.guild.icon_url_as())
            await channel.send(content=member.mention, embed=embed, components=[stat_buttons])

    @commands.Cog.listener()
    async def on_component(self, ctx):
        if ctx.custom_id == "Start Link":
            playerTag = None
            member = ctx.author

            if member in link_open:
                return await ctx.send(content="You already have a link command open, please finish linking there or type `cancel`  to cancel the command.", hidden=True)

            executor = ctx.author
            link_open.append(member)

            messagesSent = []

            cancel = False
            correctTag = False

            embed = discord.Embed(description="<a:loading:884400064313819146> Starting link...",
                                  color=discord.Color.green())

            msg = await ctx.reply(embed=embed)


            playerTag = ""
            playerToken = ""
            embed = discord.Embed(
                title="Hello, " + ctx.author.display_name + "!",
                description="Let's get started:" +
                            "\nPlease respond with the player tag of __**your**__ account\n(Example: #PC2UJVVU)\nYou have 10 minutes to reply.\See image below for help finding & copying your player tag.",
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
                            description="Player tags only, What is the correct player tag? (Image below for reference)", color=0xf30000)
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
                    title=playerTag + " is an invalid playertag. Try again.",
                    color=discord.Color.red())
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
                                {"tag": player.clan.tag},
                                {"server": ctx.guild.id}
                            ]})
                            channel = results.get("clanChannel")
                            channel = self.bot.get_channel(channel)
                            await channel.send(f"{ctx.author.mention}, welcome to {ctx.guild.name}! {greeting}")


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



def setup(bot: commands.Bot):
    bot.add_cog(joinstuff(bot))