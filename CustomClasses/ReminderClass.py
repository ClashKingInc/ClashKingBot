from utils.constants import ROLES, TOWNHALL_LEVELS
from CustomClasses.CustomBot import CustomClient
from typing import List
from CustomClasses.Roster import Roster

class Reminder:
    def __init__(self, bot: CustomClient, data):
        self.__bot = bot
        self.__data = data
        self.server_id: int = data.get("server")
        self.type: str = data.get("type")
        self.clan_tag: str = data.get("clan")
        self.channel_id: int = data.get("channel")
        self.time: str = data.get("time")
        self.roles: List[str] = data.get("roles", ROLES)
        self.townhalls: List[int] = data.get("townhalls", list(reversed(TOWNHALL_LEVELS)))
        self.custom_text: str = data.get("custom_text", "")

    @property
    def point_threshold(self):
        if self.type == "Clan Games":
            return self.__data.get("point_threshold", 4000)
        return None

    @property
    def attack_threshold(self):
        if self.type == "Clan Capital":
            return self.__data.get("attack_threshold", 1)
        return None

    @property
    def war_types(self):
        if self.type == "War":
            return self.__data.get("types", ["Random", "Friendly", "CWL"])
        return None

    @property
    def ping_type(self):
        if self.type == "roster":
            return self.__data.get("ping_type", "All Roster Members")
        return None


    async def fetch_roster(self):
        if self.type == "roster":
            result = await self.__bot.rosters.find_one({"_id" : self.__data.get("roster")})
            return Roster(bot=self.__bot, roster_result=result)
        return None

    @property
    def roster(self):
        if self.type == "roster":
            result = self.__data.get("roster")
            return Roster(bot=self.__bot, roster_result=result)
        return None

    async def set_channel_id(self, id: int):
        await self.__bot.reminders.update_one(
            {"$and": [{"clan": self.clan_tag}, {"type": self.type}, {"time": self.time}, {"server": self.server_id}]},
            {"$set": {"channel": id}})

    async def set_roles(self, roles: List[str]):
        await self.__bot.reminders.update_one(
            {"$and": [{"clan": self.clan_tag}, {"type": self.type}, {"time": self.time}, {"server": self.server_id}]},
            {"$set": {"roles": roles}})

    async def set_townhalls(self, townhalls: List[int]):
        await self.__bot.reminders.update_one(
            {"$and": [{"clan": self.clan_tag}, {"type": self.type}, {"time": self.time}, {"server": self.server_id}]},
            {"$set": {"townhalls": townhalls}})

    async def set_custom_text(self, custom_text: str):
        await self.__bot.reminders.update_one(
            {"$and": [{"clan": self.clan_tag}, {"type": self.type}, {"time": self.time}, {"server": self.server_id}]},
            {"$set": {"custom_text": custom_text}})

    async def set_war_types(self, types: List[str]):
        await self.__bot.reminders.update_one(
            {"$and": [{"clan": self.clan_tag}, {"type": self.type}, {"time": self.time}, {"server": self.server_id}]},
            {"$set": {"types": types}})

    async def set_attack_threshold(self, threshold: int):
        await self.__bot.reminders.update_one(
            {"$and": [{"clan": self.clan_tag}, {"type": self.type}, {"time": self.time}, {"server": self.server_id}]},
            {"$set": {"attack_threshold": threshold}})

    async def set_point_threshold(self, threshold: int):
        await self.__bot.reminders.update_one(
            {"$and": [{"clan": self.clan_tag}, {"type": self.type}, {"time": self.time}, {"server": self.server_id}]},
            {"$set": {"point_threshold": threshold}})

    async def delete(self):
        if self.type != "roster":
            await self.__bot.reminders.delete_one({"$and": [{"clan": self.clan_tag}, {"type": self.type}, {"time": self.time}, {"server": self.server_id}]})
        else:
            await self.__bot.reminders.delete_one({"$and": [{"roster": self.__data.get("roster")}, {"type": self.type}, {"time": self.time}, {"server": self.server_id}]})