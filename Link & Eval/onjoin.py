
from disnake.ext import commands

import disnake
from main import check_commands

from utils.clashClient import getClan, getPlayer, verifyPlayer, link_client, client, pingToChannel

usafam = client.usafam
clans = usafam.clans
server = usafam.server
welcome = usafam.welcome

link_open=[]
import emoji as em

class joinstuff(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    '''
    @commands.group(name="welcome", pass_context=True, invoke_without_command=True)
    async def welcome(self,ctx):
        pass

    @welcome.group(name="setup", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def welcome_set(self, ctx):

        embed = disnake.Embed(title="**Welcome Channel**",
                              description=f"What is the channel to post the welcome message in?\n Please make sure I have perms to send messages there.",
                              color=disnake.Color.green())
        embed.set_footer(text="Type `cancel` at any point to quit.")
        msg = await ctx.send(embed=embed)

        welcomeChannel = None
        while welcomeChannel == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            welcomeChannel = await pingToChannel(ctx, response)

            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg.edit(embed=embed)

            if welcomeChannel is None:
                embed = disnake.Embed(title="Sorry that channel is invalid. Please try again.",
                                      description=f"What is welcome channel?",
                                      color=disnake.Color.red())
                embed.set_footer(text="Type `cancel` at any point to quit.")
                await msg.edit(embed=embed)
                continue

            c = welcomeChannel
            g = ctx.guild
            r = await g.fetch_member(824653933347209227)
            perms = c.permissions_for(r)
            send_msg = perms.send_messages
            if send_msg == False:
                embed = disnake.Embed(
                    description=f"Missing Permissions.\nMust have `Send Messages` in the welcome channel.\nTry Again. What is the channel?",
                    color=disnake.Color.red())
                embed.set_footer(text="Type `cancel` at any point to quit.")
                await msg.edit(embed=embed)
                welcomeChannel = None
                continue


        emoji = "<a:redflame:932469862633181194>"
        arrowleft = "<a:6270_Arrow_1_Gif:932470483205644300>"
        arrowright = "<a:rightarrow:932470092883722271>"

        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"DESCRIPTION TEXT - YOU CAN CHOOSE"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=ctx.author.avatar_url)

        stat_buttons = [
            create_button(label="SAMPLE", emoji="1️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label="SAMPLE", emoji="2️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label="SAMPLE", emoji="3️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}")]
        buttons = create_actionrow(*stat_buttons)
        await msg.edit(content=f"{ctx.author.mention}**EXAMPLE OF LIVE EMBED**", embed=embed, components=[buttons])

        msg2 = await ctx.reply(content="What description text would you like?\nType `cancel` at any point to quit.", mention_author=False)

        description = None

        while description == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="", embed=embed)
            if len(response) >= 1900:
                await msg2.edit(content="Description must be less than 1900 characters.\nPls try again, What description text would you like?\nType `cancel` at any point to quit.")
                continue
            description = response





        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"{description}"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=ctx.author.avatar_url)

        stat_buttons = [
            create_button(label="SAMPLE", emoji="1️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label="SAMPLE", emoji="2️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label="SAMPLE", emoji="3️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}")]
        buttons = create_actionrow(*stat_buttons)
        await msg.edit(embed=embed, components=[buttons])



        await msg2.edit(content="What text would you like on button 1 (far left button)?\nType `cancel` at any point to quit.")
        button1text = None
        while button1text == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="", embed=embed)
            if len(response) >= 80:
                await msg2.edit(
                    content="Button text must be less than 80 characters.\nPls try again, What button text would you like?\nType `cancel` at any point to quit.")
                continue
            button1text = response


        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"{description}"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=ctx.author.avatar_url)

        stat_buttons = [
            create_button(label=f"{button1text}", emoji="1️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"SAMPLE", emoji="2️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"SAMPLE", emoji="3️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}")]
        buttons = create_actionrow(*stat_buttons)
        await msg.edit(embed=embed, components=[buttons])


        await msg2.edit(
            content="What text would you like on button 2 (middle button)?\nType `cancel` at any point to quit.")
        button2text = None
        while button2text == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="", embed=embed)

            if len(response) >= 80:
                await msg2.edit(
                    content="Button text must be less than 80 characters.\nPls try again, What button text would you like?\nType `cancel` at any point to quit.")
                continue
            button2text = response


        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"{description}"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=ctx.author.avatar_url)

        stat_buttons = [
            create_button(label=f"{button1text}", emoji="1️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"{button2text}", emoji="2️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"SAMPLE", emoji="3️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}")]
        buttons = create_actionrow(*stat_buttons)
        await msg.edit(embed=embed, components=[buttons])

        await msg2.edit(
            content="What text would you like on button 3 (far right button)?\nType `cancel` at any point to quit.")
        button3text = None
        while button3text == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="", embed=embed)

            if len(response) >= 80:
                await msg2.edit(
                    content="Button text must be less than 80 characters.\nPls try again, What button text would you like?\nType `cancel` at any point to quit.")
                continue
            button3text = response



        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"{description}"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=ctx.author.avatar_url)

        stat_buttons = [
            create_button(label=f"{button1text}", emoji="1️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"{button2text}", emoji="2️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"{button3text}", emoji="3️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}")]
        buttons = create_actionrow(*stat_buttons)
        await msg.edit(embed=embed, components=[buttons])


        await msg2.edit(
            content="What emoji would you like on button 1 (far left button)?\nType `cancel` at any point to quit.")
        button1emoji = None
        while button1emoji == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()

            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="", embed=embed)

            if not em.is_emoji(response):
                await msg2.edit(content=f"{response} is not a valid emoji (must be a default emoji, not disnake/server emoji).")
                continue
            button1emoji = response


        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"{description}"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=ctx.author.avatar_url)

        stat_buttons = [
            create_button(label=f"{button1text}", emoji=f"{button1emoji}", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"{button2text}", emoji="2️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"{button3text}", emoji="3️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}")]
        buttons = create_actionrow(*stat_buttons)
        await msg.edit(embed=embed, components=[buttons])


        await msg2.edit(
            content="What emoji would you like on button 2 (middle button)?\nType `cancel` at any point to quit.")
        button2emoji = None
        while button2emoji == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="", embed=embed)

            if not em.is_emoji(response):
                await msg2.edit(content=f"{response} is not a valid emoji (must be a default emoji, not disnake/server emoji).")
                continue
            button2emoji = response


        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"{description}"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=ctx.author.avatar_url)

        stat_buttons = [
            create_button(label=f"{button1text}", emoji=f"{button1emoji}", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"{button2text}", emoji=f"{button2emoji}", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"{button3text}", emoji="3️⃣", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}")]
        buttons = create_actionrow(*stat_buttons)
        await msg.edit(embed=embed, components=[buttons])

        await msg2.edit(
            content="What emoji would you like on button 3 (far right button)?\nType `cancel` at any point to quit.")
        button3emoji = None
        while button3emoji == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="", embed=embed)

            if not em.is_emoji(response):
                await msg2.edit(content=f"{response} is not a valid emoji (must be a default emoji, not disnake/server emoji).")
                continue
            button3emoji = response


        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"{description}"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=ctx.author.avatar_url)

        stat_buttons = [
            create_button(label=f"{button1text}", emoji=f"{button1emoji}", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"{button2text}", emoji=f"{button2emoji}", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}"),
            create_button(label=f"{button3text}", emoji=f"{button3emoji}", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{ctx.channel.id}")]
        buttons = create_actionrow(*stat_buttons)
        await msg.edit(embed=embed, components=[buttons])



        await msg2.edit(
            content="What channel would you like button 1 to link to (far left button)?\nType `cancel` at any point to quit.")
        button1channel = None
        while button1channel == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            button1channel = await pingToChannel(ctx, response)

            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="",embed=embed)

            if button1channel is None:
                content = "Sorry that channel is invalid. Please try again.\nWhat channel would you like button 1 to link to (far left button)?\nType `cancel` at any point to quit."
                await msg2.edit(content=content)
                continue


        await msg2.edit(
            content="What channel would you like button 2 to link to (middle button)?\nType `cancel` at any point to quit.")
        button2channel = None
        while button2channel == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            button2channel = await pingToChannel(ctx, response)

            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="", embed=embed)

            if button2channel is None:
                content = "Sorry that channel is invalid. Please try again.\nWhat channel would you like button 2 to link to (middle button)?\nType `cancel` at any point to quit."
                await msg2.edit(content=content)
                continue

        await msg2.edit(
            content="What channel would you like button 3 to link to (right button)?\nType `cancel` at any point to quit.")
        button3channel = None
        while button3channel == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            button3channel = await pingToChannel(ctx, response)

            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg2.edit(content="", embed=embed)

            if button3channel is None:
                content = "Sorry that channel is invalid. Please try again.\nWhat channel would you like button 3 to link to (right button)?\nType `cancel` at any point to quit."
                await msg2.edit(content=content)
                continue


        embed = disnake.Embed(title="Enjoy your stay!",
                              description=f"{emoji}**Welcome to {ctx.guild.name}!**{emoji}\n"
                                          f"{description}"
                                          f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=ctx.author.avatar_url)

        stat_buttons = [
            create_button(label=f"{button1text}", emoji=f"{button1emoji}", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{button1channel.id}"),
            create_button(label=f"{button2text}", emoji=f"{button2emoji}", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{button2channel.id}"),
            create_button(label=f"{button3text}", emoji=f"{button3emoji}", style=ButtonStyle.URL,
                          url=f"https://disnake.com/channels/{ctx.guild.id}/{button3channel.id}")]
        buttons = create_actionrow(*stat_buttons)
        await msg.edit(embed=embed, components=[buttons])

        await msg2.edit(
            content="Setup Complete! The embed above is a live version of how it will look.")

        results = await welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await welcome.insert_one({
                "server": ctx.guild.id,
                "welcome_channel": welcomeChannel.id,
                "description" : description,
                "button1text" : button1text,
                "button2text": button2text,
                "button3text": button3text,
                "button1emoji": button1emoji,
                "button2emoji": button2emoji,
                "button3emoji": button3emoji,
                "button1channel": button1channel.id,
                "button2channel": button2channel.id,
                "button3channel": button3channel.id,
                "link_channel" : None
            })
        else:
            await welcome.update_one({"server": ctx.guild.id}, {'$set': {
                "welcome_channel": welcomeChannel.id,
                "description" : description,
                "button1text" : button1text,
                "button2text": button2text,
                "button3text": button3text,
                "button1emoji": button1emoji,
                "button2emoji": button2emoji,
                "button3emoji": button3emoji,
                "button1channel": button1channel.id,
                "button2channel": button2channel.id,
                "button3channel": button3channel.id
            }})

    @commands.group(name="linkbutton", pass_context=True, invoke_without_command=True)
    async def linkmessage(self, ctx):
        pass

    @linkmessage.group(name="setup", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def linkmessage_set(self, ctx):

        embed = disnake.Embed(title="**Link Button Channel**",
                              description=f"What is the channel to post the Link Button message in?\n Please make sure I have perms to send messages there.",
                              color=disnake.Color.green())
        embed.set_footer(text="Type `cancel` at any point to quit.")
        msg = await ctx.send(embed=embed)

        welcomeChannel = None
        while welcomeChannel == None:
            def check(message):
                return message.content != "" and message.author == ctx.message.author and ctx.message.channel == message.channel

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            welcomeChannel = await pingToChannel(ctx, response)

            if response.lower() == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg.edit(embed=embed)

            if welcomeChannel is None:
                embed = disnake.Embed(title="Sorry that channel is invalid. Please try again.",
                                      description=f"What is the link button channel?",
                                      color=disnake.Color.red())
                embed.set_footer(text="Type `cancel` at any point to quit.")
                await msg.edit(embed=embed)
                continue

            c = welcomeChannel
            g = ctx.guild
            r = await g.fetch_member(824653933347209227)
            perms = c.permissions_for(r)
            send_msg = perms.send_messages
            if send_msg == False:
                embed = disnake.Embed(
                    description=f"Missing Permissions.\nMust have `Send Messages` in the link button channel.\nTry Again. What is the channel?",
                    color=disnake.Color.red())
                embed.set_footer(text="Type `cancel` at any point to quit.")
                await msg.edit(embed=embed)
                welcomeChannel = None
                continue

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
                "link_channel": welcomeChannel.id
            })
        else:
            await welcome.update_one({"server": ctx.guild.id}, {'$set': {
                "link_channel": welcomeChannel.id
            }})

        embed = disnake.Embed(description=f"Link Button Channel Successfully Setup!",
                              color=disnake.Color.green())
        await msg.edit(embed=embed)

    @linkmessage.group(name="remove", pass_context=True, invoke_without_command=True)
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

    @welcome.group(name="remove", pass_context=True, invoke_without_command=True)
    async def welcome_remove(self, ctx):
        results = await welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await welcome.insert_one({
                "server": None,
                "welcome_channel":None,
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

                embed.set_thumbnail(url=member.avatar_url)

                stat_buttons = [
                    create_button(label=f"{button1text}", emoji=f"{button1emoji}", style=ButtonStyle.URL,
                                  url=f"https://disnake.com/channels/{member.guild.id}/{button1channel}"),
                    create_button(label=f"{button2text}", emoji=f"{button2emoji}", style=ButtonStyle.URL,
                                  url=f"https://disnake.com/channels/{member.guild.id}/{button2channel}"),
                    create_button(label=f"{button3text}", emoji=f"{button3emoji}", style=ButtonStyle.URL,
                                  url=f"https://disnake.com/channels/{member.guild.id}/{button3channel}")]
                buttons = create_actionrow(*stat_buttons)
                await channel.send(content=f"{member.mention}",embed=embed, components=[buttons])


            link_channel = results.get("link_channel")
            if link_channel != None:
                channel = self.bot.get_channel(link_channel)
                embed = disnake.Embed(title=f"**Welcome to {member.guild.name}!**",
                                      description=f"To link your account, press the button below & follow the step by step instructions.",
                                      color=disnake.Color.green())
                stat_buttons = [
                    create_button(label="Link Account", emoji="🔗", style=ButtonStyle.blue, custom_id="Start Link", disabled=False)]
                stat_buttons = create_actionrow(*stat_buttons)
                embed.set_thumbnail(url=member.guild.icon_url_as())
                await channel.send(content=member.mention, embed=embed, components=[stat_buttons])

    

    @commands.Cog.listener()
    async def on_component(self, ctx : disnake_slash.ComponentContext):
        if ctx.channel.id == 945228791792431154:
            return
        if ctx.custom_id == "Start Link":
            playerTag = None
            member = ctx.author

            if member in link_open:
                return await ctx.send(content="You already have a link command open, please finish linking there or type `cancel` to cancel the command.", hidden=True)

            executor = ctx.author
            link_open.append(member)

            messagesSent = []

            cancel = False
            correctTag = False

            embed = disnake.Embed(description="<a:loading:884400064313819146> Starting link...",
                                  color=disnake.Color.green())

            msg = await ctx.reply(embed=embed)


            playerTag = ""
            playerToken = ""
            embed = disnake.Embed(
                title="Hello, " + ctx.author.display_name + "!",
                description="Let's get started:" +
                            "\nPlease respond with the player tag of __**your**__ account\n(Example: #PC2UJVVU)\nYou have 10 minutes to reply.\nSee image below for help finding & copying your player tag.",
                color=disnake.Color.green())

            embed.set_footer(text="Type `cancel` at any point to quit")
            embed.set_image(
                url="https://cdn.disnakeapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
            await msg.edit(embed=embed)
            x = 0
            while (correctTag == False):
                x += 1
                if x == 4:
                    link_open.remove(member)
                    embed = disnake.Embed(
                        description=f"Canceling command. Player Tag Failed 4 Times.",
                        color=disnake.Color.red())
                    return await msg.edit(embed=embed)

                def check(message):
                    ctx.message.content = message.content
                    return message.content != "" and message.author == executor

                # LETS SEEE WHAT HAPPENS

                try:
                    m = await self.bot.wait_for("message", check=check, timeout=600)
                    await m.delete()
                except:
                    link_open.remove(member)
                    embed = disnake.Embed(
                        description=f"Command Timed-out please run again.",
                        color=disnake.Color.red())
                    return await msg.edit(embed=embed)
                playerTag = ctx.message.content
                player = await getPlayer(playerTag)
                clan = await getClan(playerTag)

                if (playerTag.lower() == "cancel"):
                    cancel = True
                    link_open.remove(member)
                    canceled = disnake.Embed(
                        description="Command Canceled",
                        color=0xf30000)
                    return await msg.edit(embed=canceled)

                if (player == None):
                    if clan is not None:
                        embed = disnake.Embed(
                            title=f"Sorry, `{playerTag}` is invalid and it also appears to be the **clan** tag for " + clan.name,
                            description="Player tags only, What is the correct player tag? (Image below for reference)", color=0xf30000)
                        embed.set_image(
                            url="https://cdn.disnakeapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
                        embed.set_footer(text="Type `cancel` at any point to quit")
                        await msg.edit(embed=embed)
                    else:
                        embed = disnake.Embed(
                            title=f"Sorry, `{playerTag}` is an invalid player tag. Please try again.",
                            description="What is the correct player tag? (Image below for reference)", color=0xf30000)
                        embed.set_image(
                            url="https://cdn.disnakeapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
                        embed.set_footer(text="Type `cancel` at any point to quit")
                        await msg.edit(embed=embed)
                    continue
                else:
                    correctTag = True

            player = await getPlayer(playerTag)
            if player == None:
                link_open.remove(member)
                embed = disnake.Embed(
                    title=playerTag + " is an invalid playertag. Try again.",
                    color=disnake.Color.red())
                return await msg.edit(embed=embed, mention_author=False)
            linked = await link_client.get_link(player.tag)

            if (linked != member.id) and (linked != None):
                link_open.remove(member)
                embed = disnake.Embed(
                    description=f"[{player.name}]({player.share_link}) is already linked to another disnake user.",
                    color=disnake.Color.red())
                return await msg.edit(embed=embed, mention_author=False)
            elif linked == member.id:
                link_open.remove(member)
                evalua = self.bot.get_cog("eval")
                changes = await evalua.eval_member(ctx, member, False)

                embed = disnake.Embed(
                    description=f"You're already linked {executor.mention}! Updating your roles.\n"
                                f"Added: {changes[0]}\n"
                                f"Removed: {changes[1]}", color=disnake.Color.green())
                return await msg.edit(embed=embed, mention_author=False)

            if cancel is not True:

                embed = disnake.Embed(
                    title="What is your api token? ",
                    description=f"- Reference below for help finding your api token.\n- Open COC and navigate to Settings > More Settings - OR use the below link:\nhttps://link.clashofclans.com/?action=OpenMoreSettings" +
                                "\n- Scroll down to the bottom and copy the api token.\n- View the picture below for reference.",
                    color=disnake.Color.green())
                embed.set_footer(text="Type `cancel` at any point to quit\n(API Token is one-time use.)")
                embed.set_image(
                    url="https://media.disnakeapp.net/attachments/822599755905368095/826178477023166484/image0.png?width=1806&height=1261")
                await msg.edit(embed=embed)

                def check(message):
                    ctx.message.content = message.content
                    return message.content != "" and message.author == executor

                try:
                    m = await self.bot.wait_for("message", check=check, timeout=600)
                    await m.delete()
                except:
                    link_open.remove(member)
                    embed = disnake.Embed(
                        description=f"Command Timed-out please run again.",
                        color=disnake.Color.red())
                    return await msg.edit(embed=embed)
                playerToken = ctx.message.content
                if playerToken.lower() == "cancel":
                    cancel = True
                    link_open.remove(member)
                    canceled = disnake.Embed(
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
                        embed = disnake.Embed(
                            description=f"[{player.name}]({player.share_link}) successfully linked to {member.mention}.\n"
                                        f"Added: {changes[0]}\n"
                                        f"Removed: {changes[1]}", color=disnake.Color.green())
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
                        embed = disnake.Embed(
                            description="Hey " + member.display_name + f"! The player you are looking for is [{player.name}]({player.share_link})  however it appears u may have made a mistake. \nDouble check your player tag and/or api token again.",
                            color=disnake.Color.red())
                        await msg.edit(embed=embed)

                except:
                    link_open.remove(member)
                    embed = disnake.Embed(title="Something went wrong " + member.display_name + " :(",
                                          description="Take a second glance at your player tag and/or token, one is completely invalid.",
                                          color=disnake.Color.red())
                    await msg.edit(embed=embed)

    '''
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