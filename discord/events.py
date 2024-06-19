import aiohttp
import asyncio
import datetime
import disnake
import pendulum as pend
import random

from loguru import logger
from disnake.ext import commands
from classes.bot import CustomClient
from utility.constants import USE_CODE_TEXT, DISCORD_STATUS_TYPES

from classes.tickets import OpenTicket, TicketPanel, LOG_TYPE
from classes.DatabaseClient.familyclient import FamilyClient
from assets.emojis import SharedEmojis
from collections import deque
from commands.reminders.send import (
    clan_games_reminder,
    clan_capital_reminder,
    inactivity_reminder,
    roster_reminder,
)
from utility.discord_utils import get_webhook_for_channel


has_started = False
has_readied = False


class DiscordEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self):
        self.bot.ck_client = FamilyClient(bot=self.bot)

        if self.bot.user.id == 808566437199216691:
            return

        global has_started
        if not has_started:
            await asyncio.sleep(60)
            has_started = True
            database_guilds = await self.bot.server_db.distinct("server")
            database_guilds: set = set(database_guilds)
            missing_guilds = [guild.id for guild in self.bot.guilds if guild.id not in database_guilds]
            for guild in missing_guilds:
                await self.bot.server_db.insert_one(
                    {
                        "server": guild,
                        "banlist": None,
                        "greeting": None,
                        "cwlcount": None,
                        "topboardchannel": None,
                        "tophour": None,
                        "lbboardChannel": None,
                        "lbhour": None,
                    }
                )

            """self.bot.scheduler.add_job(clan_capital_reminder, trigger="cron", args=[self.bot, "1 hr"], day_of_week="mon", hour=6, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_capital_reminder, trigger="cron", args=[self.bot, "2 hr"], day_of_week="mon", hour=5, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_capital_reminder, trigger="cron", args=[self.bot, "4 hr"], day_of_week="mon", hour=3, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_capital_reminder, trigger="cron", args=[self.bot, "6 hr"], day_of_week="mon", hour=1, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_capital_reminder, trigger="cron", args=[self.bot, "8 hr"], day_of_week="sun", hour=23, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_capital_reminder, trigger="cron", args=[self.bot, "12 hr"], day_of_week="sun", hour=19, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_capital_reminder, trigger="cron", args=[self.bot, "16 hr"], day_of_week="sun", hour=15, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_capital_reminder, trigger="cron", args=[self.bot, "24 hr"], day_of_week="sun", hour=7, misfire_grace_time=None)

            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "144 hr"], day=22, hour=8, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "120 hr"], day=23, hour=8, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "96 hr"], day=24, hour=8, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "72 hr"], day=25, hour=8, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "48 hr"], day=26, hour=8, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "36 hr"], day=26, hour=20, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "24 hr"], day=27, hour=8, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "12 hr"], day=27, hour=20, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "6 hr"], day=28, hour=2, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "4 hr"], day=28, hour=4, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "2 hr"], day=28, hour=6, misfire_grace_time=None)
            self.bot.scheduler.add_job(clan_games_reminder, trigger="cron", args=[self.bot, "1 hr"], day=28, hour=7, misfire_grace_time=None)

            self.bot.scheduler.add_job(inactivity_reminder, trigger='interval', args=[self.bot], minutes=30, misfire_grace_time=None)
            self.bot.scheduler.add_job(roster_reminder, trigger='interval', args=[self.bot], minutes=2, misfire_grace_time=None)"""

            logger.info("We have connected")

    @commands.Cog.listener()
    async def on_ready(self):
        global has_started
        if not has_started:
            await asyncio.sleep(15)
            has_started = True
        else:
            return

        """        for command in self.bot.global_application_commands:
            print(f"Patching command integration type for {command.id}")
            await self.bot.http.edit_global_command(
                self.bot.application_id,
                command.id,
                payload={"integration_types": [0, 1], "contexts": [0, 1, 2]},
            )"""

        if self.bot.user.public_flags.verified_bot:
            for count, shard in self.bot.shards.items():
                await self.bot.change_presence(
                    activity=disnake.CustomActivity(state="Use Code ClashKing 👀", name="Custom Status"),
                    shard_id=shard.id,
                )
        else:
            default_status = {
                "activity_text": "Use Code ClashKing 👀",
                "status": "Online",
            }
            bot_settings = await self.bot.custom_bots.find_one({"token": self.bot._config.bot_token})
            if bot_settings:
                default_status = bot_settings.get("state", default_status)
            await self.bot.change_presence(
                activity=disnake.CustomActivity(state=default_status.get("activity_text"), name="Custom Status"),
                status=DISCORD_STATUS_TYPES.get(default_status.get("status")),
            )

        logger.info("ready")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: disnake.Guild):
        if not self.bot.user.public_flags.verified_bot:
            return
        msg = (
            "Thanks for inviting ClashKing to your server! It comes packed with a decent amount of features like legends tracking, autoboards, a plethora of stats, & the ability to help manage your clan & families with features like role management, ticketing, & rosters. I recommend starting by taking a look over the entire `/help` command, "
            "in general I have done my best to make the names self explanatory (aside from a few legacy names, like /check being legend commands, don't ask why lol). "
            "If you need any further help, don't hesitate to check out the documentation (in progress) or join my support server (I don't mind being a walking encyclopedia of answers to your questions).\n"
            "One last thing to note - the bot is still under heavy development & is relatively young, so please reach out with any issues & if you end up enjoying what is here, consider using Creator Code ClashKing "
            "in-game to help support the project"
        )
        results = await self.bot.server_db.find_one({"server": guild.id})
        botAdmin = (await guild.getch_member(self.bot.user.id)).guild_permissions.administrator
        if results is None:
            await self.bot.server_db.insert_one(
                {
                    "server": guild.id,
                    "banlist": None,
                    "greeting": None,
                    "cwlcount": None,
                    "topboardchannel": None,
                    "tophour": None,
                    "lbboardChannel": None,
                    "lbhour": None,
                }
            )
        # if there's a result and bot has admin perms then no msg needed.
        if results and botAdmin is True:
            return

        channel = self.bot.get_channel(937519135607373874)
        await channel.send(f"Just joined {guild.name}")
        len_g = len(self.bot.guilds)
        for count, shard in self.bot.shards.items():
            await self.bot.change_presence(
                activity=disnake.CustomActivity(state="Use Code ClashKing 👀", name="Custom Status"),
                shard_id=shard.id,
            )  # type 3 watching type#1 - playing

        channel = self.bot.get_channel(937528942661877851)
        await channel.edit(name=f"ClashKing: {len_g} Servers")

        # loop channels to find the first text channel with perms to send message.
        for guildChannel in guild.channels:
            permissions = guildChannel.permissions_for(guildChannel.guild.me)
            if str(guildChannel.type) == "text" and permissions.send_messages is True:
                firstChannel = guildChannel
                break
        else:
            return
        embed = disnake.Embed(description=msg, color=disnake.Color.blue())
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="Support Server", emoji="🔗", url="https://discord.gg/clashking"))
        buttons.append_item(disnake.ui.Button(label="Documentation", emoji="🔗", url="https://docs.clashking.xyz"))
        (
            embed.set_footer(
                text="Admin permissions are recommended for full functionality & easier set up, thank you!"
            )
            if not botAdmin
            else None
        )
        (await firstChannel.send(components=buttons, embed=embed) if results is None else None)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if not self.bot.user.public_flags.verified_bot:
            return
        channel = self.bot.get_channel(937519135607373874)
        await channel.send(f"Just left {guild.name}, {guild.member_count} members")
        len_g = len(self.bot.guilds)
        for count, shard in self.bot.shards.items():
            await self.bot.change_presence(
                activity=disnake.CustomActivity(state="Use Code ClashKing 👀", name="Custom Status"),
                shard_id=shard.id,
            )  # type 3 watching type#1 - playing
        channel = self.bot.get_channel(937528942661877851)
        await channel.edit(name=f"ClashKing: {len_g} Servers")

    @commands.Cog.listener()
    async def on_application_command(self, ctx: disnake.ApplicationCommandInteraction):
        sent_support_msg = False
        try:
            msg = await ctx.original_message()
            if not msg.flags.ephemeral:
                last_run = await self.bot.command_stats.find_one(
                    filter={"$and": [{"user": ctx.author.id}, {"sent_support_msg": True}]},
                    sort=[("time", -1)],
                )
                if last_run is None or int(pend.now(tz=pend.UTC).timestamp()) - last_run.get("time") >= 7 * 86400:
                    tries = 0
                    while msg.flags.loading:
                        tries += 1
                        await asyncio.sleep(1.5)
                        msg = await ctx.channel.fetch_message(msg.id)
                        if tries == 10:
                            break
                    if tries != 10:
                        commands_run_by_user = await self.bot.command_stats.count_documents({"user": ctx.author.id})
                        sent_support_msg = True
                        file = disnake.File("assets/support.png")
                        buttons = disnake.ui.ActionRow(
                            disnake.ui.Button(
                                label="Creator Code",
                                style=disnake.ButtonStyle.url,
                                url="https://code.clashk.ing",
                            ),
                            disnake.ui.Button(
                                label="Server",
                                style=disnake.ButtonStyle.url,
                                url="https://discord.clashk.ing",
                            ),
                            disnake.ui.Button(
                                label="X",
                                style=disnake.ButtonStyle.url,
                                url="https://x.clashk.ing",
                            ),
                            disnake.ui.Button(
                                label="Patreon",
                                style=disnake.ButtonStyle.url,
                                url="https://support.clashk.ing",
                            ),
                            disnake.ui.Button(
                                label="Github",
                                style=disnake.ButtonStyle.url,
                                url="https://git.clashk.ing",
                            ),
                        )
                        await ctx.followup.send(
                            content=f"You have run {commands_run_by_user} commands on ClashKing!\n"
                            f"- This message is only sent once weekly\n"
                            f"- Your support means a lot! Use our creator code for your purchases, star us on GitHub, or follow us on Twitter. ",
                            file=file,
                            components=[buttons],
                            ephemeral=True,
                        )
        except Exception:
            pass

        await self.bot.command_stats.insert_one(
            {
                "user": ctx.author.id,
                "command_name": ctx.application_command.qualified_name,
                "server": ctx.guild.id if ctx.guild is not None else None,
                "server_name": ctx.guild.name if ctx.guild is not None else None,
                "time": int(datetime.datetime.now().timestamp()),
                "guild_size": ctx.guild.member_count if ctx.guild is not None else 0,
                "channel": ctx.channel_id,
                "channel_name": ctx.channel.name if ctx.channel is not None else None,
                "len_mutual": len(ctx.user.mutual_guilds),
                "is_bot_dev": ctx.user.public_flags.verified_bot_developer,
                "bot": ctx.bot.user.id,
                "sent_support_msg": sent_support_msg,
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
            "Blue": disnake.ButtonStyle.primary,
            "Grey": disnake.ButtonStyle.secondary,
            "Green": disnake.ButtonStyle.success,
            "Red": disnake.ButtonStyle.danger,
        }
        button_color_cls = color_conversion.get(log.button_color)
        buttons = disnake.ui.ActionRow()
        for b_type in log.buttons:
            if b_type == "Link Button":
                buttons.append_item(
                    disnake.ui.Button(
                        label="Link Account",
                        emoji="🔗",
                        style=button_color_cls,
                        custom_id="Start Link",
                    )
                )
            elif b_type == "Link Help Button":
                buttons.append_item(
                    disnake.ui.Button(
                        label="Help",
                        emoji="❓",
                        style=button_color_cls,
                        custom_id="Link Help",
                    )
                )
            elif b_type == "Refresh Button":
                buttons.append_item(
                    disnake.ui.Button(
                        label="Refresh Roles",
                        emoji=self.bot.emoji.refresh.partial_emoji,
                        style=button_color_cls,
                        custom_id="Refresh Roles",
                    )
                )
            elif b_type == "To-Do Button":
                buttons.append_item(
                    disnake.ui.Button(
                        label="To-Do List",
                        emoji=self.bot.emoji.yes.partial_emoji,
                        style=button_color_cls,
                        custom_id="MyToDoList",
                    )
                )
            elif b_type == "Roster Button":
                buttons.append_item(
                    disnake.ui.Button(
                        label="My Rosters",
                        emoji=self.bot.emoji.calendar.partial_emoji,
                        style=button_color_cls,
                        custom_id="MyRosters",
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
                "$and": [
                    {"server": payload.guild_id},
                    {"user": payload.user.id},
                    {"status": {"$ne": "delete"}},
                ]
            }
        ).to_list(length=None)
        if not tickets:
            return
        for ticket in tickets:
            ticket = OpenTicket(bot=self.bot, open_ticket=ticket)
            if ticket.status == "delete":
                return
            panel_settings = await self.bot.tickets.find_one(
                {"$and": [{"server_id": payload.guild_id}, {"name": ticket.panel_name}]}
            )
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
            await ticket.set_ticket_status(status="delete")
            await channel.delete(reason=f"{payload.user.name} left server")


def setup(bot: CustomClient):
    bot.add_cog(DiscordEvents(bot))
