from disnake.ext import commands
import disnake
import emoji as em

from CustomClasses.CustomBot import CustomClient

class joinstuff(commands.Cog, name="Welcome Setup"):

    def __init__(self, bot: CustomClient):
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
        if send_msg is False:
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
                          url=f"https://discord.com/channels/{ctx.guild.id}/{button1_link.id}"),
            disnake.ui.Button(label=f"{button2_text}", emoji=f"{button2_emoji}",
                          url=f"https://discord.com/channels/{ctx.guild.id}/{button2_link.id}"),
            disnake.ui.Button(label=f"{button3_text}", emoji=f"{button3_emoji}",
                          url=f"https://discord.com/channels/{ctx.guild.id}/{button3_link.id}")]
        buttons = disnake.ui.ActionRow()
        for button in link_buttons:
            buttons.append_item(button)
        await ctx.send(embed=embed, components=[buttons])

        await ctx.channel.send(
            content="Welcome channel embed complete! The embed above is a live version of how it will look.")

        results = await self.bot.welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await self.bot.welcome.insert_one({
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
            await self.bot.welcome.update_one({"server": ctx.guild.id}, {'$set': {
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
        results = await self.bot.welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await self.bot.welcome.insert_one({
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
            await self.bot.welcome.update_one({"server": ctx.guild.id}, {'$set': {
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
        if send_msg is False:
            embed = disnake.Embed(
                description=f"Missing Permissions.\nMust have `Send Messages` in the link button channel.\nTry Again. What is the channel?",
                color=disnake.Color.red())
            return await ctx.send(embed=embed)

        results = await self.bot.welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await self.bot.welcome.insert_one({
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
            await self.bot.welcome.update_one({"server": ctx.guild.id}, {'$set': {
                "link_channel": channel.id
            }})

        embed = disnake.Embed(description=f"Link Button Channel Successfully Setup!",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)

    @link_button.sub_command(name="remove", description="Setup the on-join link button prompt for new users")
    async def linkmessage_remove(self, ctx):

        results = await self.bot.welcome.find_one({"server": ctx.guild.id})
        if results is None:
            await self.bot.welcome.insert_one({
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
            await self.bot.welcome.update_one({"server": ctx.guild.id}, {'$set': {
                "link_channel": None
            }})

        embed = disnake.Embed(description=f"Link Button Channel Successfully Removed!",
                              color=disnake.Color.green())
        await ctx.send(embed=embed)



def setup(bot: CustomClient):
    bot.add_cog(joinstuff(bot))