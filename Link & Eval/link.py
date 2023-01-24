from disnake.ext import commands
import disnake
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import CustomServer
from main import check_commands
from utils.search import search_results

class Linking(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="refresh", description="Self evaluate & refresh your server roles")
    async def refresh(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        change_nickname = await server.nickname_choice
        tags = await self.bot.get_tags(str(ctx.author.id))
        if tags != []:
            evalua = self.bot.get_cog("Eval")
            embed = await evalua.eval_logic(ctx=ctx, members_to_eval=[ctx.author], role_or_user=ctx.author,
                                              test=False,
                                              change_nick=change_nickname,
                                              return_embed=True)
            return await ctx.edit_original_message(embed=embed)
        else:
            embed = disnake.Embed(
                description=f"You have no accounts linked.", color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

    @commands.slash_command(name="link", description="Link clash of clans accounts to your discord profile")
    async def link(self,  ctx: disnake.ApplicationCommandInteraction, player_tag, api_token):
        """
            Parameters
            ----------
            player_tag: player_tag as found in-game
            api_token: player api-token, use /linkhelp for more info
        """
        await ctx.response.defer()
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        change_nickname = await server.nickname_choice
        try:
            player = await self.bot.getPlayer(player_tag)
            if player is None:
                embed = disnake.Embed(description=f"{player_tag} is not a valid player tag. Use the photo below to help find your player tag.", color=disnake.Color.red())
                embed.set_image(
                    url="https://cdn.discordapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
                return await ctx.edit_original_message(embed=embed)

            verified = await self.bot.verifyPlayer(player.tag, api_token)
            linked = await self.bot.link_client.get_link(player.tag)
            is_linked = (linked is not None)

            if verified and is_linked:
                if linked == ctx.author.id:
                    evalua = self.bot.get_cog("Eval")
                    embed = await evalua.eval_logic(ctx=ctx, members_to_eval=[ctx.author], role_or_user=ctx.author,
                                                    test=False,
                                                    change_nick=change_nickname,
                                                    return_embed=True)
                    await ctx.edit_original_message(embed=embed)
                else:
                    embed = disnake.Embed(
                        description=f"[{player.name}]({player.share_link}) is already linked to another discord user. Use `/unlink` to remove the link first.", color=disnake.Color.red())
                    await ctx.edit_original_message(embed=embed)

            elif verified and not is_linked:
                await self.bot.link_client.add_link(player.tag, ctx.author.id)
                evalua = self.bot.get_cog("Eval")
                embed = await evalua.eval_logic(ctx=ctx, members_to_eval=[ctx.author], role_or_user=ctx.author,
                                                test=False,
                                                change_nick=change_nickname,
                                                return_embed=True)
                embed.title = f"**{player.name} successfully linked to {str(ctx.author)}**"
                await ctx.edit_original_message(embed=embed)
                try:
                    results = await self.bot.server_db.find_one({"server": ctx.guild.id})
                    greeting = results.get("greeting")
                    if greeting is None:
                        greeting = ""

                    results = await self.bot.clan_db.find_one({"$and": [
                        {"tag": player.clan.tag},
                        {"server": ctx.guild.id}
                    ]})
                    if results is not None:
                        channel = results.get("clanChannel")
                        channel = self.bot.get_channel(channel)
                        await channel.send(f"{ctx.author.mention}, welcome to {ctx.guild.name}! {greeting}")
                except:
                    pass

            elif not verified and is_linked:
                if linked == ctx.author.id:
                    evalua = self.bot.get_cog("Eval")
                    embed = await evalua.eval_logic(ctx=ctx, members_to_eval=[ctx.author], role_or_user=ctx.author,
                                                    test=False,
                                                    change_nick=change_nickname,
                                                    return_embed=True)
                    await ctx.edit_original_message(embed=embed)
                else:
                    embed = disnake.Embed(
                        title="API Token is Incorrect!",
                        description=f"- Reference below for help finding your api token.\n- Open Clash and navigate to Settings > More Settings - OR use the below link:\nhttps://link.clashofclans.com/?action=OpenMoreSettings" +
                                    "\n- Scroll down to the bottom and copy the api token.\n- View the picture below for reference.",
                        color=disnake.Color.red())
                    embed.set_image(
                        url="https://cdn.discordapp.com/attachments/843624785560993833/961379232955658270/image0_2.png")
                    await ctx.edit_original_message(embed=embed)

            elif not verified and not is_linked:
                embed = disnake.Embed(
                    title="API Token is Incorrect!",
                    description=f"- Reference below for help finding your api token.\n- Open Clash and navigate to Settings > More Settings - OR use the below link:\nhttps://link.clashofclans.com/?action=OpenMoreSettings" +
                                "\n- Scroll down to the bottom and copy the api token.\n- View the picture below for reference.",
                    color=disnake.Color.red())
                embed.set_image(
                    url="https://cdn.discordapp.com/attachments/843624785560993833/961379232955658270/image0_2.png")
                await ctx.edit_original_message(embed=embed)
        except Exception as e:
            await ctx.edit_original_message(content=(str(e))[:1000])

    @commands.slash_command(name="verify", description="Link clash of clans accounts to your discord profile")
    async def verify(self, ctx: disnake.ApplicationCommandInteraction, player_tag):
        """
            Parameters
            ----------
            player_tag: player_tag as found in-game
        """
        await ctx.response.defer()
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        change_nickname = await server.nickname_choice
        try:
            player = await self.bot.getPlayer(player_tag)
            if player is None:
                embed = disnake.Embed(
                    description=f"{player_tag} is not a valid player tag. Use the photo below to help find your player tag.",
                    color=disnake.Color.red())
                embed.set_image(
                    url="https://cdn.discordapp.com/attachments/886889518890885141/933932859545247794/bRsLbL1.png")
                return await ctx.edit_original_message(embed=embed)

            linked = await self.bot.link_client.get_link(player.tag)
            is_linked = (linked is not None)

            if is_linked:
                if linked == ctx.author.id:
                    evalua = self.bot.get_cog("Eval")
                    embed = await evalua.eval_logic(ctx=ctx, members_to_eval=[ctx.author], role_or_user=ctx.author,
                                                    test=False,
                                                    change_nick=change_nickname,
                                                    return_embed=True)
                    await ctx.edit_original_message(embed=embed)
                else:
                    embed = disnake.Embed(
                        description=f"[{player.name}]({player.share_link}) is already linked to another discord user. Use `/unlink` to remove the link first.",
                        color=disnake.Color.red())
                    await ctx.edit_original_message(embed=embed)

            elif not is_linked:
                await self.bot.link_client.add_link(player.tag, ctx.author.id)
                evalua = self.bot.get_cog("Eval")
                embed = await evalua.eval_logic(ctx=ctx, members_to_eval=[ctx.author], role_or_user=ctx.author,
                                                test=False,
                                                change_nick=change_nickname,
                                                return_embed=True)
                embed.title = f"**{player.name} successfully linked to {str(ctx.author)}**"
                await ctx.edit_original_message(embed=embed)
                try:
                    results = await self.bot.server_db.find_one({"server": ctx.guild.id})
                    greeting = results.get("greeting")
                    if greeting is None:
                        greeting = ""

                    results = await self.bot.clan_db.find_one({"$and": [
                        {"tag": player.clan.tag},
                        {"server": ctx.guild.id}
                    ]})
                    if results is not None:
                        channel = results.get("clanChannel")
                        channel = self.bot.get_channel(channel)
                        await channel.send(f"{ctx.author.mention}, welcome to {ctx.guild.name}! {greeting}")
                except:
                    pass
        except Exception as e:
            await ctx.send(e[0:1000])

    @commands.slash_command(name="linkhelp", description="Help & Reference guide for /link command")
    async def linkhelp(self, ctx: disnake.ApplicationCommandInteraction):
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
        await ctx.send(embeds=[embed, embed2])

    @commands.slash_command(name="modlink", description="Links clash account to a discord member, on their behalf.")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def modlink(self, ctx: disnake.ApplicationCommandInteraction, member : disnake.Member, player_tag, greet=commands.Param(default="Yes", choices=["Yes", "No"])):
        """
            Parameters
            ----------
            player_tag: player_tag as found in-game
            member: discord member to link this player to
            greet: (default = yes) do(n't) send the clan greeting for a newly linked account
        """

        await ctx.response.defer()
        server = CustomServer(guild=ctx.guild, bot=self.bot)
        change_nickname = await server.nickname_choice
        player = await self.bot.getPlayer(player_tag)
        if player is None:
            embed = disnake.Embed(description="Invalid Player Tag", color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        linked = await self.bot.link_client.get_link(player.tag)

        if linked is not None:
            if linked == member.id:
                embed = disnake.Embed(
                    description=f"{player.name} is already linked to {member.mention}",
                    color=disnake.Color.red())
                if greet != "No":
                    try:
                        results = await self.bot.server_db.find_one({"server": ctx.guild.id})
                        greeting = results.get("greeting")
                        if greeting is None:
                            greeting = ""

                        results = await self.bot.clan_db.find_one({"$and": [
                            {"tag": player.clan.tag},
                            {"server": ctx.guild.id}
                        ]})
                        if results is not None:
                            channel = results.get("clanChannel")
                            channel = await self.bot.getch_channel(channel)
                            await channel.send(f"{member.mention}, welcome to {ctx.guild.name}! {greeting}")
                    except:
                        pass
                return await ctx.edit_original_message(embed=embed)
            else:
                embed = disnake.Embed(
                    title=f"{player.name} is already linked to another discord user.",
                    color=disnake.Color.red())
                return await ctx.edit_original_message(embed=embed)


        await self.bot.link_client.add_link(player.tag, member.id)

        evalua = self.bot.get_cog("Eval")
        embed = await evalua.eval_logic(ctx=ctx, members_to_eval=[member], role_or_user=member,
                                        test=False,
                                        change_nick=change_nickname,
                                        return_embed=True)
        embed.title = f"**{player.name} successfully linked to {str(member)}**"
        await ctx.edit_original_message(embed=embed)

        if greet != "No":
            try:
                results = await self.bot.server_db.find_one({"server": ctx.guild.id})
                greeting = results.get("greeting")
                if greeting is None:
                    greeting = ""

                results = await self.bot.clan_db.find_one({"$and": [
                    {"tag": player.clan.tag},
                    {"server": ctx.guild.id}
                ]})
                if results is not None:
                    channel = results.get("clanChannel")
                    channel = self.bot.get_channel(channel)
                    await channel.send(f"{member.mention}, welcome to {ctx.guild.name}! {greeting}")
            except:
                pass

    @commands.slash_command(name="unlink", description="Unlinks a clash account from discord")
    @commands.check_any(check_commands())
    async def unlink(self, ctx: disnake.ApplicationCommandInteraction, player_tag):
        """
            Parameters
            ----------
            player_tag: player_tag as found in-game
        """
        await ctx.response.defer()
        player = await self.bot.getPlayer(player_tag)
        if player is None:
            embed = disnake.Embed(description="Invalid Player Tag", color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        linked = await self.bot.link_client.get_link(player.tag)
        if linked is None:
            embed = disnake.Embed(
                title=player.name + " is not linked to a discord user.",
                color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})

        perms = ctx.author.guild_permissions.manage_guild
        whitelist_perm = await self.bot.white_list_check(ctx=ctx, command_name="unlink")
        if ctx.author.id == self.bot.owner.id:
            perms = True

        is_family = False
        if player.clan is not None and player.clan.tag in clan_tags:
            is_family = True

        perms_only_because_whitelist = False
        if whitelist_perm:
            if is_family:
                perms = True
                perms_only_because_whitelist = True

        if linked != ctx.author.id and not perms:
            embed = disnake.Embed(
                description="Must have `Manage Server` permissions or be whitelisted (`/whitelist add`) to unlink accounts that aren't yours.",
                color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        if perms:
            member = await self.bot.pingToMember(ctx, linked)
            #if they are on a different server, and not in family
            if ctx.guild.member_count <= 249 and member is None and not is_family:
                embed = disnake.Embed(
                    description=f"[{player.name}]({player.share_link}), cannot unlink players on other servers & not in your clans.\n(Reach out on the support server if you have questions about this)",
                    color=disnake.Color.red())
                return await ctx.edit_original_message(embed=embed)
            elif member is None and perms_only_because_whitelist and not is_family:
                embed = disnake.Embed(
                    description=f"[{player.name}]({player.share_link}), Must have `Manage Server` permissions to unlink accounts not on your server or in your clans.",
                    color=disnake.Color.red())
                return await ctx.edit_original_message(embed=embed)

        await self.bot.link_client.delete_link(player.tag)
        embed = disnake.Embed(description=f"[{player.name}]({player.share_link}) has been unlinked from discord.",
                              color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

    @commands.slash_command(name="buttons", description="Create a message that has buttons for easy eval/link/refresh actions.")
    async def buttons(self, ctx: disnake.ApplicationCommandInteraction, type=commands.Param(choices=["Link Button", "Refresh Button", "To-Do Button"]), ping: disnake.User = None):
        await ctx.response.defer()
        if type == "Link Button":
            embed = disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                                  description=f"To link your account, press the link button below to get started.",
                                  color=disnake.Color.green())
            stat_buttons = [disnake.ui.Button(label="Link Account", emoji="🔗", style=disnake.ButtonStyle.green,
                                              custom_id="Start Link"),
                            disnake.ui.Button(label="Help", emoji="❓", style=disnake.ButtonStyle.grey,
                                              custom_id="Link Help")]
            buttons = disnake.ui.ActionRow()
            for button in stat_buttons:
                buttons.append_item(button)
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            if ping is not None:
                content = ping.mention
            else:
                content = ""
            await ctx.send(content=content, embed=embed, components=[buttons])
        elif type == "Refresh Button":
            embed = disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                                  description=f"To refresh your roles, press the refresh button below.",
                                  color=disnake.Color.green())
            stat_buttons = [disnake.ui.Button(label="Refresh Roles", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.green, custom_id="Refresh Roles")]
            buttons = disnake.ui.ActionRow()
            for button in stat_buttons:
                buttons.append_item(button)
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            if ping is not None:
                content = ping.mention
            else:
                content = ""
            await ctx.send(content=content, embed=embed, components=[buttons])
        elif type == "To-Do Button":
            embed = disnake.Embed(description=f"To view your account to-do list click the button below!\n"
                                              f"> Clan Games\n"
                                              f"> War Hits\n"
                                              f"> Raid Hits\n"
                                              f"> Inactivity\n"
                                              f"> Legend Hits",
                                  color=disnake.Color.green())
            stat_buttons = [disnake.ui.Button(label="To-Do List", emoji=self.bot.emoji.yes.partial_emoji,
                                              style=disnake.ButtonStyle.green, custom_id="MyToDoList")]
            buttons = disnake.ui.ActionRow()
            for button in stat_buttons:
                buttons.append_item(button)
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            if ping is not None:
                content = ping.mention
            else:
                content = ""
            await ctx.send(content=content, embed=embed, components=[buttons])

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):

        if ctx.data.custom_id == "Refresh Roles":
            await ctx.response.defer()
            evalua = self.bot.get_cog("Eval")
            embed = await evalua.eval_logic(ctx=ctx, members_to_eval=[ctx.author], role_or_user=ctx.author,
                                            test=False,
                                            change_nick="Off",
                                            return_embed=True)
            if embed.description == "":
                embed.description = "Your roles are up to date!"
            await ctx.send(embed=embed, ephemeral=True)
        elif ctx.data.custom_id == "MyToDoList":
            cog = self.bot.get_cog(name="Profile")
            await ctx.response.defer(ephemeral=True)
            discord_user = ctx.author
            linked_accounts = await search_results(self.bot, str(discord_user.id))
            embed = await cog.to_do_embed(discord_user=discord_user, linked_accounts=linked_accounts)
            await ctx.send(embed=embed, ephemeral=True)

    @modlink.autocomplete("player_tag")
    @unlink.autocomplete("player_tag")
    @verify.autocomplete("player_tag")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names



def setup(bot: CustomClient):
    bot.add_cog(Linking(bot))