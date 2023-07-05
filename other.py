
import contextlib
import disnake
from disnake.ext import commands
import time
from CustomClasses.CustomBot import CustomClient
import io
from PIL import Image, ImageDraw, ImageFont
from utils.components import create_components
import openai
import os
from main import check_commands

openai.api_key = os.getenv("OPENAI_API_KEY")
class ChatBot:
    def __init__(self, system=""):
        self.system = system
        self.messages = []
        if self.system:
            self.messages.append({"role": "system", "content": system})

    def __call__(self, message):
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self):
        completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.messages)
        # Uncomment this to print out token usage each time, e.g.
        # {"completion_tokens": 86, "prompt_tokens": 26, "total_tokens": 112}
        # print(completion.usage)
        return completion.choices[0].message.content

class misc(commands.Cog, name="Other"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.up = time.time()

    async def auto_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]


    @commands.slash_command(name="role-users", description="Get a list of users in a role")
    async def roleusers(self, ctx, role: disnake.Role):
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
        if text != "":
            embed = disnake.Embed(title=f"{len(role.members)} Users in {role.name}", description=text, color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)
        current_page = 0
        await ctx.send(embed=embeds[0], components=create_components(current_page, embeds, True))

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
    async def stat(self, ctx):
        uptime = time.time() - self.up
        uptime = time.strftime("%H hours %M minutes %S seconds", time.gmtime(uptime))
        me = self.bot.user.mention

        num_clans = await self.bot.clan_db.count_documents({})
        num_players = await self.bot.player_stats.count_documents({})
        num_tickets = await self.bot.open_tickets.count_documents({})

        inservers = len(self.bot.guilds)
        members = sum(guild.member_count - 1 for guild in self.bot.guilds)
        embed = disnake.Embed(title=f'{self.bot.user.name} Stats',
                              description=f"<:bot:862911608140333086> Bot: {me}\n" +
                                          f"<:discord:840749695466864650> Discord Api Ping: {round(self.bot.latency * 1000, 2)} ms\n" +
                                          f"<:server:863148364006031422> In {str(inservers)} servers\n" +
                                          f"<a:num:863149480819949568> Watching {members} users\n" +
                                          f"🕐 Uptime: {uptime}\n"
                                          f"Tracking {num_clans} clans\n"
                                          f"Tracking {num_players} players\n"
                                          f"{num_tickets} tickets opened\n",
                              color=disnake.Color.green())

        page_buttons = [
            disnake.ui.Button(label="Bot Invite", style=disnake.ButtonStyle.url, url="https://discord.com/api/oauth2/authorize?client_id=824653933347209227&permissions=8&scope=bot%20applications.commands"),
            disnake.ui.Button(label="Support Server", style=disnake.ButtonStyle.url, url="https://discord.gg/gChZm3XCrS"),
        ]
        buttons = disnake.ui.ActionRow()
        for button in page_buttons:
            buttons.append_item(button)
        await ctx.send(embed=embed, components=[buttons])


    def ping_embed(self):
        cocping = self.bot.coc_client.http.stats.get_all_average()
        ping_text = ""
        for endpoint, ping in cocping.items():
            ping_text += f"- `{endpoint} - {round(ping, 2)}ms`\n"
        return disnake.Embed(title="COC Api Ping by Endpoint", description=ping_text, color=disnake.Color.green())


    @commands.slash_command(name="summary")
    async def summary(self, ctx: disnake.ApplicationCommandInteraction, num_messages: int = 100):
        await ctx.response.defer(ephemeral=True)
        channel: disnake.TextChannel = ctx.channel
        message_text = "Please summarize this conversation:\n"
        try:
            messages = await channel.history(limit=num_messages).flatten()
        except:
            messages = []
        if not messages:
            return await ctx.edit_original_message(content="I don't have permission to view this channel")
        for message in reversed(messages):
            if message.webhook_id is None and message.author.bot:
                continue
            if message.content == "":
                continue
            if len(message_text) + len(f"{message.author.display_name} said: {message.content}\n") > 4000:
                continue
            message_text += f"{message.author.display_name} said: {message.content}\n"
        magicbot = ChatBot(
            f"You are a chatbot that helps summarize conversations. Summarize using only bullet points. Use up to 25 bullet points.")
        message = magicbot(message_text)

        await ctx.edit_original_message(
            content=f"Summary of the last {num_messages} messages in {channel.name}:\n {message}")


    @commands.slash_command(name="pepe",
                            description="Fun Command. Create a pepe holding a sign w/ text.")
    async def createPFP(self, ctx, sign_text: str, hidden: str = commands.Param(choices=["Yes", "No"])):
        """
            Parameters
            ----------
            sign_text: Text to write on sign (up to 25 char)
            hidden : If yes, message will be visible only to you
        """
        size = 40
        if len(sign_text) > 25:
            return await ctx.send("Too long, sorry :/")

        if len(sign_text) >= 11:
            size = 30

        if len(sign_text) > 14:
            size = 23

        if len(sign_text) > 19:
            size = 16

        back = Image.open("Other/pepesign.png")

        width = 250
        height = 250
        font = ImageFont.truetype("Other/pepefont.ttf", size)
        draw = ImageDraw.Draw(back)

        draw.text(((width / 2) - 5, 55), sign_text, anchor="mm", fill=(0, 0, 0), font=font)

        temp = io.BytesIO()
        back.save(temp, format="png")

        temp.seek(0)
        file = disnake.File(fp=temp, filename="filename.png")

        if hidden == "Yes":
            await ctx.send(content="Save image or copy link & send wherever you like :)", file=file, ephemeral=True)
        else:
            await ctx.send(file=file)

    @commands.slash_command(name="faq", description="Frequently Asked Questions")
    async def faq(self, ctx: disnake.ApplicationCommandInteraction, question=None):
        await ctx.response.defer()
        q_n_a = await self.parse_faq()
        if question not in q_n_a:
            embed = disnake.Embed(description="Question not found",
                                  color=disnake.Color.red())
            await ctx.edit_original_message(embed=embed)
        if question is not None:
            embed = disnake.Embed(title=f"**{question}**", description=q_n_a[question],
                                  color=disnake.Color.green())
            await ctx.edit_original_message(embed=embed)
        else:
            embeds = []
            menu_options = []
            for spot, (question, answer) in enumerate(q_n_a.items()):
                embed = disnake.Embed(title=f"**{question}**", description=answer,
                                      color=disnake.Color.green())
                embeds.append(embed)
                menu_options.append(disnake.SelectOption(label=f"{question.replace('`', '')}", value=f"{spot}"))

            stat_select = disnake.ui.Select(options=menu_options, placeholder="FAQ's", max_values=1)
            st = disnake.ui.ActionRow()
            st.append_item(stat_select)
            faq_menu = [st]

            await ctx.edit_original_message(embed=embeds[0], components=faq_menu)
            msg = await ctx.original_message()

            def check(res: disnake.MessageInteraction):
                return res.message.id == msg.id

            while True:
                try:
                    res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
                except:
                    try:
                        await ctx.edit_original_message(components=[])
                    except:
                        pass
                    break

                await res.response.defer()
                await res.edit_original_message(embed=embeds[int(res.values[0])])

    @commands.slash_command(name="level-card", description="Set custom colors & image for level card")
    async def level_card(self, ctx: disnake.ApplicationCommandInteraction, background_image: disnake.Attachment = None, reset = commands.Param(default=None, choices=["True"])):
        await ctx.response.defer(ephemeral=True)
        custom = await self.bot.level_cards.find_one({"user_id": ctx.author.id})
        if reset is None:
            background_image = await permanent_image(bot=self.bot, url=background_image.url)
        else:
            background_image = None
        if custom is not None:
            await self.bot.level_cards.update_one({"user_id" : ctx.user.id}, {"$set" : {"background_image" : background_image}})
        else:
            await self.bot.level_cards.insert_one({"user_id" : ctx.user.id, "background_image" : background_image})

        await ctx.send(content=f"Image set to {background_image}", ephemeral=True)


    @commands.slash_command(name="custom-bot", description="Create your custom bot")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def custom_bot(self, ctx: disnake.ApplicationCommandInteraction, bot_token: str):
        if not self.bot.user.public_flags.verified_bot:
            return await ctx.send("Must run this command on the main ClashKing bot.")
        r = await self.bot.credentials.find_one({"user": ctx.author.id})
        if r is not None:
            return await ctx.send("You have already created a custom bot.")
        server = await self.bot.fetch_guild(923764211845312533)
        try:
            server_member = await server.fetch_member(ctx.author.id)
        except:
            if ctx.author.id != self.bot.owner.id:
                return await ctx.send("Must be a part of the support server")
            else:
                server_member = await server.fetch_member(self.bot.owner.id)

        has_premium = disnake.utils.get(server_member.roles, id=1018316361241477212)

        if ctx.author.id == self.bot.owner.id:
            has_premium = True
        if has_premium:
            return await ctx.send("Must be a premium bot supporter.")

        await self.bot.credentials.update_one({"user": ctx.author.id}, {"$set" : {
            "bot_token": bot_token,
            "bot_status": "",
            "server": ctx.guild.id,
            "user": ctx.author.id,
        }}, upsert=True)

        os.system(f"pm2 start main.py false true {bot_token} --interpreter=/usr/bin/python3")
        await ctx.send(content=f"Creating your custom bot!")





    '''@commands.Cog.listener()
    async def on_connect(self):
        custom_commands = self.bot.custom_commands.find({})
        for command in await custom_commands.to_list(length=10000):
            name = command.get("name")
            desc = command.get("description")
            guild = command.get("guild")
            type = command.get("type")
            command = disnake.APISlashCommand(name=name, description=desc)
            command.add_option(name=type, required=True, autocomplete=True)
            try:
                await self.bot.create_guild_command(guild_id=guild, application_command=command)
            except:
                pass

    @commands.slash_command(name="custom-command", description="Create a custom command")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def custom_command(self, ctx: disnake.ApplicationCommandInteraction, command_name: str, description: str,
                             custom_embed: str, type=commands.Param(choices=["clan"]), refresh_button = commands.Param(default="False", choices=["True"])):
        command_name: str = command_name.replace(" ", "-")
        await ctx.response.defer(ephemeral=True)
        result = await self.bot.custom_commands.find_one({"$and": [{"guild": ctx.guild.id}, {"name": command_name.lower()}]})
        if result is not None:
            return await ctx.send(content="Cannot name command after an already existing command")
        command_name = command_name.lower()
        command = disnake.APISlashCommand(name=command_name, description=description)
        command.add_option(name=type, required=True, autocomplete=True)
        await self.bot.custom_commands.insert_one({
            "name": command_name,
            "description": description,
            "embed_data": custom_embed,
            "type": type,
            "guild": ctx.guild_id,
            "refresh" : (refresh_button == "True")
        })
        command = await self.bot.create_guild_command(guild_id=ctx.guild_id, application_command=command)
        await ctx.send(f"</{command}:{command.id}> created!")

    @commands.slash_command(name="command-remove", description="Remove a custom command")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def remove_command(self, ctx: disnake.ApplicationCommandInteraction, command_name: str):
        await ctx.response.defer(ephemeral=True)
        guild_command = self.bot.get_guild_command_named(guild_id=ctx.guild.id, name=command_name.lower())
        if guild_command is None:
            return await ctx.send("Command not found")
        await self.bot.delete_guild_command(guild_id=ctx.guild_id, command_id=guild_command.id)
        await self.bot.custom_commands.delete_one({
            "name": command_name,
            "guild": ctx.guild_id
        })
        await ctx.send(f"Command removed!")

    @commands.Cog.listener()
    async def on_application_command(self, ctx: disnake.ApplicationCommandInteraction):
        command = ctx.data.name.split(" ")[0]
        result = await self.bot.custom_commands.find_one({"$and": [{"guild": ctx.guild.id}, {"name": command}]})
        if result is not None:
            await ctx.response.defer()
            type = result.get("type")
            query = ctx.filled_options[type]
            if type == "clan":
                clan = await self.bot.getClan(query)
            embed_data = result.get("embed_data")
            refresh = result.get("refresh")
            if refresh:
                buttons = disnake.ui.ActionRow()
                buttons.append_item(disnake.ui.Button(
                    label="", emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f"{command}_{clan.tag}"))
            else:
                buttons = []
            embed = await self.bot.parse_to_embed(custom_json=embed_data, clan=clan)
            await ctx.edit_original_message(embed=embed, components=buttons)

    @commands.Cog.listener()
    async def on_application_command_autocomplete(self, ctx: disnake.ApplicationCommandInteraction):
        command = ctx.data.name
        result = await self.bot.custom_commands.find_one({"$and": [{"guild": ctx.guild.id}, {"name": command}]})
        if result is not None:
            command_type = result.get("type")
            query = ctx.filled_options[command_type]
            choices = await self.auto_clan(ctx=ctx, query=query)
            await ctx.response.autocomplete(choices=choices)'''


    '''
    @commands.slash_command(name="custom-bot", description="Create your custom bot")
    async def custom_bot(self, ctx: disnake.ApplicationCommandInteraction, bot_token: str, bot_name: str, profile_picture: disnake.Attachment):
        r = await self.bot.credentials.find_one({"user" : ctx.author.id})
        if r is not None:
            return await ctx.send("You have already created a custom bot.")
        server = await self.bot.fetch_guild(923764211845312533)
        try:
            server_member = await server.fetch_member(ctx.author.id)
        except:
            if ctx.author.id != self.bot.owner.id:
                return await ctx.send("Must be a part of the support server")
            else:
                server_member = await server.fetch_member(self.bot.owner.id)
        has_legend = disnake.utils.get(server_member.roles, id=1035067240149684308)
        has_titan = disnake.utils.get(server_member.roles, id=1035066857109061646)

        if ctx.author.id == self.bot.owner.id:
            has_legend = True
        if has_legend is None and has_titan is None:
            return await ctx.send("Must be a titan or legend tier bot supporter.")

        await ctx.send(content=f"Creating your custom bot!")
        instance, password = self.bot.linode_client.linode.instance_create(ltype="g6-nanode-1", region="us-central", image="private/18031365")
        ip = instance.ipv4[0]
        server_id = ctx.guild.id

        await self.bot.credentials.insert_one({
            "bot_name" : bot_name,
            "bot_token" : bot_token,
            "bot_status" : "",
            "bot_profile_pic" : profile_picture.url,
            "ip_address" : ip,
            "server" : server_id,
            "user" : ctx.author.id,
            "password" : password
        })

        await asyncio.sleep(360)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, 22))

        session = Session()
        session.handshake(sock)
        session.userauth_password('root', password)

        channel = session.open_session()
        channel.execute('cd MagicBot')
        channel.execute('pm2 start main.py --interpreter=/usr/bin/python3')
    '''

    async def parse_faq(self):
        faq_channel = await self.bot.fetch_channel(self.bot.FAQ_CHANNEL_ID)
        q_n_a = {}
        async for message in faq_channel.history(limit=25):
            split_content = message.content.split("**")
            for count, content in enumerate(split_content):
                if "?" in content:
                    q_n_a[content] = split_content[count+1]
        return q_n_a

    @faq.autocomplete("question")
    async def faq_question(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        q_n_a = await self.parse_faq()
        questions = []
        for question, answer in q_n_a.items():
            if query.lower() in question.lower():
                questions.append(question[0:99])
        return questions





def setup(bot: CustomClient):
    bot.add_cog(misc(bot))