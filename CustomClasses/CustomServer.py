
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

    async def change_leadership_eval(self, option: bool):
        await self.bot.server_db.update_one({"server": self.guild.id}, {"$set" : {"leadership_eval" : option}})

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

    async def initialize_server(self):
        self.server = await self.bot.server_db.find_one({"server": self.guild.id})
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
        return [ServerClan(clan) for clan in self.clans]


class ServerClan():
    def __init__(self, clan_result):
        self.clan_result = clan_result

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