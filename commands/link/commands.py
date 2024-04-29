import coc
import disnake
from disnake.ext import commands
import ujson

from classes.bot import CustomClient
from .click import LinkButtonExtended
from discord import convert, autocomplete
from ..eval.utils import logic
from exceptions.CustomExceptions import MessageException, InvalidAPIToken, APITokenRequired
from utility.discord_utils import check_commands, interaction_handler
from utility.general import get_guild_icon


class Linking(LinkButtonExtended, commands.Cog):

    def __init__(self, bot: CustomClient):
        super().__init__(bot)
        self.bot = bot


    @commands.slash_command(name="link", description="Link clash of clans accounts to your discord profile")
    async def link(self, ctx: disnake.ApplicationCommandInteraction,
                   player: coc.Player = commands.Param(autocomplete=autocomplete.family_players, converter=convert.player),
                   user: disnake.Member = None,
                   api_token: str = None,
                   greet: bool = commands.Param(default=True, choices=["Yes", "No"], converter=convert.basic_bool)):
        """
            Parameters
            ----------
            player: player_tag as found in-game
            api_token: player api-token
        """
        await ctx.response.defer()

        #if it is a self-link turn off the greet
        if user is None:
            greet = False

        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
        #if the server requires an api token & there is None AND this isnt a modlink operation, throw an error
        whitelist_check = await self.bot.white_list_check(ctx=ctx, command_name="link")
        manage_guild_perms = ctx.user.guild_permissions.manage_guild
        api_token_requirement = db_server.use_api_token

        if (not whitelist_check or not manage_guild_perms) and api_token_requirement and api_token is None:
            raise APITokenRequired

        user = user or ctx.user

        linked = await self.bot.link_client.get_link(player.tag)
        is_linked = (linked is not None)  # is linked to someone already

        # if it is already linked to them, let them know
        if is_linked == user.id:
            raise MessageException(f"[{player.name}]({player.share_link}) is linked to {user.mention} already!")

        if is_linked:
            api_token_requirement = True
        #if its a relink by a regular user or the server requires api token
        if (not whitelist_check or not manage_guild_perms) and api_token_requirement:
            verified = await self.bot.coc_client.verify_player_token(player.tag, str(api_token))
            #if not verified but is linked to someone, explain
            if not verified and is_linked:
                embed = disnake.Embed(
                    title="This account is linked to someone else, you will need an api token to link it to yourself",
                    description=f"- Reference below for help finding your api token.\n- Open Clash and navigate to Settings > More Settings - OR use the below link:\nhttps://link.clashofclans.com/?action=OpenMoreSettings" +
                                "\n- Scroll down to the bottom and copy the api token.\n- View the picture below for reference.",
                    color=disnake.Color.red())
                embed.set_image(url="https://cdn.clashking.xyz/clash-assets/bot/api_token_help.png")
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
        linked_embeds = [disnake.Embed(title="Link Complete", description=f"[{player.name}]({player.share_link}) linked to {user.mention}", color=db_server.embed_color)]
        if is_linked:
            await self.bot.link_client.delete_link(player_tag=player.tag)
        await self.bot.link_client.add_link(player_tag=player.tag, discord_id=user.id)
        try:
            refresh_embeds = await logic(bot=self.bot, guild=ctx.guild, db_server=db_server, members=[server_member], role_or_user=user)
            for e in refresh_embeds:
                e.set_author(name="", icon_url=None)
                e.title = None
                e.set_footer(text="")
            linked_embeds.extend(refresh_embeds)
        except Exception:
            linked_embeds[0].description = f"[{player.name}]({player.share_link}) linked to {user.mention}"
        await ctx.edit_original_message(embeds=linked_embeds)

        try:
            if greet and player.clan:
                db_clan = db_server.get_clan(clan_tag=player.clan.tag, silent=True)
                if db_clan:
                    channel = await self.bot.getch_channel(db_clan.clan_channel)
                    greet_message = await self.bot.custom_embeds.find_one({"$and": [{"server": db_clan.server_id}, {"name": db_clan.greeting}]})
                    if greet_message is None:
                        greet_message = {"content": "Welcome {user_mention} to **{clan_name}**", "embeds": []}

                    clan = await player.get_detailed_clan()
                    local_greet_message = str(greet_message)
                    types = {
                        "{user_mention}": user.mention if user else "",
                        "{user_display_name}": user.display_name if user else "",
                        "{clan_name}": player.clan.name,
                        "{clan_link}": player.clan.share_link,
                        "{clan_leader_name}": coc.utils.get(clan.members, role=coc.Role.leader),
                        "{player_name}": player.name,
                        "{player_link}": player.share_link,
                        "{player_townhall}": player.town_hall,
                        "{player_townhall_emoji}": self.bot.fetch_emoji(player.town_hall).emoji_string,
                        "{player_league}": player.league.name,
                        "{player_league_emoji}": self.bot.fetch_emoji(player.league.name).emoji_string,
                        "{player_trophies}": player.trophies
                    }

                    for type, replace in types.items():
                        local_greet_message = local_greet_message.replace(type, str(replace))

                    local_greet_message = ujson.loads(local_greet_message)

                    await channel.send(content=local_greet_message.get("content", ""), embeds=[disnake.Embed.from_dict(data=e) for e in local_greet_message.get("embeds", [])])
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
        if ctx.author.id in self.bot.owner_ids:
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
    async def buttons(self, ctx: disnake.ApplicationCommandInteraction,
                      embed: str = commands.Param(autocomplete=autocomplete.embeds, default=None),
                      button_color: str = commands.Param(choices=["Blue", "Green", "Grey", "Red"], default="Grey")):
        await ctx.response.defer(ephemeral=True)
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)

        select_options = []
        for button_type in ["Link Button", "Link Help Button", "Refresh Button", "To-Do Button", "Roster Button"]:
            select_options.append(disnake.SelectOption(label=button_type, value=button_type))
        select = disnake.ui.Select(
            options=select_options,
            placeholder="Button Types",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=4,  # the maximum number of options a user can select
        )
        await ctx.edit_original_response(content="Choose the buttons you would like on this embed", components=[disnake.ui.ActionRow(select)])
        res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)

        selected_types = res.values

        if embed is not None:
            lookup = await self.bot.custom_embeds.find_one({"$and": [{"server": ctx.guild_id}, {"name": embed}]})
            if lookup is None:
                raise MessageException("No embed with that name found on this server")

            embed_data = lookup.get("data")
            embeds = [disnake.Embed.from_dict(data=e) for e in embed_data.get("embeds", [])]
        else:
            default_embeds = {
                "Link Button" :
                    disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                                    description=f"To link your account, press the link button below to get started.",
                                    color=embed_color),
                "Refresh Button" :
                    disnake.Embed(title=f"**Welcome to {ctx.guild.name}!**",
                                    description=f"To refresh your roles, press the refresh button below.",
                                    color=embed_color),
                "To-Do Button" :
                    disnake.Embed(description=f"To view your account to-do list click the button below!\n"
                                              f"> Clan Games\n"
                                              f"> War Hits\n"
                                              f"> Raid Hits\n"
                                              f"> Inactivity\n"
                                              f"> Legend Hits",
                                  color=embed_color),
                "Roster Button" :
                    disnake.Embed(description=f"To view all the rosters you are on & the what group (Main, Benched, etc) "
                                              f"& clans your accounts are in, press the button below.",
                                  color=embed_color),
                "other":
                    disnake.Embed(description=f"Use the buttons below to view info about your accounts.",
                                  color=embed_color)
            }
            if len(selected_types) == 1 or ("Link Button" in selected_types and "Link Help Button" in selected_types and len(selected_types) == 2):
                option = selected_types[0]
                if option == "Link Help Button":
                    option = "Link Button"
                embeds = [default_embeds.get(option)]
            else:
                embeds = [default_embeds.get("other")]
            for embed in embeds:
                embed.set_thumbnail(url=get_guild_icon(ctx.guild))

        color_conversion = {"Blue": disnake.ButtonStyle.primary,
         "Grey": disnake.ButtonStyle.secondary,
         "Green": disnake.ButtonStyle.success,
         "Red": disnake.ButtonStyle.danger}
        button_color = color_conversion.get(button_color)
        buttons = disnake.ui.ActionRow()
        for b_type in selected_types:
            if b_type == "Link Button":
                buttons.append_item(disnake.ui.Button(label="Link Account", emoji="🔗", style=button_color, custom_id="Start Link"))
            elif b_type == "Link Help Button":
                buttons.append_item(disnake.ui.Button(label="Help", emoji="❓", style=button_color, custom_id="Link Help"))
            elif b_type == "Refresh Button":
                buttons.append_item(disnake.ui.Button(label="Refresh Roles", emoji=self.bot.emoji.refresh.partial_emoji, style=button_color, custom_id="Refresh Roles"))
            elif b_type == "To-Do Button":
                buttons.append_item(disnake.ui.Button(label="To-Do List", emoji=self.bot.emoji.yes.partial_emoji, style=button_color, custom_id="MyToDoList"))
            elif b_type == "Roster Button":
                buttons.append_item(disnake.ui.Button(label="My Rosters", emoji=self.bot.emoji.calendar.partial_emoji, style=button_color, custom_id="MyRosters"))

        await ctx.edit_original_message(content="Done", components=[])
        await ctx.channel.send(embeds=embeds, components=[buttons])



def setup(bot: CustomClient):
    bot.add_cog(Linking(bot))