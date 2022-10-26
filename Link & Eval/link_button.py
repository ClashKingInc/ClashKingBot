import disnake

from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from disnake.ext import commands

class LinkWelcomeMessages(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        results = await self.bot.welcome.find_one({"server": member.guild.id})
        if results is not None:
            welcome_channel = results.get("welcome_channel")

            if welcome_channel is not None:
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
                arrowright = "<a:rightarrow:932470092883722271>"

                embed = disnake.Embed(title="Enjoy your stay!",
                                      description=f"{emoji}**Welcome to {member.guild.name}!**{emoji}\n"
                                                  f"{description}"
                                                  f"\n\n{arrowleft}__**Use the quick links below to get started.**__{arrowright}",
                                      color=disnake.Color.green())

                embed.set_thumbnail(url=member.display_avatar.url)

                stat_buttons = [
                    disnake.ui.Button(label=f"{button1text}", emoji=f"{button1emoji}",
                                      url=f"https://discord.com/channels/{member.guild.id}/{button1channel}"),
                    disnake.ui.Button(label=f"{button2text}", emoji=f"{button2emoji}",
                                      url=f"https://discord.com/channels/{member.guild.id}/{button2channel}"),
                    disnake.ui.Button(label=f"{button3text}", emoji=f"{button3emoji}",
                                      url=f"https://discord.com/channels/{member.guild.id}/{button3channel}")]
                buttons = disnake.ui.ActionRow()
                for button in stat_buttons:
                    buttons.append_item(button)
                await channel.send(content=f"{member.mention}", embed=embed, components=[buttons])

            link_channel = results.get("link_channel")
            if link_channel is not None:
                channel = self.bot.get_channel(link_channel)
                embed = disnake.Embed(title=f"**Welcome to {member.guild.name}!**",
                                      description=f"To link your account, press the link button below to get started.",
                                      color=disnake.Color.green())
                stat_buttons = [disnake.ui.Button(label="Link Account", emoji="🔗", style=disnake.ButtonStyle.green,
                                                  custom_id="Start Link"),
                                disnake.ui.Button(label="Help", emoji="❓", style=disnake.ButtonStyle.grey,
                                                  custom_id="Link Help")]
                buttons = disnake.ui.ActionRow()
                for button in stat_buttons:
                    buttons.append_item(button)
                if member.guild.icon is not None:
                    embed.set_thumbnail(url=member.guild.icon.url)
                try:
                    if member.guild.id == 923764211845312533:
                        await channel.send(content=member.mention, embed=embed, components=[stat_buttons],
                         allowed_mentions=disnake.AllowedMentions.none())
                    else:
                        await channel.send(content=member.mention, embed=embed, components=[stat_buttons])

                except:
                    pass

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):

        if ctx.data.custom_id == "Start Link":
            components = [
                    disnake.ui.TextInput(
                        label="Player Tag",
                        placeholder="Your player tag as found in-game.",
                        custom_id=f"player_tag",
                        required=True,
                        style=disnake.TextInputStyle.single_line,
                        max_length=12,
                    )
                ]
            token_option = await self.bot.welcome.find_one({"server": ctx.guild.id})
            token_option = token_option.get("api_token")
            if token_option is None:
                token_option = True
            if token_option:
                token_text = "Api Token"
            else:
                token_text = "(Optional) Api Token"
            components.append(
                    disnake.ui.TextInput(
                        label=token_text,
                        placeholder="Your Api Token as found in-game.",
                        custom_id=f"api_token",
                        required=token_option,
                        style=disnake.TextInputStyle.single_line,
                        max_length=12,
                    ))
            await ctx.response.send_modal(
                title="Link your account",
                custom_id="linkaccount-",
                components=components)

            def check(res):
                return ctx.author.id == res.author.id

            try:
                modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                    "modal_submit",
                    check=check,
                    timeout=300,
                )
            except:
                return

            player_tag = modal_inter.text_values["player_tag"]
            api_token = modal_inter.text_values["api_token"]
            await modal_inter.response.defer(ephemeral=True)

            player: MyCustomPlayer = await self.bot.getPlayer(player_tag=player_tag, custom=True)
            if player is None:
                clan = await self.bot.getClan(clan_tag=player_tag)
                if clan is not None:
                    embed = disnake.Embed(
                        description=f"Sorry, `{player_tag}` is invalid and it also appears to be the **clan** tag for {clan.name}\nUse the image below to help find your player tag.",
                        color=disnake.Color.red())
                    embed.set_image(
                        url="https://cdn.discordapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
                    return await modal_inter.edit_original_message(embed=embed)
                else:
                    embed = disnake.Embed(
                        description=f"**Sorry, `{player_tag}` is an invalid player tag** :( \nUse the image below to help find your player tag.",
                        color=disnake.Color.red())
                    embed.set_image(
                        url="https://cdn.discordapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
                    return await modal_inter.send(embed=embed)

            link_id = await player.linked()

            if token_option or link_id != ctx.author.id:
                verified = await player.verify(api_token=api_token)
            else:
                verified = True

            if link_id == ctx.author.id:
                evalua = self.bot.get_cog("Eval")
                changes = await evalua.eval_member(ctx, ctx.author, False)
                embed = disnake.Embed(
                    description=f"You're already linked {ctx.author.mention}! Updating your roles.\n"
                                f"Added: {changes[0]}\n"
                                f"Removed: {changes[1]}", color=disnake.Color.green())
                return await modal_inter.send(embed=embed)
            elif verified:
                await player.add_link(ctx.author)
                evalua = self.bot.get_cog("Eval")
                changes = await evalua.eval_member(ctx, ctx.author, False)
                embed = disnake.Embed(
                    description=f"[{player.name}]({player.share_link}) successfully linked to {ctx.author.mention}.\n"
                                f"Added: {changes[0]}\n"
                                f"Removed: {changes[1]}", color=disnake.Color.green())
                await modal_inter.send(embed=embed)
                try:
                    results = await self.bot.server_db.find_one({"server": ctx.guild.id})
                    greeting = results.get("greeting")
                    if greeting is None:
                        greeting = ""

                    results = await self.bot.clan_db.find_one({"$and": [
                        {"tag": player.clan.tag},
                        {"server": ctx.guild.id}
                    ]})
                    if ctx.author.id == 852623927284465664:
                        results = None
                    if results is not None:
                        channel = results.get("clanChannel")
                        channel = self.bot.get_channel(channel)
                        await channel.send(f"{ctx.author.mention}, welcome to {ctx.guild.name}! {greeting}")
                except:
                    pass
            elif not verified:
                if token_option:
                    embed = disnake.Embed(
                        description=f"The player you are looking for is [{player.name}]({player.share_link}), however it appears u may have made a mistake.\n Double check your api token again.",
                        color=disnake.Color.red())
                    await modal_inter.send(embed=embed)
                else:
                    embed = disnake.Embed(
                        description=f"[{player.name}]({player.share_link}) is already linked to another user. Please try again with an api token.",
                        color=disnake.Color.red())
                    await modal_inter.send(embed=embed)


        elif ctx.data.custom_id == "Link Help":
            embed = disnake.Embed(title="Finding a player tag",
                                  description=f"- Open Game\n- Navigate to your account's profile\n- Near top left click copy icon to copy player tag to clipboard\n"
                                              f"- Make sure it is the player tag & **not** the clan\n- View photo below for reference",
                                  color=disnake.Color.red())
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
            embed2 = disnake.Embed(
                title="What is your api token? ",
                description=f"- Reference below for help finding your api token.\n- Open Clash and navigate to Settings > More Settings\n- **OR** use the following link:\nhttps://link.clashofclans.com/?action=OpenMoreSettings" +
                            "\n- Scroll down to the bottom and copy the api token.\n- View the picture below for reference.",
                color=disnake.Color.red())
            embed2.set_image(
                url="https://cdn.discordapp.com/attachments/843624785560993833/961379232955658270/image0_2.png")
            await ctx.send(embeds=[embed, embed2], ephemeral=True)

def setup(bot: CustomClient):
    bot.add_cog(LinkWelcomeMessages(bot))