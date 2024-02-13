import asyncio
import datetime
import random
import disnake

from disnake.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from classes.bot import CustomClient
else:
    from disnake.ext.commands import AutoShardedBot as CustomClient

from utility.war import create_reminders, send_or_update_war_end, send_or_update_war_start
from utility.constants import USE_CODE_TEXT
has_started = False
has_readied = False
from classes.tickets import OpenTicket, TicketPanel, LOG_TYPE
from classes.DatabaseClient.familyclient import FamilyClient


class DiscordEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self):
        s_result = await self.bot.server_db.find_one({"server" : 1103679645439754335})
        self.bot.ck_client = FamilyClient(bot=self.bot)

        if self.bot.user.id == 808566437199216691:
            return

        global has_started
        if not has_started:
            has_started = True
            await asyncio.sleep(15)
            #self.bot.scheduler.add_job(SendReminders.inactivity_reminder, trigger='interval', args=[self.bot], minutes=30, misfire_grace_time=None)
            #self.bot.scheduler.add_job(SendReminders.roster_reminder, trigger='interval', args=[self.bot], minutes=2, misfire_grace_time=None)
            if self.bot.user.public_flags.verified_bot:
                for count, shard in self.bot.shards.items():
                    await self.bot.change_presence(activity=disnake.CustomActivity(state="↻ Bot starting up", name="Custom Status"), shard_id=shard.id)



            tags = await self.bot.clan_db.distinct("tag", filter={"server" : {"$in" : list(self.bot.OUR_GUILDS)}})
            self.bot.clan_list = tags

            '''reminder_tags = await self.bot.reminders.distinct("clan", filter={"$and" : [{"type" : "War"}, {"server" : {"$in" : list(self.bot.OUR_GUILDS)}}]})
            current_war_times = await self.bot.get_current_war_times(tags=reminder_tags)
            for tag in current_war_times.keys():
                new_war, war_end_time = current_war_times[tag]
                try:
                    if new_war.state == "preparation":
                        self.bot.scheduler.add_job(send_or_update_war_start, 'date', run_date=new_war.start_time.time,
                                          args=[self.bot, new_war.clan.tag], id=f"war_start_{new_war.clan.tag}",
                                          name=f"{new_war.clan.tag}_war_start", misfire_grace_time=None)
                    if new_war.end_time.seconds_until >= 0:
                        self.bot.scheduler.add_job(send_or_update_war_end, 'date', run_date=new_war.end_time.time,
                                          args=[self.bot, new_war.clan.tag, int(new_war.preparation_start_time.time.timestamp())], id=f"war_end_{new_war.clan.tag}",
                                          name=f"{new_war.clan.tag}_war_end", misfire_grace_time=None)
                except:
                    pass

                reminder_times = await self.bot.get_reminder_times(clan_tag=tag)
                try:
                    await self.bot.war_client.register_war(clan_tag=tag)
                except:
                    pass
                acceptable_times = self.bot.get_times_in_range(reminder_times=reminder_times, war_end_time=war_end_time)
                await create_reminders(bot=self.bot, times=acceptable_times, clan_tag=tag)

            self.bot.scheduler.print_jobs()'''

            print('We have logged in')

    @commands.Cog.listener()
    async def on_ready(self):
        global has_readied
        if not has_readied:
            if self.bot.user.public_flags.verified_bot:
                for count, shard in self.bot.shards.items():
                    await self.bot.change_presence(activity=disnake.CustomActivity(state="Use Code ClashKing 👀", name="Custom Status"), shard_id=shard.id)
            has_readied = True
            database_guilds = await self.bot.server_db.distinct("server")
            database_guilds: set = set(database_guilds)
            missing_guilds = [guild.id for guild in self.bot.guilds if guild.id not in database_guilds]
            for guild in missing_guilds:
                await self.bot.server_db.insert_one({
                    "server": guild,
                    "banlist": None,
                    "greeting": None,
                    "cwlcount": None,
                    "topboardchannel": None,
                    "tophour": None,
                    "lbboardChannel": None,
                    "lbhour": None,
                })

    @commands.Cog.listener()
    async def on_guild_join(self, guild:disnake.Guild):
        if not self.bot.user.public_flags.verified_bot:
            return
        msg = "Thanks for inviting ClashKing to your server! It comes packed with a decent amount of features like legends tracking, autoboards, a plethora of stats, & the ability to help manage your clan & families with features like role management, ticketing, & rosters. I recommend starting by taking a look over the entire `/help` command, " \
              "in general I have done my best to make the names self explanatory (aside from a few legacy names, like /check being legend commands, don't ask why lol). " \
              "If you need any further help, don't hesitate to check out the documentation (in progress) or join my support server (I don't mind being a walking encyclopedia of answers to your questions).\n" \
              "One last thing to note - the bot is still under heavy development & is relatively young, so please reach out with any issues & if you end up enjoying what is here, consider using Creator Code ClashKing " \
              "in-game to help support the project"
        results = await self.bot.server_db.find_one({"server": guild.id})
        botAdmin = (await guild.getch_member(self.bot.user.id)).guild_permissions.administrator
        if results is None:
            await self.bot.server_db.insert_one({
                "server": guild.id,
                "banlist": None,
                "greeting": None,
                "cwlcount": None,
                "topboardchannel": None,
                "tophour": None,
                "lbboardChannel": None,
                "lbhour": None,
            })
        # if there's a result and bot has admin perms then no msg needed.
        if results and botAdmin is True:
            return

        channel = self.bot.get_channel(937519135607373874)
        await channel.send(f"Just joined {guild.name}")
        len_g = len(self.bot.guilds)
        for count, shard in self.bot.shards.items():
            await self.bot.change_presence(
                activity=disnake.CustomActivity(state="Use Code ClashKing 👀",name="Custom Status"), shard_id=shard.id)  # type 3 watching type#1 - playing

        channel = self.bot.get_channel(937528942661877851)
        await channel.edit(name=f"ClashKing: {len_g} Servers")
        
        # loop channels to find the first text channel with perms to send message.
        for guildChannel in guild.channels:
            permissions = guildChannel.permissions_for(guildChannel.guild.me)
            if str(guildChannel.type) == 'text' and permissions.send_messages is True:
                firstChannel = guildChannel
                break
        else:
            return
        embed = disnake.Embed(description=msg, color=disnake.Color.blue())
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="Support Server", emoji="🔗", url="https://discord.gg/clashking"))
        buttons.append_item(disnake.ui.Button(label="Documentation", emoji="🔗", url="https://docs.clashking.xyz"))
        embed.set_footer(text="Admin permissions are recommended for full functionality & easier set up, thank you!") if not botAdmin else None
        await firstChannel.send(components=buttons, embed=embed) if results is None else None
        

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if not self.bot.user.public_flags.verified_bot:
            return
        channel = self.bot.get_channel(937519135607373874)
        await channel.send(f"Just left {guild.name}, {guild.member_count} members")
        len_g = len(self.bot.guilds)
        for count, shard in self.bot.shards.items():
            await self.bot.change_presence(
                activity=disnake.CustomActivity(state="Use Code ClashKing 👀",name="Custom Status"), shard_id=shard.id)  # type 3 watching type#1 - playing
        channel = self.bot.get_channel(937528942661877851)
        await channel.edit(name=f"ClashKing: {len_g} Servers")

    @commands.Cog.listener()
    async def on_application_command(self, ctx: disnake.ApplicationCommandInteraction):
        '''try:
            msg = await ctx.original_message()
            if not msg.flags.ephemeral and (ctx.locale == disnake.Locale.en_US or ctx.locale == disnake.Locale.en_GB):
                last_run = await self.bot.command_stats.find_one(filter={"user" : ctx.author.id}, sort=[("time", -1)])
                if last_run is None or int(datetime.datetime.now().timestamp()) - last_run.get('time') >= 7 * 86400:
                    tries = 0
                    while msg.flags.loading:
                        tries += 1
                        await asyncio.sleep(1.5)
                        msg = await ctx.channel.fetch_message(msg.id)
                        if tries == 10:
                            break
                    if tries != 10:
                        await ctx.followup.send(f"{random.choice(USE_CODE_TEXT)}\n", ephemeral=True)
        except Exception:
            pass'''

        await self.bot.command_stats.insert_one({
            "user": ctx.author.id,
            "command_name" : ctx.application_command.qualified_name,
            "server": ctx.guild.id if ctx.guild is not None else None,
            "server_name" : ctx.guild.name if ctx.guild is not None else None,
            "time" : int(datetime.datetime.now().timestamp()),
            "guild_size" : ctx.guild.member_count if ctx.guild is not None else 0,
            "channel" : ctx.channel_id,
            "channel_name" : ctx.channel.name if ctx.channel is not None else None,
            "len_mutual" : len(ctx.user.mutual_guilds),
            "is_bot_dev" : ctx.user.public_flags.verified_bot_developer,
            "bot" : ctx.bot.user.id
        })


    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: disnake.RawGuildMemberRemoveEvent):
        tickets = await self.bot.open_tickets.find({"$and": [{"server": payload.guild_id}, {"user": payload.user.id}, {"status": {"$ne": "delete"}}]}).to_list(length=None)
        if not tickets:
            return
        for ticket in tickets:
            ticket = OpenTicket(bot=self.bot, open_ticket=ticket)
            if ticket.status == "delete":
                return
            panel_settings = await self.bot.tickets.find_one({"$and": [{"server_id": payload.guild_id}, {"name": ticket.panel_name}]})
            panel = TicketPanel(bot=self.bot, panel_settings=panel_settings)
            channel: disnake.TextChannel = await self.bot.getch_channel(channel_id=ticket.channel)
            if channel is None:
                continue
            await panel.send_log(log_type=LOG_TYPE.TICKET_CLOSE, user=self.bot.user, ticket_channel=channel, ticket=ticket)
            await ticket.set_ticket_status(status="delete")
            await channel.delete(reason=f"{payload.user.name} left server")


def setup(bot: CustomClient):
    bot.add_cog(DiscordEvents(bot))
