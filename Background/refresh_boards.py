from disnake.ext import commands
import disnake
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from CommandsOld.buttons import basic_parser
from utils.discord_utils import get_webhook_for_channel
from Exceptions.CustomExceptions import MissingWebhookPerms

class RefreshBoards(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.refresh, 'interval', minutes=5)

    async def refresh(self):
        all_refresh_boards = await self.bot.button_store.find({"webhook_id" : {"$ne" : None}}).to_list(length=None)
        for board in all_refresh_boards:
            webhook_id = board.get("webhook_id")
            thread_id = board.get("thread_id")
            message_id = board.get("message_id")
            del board["webhook_id"]
            del board["thread_id"]
            del board["message_id"]
            embed = await basic_parser(bot=self.bot, result=board)
            try:
                webhook: disnake.Webhook = await self.bot.getch_webhook(webhook_id)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    if thread_id is None:
                        message = await webhook.send(embed=embed, wait=True)
                    else:
                        thread = await self.bot.getch_channel(thread_id)
                        message = await webhook.send(embed=embed, thread=thread, wait=True)
                    await self.bot.button_store.update_one({"button_id" : board.get("button_id")}, {"$set" : {"webhook_id" : webhook.id, "message_id" : message.id}})
                    continue

                if thread_id is not None:
                    thread = await self.bot.getch_channel(thread_id, raise_exception=True)
                    await webhook.edit_message(message_id, thread=thread, embed=embed)
                else:
                    await webhook.edit_message(message_id, embed=embed)

            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await self.bot.button_store.update_one({"button_id" : board.get("button_id")}, {"$set" : {"webhook_id" : None}})




def setup(bot: CustomClient):
    bot.add_cog(RefreshBoards(bot))