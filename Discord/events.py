import asyncio
import datetime
import random
import disnake
from main import scheduler
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from FamilyManagement.Reminders import SendReminders
from utils.war import create_reminders, send_or_update_war_end, send_or_update_war_start
from utils.constants import USE_CODE_TEXT
has_started = False

class DiscordEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self):
        print("connected")
        if self.bot.user.id == 808566437199216691:
            return
        if self.bot.user.public_flags.verified_bot:
            len_g = len(self.bot.guilds)
            for count, shard in self.bot.shards.items():
                await self.bot.change_presence(activity=disnake.CustomActivity(state="Use Code ClashKing 👀",name="Custom Status"), shard_id=shard.id)
        global has_started
        if not has_started:
            has_started = True
            await asyncio.sleep(15)
            scheduler.add_job(SendReminders.clan_capital_reminder, trigger="cron", args=[self.bot, "1 hr"], day_of_week="mon", hour=6, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_capital_reminder, trigger="cron", args=[self.bot, "2 hr"], day_of_week="mon", hour=5, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_capital_reminder, trigger="cron", args=[self.bot, "4 hr"], day_of_week="mon", hour=3, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_capital_reminder, trigger="cron", args=[self.bot, "6 hr"], day_of_week="mon", hour=1, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_capital_reminder, trigger="cron", args=[self.bot, "8 hr"],day_of_week="sun", hour=23, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_capital_reminder, trigger="cron", args=[self.bot, "12 hr"], day_of_week="sun", hour=19, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_capital_reminder, trigger="cron", args=[self.bot, "16 hr"], day_of_week="sun", hour=15, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_capital_reminder, trigger="cron", args=[self.bot, "24 hr"], day_of_week="sun", hour=7, misfire_grace_time=None)

            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "144 hr"], day=22, hour=8, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "120 hr"], day=23, hour=8, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "96 hr"], day=24, hour=8, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "72 hr"], day=25, hour=8, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "48 hr"], day=26, hour=8, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "36 hr"], day=26, hour=20, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "24 hr"], day=27, hour=8, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "12 hr"], day=27, hour=20, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "6 hr"], day=28, hour=2, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "4 hr"], day=28, hour=4, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "2 hr"], day=28, hour=6, misfire_grace_time=None)
            scheduler.add_job(SendReminders.clan_games_reminder, trigger="cron", args=[self.bot, "1 hr"], day=28, hour=7, misfire_grace_time=None)

            scheduler.add_job(SendReminders.inactivity_reminder, trigger='interval', args=[self.bot], minutes=30, misfire_grace_time=None)
            scheduler.add_job(SendReminders.roster_reminder, trigger='interval', args=[self.bot], minutes=2, misfire_grace_time=None)

            guild_fetch = await self.bot.server_db.distinct("server")
            if self.bot.user.public_flags.verified_bot:
                all_guilds = [str(g) for g in guild_fetch]
                await self.bot.server_db.update_one({"server": 923764211845312533}, {"$set": {"all_servers": all_guilds}})
            else:
                guild_fetch = [guild.id for guild in self.bot.guilds if guild.id != 923764211845312533]
            x = guild_fetch
            if self.bot.user.public_flags.verified_bot:
                active_custom_bots = await self.bot.credentials.distinct("server")
                for bot in active_custom_bots:
                    try:
                        x.remove(bot)
                    except:
                        pass
            self.bot.OUR_GUILDS = set(x)

            tags = await self.bot.clan_db.distinct("tag", filter={"server" : {"$in" : list(self.bot.OUR_GUILDS)}})
            self.bot.clan_list = tags

            reminder_tags = await self.bot.reminders.distinct("clan", filter={"$and" : [{"type" : "War"}, {"server" : {"$in" : list(self.bot.OUR_GUILDS)}}]})
            current_war_times = await self.bot.get_current_war_times(tags=reminder_tags)
            for tag in current_war_times.keys():
                new_war, war_end_time = current_war_times[tag]
                try:
                    if new_war.state == "preparation":
                        scheduler.add_job(send_or_update_war_start, 'date', run_date=new_war.start_time.time,
                                          args=[self.bot, new_war.clan.tag], id=f"war_start_{new_war.clan.tag}",
                                          name=f"{new_war.clan.tag}_war_start", misfire_grace_time=None)
                    if new_war.end_time.seconds_until >= 0:
                        scheduler.add_job(send_or_update_war_end, 'date', run_date=new_war.end_time.time,
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

            scheduler.print_jobs()

            if self.bot.user.public_flags.verified_bot:
                for g in self.bot.guilds:
                    results = await self.bot.server_db.find_one({"server": g.id})
                    if results is None:
                        await self.bot.server_db.insert_one({
                            "server": g.id,
                            "prefix": ".",
                            "banlist": None,
                            "greeting": None,
                            "cwlcount": None,
                            "topboardchannel": None,
                            "tophour": None,
                            "lbboardChannel": None,
                            "lbhour": None
                        })

            print('We have logged in')


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
        botAdmin = guild.get_member(self.bot.user.id).guild_permissions.administrator
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
        try:
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
            pass

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


def setup(bot: CustomClient):
    bot.add_cog(DiscordEvents(bot))
