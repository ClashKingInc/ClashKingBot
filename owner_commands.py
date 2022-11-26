import coc
import disnake
from disnake.ext import commands
from datetime import datetime
clan_tags = ["#2P0JJQGUJ"]
known_streak = []
count = 0
list_size = 0
from utils.clash import weekend_timestamps
import asyncio
from CustomClasses.CustomBot import CustomClient
from pymongo import UpdateOne
from PIL import Image, ImageDraw, ImageFont
import io
from detecto import core, utils, visualize

import torch

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
        for member in guild.members:
            year = member.joined_at.year
            month = member.joined_at.month
            n_year = datetime.now().year
            n_month = datetime.now().month
            num_months = (n_year - year) * 12 + (n_month - month)
            if num_months >= 12:
                r = disnake.utils.get(ctx.guild.roles, id=1029249316981833748)
                if r not in member.roles:
                    await member.add_roles(*[r])
            elif num_months >= 9:
                r = disnake.utils.get(ctx.guild.roles, id=1029249365858062366)
                if r not in member.roles:
                    await member.add_roles(*[r])
            elif num_months >= 6:
                r = disnake.utils.get(ctx.guild.roles, id=1029249360178987018)
                if r not in member.roles:
                    await member.add_roles(*[r])
            elif num_months >= 3:
                r = disnake.utils.get(ctx.guild.roles, id=1029249480261906463)
                if r not in member.roles:
                    await member.add_roles(*[r])
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

    @commands.slash_command(name="clear_emojis", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def clear_emojis(self, ctx):
        await ctx.response.defer()
        BADGE_GUILDS = [1029631304817451078, 1029631182196977766, 1029631107240562689, 1029631144641183774,
                        1029629452403097651,
                        1029629694854828082, 1029629763087777862, 1029629811221610516, 1029629853017841754,
                        1029629905903833139,
                        1029629953907634286, 1029629992830783549, 1029630376911581255, 1029630455202455563,
                        1029630702125318144,
                        1029630796966932520, 1029630873588469760, 1029630918106824754, 1029630974025277470,
                        1029631012084396102]

        while len(BADGE_GUILDS):
            for guild in BADGE_GUILDS:
                guild = self.bot.get_guild(guild)
                emojis = guild.emojis
                if len(emojis) == 0:
                    BADGE_GUILDS.remove(guild.id)
                    print(f"{len(BADGE_GUILDS)} guilds left")
                    continue
                await guild.delete_emoji(emoji=emojis[-1])
                await asyncio.sleep(3)
                print(f"{guild.name} - {len(guild.emojis)} left")


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

    @commands.slash_command(name="create_icons", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def create_icons(self, ctx):
        await ctx.response.defer()

        text = ""
        for xnumber in range(51, 100):
            number = str(xnumber)
            #create blue numbers
            image = Image.open('poster/transparent.png')
            font = ImageFont.truetype("poster/Signika-Regular.TTF", 350)
            draw = ImageDraw.Draw(image)
            W, H = (450, 450)
            _, _, w, h = draw.textbbox((0, 0), number, font=font)
            draw.text(((W - w) / 2, (H - h - 80) / 2), number, font=font, fill='#89CFF0')
            temp = io.BytesIO()
            image.save(temp, format="png")
            temp.seek(0)
            # file = disnake.File(fp=temp, filename="filename.png")
            server = await self.bot.fetch_guild(1042635521890992158)
            emoji = await server.create_custom_emoji(name=f"{number}_", image=temp.read())
            text += f"<:{emoji.name}:{emoji.id}> "

            #create white letters
            image = Image.open('poster/transparent.png')
            font = ImageFont.truetype("poster/Signika-Regular.TTF", 350)
            draw = ImageDraw.Draw(image)
            W, H = (450, 450)
            _, _, w, h = draw.textbbox((0, 0), number, font=font)
            draw.text(((W - w) / 2, (H - h - 80) / 2), number, font=font, fill='#FFFFFF')
            temp = io.BytesIO()
            image.save(temp, format="png")
            temp.seek(0)
            # file = disnake.File(fp=temp, filename="filename.png")
            server = await self.bot.fetch_guild(1042635651562086430)
            emoji = await server.create_custom_emoji(name=f"{number}_", image=temp.read())
            text += f"<:{emoji.name}:{emoji.id}> "

            #gold number emojis
            image = Image.open('poster/transparent.png')
            font = ImageFont.truetype("poster/Signika-Regular.TTF", 350)
            draw = ImageDraw.Draw(image)
            W, H = (450, 450)
            _, _, w, h = draw.textbbox((0, 0), number, font=font)
            draw.text(((W - w) / 2, (H - h - 80) / 2), number, font=font, fill='#FFD700')
            temp = io.BytesIO()
            image.save(temp, format="png")
            temp.seek(0)
            # file = disnake.File(fp=temp, filename="filename.png")
            server = await self.bot.fetch_guild(1042635608088125491)
            emoji = await server.create_custom_emoji(name=f"{number}_", image=temp.read())
            text += f"<:{emoji.name}:{emoji.id}> "

            await asyncio.sleep(delay=60)

        await ctx.edit_original_message(content=text)






def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))