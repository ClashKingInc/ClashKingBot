from disnake.ext import commands
from classes.bot import CustomClient
from background.logs.events import reminder_ee
from commands.reminders.send import war_reminder


class RemindersLog(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.reminder_ee = reminder_ee
        self.reminder_ee.on("war", self.war_reminder_event)


    async def war_reminder_event(self, event):
        await war_reminder(bot=self.bot, event=event)


def setup(bot: CustomClient):
    bot.add_cog(RemindersLog(bot))