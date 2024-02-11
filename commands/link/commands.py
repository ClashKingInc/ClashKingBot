import coc
from disnake.ext import commands
import disnake

from classes.bot import CustomClient
from utility.discord_utils import check_commands
from utility.search import search_results
from ..eval.utils import logic
from archived.commands.CommandsOlder.Utils.Player import to_do_embed
from utility.discord_utils import basic_embed_modal
from exceptions.CustomExceptions import MessageException, InvalidAPIToken, APITokenRequired
from discord import convert, autocomplete


class Linking(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="link", description="Link clash of clans accounts to your discord profile")
    async def link(self, ctx: disnake.ApplicationCommandInteraction,
                   player: coc.Player = commands.Param(autocomplete=autocomplete.all_players, converter=convert.player),
                   user: disnake.Member = None,
                   api_token: str = None,
                   greet=commands.Param(default="Yes", choices=["Yes", "No"])):
        """
            Parameters
            ----------
            player: player_tag as found in-game
            api_token: player api-token
        """
        await ctx.response.defer()
        server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
        #if the server requires an api token & there is None AND this isnt a modlink operation, throw an error
        if not (ctx.user.guild_permissions.manage_guild or self.bot.white_list_check(ctx=ctx, command_name="setup user-settings")) and server.use_api_token and api_token is None:
            raise APITokenRequired

        user = user or ctx.user

        linked = await self.bot.link_client.get_link(player.tag)
        is_linked = (linked is not None)  # is linked to someone already

        # if it is already linked to them, let them know
        if is_linked == user.id:
            raise MessageException(f"[{player.name}]({player.share_link}) is linked to {user.mention} already!")

        #if its a relink by a regular user or the server requires api token
        if not (ctx.user.guild_permissions.manage_guild or self.bot.white_list_check(ctx=ctx, command_name="setup user-settings")) and (server.use_api_token or is_linked):
            verified = await self.bot.coc_client.verify_player_token(player.tag, str(api_token))
            #if not verified but is linked to someone, explain
            if not verified and is_linked:
                embed = disnake.Embed(
                    title="This account is linked to someone else, you will need an api token to link it to yourself",
                    description=f"- Reference below for help finding your api token.\n- Open Clash and navigate to Settings > More Settings - OR use the below link:\nhttps://link.clashofclans.com/?action=OpenMoreSettings" +
                                "\n- Scroll down to the bottom and copy the api token.\n- View the picture below for reference.",
                    color=disnake.Color.red())
                embed.set_image(url="https://cdn.clashking.xyz/clash-assets/bot/find_player_tag.png")
                return await ctx.edit_original_message(embed=embed)
            elif not verified: #if just a case of wrong api token when required
                raise InvalidAPIToken

        #steps done
        # - made sure they have an api token if asked for one (unless its a modlink)
        # - made sure relinks dont happen
        # - made sure we dont override an alr linked account (again unless its a modlink)
        # - if it is an override, need api token (again unless its a modlink)
        # - by this point we have a correct api token or they dont care about one and the account isnt linked to anyone
        server_member = await ctx.guild.getch_member(user.id)
        linked_embed = disnake.Embed(title="Link Complete", description=f"[{player.name}]({player.share_link}) linked to {user.mention} and roles updated.", color=server.embed_color)
        await self.bot.link_client.add_link(player_tag=player.tag, discord_id=user.id)
        try:
            await logic(bot=self.bot, guild=ctx.guild, db_server=server, members=[server_member], role_or_user=user)
        except Exception:
            linked_embed.description = f"[{player.name}]({player.share_link}) linked to {user.mention} but could not update roles."
        await ctx.edit_original_message(embed=linked_embed)
        try:
            results = await self.bot.clan_db.find_one({"$and": [
                {"tag": player.clan.tag},
                {"server": ctx.guild.id}
            ]})
            if results is not None and greet != "No":
                greeting = results.get("greeting")
                if greeting is None:
                    badge = await self.bot.create_new_badge_emoji(url=player.clan.badge.url)
                    greeting = f", welcome to {badge}{player.clan.name}!"
                channel = results.get("clanChannel")
                channel = self.bot.get_channel(channel)
                await channel.send(f"{user.mention}{greeting}")
        except Exception:
            pass


    @commands.slash_command(name="unlink", description="Unlinks a clash account from discord")
    @commands.check_any(check_commands())
    async def unlink(self, ctx: disnake.ApplicationCommandInteraction,
                     player: coc.Player = commands.Param(autocomplete=autocomplete.user_accounts, converter=convert.player)):
        """
            Parameters
            ----------
            player: player_tag as found in-game
        """
        await ctx.response.defer()

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
            member = await ctx.guild.getch_member(linked)
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
    async def buttons(self, ctx: disnake.ApplicationCommandInteraction, type=commands.Param(choices=["Link Button", "Refresh Button", "To-Do Button", "Roster Button"]), ping: disnake.User = None,
                      custom_embed = commands.Param(default="False", choices=["True", "False"]), embed_link: str = None):

        link_embed = disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                              description=f"To link your account, press the link button below to get started.",
                              color=disnake.Color.green())
        refresh_embed = disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                              description=f"To refresh your roles, press the refresh button below.",
                              color=disnake.Color.green())
        to_do_embed = disnake.Embed(description=f"To view your account to-do list click the button below!\n"
                                              f"> Clan Games\n"
                                              f"> War Hits\n"
                                              f"> Raid Hits\n"
                                              f"> Inactivity\n"
                                              f"> Legend Hits",
                                  color=disnake.Color.green())

        roster_embed = disnake.Embed(description=f"To view all the rosters you are on & the what group (Main, Benched, etc) & clans your accounts are in, press the button below.",
                                  color=disnake.Color.green())

        if ctx.guild.icon is not None:
            refresh_embed.set_thumbnail(url=ctx.guild.icon.url)
            link_embed.set_thumbnail(url=ctx.guild.icon.url)
            to_do_embed.set_thumbnail(url=ctx.guild.icon.url)
            roster_embed.set_thumbnail(url=ctx.guild.icon.url)
        default_embeds = {"Link Button" : link_embed, "Refresh Button" : refresh_embed, "To-Do Button" : to_do_embed, "Roster Button" : roster_embed}

        if custom_embed != "False":
            if embed_link is None:
                modal_inter, embed = await basic_embed_modal(bot=self.bot,ctx=ctx)
                if embed is None:
                    raise MessageException("An Error Occured, Please Try Again.")
                ctx = modal_inter
            else:
                await ctx.response.defer()
                try:
                    if "discord.com" not in embed_link:
                        return await ctx.send(content="Not a valid message link", ephemeral=True)
                    link_split = embed_link.split("/")
                    message_id = link_split[-1]
                    channel_id = link_split[-2]

                    channel = await self.bot.getch_channel(channel_id=int(channel_id))
                    if channel is None:
                        return await ctx.send(content="Cannot access the channel this embed is in", ephemeral=True)
                    message = await channel.fetch_message(int(message_id))
                    if not message.embeds:
                        return await ctx.send(content="Message has no embeds", ephemeral=True)
                    embed = message.embeds[0]
                except:
                    return await ctx.send(content=f"Something went wrong :/ An error occured with the message link.", ephemeral=True)
        else:
            await ctx.response.defer()
            embed = default_embeds[type]

        if type == "Link Button":

            stat_buttons = [disnake.ui.Button(label="Link Account", emoji="🔗", style=disnake.ButtonStyle.green,
                                              custom_id="Start Link"),
                            disnake.ui.Button(label="Help", emoji="❓", style=disnake.ButtonStyle.grey,
                                              custom_id="Link Help")]
            buttons = disnake.ui.ActionRow()
            for button in stat_buttons:
                buttons.append_item(button)

            if ping is not None:
                content = ping.mention
            else:
                content = ""
            await ctx.send(content=content, embed=embed, components=[buttons])
        elif type == "Refresh Button":

            stat_buttons = [disnake.ui.Button(label="Refresh Roles", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.green, custom_id="Refresh Roles")]
            buttons = disnake.ui.ActionRow()
            for button in stat_buttons:
                buttons.append_item(button)
            if ping is not None:
                content = ping.mention
            else:
                content = ""
            await ctx.send(content=content, embed=embed, components=[buttons])
        elif type == "To-Do Button":
            stat_buttons = [disnake.ui.Button(label="To-Do List", emoji=self.bot.emoji.yes.partial_emoji,
                                              style=disnake.ButtonStyle.green, custom_id="MyToDoList")]
            buttons = disnake.ui.ActionRow()
            for button in stat_buttons:
                buttons.append_item(button)
            if ping is not None:
                content = ping.mention
            else:
                content = ""
            await ctx.send(content=content, embed=embed, components=[buttons])
        elif type == "Roster Button":
            stat_buttons = [disnake.ui.Button(label="My Rosters", emoji=self.bot.emoji.calendar.partial_emoji,
                                              style=disnake.ButtonStyle.green, custom_id="MyRosters")]
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
        #await ctx.response.defer(ephemeral=True)

        if ctx.data.custom_id == "Refresh Roles":
            server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
            server_member = await ctx.guild.getch_member(ctx.user.id)
            await logic(bot=self.bot, guild=ctx.guild, db_server=server, members=[server_member], role_or_user=ctx.user)
            await ctx.send(content="Your roles are now up to date!", ephemeral=True)

        elif ctx.data.custom_id == "MyToDoList":
            discord_user = ctx.author
            linked_accounts = await search_results(self.bot, str(discord_user.id))
            embed = await to_do_embed(bot=self.bot, discord_user=discord_user, linked_accounts=linked_accounts)
            await ctx.send(embed=embed, ephemeral=True)

        elif ctx.data.custom_id == "MyRosters":
            tags = await self.bot.get_tags(ping=ctx.user.id)
            roster_type_text = ctx.user.display_name
            players = await self.bot.get_players(tags=tags, custom=False)
            text = ""
            for player in players:
                rosters_found = await self.bot.rosters.find({"members.tag": player.tag}).to_list(length=100)
                if not rosters_found:
                    continue
                text += f"{self.bot.fetch_emoji(name=player.town_hall)}**{player.name}**\n"
                for roster in rosters_found:
                    our_member = next(member for member in roster["members"] if member["tag"] == player.tag)
                    group = our_member["group"]
                    if group == "No Group":
                        group = "Main"
                    text += f"{roster['alias']} | {roster['clan_name']} | {group}\n"
                text += "\n"

            if text == "":
                text = "Not Found on Any Rosters"
            embed = disnake.Embed(title=f"Rosters for {roster_type_text}", description=text,
                                  color=disnake.Color.green())
            await ctx.send(embed=embed, ephemeral=True)



def setup(bot: CustomClient):
    bot.add_cog(Linking(bot))