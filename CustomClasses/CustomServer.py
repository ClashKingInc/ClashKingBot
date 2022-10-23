
import disnake
from CustomClasses.CustomBot import CustomClient

class CustomServer():
    def __init__(self, guild: disnake.Guild, bot: CustomClient):
        self.guild = guild
        self.bot = bot
        self.server = None
        self.clans = []

    @property
    async def leadership_eval_choice(self):
        server = await self.bot.server_db.find_one({"server": self.guild.id})
        eval_option = server.get("leadership_eval")
        return True if eval_option is None else eval_option

    @property
    async def nickname_choice(self):
        server = await self.bot.server_db.find_one({"server": self.guild.id})
        auto_nick_type = server.get("auto_nick")
        return "Clan Abbreviations" if auto_nick_type is None else auto_nick_type

    @property
    async def family_label(self):
        server = await self.bot.server_db.find_one({"server": self.guild.id})
        family_label = server.get("family_label")
        return "" if family_label is None else family_label

    async def change_leadership_eval(self, option: bool):
        await self.bot.server_db.update_one({"server": self.guild.id}, {"$set" : {"leadership_eval" : option}})

    async def change_auto_nickname(self, type: str):
        await self.bot.server_db.update_one({"server": self.guild.id}, {"$set" : {"auto_nick" : type}})

    async def set_family_label(self, label: str):
        await self.bot.server_db.update_one({"server": self.guild.id}, {"$set" : {"family_label" : label}})


    @property
    async def clan_list(self):
        clan_tags = []
        tracked = self.bot.clan_db.find({"server": self.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": self.guild.id})
        if limit == 0:
            return clan_tags
        for tClan in await tracked.to_list(length=limit):
            clan_tags.append(tClan.get("tag"))
        return clan_tags

    async def initialize_server(self, with_clans=True):
        self.server = await self.bot.server_db.find_one({"server": self.guild.id})
        if with_clans:
            tracked = self.bot.clan_db.find({"server": self.guild.id})
            limit = await self.bot.clan_db.count_documents(filter={"server": self.guild.id})
            for clan in await tracked.to_list(length=limit):
                self.clans.append(clan)

    @property
    def banlist_channel(self):
        banlist = self.server.get("banlist")
        return f"<#{banlist}>" if banlist is not None else banlist

    @property
    def clan_greeting(self):
        greeting = self.server.get("greeting")
        return f"Welcome to {self.guild.name}!" if greeting is None else greeting

    @property
    def leadership_eval(self):
        eval = self.server.get("leadership_eval")
        return "Off" if eval is None or eval is False else "On"

    @property
    def reddit_feed(self):
        reddit = self.server.get("reddit_feed")
        return f"<#{reddit}>" if reddit is not None else reddit

    @property
    def server_clans(self):
        return [ServerClan(clan, self.bot) for clan in self.clans]

    @property
    def reminders(self):
        return [clan.reminders for clan in self.server_clans]

class ServerClan():
    def __init__(self, clan_result, bot):
        self.clan_result = clan_result
        self.bot: CustomClient = bot

    @property
    def name(self):
        return self.clan_result.get("name")

    @property
    def tag(self):
        return self.clan_result.get("tag")

    @property
    def clan_channel(self):
        channel = self.clan_result.get("clanChannel")
        return f"<#{channel}>" if channel is not None else channel

    @property
    def member_role(self):
        role = self.clan_result.get("generalRole")
        return f"<@&{role}>" if role is not None else role

    @property
    def leader_role(self):
        role = self.clan_result.get("leaderRole")
        return f"<@&{role}>" if role is not None else role

    @property
    def join_log(self):
        channel = self.clan_result.get("joinlog")
        return f"<#{channel}>" if channel is not None else channel

    @property
    def capital_log(self):
        channel = self.clan_result.get("clan_capital")
        return f"<#{channel}>" if channel is not None else channel

    @property
    def war_log(self):
        channel = self.clan_result.get("war_log")
        return f"<#{channel}>" if channel is not None else channel

    @property
    async def legend_log(self):
        legend_log = self.clan_result.get("legend_log")
        if legend_log is None:
            return legend_log
        webhook = legend_log.get("webhook")
        thread = legend_log.get("thread")
        if webhook is None:
            return webhook
        if thread is not None:
            return f"<#{thread}>"
        webhook = await self.bot.fetch_webhook(webhook)
        return webhook.channel.mention



    @property
    def reminders(self):
        return Reminders(self.clan_result, self.bot)

class Reminders():
    def __init__(self, clan_result, bot):
        self.clan_result = clan_result
        self.reminders = clan_result.get("reminders")
        self.bot = bot

    @property
    def clan_capital_reminder(self):
        if self.reminders is None:
            return Reminder(clan_tag=None, reminder_result=self.reminders, bot=self.bot, reminder_type="clan_capital")
        return Reminder(clan_tag=self.clan_result.get("tag"), reminder_result=self.reminders.get("clan_capital"), bot=self.bot, reminder_type="clan_capital")


class Reminder():
    def __init__(self, clan_tag, reminder_result, bot, reminder_type):
        self.clan_tag = clan_tag
        self.reminder_result = reminder_result
        self.bot: CustomClient = bot
        self.reminder_type = reminder_type

    @property
    def channel(self):
        if self.reminder_result is None:
            return Channel(channel_id=None)
        return Channel(channel_id=self.reminder_result.get("channel"))

    async def set_channel(self, channel_id: int):
        await self.bot.reminders.update_one({"tag": self.clan_tag}, {"$set": {f"reminders.{self.reminder_type}.channel": channel_id}})

    async def set_time(self, time: str, setting: bool):
        await self.bot.reminders.update_one({"tag": self.clan_tag},
                                            {"$set": {f"reminders.{self.reminder_type}.{time}": setting}})


class Channel():
    def __init__(self, channel_id):
        self.channel_id = channel_id

    def __str__(self):
        return None if self.channel_id is None else f"<#{self.channel_id}>"