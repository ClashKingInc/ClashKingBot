import asyncio
import datetime
import random
import io
import aiohttp
import disnake

from disnake.ext import commands
from classes.bot import CustomClient
from utility.war import create_reminders, send_or_update_war_end, send_or_update_war_start
from utility.constants import USE_CODE_TEXT
has_started = False
from classes.tickets import OpenTicket, TicketPanel, LOG_TYPE
from classes.DatabaseClient.familyclient import FamilyClient
from assets.emojis import SharedEmojis
from collections import deque
from commands.reminders.send_reminders import clan_games_reminder, clan_capital_reminder, inactivity_reminder, roster_reminder

class DiscordEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self):
        self.bot.ck_client = FamilyClient(bot=self.bot)
        number_emojis = await self.bot.number_emojis.find().to_list(length=None)
        number_emojis_map = {"blue": {}, "gold": {}, "white": {}}
        for emoji in number_emojis:
            number_emojis_map[emoji.get("color")][emoji.get("count")] = emoji.get("emoji_id")
        self.bot.number_emoji_map = number_emojis_map

        if self.bot.user.id == 808566437199216691:
            return

        global has_started
        if not has_started:
            await asyncio.sleep(5)
            has_started = True
            if self.bot.user.public_flags.verified_bot:
                for count, shard in self.bot.shards.items():
                    await self.bot.change_presence(activity=disnake.CustomActivity(state="Use Code ClashKing 👀", name="Custom Status"), shard_id=shard.id)
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

            self.bot.scheduler.add_job(clan_capital_reminder, trigger="cron", args=[self.bot, "1 hr"], day_of_week="mon", hour=6, misfire_grace_time=None)
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
            self.bot.scheduler.add_job(roster_reminder, trigger='interval', args=[self.bot], minutes=2, misfire_grace_time=None)

            print('We have connected')


    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(5)
        print("ready")
        #will remove later, if is a custom bot, remove ourselves from every server but one
        if not self.bot.user.public_flags.verified_bot and self.bot.user.id != 808566437199216691:
            if self.bot.guilds:
                largest_server = sorted(self.bot.guilds, key=lambda x: x.member_count, reverse=True)[0]
                for server in self.bot.guilds:
                    if server.id != largest_server.id:
                        if server.owner_id != self.bot.user.id:
                            await server.leave()
                        else:
                            await server.delete()

            for number, emoji_id in self.bot.number_emoji_map.get("gold").items():
                if number <= 50:
                    SharedEmojis.all_emojis[f"{number}_"] = emoji_id

            print(len(SharedEmojis.all_emojis), "emojis that we have")
            if not self.bot.user.public_flags.verified_bot:
                our_emoji_servers = [server for server in self.bot.guilds if server.owner_id == self.bot.user.id and server.name != "ckcustombotbadges"]
                if len(our_emoji_servers) < 8:
                    for x in range(0, (8 - len(our_emoji_servers))):
                        if x != 8:
                            guild = await self.bot.create_guild(name=f"ckemojiserver{x}")
                            our_emoji_servers.append(guild)
                        else:
                            guild = await self.bot.create_guild(name="ckcustombotbadges")

                print(", ".join([g.name for g in self.bot.guilds]))
                print(", ".join([str(len(g.emojis)) for g in self.bot.guilds]))
                print(sum([(len(g.emojis)) for g in self.bot.guilds]) - 254, "emojis installed")

                print(len(our_emoji_servers), "servers")
                our_emoji_servers = deque(our_emoji_servers)

                id_to_lookup_name_map = {}
                for emoji_name, emoji_string in SharedEmojis.all_emojis.items():
                    emoji_split = emoji_string.split(":")
                    animated = "<a:" in emoji_string
                    emoji = disnake.PartialEmoji(name=emoji_split[1][1:], id=int(str(emoji_split[2])[:-1]), animated=animated)
                    id_to_lookup_name_map[str(emoji.id)] = emoji_name


                all_our_emojis = {}
                deleted = 0
                for server in our_emoji_servers:
                    for emoji in server.emojis:
                        lookup_name = id_to_lookup_name_map.get(emoji.name)
                        if lookup_name is None:
                            deleted += 1
                            await emoji.delete()
                            continue
                        all_our_emojis[lookup_name] = f"<:{emoji.name}:{emoji.id}>"

                print(deleted, "emojis deleted")

                to_create = 0
                for emoji_name, emoji_string in SharedEmojis.all_emojis.items():
                    if emoji_name not in all_our_emojis:
                        to_create += 1

                print(f"{to_create} emojis to create")
                for emoji_name, emoji_string in SharedEmojis.all_emojis.items():
                    if emoji_name not in all_our_emojis:
                        server = our_emoji_servers[0]
                        while len(server.emojis) == server.emoji_limit:
                            our_emoji_servers.rotate(1)
                            server = our_emoji_servers[0]
                        emoji_split = emoji_string.split(":")
                        animated = "<a:" in emoji_string

                        bytes_image: bytes = None
                        session = aiohttp.ClientSession()
                        main_bot_emoji = disnake.PartialEmoji(name=emoji_split[1][1:], id=int(str(emoji_split[2])[:-1]), animated=animated)
                        async with session.get(url=main_bot_emoji.url) as resp:
                            if resp.status == 200:
                                bytes_image = (await resp.read())
                        await session.close()
                        emoji = await server.create_custom_emoji(name=str(main_bot_emoji.id), image=bytes_image)
                        lookup_name = id_to_lookup_name_map.get(emoji.name)
                        print(f"created {lookup_name}")
                        all_our_emojis[lookup_name] = f"<:{emoji.name}:{emoji.id}>"
                        our_emoji_servers.rotate(1)

                for emoji_name, emoji_string in all_our_emojis.items():
                    SharedEmojis.all_emojis[emoji_name] = emoji_string

                print("done with emoji creation")


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
