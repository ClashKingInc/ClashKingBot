import disnake
import pendulum as pend
from disnake.ext import commands

from classes.bot import CustomClient
from commands.components.buttons import button_logic
from exceptions.CustomExceptions import MissingWebhookPerms
from utility.discord_utils import get_webhook_for_channel


class RefreshBoards(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.scheduler.add_job(self.refresh, 'interval', minutes=30, misfire_grace_time=None)
        self.position_check: bool = False
        self.bot.scheduler.add_job(self.set_check_state, 'interval', hours=12, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.post, 'cron', hour=5, minute=0, misfire_grace_time=None)


    async def set_check_state(self):
        self.position_check = True


    async def refresh(self):
        all_refresh_boards = await self.bot.autoboards.find({"$and" : [{'webhook_id': {'$ne': None}}, {"type" : "refresh"}]}).to_list(length=None)
        for board in all_refresh_boards:

            webhook_id = board.get('webhook_id')
            thread_id = board.get('thread_id')
            message_id = board.get('message_id')
            button_id = board.get('button_id')
            '''if board.get('server_id') not in self.bot.OUR_GUILDS:
                continue'''
            guild = await self.bot.getch_guild(board.get('server_id'))
            embed, components = await button_logic(button_data=button_id, bot=self.bot, guild=guild, locale=disnake.Locale(board.get('locale')))
            if embed is None:
                continue

            try:
                webhook: disnake.Webhook = await self.bot.getch_webhook(webhook_id)

                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    if thread_id is None:
                        if isinstance(embed, list):
                            message = await webhook.send(embeds=embed, wait=True)
                        else:
                            message = await webhook.send(embed=embed, wait=True)
                    else:
                        thread = await self.bot.getch_channel(thread_id)
                        if isinstance(embed, list):
                            message = await webhook.send(embeds=embed, thread=thread, wait=True)
                        else:
                            message = await webhook.send(embed=embed, thread=thread, wait=True)
                    await self.bot.autoboards.update_one(
                        {'_id': board.get('_id')},
                        {'$set': {'webhook_id': webhook.id, 'message_id': message.id}},
                    )
                    continue

                thread = None
                if thread_id is not None:
                    thread = await self.bot.getch_channel(thread_id, raise_exception=True)
                    if isinstance(embed, list):
                        await webhook.edit_message(message_id, thread=thread, embeds=embed)
                    else:
                        await webhook.edit_message(message_id, thread=thread, embed=embed)
                else:
                    if isinstance(embed, list):
                        await webhook.edit_message(message_id, embeds=embed)
                    else:
                        await webhook.edit_message(message_id, embed=embed)

                if self.position_check:
                    channel = webhook.channel
                    if thread is not None:
                        channel = thread
                    messages = await channel.history(limit=15).flatten()
                    found = False
                    for position, message in enumerate(messages, start=1):
                        if message.id == message_id:
                            found = True
                            break
                    if not found:
                        raise MissingWebhookPerms
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await self.bot.autoboards.update_one({'_id': board.get('_id')}, {'$set': {'webhook_id': None}})

        self.position_check = False


    async def post(self):
        print("here")
        current_day_name = pend.now(tz=pend.UTC).format('dddd').lower()
        day_set = {current_day_name}

        print(day_set)

        all_post_boards = await self.bot.autoboards.find({"$and" : [{'webhook_id': {'$ne': None}}, {"type" : "post"}]}).to_list(length=None)
        for board in all_post_boards:
            webhook_id = board.get('webhook_id')
            thread_id = board.get('thread_id')
            button_id = board.get('button_id')
            days = board.get('days', [])
            '''if board.get('server_id') not in self.bot.OUR_GUILDS:
                continue'''
            guild = await self.bot.getch_guild(board.get('server_id'))
            if guild is None:
                continue

            days = set(days)
            if days.isdisjoint(day_set):
                continue

            embed, components = await button_logic(button_data=button_id, bot=self.bot, guild=guild, locale=disnake.Locale(board.get('locale')))
            if embed is None:
                continue

            try:
                webhook: disnake.Webhook = await self.bot.getch_webhook(webhook_id)

                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await self.bot.autoboards.update_one(
                        {'_id': board.get('_id')},
                        {'$set': {'webhook_id': webhook.id}},
                    )

                if thread_id is None:
                    if isinstance(embed, list):
                        await webhook.send(embeds=embed)
                    else:
                        await webhook.send(embed=embed)
                else:
                    thread = await self.bot.getch_channel(thread_id, raise_exception=True)
                    if isinstance(embed, list):
                        await webhook.send(embeds=embed, thread=thread)
                    else:
                        await webhook.send(embed=embed, thread=thread)

            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await self.bot.autoboards.update_one({'_id': board.get('_id')}, {'$set': {'webhook_id': None}})


def setup(bot: CustomClient):
    bot.add_cog(RefreshBoards(bot))
