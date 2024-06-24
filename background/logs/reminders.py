from disnake.ext import commands

from background.logs.events import reminder_ee
from classes.bot import CustomClient
from commands.reminders.send import war_reminder


class RemindersLog(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.reminder_ee = reminder_ee
        self.reminder_ee.on('war', self.war_reminder_event)

        self.bot.scheduler.add_job(self.clan_capital_reminder_trigger, trigger="cron", args=["1 hr"], day_of_week="mon", hour=6, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_capital_reminder_trigger, trigger="cron", args=["2 hr"], day_of_week="mon", hour=5, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_capital_reminder_trigger, trigger="cron", args=["4 hr"], day_of_week="mon", hour=3, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_capital_reminder_trigger, trigger="cron", args=["6 hr"], day_of_week="mon", hour=1, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_capital_reminder_trigger, trigger="cron", args=["8 hr"], day_of_week="sun", hour=23, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_capital_reminder_trigger, trigger="cron", args=["12 hr"], day_of_week="sun", hour=19, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_capital_reminder_trigger, trigger="cron", args=["16 hr"], day_of_week="sun", hour=15, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_capital_reminder_trigger, trigger="cron", args=["24 hr"], day_of_week="sun", hour=7, misfire_grace_time=None)

        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["144 hr"], day=22, hour=8, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["120 hr"], day=23, hour=8, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["96 hr"], day=24, hour=8, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["72 hr"], day=25, hour=8, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["48 hr"], day=26, hour=8, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["36 hr"], day=26, hour=20, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["24 hr"], day=27, hour=8, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["12 hr"], day=27, hour=20, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["6 hr"], day=28, hour=2, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["4 hr"], day=28, hour=4, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["2 hr"], day=28, hour=6, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.clan_games_reminder_trigger, trigger="cron", args=["1 hr"], day=28, hour=7, misfire_grace_time=None)

        self.bot.scheduler.add_job(self.inactivity_reminder, trigger='interval', minutes=30, misfire_grace_time=None)
        self.bot.scheduler.add_job(self.roster_reminder, trigger='interval', minutes=2, misfire_grace_time=None)


    async def war_reminder_event(self, event):
        await war_reminder(bot=self.bot, event=event)


    async def clan_capital_reminder_trigger(self, time: str):
        pass


    async def legends_reminder_trigger(self, time: str):
        pass

    async def clan_games_reminder_trigger(self, time: str):
        pass


    async def inactivity_reminder(self):
        pass


    async def roster_reminder(self):
        pass


    async def personal_legend_reminder(self, event):
        pass

    async def personal_war_reminder(self, event):
        pass


def setup(bot: CustomClient):
    bot.add_cog(RemindersLog(bot))
