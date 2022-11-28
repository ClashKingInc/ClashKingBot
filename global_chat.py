import datetime
import aiohttp
import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from main import check_commands
from urlextract import URLExtract
extractor = URLExtract()
import spacy
from profanity_filter import ProfanityFilter
import asyncio

staff_webhook = 0
class GlobalChat(commands.Cog, name="Global Chat"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot:
            return
        if message.channel.id in self.bot.global_channels:
            if message.author.id in self.bot.banned_global:
                return
            #self.bot.last_message[message.author.id] = int(datetime.datetime.utcnow().timestamp())

            urls = extractor.find_urls(message.content)
            for url in urls:
                if "discord.gg" not in url and "tenor" not in url and "gif" not in url and "giphy" not in url:
                    message.content = message.content.replace(url, "")

            nlp = spacy.load('en')
            profanity_filter = ProfanityFilter(nlps={'en': nlp})  # reuse spacy Language (optional)
            nlp.add_pipe(profanity_filter.spacy_component, last=True)

            message.content = profanity_filter.censor(message.content)
            if message.content == "" and message.attachments == [] and message.stickers == []:
                return
            mods = [633662639318237184, 706149153431879760, 161053630038802433]
            try:
                msg_id = message.reference.message_id
                rep = await message.channel.fetch_message(msg_id)
                message.content = f"> {rep.content} - {str(rep.author)}\n{message.content}"
            except:
                pass

            async def webhook_task(channel, message: disnake.Message):
                async def send_web(webhook):
                    files = [await attachment.to_file() for attachment in message.attachments]
                    files += [await sticker.to_file() for sticker in message.stickers]
                    files = files[:10]

                    web_name = f"{str(message.author.name)} | {message.guild.name}"
                    if message.author.id in mods:
                        web_name = "⚙️" + web_name
                    web_name = web_name.replace("discord", "")
                    web_name = web_name.replace("Discord", "")
                    web_name = web_name.replace("clyde", "")
                    try:
                        if str(message.guild.explicit_content_filter) == "all_members":
                            await webhook.send(username=web_name[:80], avatar_url=message.author.display_avatar,
                                                    content=message.content, files=files,
                                                    allowed_mentions=disnake.AllowedMentions.none())
                        else:
                            if message.content != "":
                                await webhook.send(username=web_name[:80],
                                                        avatar_url=message.author.display_avatar,
                                                        content=message.content,
                                                        allowed_mentions=disnake.AllowedMentions.none())
                    except:
                        return None

                if self.bot.global_webhooks[channel] == "":
                    try:
                        glob_channel: disnake.TextChannel = self.bot.get_channel(channel)
                    except:
                        try:
                            glob_channel: disnake.TextChannel = await self.bot.fetch_channel(channel)
                        except (disnake.NotFound, disnake.Forbidden):
                            result = await self.bot.global_chat_db.find_one({"channel": channel})
                            await self.bot.global_chat_db.update_one({"server": result.get("server")}, {'$set': {"channel": None}})
                            self.bot.global_channels.remove(channel)
                            return
                    webhooks = await glob_channel.webhooks()
                    glob_webhook = None
                    for webhook in webhooks:
                        if webhook.name == "Global Chat":
                            glob_webhook = webhook
                            break
                    if glob_webhook is None:
                        try:
                            glob_webhook = await glob_channel.create_webhook(name="Global Chat", reason="Global Chat")
                        except:
                            return
                    self.bot.global_webhooks[channel] = glob_webhook.id
                    await send_web(glob_webhook)
                else:
                    try:
                        webhook = await self.bot.fetch_webhook(self.bot.global_webhooks[channel])
                        await send_web(webhook)
                    except:
                        self.bot.global_webhooks[channel] = ""

            tasks = []
            for channel in self.bot.global_channels:
                if message.channel.id == channel:
                    continue
                if channel is None:
                    continue
                task = asyncio.ensure_future(webhook_task(channel, message))
                tasks.append(task)
            await asyncio.gather(*tasks)

            if staff_webhook == 0:
                try:
                    staff_channel: disnake.TextChannel = self.bot.get_channel(1046572580200525894)
                except:
                    staff_channel: disnake.TextChannel = await self.bot.fetch_channel(1046572580200525894)
                webhooks = await staff_channel.webhooks()
                glob_webhook = None
                for webhook in webhooks:
                    glob_webhook = webhook
                    break
                if glob_webhook is None:
                    glob_webhook = await staff_channel.create_webhook(name="Staff Log", reason="Global Chat")
            else:
                glob_webhook = await self.bot.fetch_webhook(staff_webhook)
            files = [await attachment.to_file() for attachment in message.attachments]
            files += [await sticker.to_file() for sticker in message.stickers]
            files = files[:10]
            await glob_webhook.send(username="Staff Log", content=message.content + f"\nUser: `{str(message.author)}` | User_ID:`{message.author.id}`", files=files, allowed_mentions=disnake.AllowedMentions.none())




    @commands.slash_command(name="global-chat", description="Global Chat")
    async def global_chat(self, ctx):
        pass

    @global_chat.sub_command(name="channel", description="Set a channel for the bot global chat!")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def global_chat_channel(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, remove = commands.Param(default="False", choices=["True", "False"])):
        await ctx.response.defer()
        result = await self.bot.global_chat_db.find_one({"server" : ctx.guild.id})
        if result is None and remove == "True":
            return await ctx.edit_original_message("No global channel set up")
        elif remove == "True":
            await self.bot.global_chat_db.update_one({"server": ctx.guild.id}, {"$set" : {"channel": None}})
            embed = disnake.Embed(description="Global Chat removed.", color=disnake.Color.green())
            self.bot.global_channels.remove(channel.id)
            return await ctx.edit_original_message(embed=embed)
        if result is None:
            await self.bot.global_chat_db.insert_one({"server" : ctx.guild.id, "channel" : channel.id})
            embed = disnake.Embed(description=f"Global Chat set to {channel.mention}\n"
                                              f"**In order to have the best experience and show emojis, you will have to create your own webhook for the bot to use**\n"
                                              f"1. Go into your channel settings\n"
                                              f"2. Go to Integrations -> Webhooks\n"
                                              f"3. Create Webhook, *important*, set it's name to `Global Chat`\n"
                                              f"If you don't do this, the bot will create it's own webhook & will function normally but won't show emojis.")
        else:
            await self.bot.global_chat_db.update_one({"server" : ctx.guild.id}, {"$set": {"channel" : channel.id}})
            embed = disnake.Embed(description=f"Global Chat set to {channel.mention}")
        self.bot.global_channels.append(channel.id)

        async def webhook_task(channel, embed_):
            async def send_web(webhook, embed):
                try:
                    await webhook.send(username="ClashKing", avatar_url=self.bot.user.avatar.url,
                                       embed=embed,
                                       allowed_mentions=disnake.AllowedMentions.none())
                except:
                    return None

            if self.bot.global_webhooks[channel] == "":
                try:
                    glob_channel: disnake.TextChannel = self.bot.get_channel(channel)
                except:
                    try:
                        glob_channel: disnake.TextChannel = await self.bot.fetch_channel(channel)
                    except (disnake.NotFound, disnake.Forbidden):
                        result = await self.bot.global_chat_db.find_one({"channel": channel})
                        await self.bot.global_chat_db.update_one({"server": result.get("server")},
                                                                 {'$set': {"channel": None}})
                        self.bot.global_channels.remove(channel)
                        return
                webhooks = await glob_channel.webhooks()
                glob_webhook = None
                for webhook in webhooks:
                    if webhook.name == "Global Chat":
                        glob_webhook = webhook
                        break
                if glob_webhook is None:
                    try:
                        glob_webhook = await glob_channel.create_webhook(name="Global Chat", reason="Global Chat")
                    except:
                        return
                self.bot.global_webhooks[channel] = glob_webhook.id
                await send_web(glob_webhook, embed_)
            else:
                try:
                    webhook = await self.bot.fetch_webhook(self.bot.global_webhooks[channel])
                    await send_web(webhook, embed_)
                except:
                    self.bot.global_webhooks[channel] = ""

        tasks = []
        for channel in self.bot.global_channels:
            if channel is None:
                continue
            em = disnake.Embed(description=f"Everyone welcome {ctx.guild.name} to the global chat!", color=disnake.Color.green())
            em.set_image(url="https://cdn.discordapp.com/attachments/923767060977303552/1046920746636685342/unknown.png")
            task = asyncio.ensure_future(webhook_task(channel, em))
            tasks.append(task)
        await asyncio.gather(*tasks)
        await ctx.edit_original_message(embed=embed)

    @global_chat.sub_command(name="report", description="Report a user in the global chat")
    async def global_chat_report(self, ctx: disnake.ApplicationCommandInteraction, message_id: str):
        if not message_id.isdigit():
            return await ctx.send(content="Message id is invalid.", ephemeral=True)
        try:
            message: disnake.WebhookMessage = await ctx.channel.fetch_message(1046587237179076668)
        except:
            return await ctx.send(content="Message id is invalid.", ephemeral=True)
        if message.channel.id not in self.bot.global_channels:
            return await ctx.send(content="Message is not in a global chat channel.", ephemeral=True)
        user = message.author.display_name
        await ctx.response.defer()
        channel = await self.bot.fetch_channel(1046595439962636318)
        embed = disnake.Embed(description=f"Report from {str(ctx.author)}\n"
                                          f"{user.split('|')} - {message.content[0:100]}", color=disnake.Color.red())
        await channel.send(embed=embed)
        await ctx.edit_original_message(content="Report submitted!")

    @global_chat.sub_command(name="staff-strike", description="Staff Command. Give a user a strike.")
    @commands.check_any(commands.has_any_role(*[1034134693869797416, 923787651058901062]))
    async def global_chat_strike(self, ctx: disnake.ApplicationCommandInteraction, user_id : str):
        await ctx.response.defer()
        try:
            user_id = int(user_id)
            user = await self.bot.fetch_user(user_id)
        except:
            return await ctx.edit_original_message(content="Not a valid user")

        results = await self.bot.global_reports.find_one({"user" : user.id})
        if results is None:
            await self.bot.global_reports.insert_one({"user" : user.id, "strikes" : 1})
        else:
            await self.bot.global_reports.update_one({"user" : user.id}, {"$inc" : {"strikes" : 1}})
        await ctx.edit_original_message(f"Gave {str(user)} a strike")





def setup(bot: CustomClient):
    bot.add_cog(GlobalChat(bot))