import aiohttp
import disnake
import io
import time

from classes.bot import CustomClient
from discord import convert, autocomplete
from disnake.ext import commands
from exceptions.CustomExceptions import MessageException
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import urlencode
from utility.components import create_components
from utility.discord_utils import interaction_handler

class misc(commands.Cog, name="Other"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.up = time.time()


    @commands.slash_command(name="role-users", description="Get a list of users in a role")
    async def roleusers(self, ctx: disnake.ApplicationCommandInteraction, role: disnake.Role):
        await ctx.response.defer()
        if not ctx.guild.chunked:
            if ctx.guild.id not in self.bot.STARTED_CHUNK:
                await ctx.guild.chunk(cache=True)
            else:
                self.bot.STARTED_CHUNK.add(ctx.guild.id)
        embeds = []
        text = ""
        num = 0
        for member in role.members:
            text += f"{member.display_name} [{member.mention}]\n"
            num += 1
            if num == 25:
                embed = disnake.Embed(title=f"{len(role.members)} Users in {role.name}", description=text, color=disnake.Color.green())
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                embeds.append(embed)
                num = 0
                text = ""

        if not embeds and text == "":
            text = "No Members in Role"
        if text != "":
            embed = disnake.Embed(title=f"{len(role.members)} Users in {role.name}", description=text, color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)
        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))

        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)

            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break
            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page], components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page], components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)



    @commands.slash_command(name="bot-stats", description="Stats about bots uptime & ping")
    async def stat(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        uptime = time.time() - self.up
        uptime = time.strftime("%H hours %M minutes %S seconds", time.gmtime(uptime))
        me = self.bot.user.mention

        num_clans = await self.bot.clan_db.count_documents({})
        num_tickets = await self.bot.open_tickets.count_documents({})
        inservers = len(self.bot.guilds)
        chunked_guilds = len([g for g in self.bot.guilds if g.chunked])
        members = sum(guild.member_count - 1 for guild in self.bot.guilds)
        if ctx.guild.shard_id in [1, 2]:
            cluster_id = 1
        elif ctx.guild.shard_id in [3, 4]:
            cluster_id = 2
        else:
            cluster_id = 3
        embed = disnake.Embed(title=f'{self.bot.user.name} Stats',
                              description=f"<:bot:862911608140333086> Bot: {me}\n" +
                                          f"<:discord:840749695466864650> Discord Api Ping: {round(self.bot.latency * 1000, 2)} ms\n" +
                                          f"<:server:863148364006031422> In {str(inservers)} servers (Cluster {cluster_id})\n" +
                                          f"<:server:863148364006031422> {str(chunked_guilds)} servers loaded\n" +
                                          f"<:server:863148364006031422> Shard Count: {self.bot.shard_count}\n" +
                                          f"<:server:863148364006031422> You are on shard {ctx.guild.shard_id}\n" +
                                          f"<a:num:863149480819949568> Watching {members} users\n" +
                                          f"🕐 Uptime: {uptime}\n"
                                          f"Tracking {num_clans} clans\n"
                                          f"{num_tickets} tickets opened\n",
                              color=disnake.Color.green())



        page_buttons = [
            disnake.ui.Button(label="Bot Invite", style=disnake.ButtonStyle.url, url="https://discord.com/api/oauth2/authorize?client_id=824653933347209227&permissions=8&scope=bot%20applications.commands"),
            disnake.ui.Button(label="Support Server", style=disnake.ButtonStyle.url, url="https://discord.gg/gChZm3XCrS"),
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)
        await ctx.edit_original_message(embed=embed, components=[buttons])


    @commands.slash_command(name="debug", description="Debug issues on your server")
    async def debug(self, ctx: disnake.ApplicationCommandInteraction,
                    server: disnake.Guild = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server)):
        server = server or ctx.guild
        pass


    @commands.slash_command(name="pepe", description="Fun Command. Create a pepe holding a sign w/ text.")
    async def create_pepe(self, ctx, sign_text: str, hidden: str = commands.Param(choices=["Yes", "No"])):
        """
            Parameters
            ----------
            sign_text: Text to write on sign (up to 40 char)
            hidden : If yes, message will be visible only to you
        """

        text_size = 40
        if len(sign_text) >= 11:
            text_size = int((-0.43 * len(sign_text)) + 36)
        if text_size < 5:
            raise MessageException("Message too long, sorry :/")
        back = Image.open("commands/other/pepesign.png")

        width = 250
        font = ImageFont.truetype("commands/other/pepefont.ttf", text_size)
        draw = ImageDraw.Draw(back)

        def split_text(text, max_length):
            words = text.split()
            current_line = ""
            lines = []

            for word in words:
                if len(current_line + ' ' + word) > max_length:
                    lines.append(current_line)
                    current_line = word
                else:
                    if current_line:
                        current_line += ' '
                    current_line += word

            if current_line:
                lines.append(current_line)

            return '\n'.join(lines)

        characters_per_line = int(0.35 * len(sign_text) + 5.88)
        sign_text = split_text(sign_text, characters_per_line)
        height = 55
        height = height - (2 * sign_text.count("\n"))
        draw.text(((width / 2) - 5, height), sign_text, anchor="mm", fill=(0, 0, 0), font=font)

        temp = io.BytesIO()
        back.save(temp, format="png")

        temp.seek(0)
        file = disnake.File(fp=temp, filename="filename.png")

        if hidden == "Yes":
            await ctx.send(content="Save image or copy link & send wherever you like :)", file=file, ephemeral=True)
        else:
            try:
                await ctx.send("Done", ephemeral=True)
                await ctx.channel.send(file=file)
            except Exception:
                await ctx.send(file=file)


    @commands.slash_command(name="fankit", description="View images from the fankit")
    async def fankit(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        await ctx.response.defer()

        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild.id)

        async with aiohttp.ClientSession() as session:
            async with session.get("https://fankit.supercell.com/api/assets/search/338?q={query}&limit=25&page=1&requestnewflag=true&order=RELEVANCE".format(query=query)) as response:
                data = await response.json()

        data = data.get("data", [])

        def create_embed(data_item):
            embed = disnake.Embed(title=data_item["title"], color=embed_color)
            embed.set_image(url=data_item["preview_url"])
            return embed

        def create_buttons(index, total):
            buttons = [
                disnake.ui.Button(label="Previous", style=disnake.ButtonStyle.primary, custom_id="prev", disabled=(index == 0)),
                disnake.ui.Button(label="Next", style=disnake.ButtonStyle.primary, custom_id="next", disabled=(index == total - 1)),
                disnake.ui.Button(label="Download", style=disnake.ButtonStyle.url, url=data[index]["preview_url"]),
                disnake.ui.Button(label="Add as Emoji", style=disnake.ButtonStyle.secondary, custom_id="add_emoji")
            ]
            return buttons

        index = 0
        message = await ctx.send(embed=create_embed(data[index]), components=create_buttons(index, len(data)))

        while True:
            interaction: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, msg=message)
            if interaction.component.custom_id == "prev":
                index = max(0, index - 1)
            elif interaction.component.custom_id == "next":
                index = min(len(data) - 1, index + 1)
            elif interaction.component.custom_id == "download":
                await interaction.followup.send(data[index]["preview_url"], ephemeral=True)
            elif interaction.component.custom_id == "add_emoji":
                if interaction.user.guild_permissions.manage_emojis_and_stickers:
                    url = data[index]["generic_url"].replace("{width}", "250")
                    title = data[index]["title"][:32]

                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as response:
                            image_data = await response.read()

                    guild = ctx.guild
                    emoji = await guild.create_custom_emoji(name=title, image=image_data)
                    await ctx.followup.send(f"Emoji created: {emoji}", ephemeral=True)
                else:
                    await ctx.followup.send("You do not have permission to add emojis.", ephemeral=True)

            await interaction.edit_original_message(embed=create_embed(data[index]), components=create_buttons(index, len(data)))


    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.content[:2] == "-/" and self.bot.user.public_flags.verified_bot:
            try:
                command = self.bot.get_global_command_named(name=message.content.replace("-/", "").split(" ")[0])
                await message.channel.send(f"</{message.content.replace('-/', '')}:{command.id}>")
            except Exception:
                pass
        elif message.channel.id == 1204977978438848522 and self.bot.user.mention in message.content:
            query = message.content.replace(self.bot.user.mention, "")
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.gitbook.com/v1/spaces/iSJhS5UxZkjOhR5eSxhS/search/ask?{urlencode({"query": query})}') as response:
                    if response.status == 200:
                        answer = await response.json()
                    else:
                        answer = None
            if answer is not None:
                try:
                    await message.reply(content=answer.get("answer").get("text"))
                except Exception:
                    await message.reply(content="I dont have the answer to that yet, but you can take a look at my docs <https://docs.clashking.xyz>")











def setup(bot: CustomClient):
    bot.add_cog(misc(bot))