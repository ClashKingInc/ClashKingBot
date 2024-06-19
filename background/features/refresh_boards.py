import disnake

from disnake.ext import commands
from classes.bot import CustomClient
from utility.discord_utils import get_webhook_for_channel
from exceptions.CustomExceptions import MissingWebhookPerms
from commands.components.buttons import button_logic


class RefreshBoards(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.scheduler.add_job(self.refresh, "interval", minutes=5)

    async def refresh(self):
        if not self.bot.user.public_flags.verified_bot:  # only main bot for now
            return
        all_refresh_boards = await self.bot.button_store.find({"webhook_id": {"$ne": None}}).to_list(length=None)
        for board in all_refresh_boards:
            webhook_id = board.get("webhook_id")
            thread_id = board.get("thread_id")
            message_id = board.get("message_id")
            button_id = board.get("button_id")
            guild = await self.bot.getch_guild(board.get("server"))
            embed = await button_logic(button_data=button_id, bot=self.bot, guild=guild)
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
                    await self.bot.button_store.update_one(
                        {"_id": board.get("_id")},
                        {"$set": {"webhook_id": webhook.id, "message_id": message.id}},
                    )
                    continue

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

            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await self.bot.button_store.update_one({"_id": board.get("_id")}, {"$set": {"webhook_id": None}})


def setup(bot: CustomClient):
    bot.add_cog(RefreshBoards(bot))
