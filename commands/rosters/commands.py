import asyncio
import base64
import datetime
import uuid
from typing import List

import coc
import disnake
from IPython import embed
from babel.util import missing
from disnake.ext import commands

from classes.bot import CustomClient
from classes.roster import Roster
from discord.options import autocomplete, convert
from exceptions.CustomExceptions import *
from utility.discord_utils import check_commands, interaction_handler


last_run = {}
refresh_last_run = {}


class RosterCommands(commands.Cog, name='Rosters'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='roster')
    async def roster(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @roster.sub_command(name='post', description='Post a roster')
    async def roster_post(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        roster: str = commands.Param(autocomplete=autocomplete.roster_alias),
        type: str = commands.Param(choices=['Signup', 'Post', 'Static']),
    ):
        await ctx.response.defer(ephemeral=True)
        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        embed = await _roster.embed()
        all_buttons = []
        if type == 'Signup':
            top_row = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label='Join',
                    style=disnake.ButtonStyle.green,
                    custom_id=f'Signup_{roster}',
                ),
                disnake.ui.Button(
                    label='Remove',
                    style=disnake.ButtonStyle.red,
                    custom_id=f'RemoveMe_{roster}',
                ),
                disnake.ui.Button(
                    label='',
                    emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'Refresh_{roster}',
                ),
                disnake.ui.Button(
                    label='',
                    emoji=self.bot.emoji.gear.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'RosterMenu_{roster}',
                ),
            )
            all_buttons.append(top_row)

            bottom_row = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label='Open Clan',
                    style=disnake.ButtonStyle.url,
                    url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{_roster.roster_result.get('clan_tag').strip('#')}",
                ),
            )
            all_buttons.append(bottom_row)
        elif type == 'Post':
            top_row_buttons = [
                disnake.ui.Button(
                    label='',
                    emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'Refresh_{roster}',
                ),
                disnake.ui.Button(
                    label='',
                    emoji=self.bot.emoji.gear.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'RosterMenu_{roster}',
                ),
                disnake.ui.Button(
                    label='Open Clan',
                    style=disnake.ButtonStyle.url,
                    url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{_roster.roster_result.get('clan_tag').strip('#')}",
                ),
            ]
            top_row = disnake.ui.ActionRow()
            for button in top_row_buttons:
                top_row.append_item(button)
            all_buttons.append(top_row)

        await ctx.channel.send(embed=embed, components=all_buttons)
        await ctx.send(content='Roster Sent', ephemeral=True)

    @roster.sub_command(name='create', description='Create a roster')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_create(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = commands.Param(converter=convert.clan, autocomplete=autocomplete.clan),
        roster_alias: str = commands.Param(autocomplete=autocomplete.roster_alias, max_length=100),
        add_members_to_roster: str = commands.Param(default='No', choices=['Yes', 'No']),
    ):
        await ctx.response.defer()
        roster = Roster(bot=self.bot)
        await roster.create_roster(
            guild=ctx.guild,
            clan=clan,
            alias=roster_alias[:100],
            add_members=(add_members_to_roster == 'Yes'),
        )
        embed = disnake.Embed(
            description=f"**{roster.roster_result.get('alias')}** Roster created & tied to {roster.roster_result.get('clan_name')}, View with `/roster post`",
            color=disnake.Color.green(),
        )
        embed.set_thumbnail(url=clan.badge.url)
        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name='delete', description='Delete members from a roster (or the roster itself)')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_delete(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        roster: str = commands.Param(autocomplete=autocomplete.roster_alias),
        type: str = commands.Param(choices=['Clear Members', 'Delete Roster']),
    ):
        await ctx.response.defer()
        _roster = Roster(self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        if type == 'Delete Roster':
            await _roster.delete()
            embed = disnake.Embed(
                description=f"Roster - **{_roster.roster_result.get('alias')}** that was tied to {_roster.roster_result.get('clan_name')} has been **deleted**.",
                color=disnake.Color.red(),
            )
        elif type == 'Clear Members':
            await _roster.clear_roster()
            embed = disnake.Embed(
                description=f"Roster - **{_roster.roster_result.get('alias')}** that was tied to {_roster.roster_result.get('clan_name')} has been **cleared**.",
                color=disnake.Color.red(),
            )
        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name='add-player', description='Add a player to a roster')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_add(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        roster: str = commands.Param(autocomplete=autocomplete.roster_alias),
        players: List[coc.Player] = commands.Param(converter=convert.multi_player, autocomplete=autocomplete.family_players),
    ):
        await ctx.response.defer(ephemeral=True)
        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        added_text = ''
        messed_text = ''
        for player in players:
            try:
                await _roster.add_member(player=player, sub=False)
                added_text += f'{self.bot.fetch_emoji(player.town_hall)}{player.name}\n'
            except Exception as e:
                messed_text += f'{self.bot.fetch_emoji(player.town_hall)}{player.name} - {e}\n'
        if added_text == '':
            added_text = f'No Players'
        embed = disnake.Embed(
            title=f"Added to **{_roster.roster_result.get('alias')}** roster",
            description=added_text,
            color=disnake.Color.green(),
        )
        if messed_text != '':
            embed.add_field(name='Not Added (Errors)', value=messed_text)
        embed.set_thumbnail(url=_roster.roster_result.get('clan_badge'))
        await ctx.send(embed=embed, ephemeral=True)

    @roster.sub_command(
        name='move-player',
        description='(re)Move a player from one roster to/from another',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_move(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        roster: str = commands.Param(autocomplete=autocomplete.roster_alias),
    ):
        await ctx.response.defer()
        _roster = Roster(bot=self.bot)
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        embed = await _roster.embed(move_text='Mode: move')
        components = await _roster.mode_components(mode='move', player_page=0, roster_page=0, other_roster_page=0)
        await ctx.edit_original_message(embed=embed, components=components)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        _new_roster = Roster(bot=self.bot)
        await _new_roster.find_roster(guild=ctx.guild, alias=roster)
        new_roster = roster
        mode = 'move'
        group = 'No Group'

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', check=check, timeout=600)
            except Exception:
                break

            if res.author.id != ctx.author.id:
                await res.send(
                    content='Must run the command to interact with components.',
                    ephemeral=True,
                )
                continue
            await res.response.defer()

            PLAYER_PAGE = 0
            EDIT_ROSTER_PAGE = 0
            MOVE_ROSTER_PAGE = 0
            try:
                if 'button' in str(res.data.component_type):
                    button_value = res.data.custom_id
                    button_value = button_value.split('_')[1]
                    mode = button_value
                    if button_value == 'move':
                        embed = await _roster.embed(move_text=f'Mode: {button_value} | Moving to {new_roster}\nGroup Mode: {group}')
                    else:
                        embed = await _roster.embed(move_text=f'Mode: {button_value}')
                    components = await _roster.mode_components(
                        mode=button_value,
                        player_page=0,
                        roster_page=0,
                        other_roster_page=0,
                    )
                    await res.edit_original_message(embed=embed, components=components)
                else:
                    if 'players_1' in res.values or 'players_2' in res.values or 'players_0' in res.values:
                        for value in res.values:
                            if 'players' in value:
                                PLAYER_PAGE = int(value.split('_')[1])
                                components = await _roster.mode_components(
                                    mode=mode,
                                    player_page=PLAYER_PAGE,
                                    roster_page=EDIT_ROSTER_PAGE,
                                    other_roster_page=MOVE_ROSTER_PAGE,
                                )
                                await res.edit_original_message(embed=embed, components=components)
                                break
                    elif any('edit_' in value for value in res.values):
                        players = await self.bot.get_players(tags=[value.split('_')[1] for value in res.values])
                        for player in players:
                            if isinstance(player, coc.errors.NotFound):
                                continue
                            if mode == 'move':
                                await _roster.move_member(player=player, new_roster=_new_roster, group=group)
                            else:
                                await _roster.remove_member(player=player)
                        # embed = disnake.Embed(
                        # description=f"{', '.join([player.name for player in players if not isinstance(player, coc.errors.NotFound)])} moved from **{_roster.roster_result.get('alias')}** to **{_new_roster.roster_result.get('alias')}** roster",
                        # color=disnake.Color.green())
                        # embed.set_thumbnail(url=_new_roster.roster_result.get("clan_badge"))
                        # await res.followup.send(embed=embed, ephemeral=True)
                        await _new_roster.find_roster(
                            guild=ctx.guild,
                            alias=_new_roster.roster_result.get('alias'),
                        )
                        await _roster.find_roster(guild=ctx.guild, alias=_roster.roster_result.get('alias'))
                        if mode == 'move':
                            embed = await _roster.embed(move_text=f'Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}')
                        else:
                            embed = await _roster.embed(move_text=f'Mode: {mode}')
                        PLAYER_PAGE = 0
                        components = await _roster.mode_components(
                            mode=mode,
                            player_page=PLAYER_PAGE,
                            roster_page=EDIT_ROSTER_PAGE,
                            other_roster_page=MOVE_ROSTER_PAGE,
                        )
                        await res.edit_original_message(embed=embed, components=components)

                    elif 'roster_' in res.values[0]:
                        alias = res.values[0].split('_')[1]
                        await _roster.find_roster(guild=ctx.guild, alias=alias)
                        if mode == 'move':
                            embed = await _roster.embed(move_text=f'Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}')
                        else:
                            embed = await _roster.embed(move_text=f'Mode: {mode}')
                        PLAYER_PAGE = 0
                        EDIT_ROSTER_PAGE = 0
                        MOVE_ROSTER_PAGE = 0
                        components = await _roster.mode_components(
                            mode=mode,
                            player_page=PLAYER_PAGE,
                            roster_page=EDIT_ROSTER_PAGE,
                            other_roster_page=MOVE_ROSTER_PAGE,
                        )
                        await res.edit_original_message(embed=embed, components=components)

                    elif 'editrosters_' in res.values[0]:
                        EDIT_ROSTER_PAGE = int(res.values[0].split('_')[1])
                        components = await _roster.mode_components(
                            mode=mode,
                            player_page=PLAYER_PAGE,
                            roster_page=EDIT_ROSTER_PAGE,
                            other_roster_page=MOVE_ROSTER_PAGE,
                        )
                        await res.edit_original_message(embed=embed, components=components)

                    elif 'moverosters_' in res.values[0]:
                        MOVE_ROSTER_PAGE = int(res.values[0].split('_')[1])
                        components = await _roster.mode_components(
                            mode=mode,
                            player_page=PLAYER_PAGE,
                            roster_page=EDIT_ROSTER_PAGE,
                            other_roster_page=MOVE_ROSTER_PAGE,
                        )
                        await res.edit_original_message(embed=embed, components=components)

                    elif 'rostermove_' in res.values[0]:
                        alias = res.values[0].split('_')[1]
                        new_roster = alias
                        await _new_roster.find_roster(guild=ctx.guild, alias=new_roster)
                        embed = await _roster.embed(move_text=f'Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}')
                        PLAYER_PAGE = 0
                        EDIT_ROSTER_PAGE = 0
                        MOVE_ROSTER_PAGE = 0
                        components = await _roster.mode_components(
                            mode=mode,
                            player_page=PLAYER_PAGE,
                            roster_page=EDIT_ROSTER_PAGE,
                            other_roster_page=MOVE_ROSTER_PAGE,
                        )
                        await res.edit_original_message(embed=embed, components=components)

                    elif 'rostergroup_' in res.values[0]:
                        group = res.values[0].split('_')[-1]
                        embed = await _roster.embed(move_text=f'Mode: {mode} | Moving to {new_roster}\nGroup Mode: {group}')
                        components = await _roster.mode_components(
                            mode=mode,
                            player_page=PLAYER_PAGE,
                            roster_page=EDIT_ROSTER_PAGE,
                            other_roster_page=MOVE_ROSTER_PAGE,
                        )
                        await res.edit_original_message(embed=embed, components=components)

            except Exception as error:
                if isinstance(error, RosterAliasAlreadyExists):
                    embed = disnake.Embed(
                        description=f'Roster with this alias already exists.',
                        color=disnake.Color.red(),
                    )
                    await res.send(embed=embed, ephemeral=True)

                if isinstance(error, RosterDoesNotExist):
                    embed = disnake.Embed(
                        description=f'Roster with this alias does not exist. Use `/roster create`',
                        color=disnake.Color.red(),
                    )
                    await res.send(embed=embed, ephemeral=True)

                if isinstance(error, PlayerAlreadyInRoster):
                    embed = disnake.Embed(
                        description=f'Player has already been added to this roster.',
                        color=disnake.Color.red(),
                    )
                    await res.send(embed=embed, ephemeral=True)

                if isinstance(error, PlayerNotInRoster):
                    embed = disnake.Embed(
                        description=f'Player not found in this roster.',
                        color=disnake.Color.red(),
                    )
                    await res.send(embed=embed, ephemeral=True)

    @roster.sub_command(name='groups', description='create/remove a group players can be placed in')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_create_player_group(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        add: str = None,
        remove: str = None,
    ):
        await ctx.response.defer()
        results = await self.bot.server_db.find_one({'server': ctx.guild.id})
        groups = results.get('player_groups', [])

        if add is not None and len(groups) == 25:
            embed = disnake.Embed(
                description='**Please remove a player group before you add another (limit 25).**',
                color=disnake.Color.red(),
            )
            return await ctx.edit_original_message(embed=embed)

        text = ''
        if add is not None:
            if len(add) >= 50:
                text += f'**{add}** cannot be added as a player group, must be under 50 characters\n'
            elif add not in groups:
                await self.bot.server_db.update_one({'server': ctx.guild.id}, {'$push': {'player_groups': add}})
                text += f'**{add}** added as a player group.\n'

        if remove is not None:
            if remove in groups:
                await self.bot.server_db.update_one({'server': ctx.guild.id}, {'$pull': {'player_groups': remove}})
                text += f'**{remove}** removed as a player group.'
            else:
                text += f'**{remove}** not an existing player group.'

        embed = disnake.Embed(title='Roster Group Changes', description=text, color=disnake.Color.green())
        return await ctx.edit_original_message(embed=embed)

    @roster.sub_command(
        name='refresh',
        description='Refresh the data in a roster (townhall levels, hero levels)',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_refresh(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        roster: str = commands.Param(name='roster_', autocomplete=autocomplete.roster_alias),
    ):
        await ctx.response.defer()
        if roster != 'REFRESH ALL':
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=roster)
            await _roster.refresh_roster()
            embed = disnake.Embed(
                description=f"Player data for **{_roster.roster_result.get('alias')}** roster has been refreshed.",
                color=disnake.Color.green(),
            )
            embed.set_thumbnail(url=_roster.roster_result.get('clan_badge'))
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
                return await ctx.edit_original_message(
                    embed=disnake.Embed(
                        description=f'Bulk Refresh can only be run once every 30 minutes, please try again <t:{diff}:R>',
                        color=disnake.Color.red(),
                    )
                )
            last_run[ctx.guild.id] = int(datetime.datetime.now().timestamp())
            roster_list = await self.bot.rosters.find({'$and': [{'server_id': ctx.guild.id}]}).to_list(length=100)
            await ctx.edit_original_message(f'Bulk Roster Refresh Has Been Added to Queue')
            for count, roster in enumerate(roster_list, 1):
                await asyncio.sleep(5)
                await ctx.edit_original_message(f"Refreshing {roster.get('alias')} ({count}/{len(roster_list)})")
                _roster = Roster(bot=self.bot, roster_result=roster)
                await _roster.refresh_roster()
            embed = disnake.Embed(
                description=f'Player data for all {len(roster_list)} rosters on this server have been refreshed.',
                color=disnake.Color.green(),
            )
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            await ctx.edit_original_message(content=None, embed=embed)

    @roster.sub_command(name='missing', description="Ping missing, out of place, or all players on roster")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_ping(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        roster: str = commands.Param(autocomplete=autocomplete.roster_alias),
        message: str = '',
        type: str = commands.Param(choices=["Ping Missing", "Ping Out of Place", "Ping All"])
    ):
        _roster = Roster(bot=self.bot)
        await ctx.response.defer()
        await _roster.find_roster(guild=ctx.guild, alias=roster)

        if not ctx.guild.chunked:
            if ctx.guild.id not in self.bot.STARTED_CHUNK:
                await ctx.guild.chunk(cache=True)
            else:
                self.bot.STARTED_CHUNK.add(ctx.guild.id)

        if type == 'Ping Missing' or type == "Ping Out of Place":
            reverse = type == 'Ping Out of Place'
            embed = await _roster.missing_embed(reverse=reverse)
            miss_text = 'Missing'
            if reverse:
                miss_text = 'Out of Place'
        else:
            embed = await _roster.embed()
            miss_text = 'All Roster'


        ping_buttons = [
            disnake.ui.Button(
                label=f'Ping {miss_text} Members',
                emoji=self.bot.emoji.pin.partial_emoji,
                style=disnake.ButtonStyle.green,
                custom_id=f'ping',
            )
        ]
        buttons = disnake.ui.ActionRow()
        for button in ping_buttons:
            buttons.append_item(button)
        await ctx.edit_original_message(embed=embed, components=[buttons])
        msg = await ctx.original_message()
        if message != '':
            await _roster.set_missing_text(text=message)

        def check(res: disnake.MessageInteraction):
            return (res.message.id == msg.id) and (res.user == ctx.user)

        try:
            res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', check=check, timeout=600)
        except:
            return await msg.edit(components=[])

        await res.response.defer()
        if type == 'Ping Missing' or type == "Ping Out of Place":
            missing = await _roster.missing_list(reverse=reverse)
        else:
            missing = _roster.members

        tags = [member.get('tag') for member in missing]
        names = {}
        for member in missing:
            names[member.get('tag')] = member.get('name')
        links = await self.bot.link_client.get_links(*tags)
        missing_text = ''
        for player_tag, discord_id in links:
            member = disnake.utils.get(ctx.guild.members, id=discord_id)
            name = names[player_tag]
            if member is None:
                missing_text += f'{name} | {player_tag}\n'
            else:
                missing_text += f'{name} | {member.mention}\n'
        await msg.delete()
        top_text = (f"**Pinging {miss_text} Members**\n"
                    f"{_roster.clan_name} | {_roster.alias} | {'' if not _roster.time else self.bot.timestamper(_roster.time).relative}\n")
        button = disnake.ui.Button(
            label='Clan Link',
            emoji='🔗',
            style=disnake.ButtonStyle.url,
            url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{_roster.roster_result.get('clan_tag').strip('#')}",
        )
        buttons = [disnake.ui.ActionRow(button)]
        await res.channel.send(content=f'{top_text}{_roster.missing_text}{missing_text}', components=buttons)
        await res.send(content="Done, Notified!", ephemeral=True, delete_after=5)

    @roster.sub_command(
        name='settings',
        description='Edit settings for a roster',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_restrict(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        roster: str = commands.Param(autocomplete=autocomplete.roster_alias),
    ):
        await ctx.response.defer(ephemeral=True)
        random_uuid = uuid.uuid4()
        uuid_bytes = random_uuid.bytes
        base64_uuid = base64.urlsafe_b64encode(uuid_bytes).rstrip(b'=')
        url_safe_uuid = base64_uuid.decode('utf-8')
        await self.bot.rosters.update_one({'$and': [{'server_id': ctx.guild.id}, {'alias': roster}]}, {'$set': {'token': url_safe_uuid}})
        await ctx.send(content=f'Edit your roster here -> https://api.clashking.xyz/roster/?token={url_safe_uuid}', ephemeral=True)

    @roster.sub_command(name='list', description='List of rosters on this server')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_list(self, ctx: disnake.ApplicationCommandInteraction):
        result = self.bot.rosters.find({'$and': [{'server_id': ctx.guild.id}]})
        count = await self.bot.rosters.count_documents({'$and': [{'server_id': ctx.guild.id}]})
        if count == 0:
            embed = disnake.Embed(
                description='**No rosters on this server. Use `/roster create` to get started.**',
                colour=disnake.Color.red(),
            )
            return await ctx.send(embed=embed)
        await ctx.response.defer()
        text = ''
        for roster in await result.to_list(length=count):
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=roster.get('alias'))
            text += f"- {_roster.roster_result.get('alias')} | {_roster.roster_result.get('clan_name')} | {len(_roster.roster_result.get('members'))}/{_roster.roster_size}"
            if _roster.time is not None:
                text += f' | {self.bot.timestamper(_roster.time).cal_date}\n'
            else:
                text += '\n'

        embed = disnake.Embed(
            title=f'{ctx.guild.name} Roster List',
            description=text,
            colour=disnake.Color.green(),
        )
        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(
        name='role',
        description='Set a role that will be added when a person signs up & vice versa',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_role(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        roster: str = commands.Param(autocomplete=autocomplete.roster_alias),
        role: disnake.Role = commands.Param(),
        group: str = None,
        remove_role=commands.Param(default=None, choices=['True']),
    ):
        _roster = Roster(bot=self.bot)
        await ctx.response.defer()
        await _roster.find_roster(guild=ctx.guild, alias=roster)
        if remove_role == 'True':
            role = None
        results = await self.bot.server_db.find_one({'server': ctx.guild.id})
        groups = results.get('player_groups', [])
        if group is not None and group not in groups:
            embed = disnake.Embed(
                description=f'{group} does not exist as a group for {roster}',
                colour=disnake.Color.red(),
            )
            return await ctx.edit_original_message(embed=embed)
        await _roster.set_role(role=role, group=group)

        group_text = f'for {group} group ' if group is not None else ''
        if role is not None:
            embed = disnake.Embed(
                description=f'{roster} role {group_text}set to {role.mention}',
                colour=disnake.Color.green(),
            )
        else:
            embed = disnake.Embed(
                description=f'{roster} role {group_text}removed',
                colour=disnake.Color.green(),
            )
        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(
        name='role-refresh',
        description='Refresh the roles of those signed up to this roster',
    )
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_role_refresh(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        roster: str = commands.Param(autocomplete=autocomplete.roster_alias),
    ):
        await ctx.response.defer()

        if ctx.guild.id not in self.bot.STARTED_CHUNK:
            await ctx.guild.chunk(cache=True)
        else:
            self.bot.STARTED_CHUNK.add(ctx.guild.id)
            return
        if roster != 'REFRESH ALL':
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=roster)
            try:
                await _roster.refresh_roles()
            except NoRosterRoles:
                embed = disnake.Embed(
                    description='**No roster roles set up for this roster. Use `/roster role` to get started.**',
                    colour=disnake.Color.red(),
                )
                return await ctx.edit_original_message(embed=embed)
            roster_alias = _roster.alias
        else:
            global refresh_last_run
            l_run = last_run.get(ctx.guild_id, 0)
            if int(datetime.datetime.now().timestamp()) - l_run <= 1800:
                diff = int(datetime.datetime.now().timestamp()) - l_run
                diff = int(datetime.datetime.now().timestamp()) + (1800 - diff)
                return await ctx.edit_original_message(
                    embed=disnake.Embed(
                        description=f'Bulk Role Refresh can only be run once every 30 minutes, please try again <t:{diff}:R>',
                        color=disnake.Color.red(),
                    )
                )
            await ctx.edit_original_message(f'Bulk Roster Role Refresh Has Been Added to Queue')
            results = await self.bot.rosters.find({'server_id': ctx.guild.id}).to_list(length=None)
            for count, roster in enumerate(results, 1):
                _roster = Roster(bot=self.bot, roster_result=roster)
                try:
                    await asyncio.sleep(3)
                    await ctx.edit_original_message(f'Refreshing {_roster.alias} ({count}/{len(results)})')
                    await _roster.refresh_roles()
                except NoRosterRoles:
                    continue
            roster_alias = 'All Rosters'

        embed = disnake.Embed(
            description=f'**Roles updated for {roster_alias}**',
            colour=disnake.Color.green(),
        )
        return await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name='copy', description='import/export/copy rosters')
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def roster_copy(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        export_roster: str = None,
        import_code: str = None,
    ):
        await ctx.response.defer()
        if export_roster == import_code == None:
            return await ctx.edit_original_message(content='**Must select an option to import or export.')
        if export_roster is not None:
            _roster = Roster(bot=self.bot)
            await _roster.find_roster(guild=ctx.guild, alias=export_roster)
            code = await _roster.export()
            embed = disnake.Embed(description=f'Here is your unique code to export this roster: `{code}`')
        else:
            result = await self.bot.rosters.find_one({'roster_id': import_code.upper()})
            name_result = await self.bot.rosters.find_one({'alias': f'Import {import_code}'})
            num = ''
            count = 0
            while name_result is not None:
                count += 1
                num = f'{count}'
                name_result = await self.bot.rosters.find_one({'alias': f'Import {import_code}{count}'})
            del result['_id']
            result['alias'] = f'Import {import_code}{num}'
            result['server_id'] = ctx.guild.id
            await self.bot.rosters.insert_one(result)
            embed = disnake.Embed(description=f'Roster imported as **Import {import_code}{num}** from `{import_code}`')

        await ctx.edit_original_message(embed=embed)

    @roster.sub_command(name='search', description='Get a list of rosters a user or player is on')
    async def roster_search(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        user: disnake.Member = None,
        player: coc.Player = commands.Param(
            default=None,
            converter=convert.player,
            autocomplete=autocomplete.family_players,
        ),
    ):
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
        text = ''
        for player in players:
            if user is not None and user.id == ctx.user.id:
                rosters_found = await self.bot.rosters.find({'members.tag': player.tag}).to_list(length=100)
            else:
                rosters_found = await self.bot.rosters.find({'$and': [{'server_id': ctx.guild.id}, {'members.tag': player.tag}]}).to_list(length=100)

            if not rosters_found:
                continue
            text += f'{self.bot.fetch_emoji(name=player.town_hall)}**{player.name}**\n'
            for roster in rosters_found:
                our_member = next(member for member in roster['members'] if member['tag'] == player.tag)
                group = our_member['group']
                if group == 'No Group':
                    group = 'Main'
                text += f"{roster['alias']} | {roster['clan_name']} | {group}\n"
            text += '\n'

        if text == '':
            text = 'Not Found on Any Rosters'
        embed = disnake.Embed(
            title=f'Rosters for {roster_type_text}',
            description=text,
            color=disnake.Color.green(),
        )
        await ctx.edit_original_message(embed=embed)

    @roster_create_player_group.autocomplete('remove')
    @roster_role.autocomplete('group')
    async def autocomp_group(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        results = await self.bot.server_db.find_one({'server': ctx.guild.id})
        groups = results.get('player_groups', [])
        return [f'{group}' for group in groups if query.lower() in group.lower()]

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if 'Refresh_' in str(ctx.data.custom_id):
            await ctx.response.defer()
            alias = str(ctx.data.custom_id).split('_')[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)
            embed = await roster.embed()
            await ctx.edit_original_message(embed=embed)

        elif 'RosterMenu_' in str(ctx.data.custom_id):
            alias = str(ctx.data.custom_id).split('_')[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)

            whitelist_check = await self.bot.white_list_check(ctx=ctx, command_name='roster settings')
            manage_guild_perms = ctx.user.guild_permissions.manage_guild

            if not whitelist_check and not manage_guild_perms:
                return await ctx.send(
                    content='Must have `Manage Guild` perms or be whitelisted for `/roster settings` to use the settings menu',
                    ephemeral=True,
                )
            random_uuid = uuid.uuid4()
            uuid_bytes = random_uuid.bytes
            base64_uuid = base64.urlsafe_b64encode(uuid_bytes).rstrip(b'=')
            url_safe_uuid = base64_uuid.decode('utf-8')
            await self.bot.rosters.update_one({'$and': [{'server_id': ctx.guild.id}, {'alias': roster.alias}]}, {'$set': {'token': url_safe_uuid}})
            await ctx.send(content=f'Edit your roster here -> https://api.clashking.xyz/roster/?token={url_safe_uuid}', ephemeral=True)

        elif 'Signup_' in str(ctx.data.custom_id):
            alias = str(ctx.data.custom_id).split('_')[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)

            await ctx.response.defer()
            main_message = await ctx.original_message()
            linked_accounts = await self.bot.get_tags(ping=str(ctx.user.id))
            if not linked_accounts:
                return await ctx.send(
                    content='No accounts linked to you. Use `/link` to get started.',
                    ephemeral=True,
                )
            accounts = await self.bot.get_players(tags=linked_accounts)
            accounts.sort(key=lambda x: (x.town_hall, x.trophies), reverse=True)
            options = []
            player_dict = {}
            roster_tags = [member.get('tag') for member in roster.players]
            for account in accounts:
                account: coc.Player
                if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                    continue
                if account.tag in roster_tags:
                    continue
                player_dict[account.tag] = account
                options.append(
                    disnake.SelectOption(
                        label=account.name,
                        emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji,
                        value=f'player_{account.tag}',
                    )
                )

            if not options:
                return await ctx.send(content='No accounts to add', ephemeral=True)

            button_options = [disnake.SelectOption(label='Main Group', value=f'signup_No Group')]
            for button in roster.buttons:
                button_options.append(
                    disnake.SelectOption(
                        label=button,
                        value=f'signup_{button}',
                    )
                )
            placement_select = disnake.ui.Select(
                options=button_options[:25],
                placeholder='Select Roster Group',
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )

            options = options[:25]
            select = disnake.ui.Select(
                options=options,
                placeholder='Select Account(s)',
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            dropdown = [
                disnake.ui.ActionRow(select),
                disnake.ui.ActionRow(placement_select),
                disnake.ui.ActionRow(disnake.ui.Button(label='Submit', style=disnake.ButtonStyle.green, custom_id='Save')),
            ]
            msg = await ctx.followup.send(content='Select Account(s) to Add & Where to add them', components=dropdown, ephemeral=True)

            save = False
            accounts_to_add = []
            group = None
            while not save:
                res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, msg=msg)
                if 'button' in str(res.data.component_type):
                    if not accounts_to_add and not group:
                        await res.send('Must select accounts & group to submit')
                    else:
                        save = True
                elif any('player_' in s for s in res.values):
                    accounts_to_add = [value.split('_')[-1] for value in res.values]
                elif any('signup_' in s for s in res.values):
                    group = res.values[0].split('_')[-1]

            await roster.find_roster(guild=ctx.guild, alias=alias)
            added = []
            for account in accounts_to_add:
                added.append(player_dict[account].name)
                await roster.add_member(player_dict[account], group=group)

            if roster.role is not None:
                try:
                    role = ctx.guild.get_role(roster.role)
                    await ctx.user.add_roles(*[role])
                except:
                    pass

            await msg.edit(content=f"Added {', '.join(added)} to {group} Group", components=[])
            embed = await roster.embed()
            await main_message.edit(embed=embed)

        elif 'RemoveMe_' in str(ctx.data.custom_id):
            alias = str(ctx.data.custom_id).split('_')[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)

            await ctx.response.defer()
            main_message = await ctx.original_message()
            linked_accounts = await self.bot.get_tags(ping=str(ctx.user.id))
            if not linked_accounts:
                return await ctx.send(
                    content='No accounts linked to you. Use `/link` to get started.',
                    ephemeral=True,
                )
            accounts = await self.bot.get_players(tags=linked_accounts)
            options = []
            player_dict = {}
            roster_tags = [member.get('tag') for member in roster.players]
            for account in accounts:
                account: coc.Player
                if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                    continue
                if account.tag not in roster_tags:
                    continue
                player_dict[account.tag] = account
                options.append(
                    disnake.SelectOption(
                        label=account.name,
                        emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji,
                        value=f'{account.tag}',
                    )
                )

            if not options:
                return await ctx.send(content='No accounts to remove', ephemeral=True)
            options = options[:25]
            select = disnake.ui.Select(
                options=options,
                placeholder='Select Account(s)',
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            dropdown = [disnake.ui.ActionRow(select)]
            msg = await ctx.followup.send(
                content='Select Account(s) to Remove',
                components=dropdown,
                ephemeral=True,
            )

            def check(res: disnake.MessageInteraction):
                return res.message.id == msg.id

            try:
                res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', check=check, timeout=600)
            except:
                return await msg.edit(components=[])

            await res.response.defer()
            accounts_to_add = res.values
            added = []

            for account in accounts_to_add:
                added.append(player_dict[account].name)
                await roster.remove_member(player_dict[account])
            await roster.find_roster(guild=ctx.guild, alias=alias)
            matching = [player for player in roster.players if player['discord'] == str(ctx.user) and player['group'] in ['No Group', 'Sub']]
            if roster.role is not None and not matching:
                try:
                    role = ctx.guild.get_role(roster.role)
                    await res.user.remove_roles(*[role])
                except:
                    pass
            await res.edit_original_message(content=f"Removed {', '.join(added)}", components=[])
            embed = await roster.embed()
            await main_message.edit(embed=embed)

        elif 'SubMe_' in str(ctx.data.custom_id):
            alias = str(ctx.data.custom_id).split('_')[1]
            roster = Roster(bot=self.bot)
            await roster.find_roster(guild=ctx.guild, alias=alias)

            await ctx.response.defer()
            main_message = await ctx.original_message()
            linked_accounts = await self.bot.get_tags(ping=str(ctx.user.id))
            if not linked_accounts:
                return await ctx.send(
                    content='No accounts linked to you. Use `/link` to get started.',
                    ephemeral=True,
                )
            accounts = await self.bot.get_players(tags=linked_accounts)
            options = []
            player_dict = {}
            roster_tags = [member.get('tag') for member in roster.players]
            for account in accounts:
                account: coc.Player
                if account.town_hall > roster.th_max or account.town_hall < roster.th_min:
                    continue
                if account.tag in roster_tags:
                    continue
                player_dict[account.tag] = account
                options.append(
                    disnake.SelectOption(
                        label=account.name,
                        emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji,
                        value=f'{account.tag}',
                    )
                )

            if not options:
                return await ctx.send(content='No accounts to add', ephemeral=True)
            options = options[:25]
            select = disnake.ui.Select(
                options=options,
                placeholder='Select Account(s)',
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            dropdown = [disnake.ui.ActionRow(select)]
            msg = await ctx.followup.send(content='Select Account(s) to Add', components=dropdown, ephemeral=True)

            def check(res: disnake.MessageInteraction):
                return res.message.id == msg.id

            try:
                res: disnake.MessageInteraction = await self.bot.wait_for('message_interaction', check=check, timeout=600)
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
    bot.add_cog(RosterCommands(bot))
