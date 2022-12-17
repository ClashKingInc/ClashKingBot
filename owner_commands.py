import coc
import disnake
from disnake.ext import commands
from datetime import datetime
clan_tags = ["#2P0JJQGUJ"]
known_streak = []
count = 0
list_size = 0
import asyncio
from CustomClasses.CustomBot import CustomClient
from pymongo import UpdateOne
from PIL import Image, ImageDraw, ImageFont
import io
import chat_exporter

class OwnerCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.command(name='reload', hidden=True)
    async def _reload(self,ctx, *, module: str):
        """Reloads a module."""
        if ctx.message.author.id == 706149153431879760:
            try:
                self.bot.unload_extension(module)
                self.bot.load_extension(module)
            except:
                await ctx.send('<a:no:862552093324083221> Could not reload module.')
            else:
                await ctx.send('<a:check:861157797134729256> Reloaded module successfully')
        else:
            await ctx.send("You aren't magic. <:PS_Noob:783126177970782228>")

    @commands.slash_command(name="owner_anniversary", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def anniversary(self, ctx: disnake.ApplicationCommandInteraction):
        guild = ctx.guild
        await ctx.send(content="Edited 0 members")
        x = 0
        twelve_month = disnake.utils.get(ctx.guild.roles, id=1029249316981833748)
        nine_month = disnake.utils.get(ctx.guild.roles, id=1029249365858062366)
        six_month = disnake.utils.get(ctx.guild.roles, id=1029249360178987018)
        three_month = disnake.utils.get(ctx.guild.roles, id=1029249480261906463)
        for member in guild.members:
            if member.bot:
                continue
            year = member.joined_at.year
            month = member.joined_at.month
            n_year = datetime.now().year
            n_month = datetime.now().month
            num_months = (n_year - year) * 12 + (n_month - month)
            if num_months >= 12:
                if twelve_month not in member.roles:
                    await member.add_roles(*[twelve_month])
                if nine_month in member.roles or six_month in member.roles or three_month in member.roles:
                    await member.remove_roles(*[nine_month, six_month, three_month])
            elif num_months >= 9:
                if nine_month not in member.roles:
                    await member.add_roles(*[nine_month])
                if twelve_month in member.roles or six_month in member.roles or three_month in member.roles:
                    await member.remove_roles(*[twelve_month, six_month, three_month])
            elif num_months >= 6:
                if six_month not in member.roles:
                    await member.add_roles(*[six_month])
                if twelve_month in member.roles or nine_month in member.roles or three_month in member.roles:
                    await member.remove_roles(*[twelve_month, nine_month, three_month])
            elif num_months >= 3:
                if three_month not in member.roles:
                    await member.add_roles(*[three_month])
                if twelve_month in member.roles or nine_month in member.roles or six_month in member.roles:
                    await member.remove_roles(*[twelve_month, nine_month, six_month])
            x += 1
            if x % 5 == 0:
                await ctx.edit_original_message(content=f"Edited {x} members")
        await ctx.edit_original_message(content="Done")


    @commands.command(name="testraid")
    @commands.is_owner()
    async def testraid(self, ctx, tag):

        text = ""
        clan = await self.bot.getClan(tag)

        tracked = self.bot.clan_db.find({"tag": f"{clan.tag}"})
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await self.bot.fetch_guild(server)
            except:
                continue
            clancapital_channel = cc.get("clan_capital")
            if clancapital_channel is None:
                continue

            try:
                clancapital_channel = await server.fetch_channel(clancapital_channel)
                if clancapital_channel is None:
                    continue
            except:
                continue

            embed = disnake.Embed(
                description=f"Test Player donated <:capitalgold:987861320286216223>1000"
                , color=disnake.Color.green())

            embed.set_footer(icon_url=clan.badge.url, text=clan.name)

            try:
                member = await server.fetch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send =ow.send_messages
                embed_link = ow.embed_links
                await clancapital_channel.send(embed=embed)
                text += f"{server.name} : Successful\n> Send Messages Perm: {send}\nEmbed Link Perm: {embed_link}\n"
            except Exception as e:
                member = await server.getch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send = ow.send_messages
                embed_link = ow.embed_links
                text += f"{server.name} : Not Successful\n> Send Messages Perm: {send}\nEmbed Link Perm: {embed_link}\n> {str(e)[0:1000]}\n"

        embed = disnake.Embed(title=f"Test Raid {clan.name}", description=text, color=disnake.Color.green())
        await ctx.send(embed=embed)

    @commands.command(name="testreddit")
    @commands.is_owner()
    async def testraid(self, ctx, server_id):

        text = ""
        server_id = int(server_id)

        server = await self.bot.server_db.find_one({"server" : server_id})
        reddit_channel = server.get("reddit_feed")
        if reddit_channel is None:
            await ctx.send("No channel set up")

        server = server.get("server")

        server = await self.bot.fetch_guild(server)



        reddit_channel = await server.fetch_channel(reddit_channel)
        if reddit_channel is None:
            await ctx.send("Invalid channel")


        embed = disnake.Embed(
            description=f"Test Reddit Feed"
            , color=disnake.Color.green())

        try:
            member = await server.fetch_member(self.bot.user.id)
            ow = reddit_channel.overwrites_for(member)
            send = ow.send_messages
            embed_link = ow.embed_links
            await reddit_channel.send(embed=embed)
            text += f"{server.name} : Successful\n> Send Messages Perm: {send}\nEmbed Link Perm: {embed_link}\n"
        except Exception as e:
            member = await server.getch_member(self.bot.user.id)
            ow = reddit_channel.overwrites_for(member)
            send = ow.send_messages
            embed_link = ow.embed_links
            text += f"{server.name} : Not Successful\n> Send Messages Perm: {send}\nEmbed Link Perm: {embed_link}\n> {str(e)[0:1000]}\n"

        embed = disnake.Embed(title=f"Test Reddit Feed for {server.name}", description=text, color=disnake.Color.green())
        await ctx.send(embed=embed)

    @commands.command(name='leave')
    @commands.is_owner()
    async def leaveg(self,ctx, *, guild_name):
        guild = disnake.utils.get(self.bot.guilds, name=guild_name)  # Get the guild by name
        if guild is None:
            await ctx.send("No guild with that name found.")  # No guild found
            return
        await guild.leave()  # Guild found
        await ctx.send(f"I left: {guild.name}!")

    @commands.slash_command(name="test_cc", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def clan_capital_reminder(self, ctx):
        reminder_time = "1 hr"
        all_reminders = self.bot.reminders.find({"$and": [
            {"type": "Clan Capital"},
            {"time" : reminder_time}
        ]})
        for reminder in await all_reminders.to_list(length=10000):
            custom_text = reminder.get("custom_text")
            if custom_text is None:
                custom_text = ""
            else:
                custom_text = "\n" + custom_text
            channel = reminder.get("channel")
            try:
                channel = await self.bot.fetch_channel(channel)
            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.reminders.delete_one({"$and": [
                    {"clan": reminder.get("clan")},
                    {"server": reminder.get("server")},
                    {"time": f"{reminder_time}"},
                    {"type": "Clan Capital"}
                ]})
            server = self.bot.get_guild(reminder.get("server"))
            print("here2")
            if server is None:
                continue
            raid_weekend = await self.bot.get_raid(clan_tag=reminder.get("clan"))
            print(raid_weekend)
            if raid_weekend is None:
                continue
            missing = {}
            names = {}
            max = {}
            for member in raid_weekend.members:
                if member.attack_count < (member.attack_limit + member.bonus_attack_limit):
                    names[member.tag] = member.name
                    missing[member.tag] = (member.attack_limit + member.bonus_attack_limit) - member.attack_count
                    max[member.tag] = (member.attack_limit + member.bonus_attack_limit)

            tags = list(missing.keys())
            if not missing:
                return
            links = await self.bot.link_client.get_links(*tags)
            missing_text = ""
            for player_tag, discord_id in links:
                num_missing = missing[player_tag]
                max_do = max[player_tag]
                name = names[player_tag]
                member = disnake.utils.get(server.members, id=discord_id)
                if member is None:
                    missing_text += f"{num_missing} raids- {name} | {player_tag}\n"
                else:
                    missing_text += f"{num_missing} raids- {name} | {member.mention}\n"
            time = str(reminder_time).replace("hr", "")
            clan = await self.bot.getClan(clan_tag=reminder.get("clan"))
            badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            reminder_text = f"**{badge}{clan.name}\n{time} Hours Remaining in Raid Weekend**\n" \
                            f"{missing_text}" \
                            f"{custom_text}"
            await channel.send(content=reminder_text)


    @commands.slash_command(name="transcript",guild_ids=[923764211845312533] )
    @commands.is_owner()
    async def create_transcript(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        message = await chat_exporter.quick_export(ctx.channel)
        await chat_exporter.quick_link(ctx.channel, message)
        await ctx.edit_original_message(content="Here is your transcript!")

    @commands.slash_command(name="testlog")
    @commands.is_owner()
    async def testfwlog(self, ctx: disnake.ApplicationCommandInteraction, clan_tag):
        log = await self.bot.war_client.war_result_log(clan_tag=clan_tag)
        clan = await self.bot.getClan(clan_tag)
        for war in log:
            war_cog = self.bot.get_cog(name="War")
            embed = await war_cog.main_war_page(war=war, clan=clan)
            await ctx.channel.send(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))