
from disnake.ext import commands

import disnake
from main import check_commands

from utils.clash import getClan, getPlayer, verifyPlayer, link_client, client, pingToChannel

usafam = client.usafam
clans = usafam.clans
server = usafam.server
welcome = usafam.welcome

link_open=[]
import emoji as em

class joinstuff(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="welcome-message")
    async def welcome_message(self, ctx):
        pass

    @commands.slash_command(name="welcome-link")
    async def link_button(self, ctx):
        pass

    @welcome_message.sub_command(name="set", description="Set a customizable on-join welcome message for your server")
    async def welcome_set(self, ctx: disnake.ApplicationCommandInteraction, welcome_channel:disnake.TextChannel, body_text:str,
                          button1_text:str, button1_emoji:str, button1_link:disnake.TextChannel,
                          button2_text:str, button2_emoji:str, button2_link:disnake.TextChannel,
                          button3_text:str, button3_emoji:str, button3_link:disnake.TextChannel,):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        g = ctx.guild
        r = await g.fetch_member(824653933347209227)
        perms = welcome_channel.permissions_for(r)
        send_msg = perms.send_messages
        if send_msg == False:
            embed = disnake.Embed(
                description=f"Missing Permissions.\nMust have `Send Messages` in the welcome channel.\n",
                color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if len(button1_text) > 80 or len(button2_text) > 80 or len(button3_text) > 80:
            embed = disnake.Embed(
                description=f"Button text must be less than or equal to 80 characters.",
                color=disnake.Color.red())
            return await ctx.send(embed=embed)

        emoji = "<a:redflame:932469862633181194>"
        arrowleft = "<a:6270_Arrow_1_Gif:932470483205644300>"
        arrowright = "<a:rightarrow:932470092883722271>"

        if not em.is_emoji(button1_emoji):
            return await ctx.send(
                content=f"{button1_emoji} is not a valid emoji (must be a default emoji, not discord/server emoji).")
        if not em.is_emoji(button2_emoji):
            return await ctx.send(
                content=f"{button2_emoji} is not a valid emoji (must be a default emoji, not discord/server emoji).")
        if not em.is_emoji(button3_emoji):
            return await ctx.send(
                content=f"{button3_emoji} is not a valid emoji (must be a default emoji, not discord/server emoji).")

        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"{body_text}"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        if ctx.author.avatar is None:
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/843624785560993833/961411093622816819/4_1.png")
        else:
            embed.set_thumbnail(url=ctx.author.avatar.url)

        link_buttons = [
            disnake.ui.Button(label=f"{button1_text}", emoji=f"{button1_emoji}",
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{button1_link.id}"),
            disnake.ui.Button(label=f"{button2_text}", emoji=f"{button2_emoji}",
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{button2_link.id}"),
            disnake.ui.Button(label=f"{button3_text}", emoji=f"{button3_emoji}",
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{button3_link.id}")]
        buttons = disnake.ui.ActionRow()
        for button in link_buttons:
            buttons.append_item(button)
        await ctx.send(embed=embed, components=[buttons])

        await ctx.channel.send(
            content="Welcome channel embed complete! The embed above is a live version of how it will look.")

        results = await welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await welcome.insert_one({
                "server": ctx.guild.id,
                "welcome_channel": welcome_channel.id,
                "description" : body_text,
                "button1text" : button1_text,
                "button2text": button2_text,
                "button3text": button3_text,
                "button1emoji": button1_emoji,
                "button2emoji": button2_emoji,
                "button3emoji": button3_emoji,
                "button1channel": button1_link.id,
                "button2channel": button2_link.id,
                "button3channel": button3_link.id,
                "link_channel" : None
            })
        else:
            await welcome.update_one({"server": ctx.guild.id}, {'$set': {
                "welcome_channel": welcome_channel.id,
                "description" : body_text,
                "button1text" : button1_text,
                "button2text": button2_text,
                "button3text": button3_text,
                "button1emoji": button1_emoji,
                "button2emoji": button2_emoji,
                "button3emoji": button3_emoji,
                "button1channel": button1_link.id,
                "button2channel": button2_link.id,
                "button3channel": button3_link.id
            }})

    @welcome_message.sub_command(name="remove", description="Remove the server welcome message")
    async def welcome_remove(self, ctx):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)
        results = await welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await welcome.insert_one({
                "server": None,
                "welcome_channel": None,
                "description": None,
                "button1text": None,
                "button2text": None,
                "button3text": None,
                "button1emoji": None,
                "button2emoji": None,
                "button3emoji": None,
                "button1channel": None,
                "button2channel": None,
                "button3channel": None,
                "link_channel": None
            })
        else:
            await welcome.update_one({"server": ctx.guild.id}, {'$set': {
                "welcome_channel": None,
                "description": None,
                "button1text": None,
                "button2text": None,
                "button3text": None,
                "button1emoji": None,
                "button2emoji": None,
                "button3emoji": None,
                "button1channel": None,
                "button2channel": None,
                "button3channel": None
            }})

        embed = disnake.Embed(description=f"Welcome Embed Successfully Removed!",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)


    @link_button.sub_command(name="set", description="Setup the on-join link button prompt for new users")
    async def linkmessage_set(self, ctx: disnake.ApplicationCommandInteraction, channel:disnake.TextChannel):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        g = ctx.guild
        r = await g.fetch_member(824653933347209227)
        perms = channel.permissions_for(r)
        send_msg = perms.send_messages
        if send_msg == False:
            embed = disnake.Embed(
                description=f"Missing Permissions.\nMust have `Send Messages` in the link button channel.\nTry Again. What is the channel?",
                color=disnake.Color.red())
            return await ctx.send(embed=embed)

        results = await welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await welcome.insert_one({
                "server": ctx.guild.id,
                "welcome_channel": None,
                "description": None,
                "button1text": None,
                "button2text": None,
                "button3text": None,
                "button1emoji": None,
                "button2emoji": None,
                "button3emoji": None,
                "button1channel": None,
                "button2channel": None,
                "button3channel": None,
                "link_channel": channel.id
            })
        else:
            await welcome.update_one({"server": ctx.guild.id}, {'$set': {
                "link_channel": channel.id
            }})

        embed = disnake.Embed(description=f"Link Button Channel Successfully Setup!",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @link_button.sub_command(name="remove", description="Setup the on-join link button prompt for new users")
    async def linkmessage_remove(self, ctx):

        results = await welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await welcome.insert_one({
                "server": ctx.guild.id,
                "welcome_channel": None,
                "description": None,
                "button1text": None,
                "button2text": None,
                "button3text": None,
                "button1emoji": None,
                "button2emoji": None,
                "button3emoji": None,
                "button1channel": None,
                "button2channel": None,
                "button3channel": None,
                "link_channel": None
            })
        else:
            await welcome.update_one({"server": ctx.guild.id}, {'$set': {
                "link_channel": None
            }})

        embed = disnake.Embed(description=f"Link Button Channel Successfully Removed!",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        results = await welcome.find_one({"server": member.guild.id})
        if results is not None:
            welcome_channel = results.get("welcome_channel")

            if welcome_channel != None:
                description = results.get("description")
                button1text = results.get("button1text")
                button2text = results.get("button2text")
                button3text = results.get("button3text")
                button1emoji = results.get("button1emoji")
                button2emoji = results.get("button2emoji")
                button3emoji = results.get("button3emoji")
                button1channel = results.get("button1channel")
                button2channel = results.get("button2channel")
                button3channel = results.get("button3channel")

                channel = self.bot.get_channel(welcome_channel)

                emoji = "<a:redflame:932469862633181194>"
                arrowleft = "<a:6270_Arrow_1_Gif:932470483205644300>"
                arrowright =  "<a:rightarrow:932470092883722271>"

                embed = disnake.Embed(title="Enjoy your stay!",
                                      description=f"{emoji}**Welcome to {member.guild.name}!**{emoji}\n"
                                                  f"{description}"
                                                  f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                                      color=disnake.Color.green())

                if member.avatar is None:
                    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/843624785560993833/961411093622816819/4_1.png")
                else:
                    embed.set_thumbnail(url=member.avatar.url)

                stat_buttons = [
                    disnake.ui.Button(label=f"{button1text}", emoji=f"{button1emoji}",
                                  url=f"https://disnake.com/channels/{member.guild.id}/{button1channel}"),
                    disnake.ui.Button(label=f"{button2text}", emoji=f"{button2emoji}",
                                  url=f"https://disnake.com/channels/{member.guild.id}/{button2channel}"),
                    disnake.ui.Button(label=f"{button3text}", emoji=f"{button3emoji}",
                                  url=f"https://disnake.com/channels/{member.guild.id}/{button3channel}")]
                buttons = disnake.ui.ActionRow()
                for button in stat_buttons:
                    buttons.append_item(button)
                await channel.send(content=f"{member.mention}",embed=embed, components=[buttons])


            link_channel = results.get("link_channel")
            if link_channel != None:
                channel = self.bot.get_channel(link_channel)
                embed = disnake.Embed(title=f"**Welcome to {member.guild.name}!**",
                                      description=f"To link your account, press the button below & follow the step by step instructions.",
                                      color=disnake.Color.green())
                stat_buttons = [
                    disnake.ui.Button(label="Link Account", emoji="🔗", style=disnake.ButtonStyle.blurple, custom_id="Start Link")]
                buttons = disnake.ui.ActionRow()
                for button in stat_buttons:
                    buttons.append_item(button)
                if member.guild.icon is not None:
                    embed.set_thumbnail(url=member.guild.icon.url)
                await channel.send(content=member.mention, embed=embed, components=[stat_buttons])


    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if ctx.channel.id == 945228791792431154:
            return

        if ctx.data.custom_id == "Start Link":
            playerTag = None
            member = ctx.author

            if member in link_open:
                return await ctx.send(content="You already have a link command open, please finish linking there or type `cancel` to cancel the command.", ephemeral=True)

            executor = ctx.author
            link_open.append(member)

            cancel = False
            correctTag = False

            embed = disnake.Embed(description="<a:loading:884400064313819146> Starting link...",
                                  color=disnake.Color.green())

            await ctx.send(embed=embed)


            playerTag = ""
            playerToken = ""
            embed = disnake.Embed(
                title="Hello, " + ctx.author.display_name + "!",
                description="Let's get started:" +
                            "\nPlease respond with the player tag of __**your**__ account\n(Example: #PC2UJVVU)\nYou have 10 minutes to reply.\nSee image below for help finding & copying your player tag.",
                color=disnake.Color.green())

            embed.set_footer(text="Type `cancel` at any point to quit")
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
            await ctx.edit_original_message(embed=embed)
            x = 0
            while (correctTag == False):
                x += 1
                if x == 4:
                    link_open.remove(member)
                    embed = disnake.Embed(
                        description=f"Canceling command. Player Tag Failed 4 Times.",
                        color=disnake.Color.red())
                    return await ctx.edit_original_message(embed=embed)

                def check(message):
                    ctx.message.content = message.content
                    return message.content != "" and message.author == executor and message.channel.id == ctx.channel.id

                # LETS SEEE WHAT HAPPENS

                try:
                    m = await self.bot.wait_for("message", check=check, timeout=600)
                    await m.delete()
                except:
                    link_open.remove(member)
                    embed = disnake.Embed(
                        description=f"Command Timed-out please run again.",
                        color=disnake.Color.red())
                    return await ctx.edit_original_message(embed=embed)
                playerTag = ctx.message.content
                player = await getPlayer(playerTag)
                clan = await getClan(playerTag)

                if (playerTag.lower() == "cancel"):
                    cancel = True
                    link_open.remove(member)
                    canceled = disnake.Embed(
                        description="Command Canceled",
                        color=0xf30000)
                    return await ctx.edit_original_message(embed=canceled)

                if (player == None):
                    if clan is not None:
                        embed = disnake.Embed(
                            title=f"Sorry, `{playerTag}` is invalid and it also appears to be the **clan** tag for " + clan.name,
                            description="Player tags only, What is the correct player tag? (Image below for reference)", color=0xf30000)
                        embed.set_image(
                            url="https://cdn.disnakeapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
                        embed.set_footer(text="Type `cancel` at any point to quit")
                        await ctx.edit_original_message(embed=embed)
                    else:
                        embed = disnake.Embed(
                            title=f"Sorry, `{playerTag}` is an invalid player tag. Please try again.",
                            description="What is the correct player tag? (Image below for reference)", color=0xf30000)
                        embed.set_image(
                            url="https://cdn.disnakeapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
                        embed.set_footer(text="Type `cancel` at any point to quit")
                        await ctx.edit_original_message(embed=embed)
                    continue
                else:
                    correctTag = True

            player = await getPlayer(playerTag)
            if player == None:
                link_open.remove(member)
                embed = disnake.Embed(
                    title=playerTag + " is an invalid playertag. Try again.",
                    color=disnake.Color.red())
                return await ctx.edit_original_message(embed=embed)
            linked = await link_client.get_link(player.tag)

            if (linked != member.id) and (linked != None):
                link_open.remove(member)
                embed = disnake.Embed(
                    description=f"[{player.name}]({player.share_link}) is already linked to another discord user.",
                    color=disnake.Color.red())
                return await ctx.edit_original_message(embed=embed)
            elif linked == member.id:
                link_open.remove(member)
                evalua = self.bot.get_cog("eval")
                changes = await evalua.eval_member(ctx, member, False)

                embed = disnake.Embed(
                    description=f"You're already linked {executor.mention}! Updating your roles.\n"
                                f"Added: {changes[0]}\n"
                                f"Removed: {changes[1]}", color=disnake.Color.green())
                return await ctx.edit_original_message(embed=embed)

            if cancel is not True:

                embed = disnake.Embed(
                    title="What is your api token? ",
                    description=f"- Reference below for help finding your api token.\n- Open Clash and navigate to Settings > More Settings - OR use the below link:\nhttps://link.clashofclans.com/?action=OpenMoreSettings" +
                                "\n- Scroll down to the bottom and copy the api token.\n- View the picture below for reference.",
                    color=disnake.Color.green())
                embed.set_footer(text="Type `cancel` at any point to quit\n(API Token is one-time use.)")
                embed.set_image(
                    url="https://cdn.discordapp.com/attachments/843624785560993833/961379232955658270/image0_2.png")
                await ctx.edit_original_message(embed=embed)

                def check(message):
                    ctx.message.content = message.content
                    return message.content != "" and message.author == executor and message.channel.id == ctx.channel.id

                try:
                    m = await self.bot.wait_for("message", check=check, timeout=600)
                    await m.delete()
                except:
                    link_open.remove(member)
                    embed = disnake.Embed(
                        description=f"Command Timed-out please run again.",
                        color=disnake.Color.red())
                    return await ctx.edit_original_message(embed=embed)
                playerToken = ctx.message.content
                if playerToken.lower() == "cancel":
                    cancel = True
                    link_open.remove(member)
                    canceled = disnake.Embed(
                        description="Command Canceled",
                        color=0xf30000)
                    return await ctx.edit_original_message(embed=canceled)

            if cancel is not True:
                try:
                    playerVerified = await verifyPlayer(player.tag, playerToken)
                    linked = await link_client.get_link(player.tag)

                    if (linked is None) and (playerVerified == True):
                        link_open.remove(member)
                        await link_client.add_link(player.tag, member.id)
                        evalua = self.bot.get_cog("eval")
                        changes = await evalua.eval_member(ctx, member, False)
                        embed = disnake.Embed(
                            description=f"[{player.name}]({player.share_link}) successfully linked to {member.mention}.\n"
                                        f"Added: {changes[0]}\n"
                                        f"Removed: {changes[1]}", color=disnake.Color.green())
                        await ctx.edit_original_message(embed=embed)
                        try:
                            results = await server.find_one({"server": ctx.guild.id})
                            greeting = results.get("greeting")
                            if greeting == None:
                                greeting = ""

                            results = await clans.find_one({"$and": [
                                {"tag": player.clan.tag},
                                {"server": ctx.guild.id}
                            ]})
                            if results != None:
                                channel = results.get("clanChannel")
                                channel = self.bot.get_channel(channel)
                                await channel.send(f"{ctx.author.mention}, welcome to {ctx.guild.name}! {greeting}")
                        except:
                            pass

                    elif (linked is None) and (playerVerified == False):
                        link_open.remove(member)
                        embed = disnake.Embed(
                            description="Hey " + member.display_name + f"! The player you are looking for is [{player.name}]({player.share_link})  however it appears u may have made a mistake. \nDouble check your api token again.",
                            color=disnake.Color.red())
                        await ctx.edit_original_message(embed=embed)

                except:
                    link_open.remove(member)
                    embed = disnake.Embed(title="Something went wrong " + member.display_name + " :(",
                                          description="Take a second glance at your player tag and/or token, one is completely invalid.",
                                          color=disnake.Color.red())
                    await ctx.edit_original_message(embed=embed)

    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        results = await server.find_one({"server": guild.id})
        if results is None:
            await server.insert_one({
                "server": guild.id,
                "prefix": ".",
                "banlist": None,
                "greeting": None,
                "cwlcount": None,
                "topboardchannel": None,
                "tophour": None,
                "lbboardChannel": None,
                "lbhour": None
            })
        channel = self.bot.get_channel(937519135607373874)
        await channel.send(f"Just joined {guild.name}")


def setup(bot: commands.Bot):
    bot.add_cog(joinstuff(bot))