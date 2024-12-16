import asyncio
import datetime

import disnake
import pendulum as pend
from disnake.ext import commands
from loguru import logger
from classes.emoji import Emojis
from classes.bot import CustomClient
from classes.DatabaseClient.familyclient import FamilyClient
from classes.tickets import LOG_TYPE, OpenTicket, TicketPanel
from utility.constants import DISCORD_STATUS_TYPES, EMBED_COLOR_CLASS
from utility.discord_utils import get_webhook_for_channel, PATCHABLE_COMMANDS
from utility.startup import fetch_emoji_dict


has_started = False

class DiscordEvents(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self):
        emojis = await fetch_emoji_dict(bot=self.bot)
        self.bot.loaded_emojis = emojis
        self.bot.emoji = Emojis(bot=self.bot)
        self.bot.ck_client = FamilyClient(bot=self.bot)

        logger.info('We have connected to the discord gateway')


    @commands.Cog.listener()
    async def on_ready(self):
        global has_started
        if has_started:
            return

        has_started = True
        if self.bot._config.cluster_id == 1:
            await self.sync_patchable_commands()

        if self.bot.user.public_flags.verified_bot:
            for count, shard in self.bot.shards.items():
                await self.bot.change_presence(
                    activity=disnake.CustomActivity(state='Use Code ClashKing 👀', name='Custom Status'),
                    shard_id=shard.id,
                )
        else:
            default_status = {
                'activity_text': 'Use Code ClashKing 👀',
                'status': 'Online',
            }
            await self.bot.change_presence(
                activity=disnake.CustomActivity(state=default_status.get('activity_text'), name='Custom Status'),
                status=DISCORD_STATUS_TYPES.get(default_status.get('status')),
            )

        database_guilds = await self.bot.server_db.distinct('server')
        database_guilds: set = set(database_guilds)
        missing_guilds = [guild.id for guild in self.bot.guilds if guild.id not in database_guilds]
        for guild in missing_guilds:
            try:
                await self.bot.server_db.insert_one(
                    {
                        'server': guild,
                        'banlist': None,
                        'greeting': None,
                        'cwlcount': None,
                        'topboardchannel': None,
                        'tophour': None,
                        'lbboardChannel': None,
                        'lbhour': None,
                    }
                )
            except:
                continue

        logger.info('Bot has loaded & is ready')



    @commands.Cog.listener()
    async def on_guild_join(self, guild: disnake.Guild):
        if not self.bot.user.public_flags.verified_bot:
            return

        log_channel = await self.bot.getch_channel(937519135607373874)

        server_name = guild.name
        server_id = guild.id
        owner = guild.owner
        member_count = guild.member_count
        roles = len(guild.roles)
        channels = len([ch for ch in guild.channels if str(ch.type) in ['text', 'voice']])
        text_channels = len([ch for ch in guild.channels if str(ch.type) == 'text'])
        voice_channels = len([ch for ch in guild.channels if str(ch.type) == 'voice'])
        creation_date = pend.instance(guild.created_at).to_datetime_string()  # Format: YYYY-MM-DD HH:mm:ss
        description = guild.description or "No description provided"
        icon_url = guild.icon.url if guild.icon else None
        banner_url = guild.banner.url if guild.banner else None
        bot_admin = (await guild.getch_member(self.bot.user.id)).guild_permissions.administrator

        # Check boost status
        boost_level = guild.premium_tier
        boosts = guild.premium_subscription_count

        # Construct embed with all details
        embed = disnake.Embed(
            title="Joined a New Server! 🎉",
            description=f"**ClashKing has joined the server:** `{server_name}`",
            color=disnake.Color.green(),
            timestamp=pend.now()
        )

        # Add fields with detailed server info
        embed.add_field(name="Server ID", value=f"{server_id}", inline=True)
        embed.add_field(name="Owner", value=f"{owner}", inline=True)
        embed.add_field(name="Member Count", value=f"{member_count}", inline=True)
        embed.add_field(name="Total Roles", value=f"{roles}", inline=True)
        embed.add_field(name="Total Channels", value=f"{channels} (Text: {text_channels}, Voice: {voice_channels})",
                        inline=False)
        embed.add_field(name="Creation Date", value=f"{creation_date}", inline=True)
        embed.add_field(name="Server Description", value=f"{description}", inline=False)
        embed.add_field(name="Boost Level", value=f"Tier {boost_level} with {boosts} Boosts", inline=True)
        embed.add_field(name="Admin Permissions?", value="✅ Yes" if bot_admin else "❌ No", inline=True)

        if icon_url:
            embed.set_thumbnail(url=icon_url)
        if banner_url:
            embed.set_image(url=banner_url)

        await log_channel.send(embed=embed)

        msg = (
            "# Thanks for inviting **ClashKing**! 🎉\n\n"
            "ClashKing is designed to simplify clan and family management while providing powerful features like **legends tracking**, **autoboards**, and **in-depth stats**. "
            "It also includes tools like **role management**, **ticketing**, and **roster management** to make running your clan easier.\n\n"
            "To get started, browse the [documentation](https://docs.clashking.xyz) & run `/help` to explore the available features."
            " For additional support, you can also query our docs with `/ask` or join the [support/community server](https://discord.gg/clashking).\n\n"
            "**Note:** ClashKing is actively developed and improving constantly. If you encounter any issues or have feature suggestions, let me know! If you enjoy the bot, "
            "consider supporting the project by using Creator Code **ClashKing** in-game. Thank you for being part of this journey! - Destinea, Magic, & Obno ❤️"
        )

        # Check if server settings exist in the database
        results = await self.bot.server_db.find_one({'server': guild.id})

        # Insert default server settings if none exist
        if results is None:
            await self.bot.server_db.insert_one(
                {
                    'server': guild.id,
                    'banlist': None,
                    'greeting': None,
                    'cwlcount': None,
                    'topboardchannel': None,
                    'tophour': None,
                    'lbboardChannel': None,
                    'lbhour': None,
                }
            )

        if results and bot_admin:
            return

        first_channel = next(
            (channel for channel in guild.channels
             if str(channel.type) == 'text' and channel.permissions_for(channel.guild.me).send_messages),
            None
        )
        if not first_channel:
            return

        embed = disnake.Embed(description=msg, color=EMBED_COLOR_CLASS)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label='Support Server', emoji='🔗', url='https://discord.gg/clashking'))
        buttons.append_item(disnake.ui.Button(label='Documentation', emoji='🔗', url='https://docs.clashking.xyz'))

        # Add a footer if the bot lacks admin permissions
        if not bot_admin:
            embed.set_footer(
                text='Admin permissions are recommended for full functionality and easier setup. Thank you!')

        # Send the message only if the server settings were just created
        if results is None:
            await first_channel.send(embed=embed, components=buttons)



    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if not self.bot.user.public_flags.verified_bot:
            return
        log_channel = await self.bot.getch_channel(937519135607373874)

        server_name = guild.name
        server_id = guild.id
        owner = guild.owner
        member_count = guild.member_count
        roles = len(guild.roles)
        channels = len([ch for ch in guild.channels if str(ch.type) in ['text', 'voice']])
        text_channels = len([ch for ch in guild.channels if str(ch.type) == 'text'])
        voice_channels = len([ch for ch in guild.channels if str(ch.type) == 'voice'])
        creation_date = pend.instance(guild.created_at).to_datetime_string()  # Format: YYYY-MM-DD HH:mm:ss
        description = guild.description or "No description provided"
        icon_url = guild.icon.url if guild.icon else None
        banner_url = guild.banner.url if guild.banner else None
        bot_admin = (await guild.getch_member(self.bot.user.id)).guild_permissions.administrator

        boost_level = guild.premium_tier
        boosts = guild.premium_subscription_count

        embed = disnake.Embed(
            title="Left a Server 🛑",
            description=f"**ClashKing has been removed from the server:** `{server_name}`",
            color=disnake.Color.red(),
            timestamp=pend.now()
        )

        embed.add_field(name="Server ID", value=f"{server_id}", inline=True)
        embed.add_field(name="Owner", value=f"{owner}", inline=True)
        embed.add_field(name="Member Count", value=f"{member_count}", inline=True)
        embed.add_field(name="Total Roles", value=f"{roles}", inline=True)
        embed.add_field(name="Total Channels", value=f"{channels} (Text: {text_channels}, Voice: {voice_channels})",
                        inline=False)
        embed.add_field(name="Creation Date", value=f"{creation_date}", inline=True)
        embed.add_field(name="Server Description", value=f"{description}", inline=False)
        embed.add_field(name="Boost Level", value=f"Tier {boost_level} with {boosts} Boosts", inline=True)
        embed.add_field(name="Admin Permissions?", value="✅ Yes" if bot_admin else "❌ No", inline=True)

        if icon_url:
            embed.set_thumbnail(url=icon_url)
        if banner_url:
            embed.set_image(url=banner_url)

        await log_channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_application_command(self, ctx: disnake.ApplicationCommandInteraction):
        sent_support_msg = False

        try:
            msg = await ctx.original_message()
            if not msg.flags.ephemeral:
                # Check the last support message sent
                last_run = await self.bot.command_stats.find_one(
                    filter={'$and': [{'user': ctx.author.id}, {'sent_support_msg': True}]},
                    sort=[('time', -1)]
                )
                current_time = int(pend.now(tz=pend.UTC).timestamp())
                week_in_seconds = 7 * 86400

                if last_run is None or current_time - last_run.get('time', 0) >= week_in_seconds:
                    # Wait until the message is no longer loading
                    for _ in range(10):
                        if not msg.flags.loading:
                            break
                        await asyncio.sleep(1.5)
                        msg = await ctx.channel.fetch_message(msg.id)

                    if not msg.flags.loading:
                        commands_run_by_user = await self.bot.command_stats.count_documents({'user': ctx.author.id})
                        sent_support_msg = True

                        file = disnake.File('assets/support.png')
                        buttons = disnake.ui.ActionRow(
                            disnake.ui.Button(
                                label='Creator Code',
                                style=disnake.ButtonStyle.url,
                                url='https://code.clashk.ing'
                            ),
                            disnake.ui.Button(
                                label='Server',
                                style=disnake.ButtonStyle.url,
                                url='https://discord.gg/clashking'
                            ),
                            disnake.ui.Button(
                                label='X',
                                style=disnake.ButtonStyle.url,
                                url='https://x.clashk.ing'
                            ),
                            disnake.ui.Button(
                                label='Patreon',
                                style=disnake.ButtonStyle.url,
                                url='https://support.clashk.ing'
                            ),
                            disnake.ui.Button(
                                label='Github',
                                style=disnake.ButtonStyle.url,
                                url='https://git.clashk.ing'
                            )
                        )

                        await ctx.followup.send(
                            content=(
                                f'You have run {commands_run_by_user} commands on ClashKing!\n'
                                f'- This message is only sent once weekly\n'
                                f'- Your support means a lot! Use our creator code for your purchases, star us on GitHub, or follow us on Twitter.'
                            ),
                            file=file,
                            components=[buttons],
                            ephemeral=True
                        )
                        sent_support_msg = True
        except Exception as e:
            pass

        await self.bot.command_stats.insert_one(
            {
                'user': ctx.author.id,
                'command_name': ctx.application_command.qualified_name,
                'server': ctx.guild.id if ctx.guild is not None else None,
                'server_name': ctx.guild.name if ctx.guild is not None else None,
                'time': int(datetime.datetime.now().timestamp()),
                'guild_size': ctx.guild.member_count if ctx.guild is not None else 0,
                'channel': ctx.channel_id,
                'channel_name': ctx.channel.name if ctx.channel is not None and hasattr(ctx.channel, "name") else None,
                'len_mutual': len(ctx.user.mutual_guilds),
                'is_bot_dev': ctx.user.public_flags.verified_bot_developer,
                'bot': ctx.bot.user.id,
                'sent_support_msg': sent_support_msg,
                'interaction_id' : ctx.id,
                'options' : str(ctx.filled_options)
            }
        )


    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        if member.guild.id not in self.bot.OUR_GUILDS:
            return

        server_db = await self.bot.ck_client.get_server_settings(server_id=member.guild.id)

        if not server_db.welcome_link_log.webhook or not server_db.welcome_link_log.embeds:
            return

        log = server_db.welcome_link_log

        embeds = [disnake.Embed.from_dict(data=e) for e in log.embeds]
        color_conversion = {
            'Blue': disnake.ButtonStyle.primary,
            'Grey': disnake.ButtonStyle.secondary,
            'Green': disnake.ButtonStyle.success,
            'Red': disnake.ButtonStyle.danger,
        }
        button_color_cls = color_conversion.get(log.button_color)
        buttons = disnake.ui.ActionRow()
        for b_type in log.buttons:
            if b_type == 'Link Button':
                buttons.append_item(
                    disnake.ui.Button(
                        label='Link Account',
                        emoji='🔗',
                        style=button_color_cls,
                        custom_id='Start Link',
                    )
                )
            elif b_type == 'Link Help Button':
                buttons.append_item(
                    disnake.ui.Button(
                        label='Help',
                        emoji='❓',
                        style=button_color_cls,
                        custom_id='Link Help',
                    )
                )
            elif b_type == 'Refresh Button':
                buttons.append_item(
                    disnake.ui.Button(
                        label='Refresh Roles',
                        emoji=self.bot.emoji.refresh.partial_emoji,
                        style=button_color_cls,
                        custom_id='Refresh Roles',
                    )
                )
            elif b_type == 'To-Do Button':
                buttons.append_item(
                    disnake.ui.Button(
                        label='To-Do List',
                        emoji=self.bot.emoji.green_check.partial_emoji,
                        style=button_color_cls,
                        custom_id='MyToDoList',
                    )
                )
            elif b_type == 'Roster Button':
                buttons.append_item(
                    disnake.ui.Button(
                        label='My Rosters',
                        emoji=self.bot.emoji.calendar.partial_emoji,
                        style=button_color_cls,
                        custom_id='MyRosters',
                    )
                )

        try:
            webhook = await self.bot.getch_webhook(log.webhook)
            if webhook.user.id != self.bot.user.id:
                webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                await log.set_webhook(id=webhook.id)
            await webhook.send(content=member.mention, embeds=embeds, components=[buttons])
        except (disnake.NotFound, disnake.Forbidden):
            await log.set_webhook(id=None)

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: disnake.RawGuildMemberRemoveEvent):
        return
        tickets = await self.bot.open_tickets.find(
            {
                '$and': [
                    {'server': payload.guild_id},
                    {'user': payload.user.id},
                    {'status': {'$ne': 'delete'}},
                ]
            }
        ).to_list(length=None)
        if not tickets:
            return
        for ticket in tickets:
            ticket = OpenTicket(bot=self.bot, open_ticket=ticket)
            if ticket.status == 'delete':
                return
            panel_settings = await self.bot.tickets.find_one({'$and': [{'server_id': payload.guild_id}, {'name': ticket.panel_name}]})
            panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)
            channel: disnake.TextChannel = await self.bot.getch_channel(channel_id=ticket.channel)
            if channel is None:
                continue
            await panel.send_log(
                log_type=LOG_TYPE.TICKET_CLOSE,
                user=self.bot.user,
                ticket_channel=channel,
                ticket=ticket,
            )
            await ticket.set_ticket_status(status='delete')
            await channel.delete(reason=f'{payload.user.name} left server')


    async def sync_patchable_commands(self):
        """
        Sync global commands to patch or revert top-level commands as needed.
        """
        # Fetch all current global commands from Discord
        global_commands = await self.bot.http.get_global_commands(self.bot.application_id)

        # Desired patchable contexts
        PATCH_CONTEXTS = {"integration_types": [0, 1], "contexts": [0, 1, 2]}  # Patched
        DEFAULT_CONTEXTS = {"integration_types": [0], "contexts": None}  # Normal slash commands

        # Iterate through current global commands
        for command in global_commands:
            command_name = command["name"]
            command_id = command["id"]

            # Check if the command is in the PATCHABLE_COMMANDS registry
            if command_name in PATCHABLE_COMMANDS:
                await self._update_command_if_needed(command_id, PATCH_CONTEXTS, command)
            else:
                await self._update_command_if_needed(command_id, DEFAULT_CONTEXTS, command)


    async def _update_command_if_needed(self, command_id, desired_contexts, command):
        """
        Updates a command's contexts only if they differ from the desired state.
        """
        current_contexts = {
            "integration_types": command.get("integration_types", []),
            "contexts": command.get("contexts", [])
        }
        # Only send API call if there's a difference
        if current_contexts != desired_contexts:
            await self.bot.http.edit_global_command(
                self.bot.application_id,
                command_id,
                payload=desired_contexts,
            )
        else:
            pass


def setup(bot: CustomClient):
    bot.add_cog(DiscordEvents(bot))
