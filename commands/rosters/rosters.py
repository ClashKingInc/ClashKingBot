import asyncio
import datetime
import disnake
import coc
import pytz

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from Assets.emojiDictionary import emojiDictionary
from CustomClasses.Roster import Roster
from main import check_commands
from exceptions.CustomExceptions import *
from typing import List
from collections import defaultdict
from Utils.discord_utils import interaction_handler
last_run = {}
refresh_last_run = {}

class Roster_Commands(commands.Cog, name="Rosters"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    async def player_convertor(self, player_tags: str):
        player_tags = player_tags.split(",")[:50]
        players = []
        for player_tag in player_tags:
            player = await self.bot.getPlayer(player_tag=player_tag)
            if player is not None:
                players.append(player)
        if not players:
            raise coc.errors.NotFound
        return players

    @commands.slash_command(name="roster")
    async def roster(self, ctx: disnake.ApplicationCommandInteraction):
        pass


    @roster.sub_command(name="create", description="Create a roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_create(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), roster_alias: str = commands.Param(name="roster_alias", max_length=100), add_members_to_roster: str = commands.Param(default="No", choices=["Yes", "No"])):
        await ctx.response.defer()
        roster = Roster(bot=self.bot)
        await roster.create_roster(guild=ctx.guild, clan=clan, alias=roster_alias[:100], add_members=(add_members_to_roster == "Yes"))
        embed = disnake.Embed(description=f"**{roster.roster_result.get('alias')}** Roster created & tied to {roster.roster_result.get('clan_name')}", color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.url)
        await ctx.edit_original_message(embed=embed)


    @roster.sub_command(name="delete", description="Delete a roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_delete(self, ctx: disnake.ApplicationCommandInteraction, roster: str):
        await ctx.response.defer()
        _roster = Roster(self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        await _roster.delete()
        embed = disnake.Embed(
            description=f"Roster - **{_roster.roster_result.get('alias')}** that was tied to {_roster.roster_result.get('clan_name')} has been **deleted**.",
            color=disnake.Color.red())
        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name="clear", description="Clear a roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_clear(self, ctx: disnake.ApplicationCommandInteraction, roster: str):
        await ctx.response.defer()
        _roster = Roster(self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        await _roster.clear_roster()
        embed = disnake.Embed(
            description=f"Roster - **{_roster.roster_result.get('alias')}** that was tied to {_roster.roster_result.get('clan_name')} has been **cleared**.",
            color=disnake.Color.red())
        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name="signup", description="Create a signup for a roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_create_signups(self, ctx: disnake.ApplicationCommandInteraction, roster: str):
        await ctx.response.defer()
        _roster = Roster(self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        embed = await _roster.embed()
        signup_buttons = [
            disnake.ui.Button(label="Add", emoji=self.bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green, custom_id=f"Signup_{roster}"),
            disnake.ui.Button(label="Remove", emoji=self.bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,custom_id=f"RemoveMe_{roster}"),
            disnake.ui.Button(label="Sub", emoji=self.bot.emoji.switch.partial_emoji, style=disnake.ButtonStyle.blurple, custom_id=f"SubMe_{roster}"),
        ]
        ad_buttons = [disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,custom_id=f"Refresh_{roster}"),
                      disnake.ui.Button(label="Clan Link", emoji="🔗", style=disnake.ButtonStyle.url,
                              url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{_roster.roster_result.get('clan_tag').strip('#')}"),
                      disnake.ui.Button(label="", emoji=self.bot.emoji.menu.partial_emoji, style=disnake.ButtonStyle.grey,custom_id=f"Menu_{roster}")]
        buttons = disnake.ui.ActionRow()
        for button in signup_buttons:
            buttons.append_item(button)
        buttons2 = disnake.ui.ActionRow()
        for button in ad_buttons:
            buttons2.append_item(button)
        await ctx.edit_original_message(embed=embed, components=[buttons, buttons2])


    @roster.sub_command(name="add-player", description="Add a player to a roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_add(self, ctx: disnake.ApplicationCommandInteraction, roster: str, players: List[coc.Player] = commands.Param(converter=player_convertor), sub = commands.Param(name="sub", default=False, choices=["Yes"])):
        await ctx.response.defer(ephemeral=True)
        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        added_text = ""
        messed_text = ""
        for player in players:
            try:
                await _roster.add_member(player=player, sub=(sub=="Yes"))
                added_text += f"{emojiDictionary(player.town_hall)}{player.name}\n"
            except Exception as e:
                messed_text += f"{emojiDictionary(player.town_hall)}{player.name} - {e}\n"
        if added_text == "":
            added_text = f"No Players"
        embed = disnake.Embed(title=f"Added to **{_roster.roster_result.get('alias')}** roster", description=added_text,color=disnake.Color.green())
        if messed_text != "":
            embed.add_field(name="Not Added (Errors)", value=messed_text)
        embed.set_thumbnail(url=_roster.roster_result.get("clan_badge"))
        await ctx.send(embed=embed, ephemeral=True)


    @roster.sub_command(name="remove-player", description="Remove a player from a roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_remove(self, ctx: disnake.ApplicationCommandInteraction, roster: str):
        await ctx.response.defer()
        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        embed = await _roster.embed(move_text="Mode: remove")
        components = await _roster.mode_components(mode="remove", player_page=0)
        await ctx.edit_original_message(embed=embed, components=components)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        _new_roster = Roster(bot=self.bot)
        await _new_roster.find_roster(guild=ctx.guild, alias=roster)
        new_roster = roster
        mode = "remove"
        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author.id != ctx.author.id:
                await res.send(content="Must run the command to interact with components.", ephemeral=True)
                continue
            await res.response.defer()
            try:
                if "button" in str(res.data.component_type):
                    button_value = res.data.custom_id
                    button_value = button_value.split("_")[1]
                    mode = button_value
                    if button_value == "move":
                        embed = await _roster.embed(
                            move_text=f"Mode: {button_value} | Moving to {new_roster}\nGroup Mode: {group}")
                    else:
                        embed = await _roster.embed(move_text=f"Mode: {button_value}")
                    components = await _roster.mode_components(mode=button_value, player_page=0)
                    await res.edit_original_message(embed=embed, components=components)
                else:
                    if "players_1" in res.values or "players_2" in res.values or "players_0" in res.values:
                        for value in res.values:
                            if "players" in value:
                                page = value.split("_")[1]
                                components = await _roster.mode_components(mode=mode, player_page=int(page))
                                await res.edit_original_message(embed=embed, components=components)
                                break
                    elif any("edit_" in value for value in res.values):
                        players = await self.bot.get_players(tags=[value.split("_")[1] for value in res.values])
                        for player in players:
                            if isinstance(player, coc.errors.NotFound):
                                continue
                            if mode == "move":
                                await _roster.move_member(player=player, new_roster=_new_roster, group=group)
                            else:
                                await _roster.remove_member(player=player)
                        # embed = disnake.Embed(
                        # description=f"{', '.join([player.name for player in players if not isinstance(player, coc.errors.NotFound)])} moved from **{_roster.roster_result.get('alias')}** to **{_new_roster.roster_result.get('alias')}** roster",
                        # color=disnake.Color.green())
                        # embed.set_thumbnail(url=_new_roster.roster_result.get("clan_badge"))
                        # await res.followup.send(embed=embed, ephemeral=True)
                        await _new_roster.find_roster(guild=ctx.guild, alias=_new_roster.roster_result.get("alias"))
                        await _roster.find_roster(guild=ctx.guild, alias=_roster.roster_result.get("alias"))
                        if mode == "move":
                            embed = await _roster.embed(
                                move_text=f"Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}")
                        else:
                            embed = await _roster.embed(move_text=f"Mode: {mode}")
                        components = await _roster.mode_components(mode=mode, player_page=0)
                        await res.edit_original_message(embed=embed, components=components)
                    elif "roster_" in res.values[0]:
                        alias = res.values[0].split("_")[1]
                        await _roster.find_roster(guild=ctx.guild, alias=alias)
                        if mode == "move":
                            embed = await _roster.embed(
                                move_text=f"Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}")
                        else:
                            embed = await _roster.embed(move_text=f"Mode: {mode}")
                        components = await _roster.mode_components(mode=mode, player_page=0)
                        await res.edit_original_message(embed=embed, components=components)
                    elif "rostermove_" in res.values[0]:
                        alias = res.values[0].split("_")[1]
                        new_roster = alias
                        await _new_roster.find_roster(guild=ctx.guild, alias=new_roster)
                        embed = await _roster.embed(
                            move_text=f"Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}")
                        await res.edit_original_message(embed=embed)
                    elif "rostergroup_" in res.values[0]:
                        group = res.values[0].split("_")[-1]
                        embed = await _roster.embed(
                            move_text=f"Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}")
                        components = await _roster.mode_components(mode=mode, player_page=0)
                        await res.edit_original_message(embed=embed, components=components)

            except Exception as error:
                if isinstance(error, RosterAliasAlreadyExists):
                    embed = disnake.Embed(description=f"Roster with this alias already exists.",
                                          color=disnake.Color.red())
                    await res.send(embed=embed, ephemeral=True)

                if isinstance(error, RosterDoesNotExist):
                    embed = disnake.Embed(description=f"Roster with this alias does not exist. Use `/roster create`",
                                          color=disnake.Color.red())
                    await res.send(embed=embed, ephemeral=True)

                if isinstance(error, PlayerAlreadyInRoster):
                    embed = disnake.Embed(description=f"Player has already been added to this roster.",
                                          color=disnake.Color.red())
                    await res.send(embed=embed, ephemeral=True)

                if isinstance(error, PlayerNotInRoster):
                    embed = disnake.Embed(description=f"Player not found in this roster.",
                                          color=disnake.Color.red())
                    await res.send(embed=embed, ephemeral=True)


    @roster.sub_command(name="move-player", description="Move a player from one roster to another")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_move(self, ctx: disnake.ApplicationCommandInteraction, roster: str, new_roster: str = commands.Param(name="new_roster")):

        await ctx.response.defer()
        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        embed = await _roster.embed(move_text=f"Mode: Move | Moving to {new_roster}\nGroup Mode: No Group")
        components = await _roster.mode_components(mode="move", player_page=0)
        await ctx.edit_original_message(embed=embed, components=components)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        _new_roster = Roster(bot=self.bot)
        await _new_roster.find_roster(guild=ctx.guild, alias=new_roster)
        mode = "move"
        group = "No Group"
        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author.id != ctx.author.id:
                await res.send(content="Must run the command to interact with components.", ephemeral=True)
                continue
            await res.response.defer()
            try:
                if "button" in str(res.data.component_type):
                    button_value = res.data.custom_id
                    button_value = button_value.split("_")[1]
                    mode = button_value
                    if button_value == "move":
                        embed = await _roster.embed(move_text=f"Mode: {button_value} | Moving to {new_roster}\nGroup Mode: {group}")
                    else:
                        embed = await _roster.embed(move_text=f"Mode: {button_value}")
                    components = await _roster.mode_components(mode=button_value, player_page=0)
                    await res.edit_original_message(embed=embed, components=components)
                else:
                    if "players_1" in res.values or "players_2" in res.values or "players_0" in res.values:
                        for value in res.values:
                            if "players" in value:
                                page = value.split("_")[1]
                                components = await _roster.mode_components(mode=mode, player_page=int(page))
                                await res.edit_original_message(embed=embed, components=components)
                                break
                    elif any("edit_" in value for value in res.values):
                        players = await self.bot.get_players(tags = [value.split("_")[1] for value in res.values])
                        for player in players:
                            if isinstance(player, coc.errors.NotFound):
                                continue
                            if mode == "move":
                                await _roster.move_member(player=player, new_roster=_new_roster, group=group)
                            else:
                                await _roster.remove_member(player=player)
                        #embed = disnake.Embed(
                            #description=f"{', '.join([player.name for player in players if not isinstance(player, coc.errors.NotFound)])} moved from **{_roster.roster_result.get('alias')}** to **{_new_roster.roster_result.get('alias')}** roster",
                            #color=disnake.Color.green())
                        #embed.set_thumbnail(url=_new_roster.roster_result.get("clan_badge"))
                        #await res.followup.send(embed=embed, ephemeral=True)
                        await _new_roster.find_roster(guild=ctx.guild, alias=_new_roster.roster_result.get("alias"))
                        await _roster.find_roster(guild=ctx.guild, alias=_roster.roster_result.get("alias"))
                        if mode == "move":
                            embed = await _roster.embed(move_text=f"Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}")
                        else:
                            embed = await _roster.embed(move_text=f"Mode: {mode}")
                        components = await _roster.mode_components(mode=mode, player_page=0)
                        await res.edit_original_message(embed=embed, components=components)
                    elif "roster_" in res.values[0]:
                        alias = res.values[0].split("_")[1]
                        await _roster.find_roster(guild=ctx.guild, alias=alias)
                        if mode == "move":
                            embed = await _roster.embed(move_text=f"Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}")
                        else:
                            embed = await _roster.embed(move_text=f"Mode: {mode}")
                        components = await _roster.mode_components(mode=mode, player_page=0)
                        await res.edit_original_message(embed=embed, components=components)
                    elif "rostermove_" in res.values[0]:
                        alias = res.values[0].split("_")[1]
                        new_roster = alias
                        await _new_roster.find_roster(guild=ctx.guild, alias=new_roster)
                        embed = await _roster.embed(move_text=f"Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}")
                        await res.edit_original_message(embed=embed)
                    elif "rostergroup_" in res.values[0]:
                        group = res.values[0].split("_")[-1]
                        embed = await _roster.embed(
                            move_text=f"Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}")
                        components = await _roster.mode_components(mode=mode, player_page=0)
                        await res.edit_original_message(embed=embed, components=components)


            except Exception as error:
                if isinstance(error, RosterAliasAlreadyExists):
                    embed = disnake.Embed(description=f"Roster with this alias already exists.",
                                          color=disnake.Color.red())
                    await res.send(embed=embed, ephemeral=True)

                if isinstance(error, RosterDoesNotExist):
                    embed = disnake.Embed(description=f"Roster with this alias does not exist. Use `/roster create`",
                                          color=disnake.Color.red())
                    await res.send(embed=embed, ephemeral=True)

                if isinstance(error, PlayerAlreadyInRoster):
                    embed = disnake.Embed(description=f"Player has already been added to this roster.",
                                          color=disnake.Color.red())
                    await res.send(embed=embed, ephemeral=True)

                if isinstance(error, PlayerNotInRoster):
                    embed = disnake.Embed(description=f"Player not found in this roster.",
                                          color=disnake.Color.red())
                    await res.send(embed=embed, ephemeral=True)


    @roster.sub_command(name="groups", description="create/remove a group players can be placed in")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_create_player_group(self, ctx: disnake.ApplicationCommandInteraction, add: str = None, remove: str = None):
        await ctx.response.defer()
        results = await self.bot.server_db.find_one({"server": ctx.guild.id})
        groups = results.get("player_groups", [])

        if add is not None and len(groups) == 25:
            embed = disnake.Embed(description="**Please remove a player group before you add another (limit 25).**", color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        text = ""
        if add is not None:
            if len(add) >= 50:
                text += f"**{add}** cannot be added as a player group, must be under 50 characters\n"
            elif add not in groups:
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {"$push" : {"player_groups" : add}})
                text += f"**{add}** added as a player group.\n"

        if remove is not None:
            if remove in groups:
                await self.bot.server_db.update_one({"server": ctx.guild.id}, {"$pull": {"player_groups": remove}})
                text += f"**{remove}** removed as a player group."
            else:
                text += f"**{remove}** not an existing player group."

        embed = disnake.Embed(title="Roster Group Changes", description=text, color=disnake.Color.green())
        return await ctx.edit_original_message(embed=embed)


    @roster.sub_command(name="post", description="Post a roster")
    async def roster_post(self, ctx: disnake.ApplicationCommandInteraction, roster: str):
        await ctx.response.defer()
        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        embed = await _roster.embed()
        ad_buttons = [
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"Refresh_{roster}"),
            disnake.ui.Button(label="Clan Link", emoji="🔗", style=disnake.ButtonStyle.url,
                              url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{_roster.roster_result.get('clan_tag').strip('#')}"),
            disnake.ui.Button(label="", emoji=self.bot.emoji.menu.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"Menu_{roster}")]
        buttons = disnake.ui.ActionRow()
        for button in ad_buttons:
            buttons.append_item(button)
        await ctx.edit_original_message(embed=embed, components=[buttons])


    @roster.sub_command(name="refresh", description="Refresh the data in a roster (townhall levels, hero levels)")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_refresh(self, ctx: disnake.ApplicationCommandInteraction, roster: str = commands.Param(name="roster_")):
        await ctx.response.defer()
        if roster != "REFRESH ALL":
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=roster)
            await _roster.refresh_roster()
            embed = disnake.Embed(
                description=f"Player data for **{_roster.roster_result.get('alias')}** roster has been refreshed.",
                color=disnake.Color.green())
            embed.set_thumbnail(url=_roster.roster_result.get("clan_badge"))
            await ctx.edit_original_message(embed=embed)
        else:
            global last_run
            l_run = 0
            try:
                l_run = last_run[ctx.guild_id]
            except:
                pass
            if int(datetime.datetime.now().timestamp()) - l_run <= 1800:
                diff = int(datetime.datetime.now().timestamp()) - l_run
                diff = int(datetime.datetime.now().timestamp()) + (1800 - diff)
                return await ctx.edit_original_message(embed=disnake.Embed(description=f"Bulk Refresh can only be run once every 30 minutes, please try again <t:{diff}:R>", color=disnake.Color.red()))
            last_run[ctx.guild.id] = int(datetime.datetime.now().timestamp())
            roster_list = await self.bot.rosters.find({"$and": [{"server_id": ctx.guild.id}]}).to_list(length=100)
            await ctx.edit_original_message(f"Bulk Roster Refresh Has Been Added to Queue")
            for count, roster in enumerate(roster_list, 1):
                await asyncio.sleep(5)
                await ctx.edit_original_message(f"Refreshing {roster.get('alias')} ({count}/{len(roster_list)})")
                _roster = Roster(bot=self.bot, roster_result=roster)
                await _roster.refresh_roster()
            embed = disnake.Embed(
                description=f"Player data for all {len(roster_list)} rosters on this server have been refreshed.",
                color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            await ctx.edit_original_message(content=None, embed=embed)

    @roster.sub_command(name="missing", description="Players that aren't in the clan tied to the roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_missing(self, ctx: disnake.ApplicationCommandInteraction, roster: str, message:str ="", reverse = commands.Param(description="Instead ping those in clan who shouldn't be, i.e. not on roster.", default="False", choices= ["True"])):
        _roster = Roster(bot=self.bot)
        await ctx.response.defer()
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        reverse = (reverse == "True")
        embed = await _roster.missing_embed(reverse=reverse)
        miss_text = "Missing"
        if reverse:
            miss_text = "Out of Place"
        ping_buttons = [
            disnake.ui.Button(label=f"Ping {miss_text}", emoji=self.bot.emoji.pin.partial_emoji, style=disnake.ButtonStyle.green,
                              custom_id=f"ping")
        ]
        buttons = disnake.ui.ActionRow()
        for button in ping_buttons:
            buttons.append_item(button)
        await ctx.edit_original_message(embed=embed, components=[buttons])
        msg = await ctx.original_message()         
        if message != "":
            await _roster.set_missing_text(text=message)
        def check(res: disnake.MessageInteraction):
            return (res.message.id == msg.id) and (res.user == ctx.user)

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()
        missing = await _roster.missing_list(reverse=reverse)
        tags = [member.get("tag") for member in missing]
        names = {}
        for member in missing:
            names[member.get("tag")] = member.get("name")
        links = await self.bot.link_client.get_links(*tags)
        missing_text = ""
        for player_tag, discord_id in links:
            member = disnake.utils.get(ctx.guild.members, id=discord_id)
            name = names[player_tag]
            if member is None:
                missing_text += f"{name} | {player_tag}\n"
            else:
                missing_text += f"{name} | {member.mention}\n"
        await msg.edit(components=[])
        await res.send(content=f"{_roster.missing_text}{missing_text}")

    @roster.sub_command(name="restrict", description="Set restrictions for a roster - th level & max roster size")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_restrict(self, ctx: disnake.ApplicationCommandInteraction, roster: str, th_min: int = None, th_max: int = None, max_roster_size: int = None):
        """
            Parameters
            ----------
            roster: roster to edit
            th_min: set a th minimum that can sign up
            th_max: set a th maximum that can sign up
            max_roster_size: set a max roster size (largest is 60 including subs)
        """
        if th_min is None and th_max is None and max_roster_size is None:
            embed = disnake.Embed(
                description=f"**Please enter at least one field**.",
                color=disnake.Color.red())
            return await ctx.send(embed=embed)
        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        old_th_min = _roster.th_min
        old_th_max = _roster.th_max
        if th_min is not None or th_max is not None:
            if th_min is None:
                th_min = old_th_min
            if th_max is None:
                th_max = old_th_max
            await _roster.restrict_th(min=th_min, max=th_max)

        if max_roster_size is not None:
            if max_roster_size > 60:
                max_roster_size = 60
            if max_roster_size == 0:
                max_roster_size = 1
            await _roster.restrict_size(roster_size=max_roster_size)

        embed = disnake.Embed(
            description=f"**{_roster.roster_result.get('alias')}** restrictions have been updated.",
            color=disnake.Color.green())
        embed.set_thumbnail(url=_roster.roster_result.get("clan_badge"))
        await ctx.send(embed=embed)

    @roster.sub_command(name="layout", description="Edit roster name, description")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_edit_layout(self, ctx: disnake.ApplicationCommandInteraction, roster: str, clear = commands.Param(default=None, choices=["Description", "Image"])):
        if clear is not None:
            await ctx.response.defer()
            if clear == "Image":
                _roster = Roster(bot=self.bot)
                await _roster.find_roster(guild=ctx.guild, alias=roster)
                await _roster.set_image(
                    url="https://cdn.discordapp.com/attachments/1028905437300531271/1028905577662922772/unknown.png")
                embed = disnake.Embed(description=f"{roster} Roster image removed",
                                      colour=disnake.Color.green())
                return await ctx.edit_original_message(embed=embed)
            elif clear == "Description":
                _roster = Roster(bot=self.bot)
                await _roster.find_roster(guild=ctx.guild, alias=roster)
                await _roster.set_description(description=None)
                embed = disnake.Embed(description=f"{roster} Roster description removed",
                                      colour=disnake.Color.green())
                return await ctx.edit_original_message(embed=embed)

        components = [
            disnake.ui.TextInput(
                label=f"New Roster Name",
                placeholder="New Name to Set",
                custom_id=f"name",
                required=False,
                style=disnake.TextInputStyle.single_line,
                max_length=75,
            ),
            disnake.ui.TextInput(
                label=f"New Roster Description",
                placeholder="New Description to Set",
                custom_id=f"description",
                required=False,
                style=disnake.TextInputStyle.single_line,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label=f"New Roster Image",
                placeholder="Link to New Image to Set",
                custom_id=f"image",
                required=False,
                style=disnake.TextInputStyle.single_line,
                max_length=250,
            )
        ]
        await ctx.response.send_modal(
            title="Edit Layout",
            custom_id=f"layout-{int(datetime.datetime.now().timestamp())}",
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
        await modal_inter.response.defer()
        new_name = modal_inter.text_values["name"]
        description = modal_inter.text_values["description"]
        image = modal_inter.text_values["image"]

        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)


        text = ""
        if new_name != "":
            await _roster.rename(new_name=new_name)
            await _roster.find_roster(guild=ctx.guild, alias=new_name)
            text += f"Roster renamed to **{new_name}**\n"

        if description != "":
            await _roster.set_description(description=description)
            text += f"Roster description set to `{description}`\n"

        if image != "":
            pic = await _roster.set_image(url=image)
            text += "Roster image set to the below (if not showing, image was invalid)"

        if text == "":
            text = "No Changes Made."
        embed = disnake.Embed(description=text, color=disnake.Color.green())

        if image != "":
            embed.set_image(url=pic)

        embed.set_thumbnail(url=_roster.roster_result.get("clan_badge"))
        await modal_inter.edit_original_message(embed=embed)

    @roster.sub_command(name="time", description="Set a time for roster/event")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_time(self, ctx: disnake.ApplicationCommandInteraction, roster: str, timezone: str, remove = commands.Param(default=None, choices=["Yes"])):
        if remove == "Yes":
            await ctx.response.defer()
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=roster)
            await _roster.set_time(time=None)
            embed = disnake.Embed(description=f"{roster} Roster time removed",
                                  colour=disnake.Color.green())
            return await ctx.edit_original_message(embed=embed)

        components = [
            disnake.ui.TextInput(
                label=f"Enter the Date (2002-03-12)",
                placeholder="YYYY-MM-DD",
                custom_id=f"date",
                required=True,
                style=disnake.TextInputStyle.single_line,
                max_length=50,
            ),
            disnake.ui.TextInput(
                label=f"Enter the Time (21:30)",
                placeholder="HH:MM",
                custom_id=f"time",
                required=True,
                style=disnake.TextInputStyle.single_line,
                max_length=50,
            ),
        ]
        # await ctx.send(content="Modal Opened", ephemeral=True)
        await ctx.response.send_modal(
            title="Enter Date & Time",
            custom_id=f"date-time-{int(datetime.datetime.now().timestamp())}",
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

        date = modal_inter.text_values["date"]
        time = modal_inter.text_values["time"]

        tz = pytz.timezone(timezone)
        try:
            timestamp = pytz.timezone(timezone).localize(datetime.datetime.strptime(f"{date}T{time}", "%Y-%m-%dT%H:%M"))
            timestamp = int(timestamp.timestamp())
        except:
            return await modal_inter.send(content="**Invalid Date/Time**", ephemeral=True)

        await modal_inter.response.defer()
        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        await _roster.set_time(time=timestamp)
        embed = disnake.Embed(description=f"{roster} Roster time set to <t:{timestamp}:F>", color=disnake.Color.green())
        await modal_inter.edit_original_message(embed=embed)

    @roster.sub_command(name="change-link", description="Change linked clan for roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_change_link(self, ctx: disnake.ApplicationCommandInteraction, roster: str, clan: coc.Clan = commands.Param(converter=clan_converter)):
        _roster = Roster(bot=self.bot)
        await ctx.response.defer()
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        await _roster.change_linked_clan(new_clan=clan)
        embed = disnake.Embed(
            description=f"Roster **{_roster.roster_result.get('alias')}** linked clan has been changed to **{clan.name}**",
            color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.url)
        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name="sort", description="Choose how to sort your roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_sort(self, ctx: disnake.ApplicationCommandInteraction, roster: str):
        _roster = Roster(bot=self.bot)
        await ctx.response.defer()
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        column_choices = ["Name", "Player Tag", "Heroes", "Townhall Level", "Discord", "30 Day Hitrate", "Current Clan", "Clan Tag", "War Opt Status", "Trophies"]
        select_options = []
        for category in column_choices:
            select_options.append(disnake.SelectOption(label=category, value=category))
        select = disnake.ui.Select(
            options=select_options,
            placeholder="Categories",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=4,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        embed = disnake.Embed(
            description="**Select from the column choices below\nNOTE: The order you pick them is the order they will be sorted in..**",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=dropdown)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                      timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()
        await _roster.set_sort(columns=res.values)
        embed = disnake.Embed(
            description=f"{roster} roster sort by : `{', '.join(res.values)}`",
            color=disnake.Color.green())
        await res.edit_original_message(embed=embed, components=[])

    @roster.sub_command(name="columns", description="Choose the columns of your roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_columns(self, ctx: disnake.ApplicationCommandInteraction, roster: str = commands.Param(name="roster_")):
        await ctx.response.defer()
        column_choices = ["Name", "Player Tag", "Heroes", "Townhall Level", "Discord", "30 Day Hitrate", "Current Clan", "Clan Tag", "War Opt Status", "Trophies"]
        roster_list = []
        if roster != "SET ALL":
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=roster)
            roster_list.append(_roster)
        else:
            results = await self.bot.rosters.find({"server_id": ctx.guild.id}).to_list(length=None)
            for count, roster in enumerate(results, 1):
                _roster = Roster(bot=self.bot, roster_result=roster)
                roster_list.append(_roster)
            roster = "All Roster's"
        select_options = []
        for category in column_choices:
            select_options.append(disnake.SelectOption(label=category, value=category))
        select = disnake.ui.Select(
            options=select_options,
            placeholder="Categories",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=4,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]
        embed = disnake.Embed(
            description="**Select from the column choices below\nNOTE: The order you pick them is the order they will appear on your roster from left to right.**",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed, components=dropdown)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()
        if "Name" not in res.values:
            embed = disnake.Embed(
                description=f"Name is a required column field.",
                color=disnake.Color.red())
            return await res.edit_original_message(embed=embed, components=[])
        for r in roster_list:
            await r.set_columns(columns=res.values)
        embed = disnake.Embed(
            description=f"{roster} columns set to : `{', '.join(res.values)}`",
            color=disnake.Color.green())
        await res.edit_original_message(embed=embed, components=[])

    @roster.sub_command(name="list", description="List of rosters on this server")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_list(self, ctx: disnake.ApplicationCommandInteraction):
        result = self.bot.rosters.find({"$and": [{"server_id": ctx.guild.id}]})
        count = await self.bot.rosters.count_documents({"$and": [{"server_id": ctx.guild.id}]})
        if count == 0:
            embed =disnake.Embed(description="**No rosters on this server. Use `/roster create` to get started.**", colour=disnake.Color.red())
            return await ctx.send(embed=embed)
        await ctx.response.defer()
        text = ""
        for roster in await result.to_list(length=count):
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=roster.get("alias"))
            text += f"- {_roster.roster_result.get('alias')} | {_roster.roster_result.get('clan_name')} | {len(_roster.roster_result.get('members'))}/{_roster.roster_size}"
            if _roster.role is not None:
                text += f" | <@&{_roster.role}>\n"
            else:
                text += "\n"

        embed = disnake.Embed(title=f"{ctx.guild.name} Roster List",
            description=text,colour=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name="role", description="Set a role that will be added when a person signs up & vice versa")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_role(self, ctx: disnake.ApplicationCommandInteraction, roster: str, role: disnake.Role, group: str = None, remove_role = commands.Param(default=None, choices=["True"])):
        _roster = Roster(bot=self.bot)
        await ctx.response.defer()
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        if remove_role == "True":
            role = None
        results = await self.bot.server_db.find_one({"server": ctx.guild.id})
        groups = results.get("player_groups", [])
        if group is not None and group not in groups:
            embed = disnake.Embed(description=f"{group} does not exist as a group for {roster}", colour=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        await _roster.set_role(role=role, group=group)

        group_text = f"for {group} group " if group is not None else ""
        if role is not None:
            embed = disnake.Embed(description=f"{roster} role {group_text}set to {role.mention}", colour=disnake.Color.green())
        else:
            embed = disnake.Embed(description=f"{roster} role {group_text}removed", colour=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name="role-refresh", description="Refresh the roles of those signed up to this roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_role_refresh(self, ctx: disnake.ApplicationCommandInteraction, roster: str):
        await ctx.response.defer()
        if roster != "REFRESH ALL":
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=roster)
            try:
                await _roster.refresh_roles()
            except NoRosterRoles:
                embed = disnake.Embed(
                    description="**No roster roles set up for this roster. Use `/roster role` to get started.**",
                    colour=disnake.Color.red())
                return await ctx.edit_original_message(embed=embed)
            roster_alias = _roster.alias
        else:
            global refresh_last_run
            l_run = last_run.get(ctx.guild_id, 0)
            if int(datetime.datetime.now().timestamp()) - l_run <= 1800:
                diff = int(datetime.datetime.now().timestamp()) - l_run
                diff = int(datetime.datetime.now().timestamp()) + (1800 - diff)
                return await ctx.edit_original_message(embed=disnake.Embed(
                    description=f"Bulk Role Refresh can only be run once every 30 minutes, please try again <t:{diff}:R>",
                    color=disnake.Color.red()))
            await ctx.edit_original_message(f"Bulk Roster Role Refresh Has Been Added to Queue")
            results = await self.bot.rosters.find({"server_id": ctx.guild.id}).to_list(length=None)
            for count, roster in enumerate(results, 1):
                _roster = Roster(bot=self.bot, roster_result=roster)
                try:
                    await asyncio.sleep(3)
                    await ctx.edit_original_message(f"Refreshing {_roster.alias} ({count}/{len(results)})")
                    await _roster.refresh_roles()
                except NoRosterRoles:
                    continue
            roster_alias = "All Rosters"

        embed = disnake.Embed(description=f"**Roles updated for {roster_alias}**",
                              colour=disnake.Color.green())
        return await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name="copy", description="import/export/copy rosters")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_copy(self, ctx: disnake.ApplicationCommandInteraction, export_roster: str = None, import_code: str = None):
        await ctx.response.defer()
        if export_roster == import_code == None:
            return await ctx.edit_original_message(content="**Must select an option to import or export.")
        if export_roster is not None:
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=export_roster)
            code = await _roster.export()
            embed = disnake.Embed(description=f"Here is your unique code to export this roster: `{code}`")
        else:
            result = await self.bot.rosters.find_one({"roster_id" : import_code.upper()})
            name_result = await self.bot.rosters.find_one({"alias": f"Import {import_code}"})
            num = ""
            count = 0
            while name_result is not None:
                count += 1
                num = f"{count}"
                name_result = await self.bot.rosters.find_one({"alias": f"Import {import_code}{count}"})
            del result["_id"]
            result["alias"] = f"Import {import_code}{num}"
            result["server_id"] = ctx.guild.id
            await self.bot.rosters.insert_one(result)
            embed = disnake.Embed(description=f"Roster imported as **Import {import_code}{num}** from `{import_code}`")

        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name="search", description="Get a list of rosters a user or player is on")
    async def roster_search(self, ctx: disnake.ApplicationCommandInteraction, user: disnake.Member = None, player: coc.Player = commands.Param(default=None, converter=player_convertor)):
        await ctx.response.defer()
        if user is None and player is None:
            user = ctx.user
        if user is not None:
            tags = await self.bot.get_tags(ping=user.id)
            roster_type_text = user.display_name
        else:
            tags = [player.tag]
            roster_type_text = player.name

        players = await self.bot.get_players(tags=tags, custom=False)
        text = ""
        for player in players:
            if user is not None and user.id == ctx.user.id:
                rosters_found = await self.bot.rosters.find({"members.tag": player.tag}).to_list(length=100)
            else:
                rosters_found = await self.bot.rosters.find(
                    {"$and": [{"server_id": ctx.guild.id}, {"members.tag": player.tag}]}).to_list(length=100)

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
        embed = disnake.Embed(title=f"Rosters for {roster_type_text}", description=text, color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)




    @roster_create.autocomplete("clan")
    @roster_change_link.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[:25]

    @roster_create_player_group.autocomplete("remove")
    @roster_role.autocomplete("group")
    async def autocomp_group(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        results = await self.bot.server_db.find_one({"server": ctx.guild.id})
        groups = results.get("player_groups", [])
        return [f"{group}" for group in groups if query.lower() in group.lower()]

    @roster_delete.autocomplete("roster")
    @roster_create_signups.autocomplete("roster")
    @roster_post.autocomplete("roster")
    @roster_refresh.autocomplete("roster_")
    @roster_missing.autocomplete("roster")
    @roster_add.autocomplete("roster")
    @roster_remove.autocomplete("roster")
    @roster_move.autocomplete("roster")
    @roster_move.autocomplete("new_roster")
    @roster_restrict.autocomplete("roster")
    @roster_edit_layout.autocomplete("roster")
    @roster_change_link.autocomplete("roster")
    @roster_clear.autocomplete("roster")
    @roster_sort.autocomplete("roster")
    @roster_columns.autocomplete("roster_")
    @roster_role.autocomplete("roster")
    @roster_role_refresh.autocomplete("roster")
    @roster_copy.autocomplete("export_roster")
    @roster_time.autocomplete("roster")
    async def autocomp_rosters(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        aliases = await self.bot.rosters.distinct("alias", filter={"server_id": ctx.guild_id })
        alias_list = []
        if ctx.data.focused_option.name == "roster_" or ctx.options.get("role-refresh"):
            if ctx.options.get("columns"):
                alias_list.append("SET ALL")
            else:
                alias_list.append("REFRESH ALL")
        for alias in aliases:
            if query.lower() in alias.lower():
                alias_list.append(f"{alias}")
        return alias_list[:25]

    @roster_add.autocomplete("players")
    @roster_search.autocomplete("player")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names

    @roster_time.autocomplete("timezone")
    async def timezone_autocomplete(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        all_tz = pytz.common_timezones
        return_list = []
        for tz in all_tz:
            if query.lower() in tz.lower():
                return_list.append(tz)
                if len(return_list) == 25:
                    break
        return return_list[:25]


    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "Refresh_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            alias = str(ctx.data.custom_id).split("_")[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)
            embed = await roster.embed()
            await ctx.edit_original_message(embed=embed)

        elif "Menu_" in str(ctx.data.custom_id):
            alias = str(ctx.data.custom_id).split("_")[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)
            message = ctx.message
            perms = ctx.permissions.manage_guild
            if ctx.author.id == self.bot.owner.id:
                perms = True
            if not perms:
                return await ctx.send(content="Must have `Manage Guild` perms to use the menu", ephemeral=True)
            options = [disnake.SelectOption(label="Remove Signup Buttons", value="remove_buttons"),
                       disnake.SelectOption(label="Refresh Components", value="re_comp"),
                       disnake.SelectOption(label="Add Discord User", value="add_discord"),
                       disnake.SelectOption(label="Remove Discord User", value="remove_discord")]
            select = disnake.ui.Select(
                options=options,
                placeholder="Menu Options",
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            dropdown = [disnake.ui.ActionRow(select)]
            await ctx.send(content="Menu Options", components=dropdown, ephemeral=True)

            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", timeout=600)
            except:
                return

            if res.values[0] == "remove_buttons":
                await message.edit(components=[])
                await res.send(content="Components Removed", ephemeral=True)
            elif res.values[0] == "re_comp":
                signup_buttons = [
                    disnake.ui.Button(label="Add", emoji=self.bot.emoji.yes.partial_emoji,
                                      style=disnake.ButtonStyle.green, custom_id=f"Signup_{alias}"),
                    disnake.ui.Button(label="Remove", emoji=self.bot.emoji.no.partial_emoji,
                                      style=disnake.ButtonStyle.red, custom_id=f"RemoveMe_{alias}"),
                    disnake.ui.Button(label="Sub", emoji=self.bot.emoji.switch.partial_emoji,
                                      style=disnake.ButtonStyle.blurple, custom_id=f"SubMe_{alias}"),
                    disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji,
                                      style=disnake.ButtonStyle.grey, custom_id=f"Refresh_{alias}"),
                    disnake.ui.Button(label="", emoji=self.bot.emoji.menu.partial_emoji, style=disnake.ButtonStyle.grey,
                                      custom_id=f"Menu_{alias}")
                ]
                buttons = disnake.ui.ActionRow()
                for button in signup_buttons:
                    buttons.append_item(button)
                await message.edit(components=[buttons])
                await res.send(content="Components Refreshed", ephemeral=True)

            elif res.values[0] == "add_discord":

                carryover_text = ""
                await res.response.defer()
                while True:
                    role_select = disnake.ui.UserSelect(placeholder="Choose User", max_values=1)
                    dropdown = [disnake.ui.ActionRow(role_select)]
                    await res.edit_original_message(content=f"{carryover_text}Choose Member to add Accounts for", components=dropdown)
                    res = await interaction_handler(bot=self.bot, ctx=res)
                    linked_accounts = await self.bot.link_client.get_linked_players(res.values[0])
                    if not linked_accounts:
                        carryover_text = "**No accounts linked to that user**\n"
                        continue
                    accounts = await self.bot.get_players(tags=linked_accounts)
                    options = []
                    player_dict = {}
                    roster_tags = [member.get("tag") for member in roster.players]
                    for account in accounts:
                        account: coc.Player
                        if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                            continue
                        if account.tag in roster_tags:
                            continue
                        player_dict[account.tag] = account
                        options.append(disnake.SelectOption(label=account.name, emoji=self.bot.fetch_emoji(
                            name=account.town_hall).partial_emoji, value=f"{account.tag}"))

                    if not options:
                        carryover_text = "**All of that user's accounts are already on the roster**\n"
                        continue

                    options = options[:25]
                    select = disnake.ui.Select(
                        options=options,
                        placeholder="Select Account(s)",
                        # the placeholder text to show when no options have been chosen
                        min_values=1,  # the minimum number of options a user must select
                        max_values=len(options),  # the maximum number of options a user can select
                    )
                    dropdown = [disnake.ui.ActionRow(select)]
                    await res.edit_original_message(content="Select Account(s) to Add", components=dropdown)

                    res = await interaction_handler(bot=self.bot, ctx=res)

                    await roster.find_roster(guild=ctx.guild, alias=alias)
                    accounts_to_add = res.values
                    added = []
                    for account in accounts_to_add:
                        added.append(player_dict[account].name)
                        await roster.add_member(player_dict[account])
                    carryover_text = f"**Added {', '.join(added)}**\n"
                    await roster.refresh_roster()
                    embed = await roster.embed()
                    await message.edit(embed=embed)

            elif res.values[0] == "remove_discord":

                carryover_text = ""
                await res.response.defer()
                while True:
                    role_select = disnake.ui.UserSelect(placeholder="Choose User", max_values=1)
                    dropdown = [disnake.ui.ActionRow(role_select)]
                    await res.edit_original_message(content=f"{carryover_text}Choose Member to remove Accounts for", components=dropdown)
                    res = await interaction_handler(bot=self.bot, ctx=res)
                    linked_accounts = await self.bot.link_client.get_linked_players(res.values[0])
                    if not linked_accounts:
                        carryover_text = "**No accounts linked to that user**\n"
                        continue
                    accounts = await self.bot.get_players(tags=linked_accounts)
                    options = []
                    player_dict = {}
                    roster_tags = [member.get("tag") for member in roster.players]
                    for account in accounts:
                        account: coc.Player
                        if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                            continue
                        if account.tag not in roster_tags:
                            continue
                        player_dict[account.tag] = account
                        options.append(disnake.SelectOption(label=account.name, emoji=self.bot.fetch_emoji(
                            name=account.town_hall).partial_emoji, value=f"{account.tag}"))

                    if not options:
                        carryover_text = "**None of that user's accounts are on this roster**\n"
                        continue

                    options = options[:25]
                    select = disnake.ui.Select(
                        options=options,
                        placeholder="Select Account(s)",
                        # the placeholder text to show when no options have been chosen
                        min_values=1,  # the minimum number of options a user must select
                        max_values=len(options),  # the maximum number of options a user can select
                    )
                    dropdown = [disnake.ui.ActionRow(select)]
                    await res.edit_original_message(content="Select Account(s) to Remove", components=dropdown)

                    res = await interaction_handler(bot=self.bot, ctx=res)

                    await roster.find_roster(guild=ctx.guild, alias=alias)
                    accounts_to_add = res.values
                    added = []
                    for account in accounts_to_add:
                        added.append(player_dict[account].name)
                        await roster.remove_member(player_dict[account])
                    carryover_text = f"**Removed: {', '.join(added)}**\n"
                    await roster.refresh_roster()
                    embed = await roster.embed()
                    await message.edit(embed=embed)


        elif "Signup_" in str(ctx.data.custom_id):
            alias = str(ctx.data.custom_id).split("_")[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)

            await ctx.response.defer()
            main_message = await ctx.original_message()
            linked_accounts = await self.bot.get_tags(ping=str(ctx.user.id))
            if not linked_accounts:
                return await ctx.send(content="No accounts linked to you. Use `/link` to get started.", ephemeral=True)
            accounts = await self.bot.get_players(tags=linked_accounts)
            options = []
            player_dict = {}
            roster_tags = [member.get("tag") for member in roster.players]
            for account in accounts:
                account: coc.Player
                if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                    continue
                if account.tag in roster_tags:
                    continue
                player_dict[account.tag] = account
                options.append(disnake.SelectOption(label=account.name, emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji, value=f"{account.tag}"))

            if not options:
                return await ctx.send(content="No accounts to add", ephemeral=True)
            options = options[:25]
            select = disnake.ui.Select(
                options=options,
                placeholder="Select Account(s)",
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            dropdown = [disnake.ui.ActionRow(select)]
            msg = await ctx.followup.send(content="Select Account(s) to Add", components=dropdown, ephemeral=True)
            def check(res: disnake.MessageInteraction):
                return res.message.id == msg.id

            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,timeout=600)
            except:
                return await msg.edit(components=[])

            await res.response.defer()
            await roster.find_roster(guild=ctx.guild, alias=alias)
            accounts_to_add = res.values
            added = []
            for account in accounts_to_add:
                added.append(player_dict[account].name)
                await roster.add_member(player_dict[account])

            if roster.role is not None:
                try:
                    role = ctx.guild.get_role(roster.role)
                    await res.user.add_roles(*[role])
                except:
                    pass

            await res.edit_original_message(content=f"Added {', '.join(added)}", components=[])
            embed = await roster.embed()
            await main_message.edit(embed=embed)

        elif "RemoveMe_" in str(ctx.data.custom_id):
            alias = str(ctx.data.custom_id).split("_")[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)

            await ctx.response.defer()
            main_message = await ctx.original_message()
            linked_accounts = await self.bot.get_tags(ping=str(ctx.user.id))
            if not linked_accounts:
                return await ctx.send(content="No accounts linked to you. Use `/link` to get started.", ephemeral=True)
            accounts = await self.bot.get_players(tags=linked_accounts)
            options = []
            player_dict = {}
            roster_tags = [member.get("tag") for member in roster.players]
            for account in accounts:
                account: coc.Player
                if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                    continue
                if account.tag not in roster_tags:
                    continue
                player_dict[account.tag] = account
                options.append(disnake.SelectOption(label=account.name, emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji, value=f"{account.tag}"))

            if not options:
                return await ctx.send(content="No accounts to remove", ephemeral=True)
            options = options[:25]
            select = disnake.ui.Select(
                options=options,
                placeholder="Select Account(s)",
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            dropdown = [disnake.ui.ActionRow(select)]
            msg = await ctx.followup.send(content="Select Account(s) to Remove", components=dropdown, ephemeral=True)

            def check(res: disnake.MessageInteraction):
                return res.message.id == msg.id

            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                return await msg.edit(components=[])

            await res.response.defer()
            accounts_to_add = res.values
            added = []

            for account in accounts_to_add:
                added.append(player_dict[account].name)
                await roster.remove_member(player_dict[account])
            await roster.find_roster(guild=ctx.guild, alias=alias)
            matching = [player for player in roster.players if player["discord"] == str(ctx.user) and player["group"] in ["No Group", "Sub"]]
            if roster.role is not None and not matching:
                try:
                    role = ctx.guild.get_role(roster.role)
                    await res.user.remove_roles(*[role])
                except:
                    pass
            await res.edit_original_message(content=f"Removed {', '.join(added)}", components=[])
            embed = await roster.embed()
            await main_message.edit(embed=embed)

        elif "SubMe_" in str(ctx.data.custom_id):
            alias = str(ctx.data.custom_id).split("_")[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)

            await ctx.response.defer()
            main_message = await ctx.original_message()
            linked_accounts = await self.bot.get_tags(ping=str(ctx.user.id))
            if not linked_accounts:
                return await ctx.send(content="No accounts linked to you. Use `/link` to get started.", ephemeral=True)
            accounts = await self.bot.get_players(tags=linked_accounts)
            options = []
            player_dict = {}
            roster_tags = [member.get("tag") for member in roster.players]
            for account in accounts:
                account: coc.Player
                if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                    continue
                if account.tag in roster_tags:
                    continue
                player_dict[account.tag] = account
                options.append(disnake.SelectOption(label=account.name, emoji=
                    self.bot.fetch_emoji(name=account.town_hall).partial_emoji, value=f"{account.tag}"))

            if not options:
                return await ctx.send(content="No accounts to add", ephemeral=True)
            options = options[:25]
            select = disnake.ui.Select(
                options=options,
                placeholder="Select Account(s)",
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            dropdown = [disnake.ui.ActionRow(select)]
            msg = await ctx.followup.send(content="Select Account(s) to Add", components=dropdown, ephemeral=True)

            def check(res: disnake.MessageInteraction):
                return res.message.id == msg.id

            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                return await msg.edit(components=[])

            await res.response.defer()
            accounts_to_add = res.values
            added = []
            for account in accounts_to_add:
                added.append(player_dict[account].name)
                await roster.add_member(player_dict[account], sub=True)

            await res.edit_original_message(content=f"Added as a sub {', '.join(added)}", components=[])
            embed = await roster.embed()
            await main_message.edit(embed=embed)




def setup(bot: CustomClient):
    bot.add_cog(Roster_Commands(bot))
