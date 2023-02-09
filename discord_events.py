import disnake
import coc
from main import scheduler
from disnake.ext import commands
from Assets.thPicDictionary import thDictionary
from utils.troop_methods import heros, heroPets
from Exceptions import *
from CustomClasses.CustomBot import CustomClient

class DiscordEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.Cog.listener()
    async def on_ready(self):
        len_g = len(self.bot.guilds)
        for count, shard in self.bot.shards.items():
            await self.bot.change_presence(activity=disnake.Activity(name=f'{len_g} servers | Shard {count + 1}' ,type=3), shard_id=shard.id)  # type 3 watching type#1 - playing

    @commands.Cog.listener()
    async def on_connect(self):
        print("connected")
        global_chats = await self.bot.global_chat_db.distinct("channel")
        self.bot.global_channels = [chat for chat in global_chats if chat is not None]

        global_banned = self.bot.global_reports.find({})
        for banned in await global_banned.to_list(length=1000):
            strikes = banned.get("strikes")
            if strikes >= 3:
                self.bot.banned_global.append(banned.get("user"))


        '''tags = await self.bot.clan_db.distinct("tag")
        self.bot.clan_list = tags
        reminder_tags = await self.bot.reminders.distinct("clan", filter={"type" : "War"})
        self.bot.coc_client.add_war_updates(*tags)

        current_war_times = await self.bot.get_current_war_times(tags=reminder_tags)
        cog = self.bot.get_cog(name="Reminder Cron")
        for tag in current_war_times.keys():
            war_end_time = current_war_times[tag]
            reminder_times = await self.bot.get_reminder_times(clan_tag=tag)
            try:
                await self.bot.war_client.register_war(clan_tag=tag)
            except:
                pass
            acceptable_times = self.bot.get_times_in_range(reminder_times=reminder_times, war_end_time=war_end_time)
            if not acceptable_times:
                continue
            for time in acceptable_times:
                reminder_time = time[0] / 3600
                if reminder_time.is_integer():
                    reminder_time = int(reminder_time)
                send_time = time[1]
                try:
                    scheduler.add_job(cog.war_reminder, 'date', run_date=send_time, args=[tag, reminder_time], id=f"{reminder_time}_{tag}", name=f"{tag}", misfire_grace_time=None)
                except:
                    pass
        scheduler.print_jobs()'''

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
        results = await self.bot.server_db.find_one({"server": guild.id})
        if results is None:
            await self.bot.server_db.insert_one({
                "server": guild.id,
                "prefix": ".",
                "banlist": None,
                "greeting": None,
                "cwlcount": None,
                "topboardchannel": None,
                "tophour": None,
                "lbboardChannel": None,
                "lbhour": None
            })
        channel = self.bot.get_channel(937519135607373874)
        await channel.send(f"Just joined {guild.name}")
        owner = guild.owner
        len_g = len(self.bot.guilds)
        for count, shard in self.bot.shards.items():
            await self.bot.change_presence(
                activity=disnake.Activity(name=f'{len_g} servers | Shard {count + 1}',
                                          type=3), shard_id=shard.id)  # type 3 watching type#1 - playing

        channel = self.bot.get_channel(937528942661877851)
        await channel.edit(name=f"ClashKing: {len_g} Servers")


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        channel = self.bot.get_channel(937519135607373874)
        await channel.send(f"Just left {guild.name}, {guild.member_count} members")
        len_g = len(self.bot.guilds)
        for count, shard in self.bot.shards.items():
            await self.bot.change_presence(
                activity=disnake.Activity(name=f'{len_g} servers | Shard {count + 1}',
                                          type=3), shard_id=shard.id)  # type 3 watching type#1 - playing
        channel = self.bot.get_channel(937528942661877851)
        await channel.edit(name=f"ClashKing: {len_g} Servers")


    @commands.Cog.listener()
    async def on_application_command(self, ctx:disnake.ApplicationCommandInteraction):
        channel = self.bot.get_channel(960972432993304616)
        try:
            server = ctx.guild.name
        except:
            server = "None"

        user = ctx.author
        command = ctx.application_command
        embed = disnake.Embed(
            description=f"</{command.qualified_name}:{ctx.data.id}> **{ctx.filled_options}** \nused by {user.mention} [{user.name}] in {server} server",
            color=disnake.Color.blue())
        embed.set_thumbnail(url=user.display_avatar.url)
        await channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: disnake.ApplicationCommandInteraction, error):
        if isinstance(error, disnake.ext.commands.ConversionError):
            error = error.original

        if isinstance(error, coc.errors.NotFound):
            embed = disnake.Embed(description="Not a valid clan/player tag.", color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if isinstance(error, coc.errors.Maintenance):
            embed = disnake.Embed(description=f"Game is currently in Maintenance.", color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.CheckAnyFailure):
            if isinstance(error.errors[0], disnake.ext.commands.MissingPermissions):
                embed = disnake.Embed(description=error.errors[0], color=disnake.Color.red())
                return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.MissingPermissions):
            embed = disnake.Embed(description=error, color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if isinstance(error, disnake.ext.commands.CommandError):
            error = error.original

        if isinstance(error, RosterAliasAlreadyExists):
            embed = disnake.Embed(description=f"Roster with this alias already exists.", color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, RosterDoesNotExist):
            embed = disnake.Embed(description=f"Roster with this alias does not exist. Use `/roster create`", color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PlayerAlreadyInRoster):
            embed = disnake.Embed(description=f"Player has already been added to this roster.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PlayerNotInRoster):
            embed = disnake.Embed(description=f"Player not found in this roster.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, RosterSizeLimit):
            embed = disnake.Embed(description=f"Roster has hit max size limit",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PanelNotFound):
            embed = disnake.Embed(description=f"Panel not found!",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, ButtonNotFound):
            embed = disnake.Embed(description=f"Button not found!",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, PanelAlreadyExists):
            embed = disnake.Embed(description=f"Panel of this name already exists!",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, ButtonAlreadyExists):
            embed = disnake.Embed(description=f"Button of this name already exists!",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, FaultyJson):
            embed = disnake.Embed(description=f"Custom Embed Code is Faulty - > be sure to use this site -> https://autocode.com/tools/discord/embed-builder/ , "
                                              f"create your embed, then click `copy code`",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed, ephemeral=True)



def setup(bot: CustomClient):
    bot.add_cog(DiscordEvents(bot))