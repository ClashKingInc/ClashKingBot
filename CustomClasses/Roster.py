import disnake
import coc
import emoji

from CustomClasses.CustomBot import CustomClient
from Exceptions import *
from collections import defaultdict

class Roster():
    def __init__(self, bot: CustomClient):
        self.roster_result = None
        self.bot = bot

    async def create_roster(self, guild: disnake.Guild, clan: coc.Clan, alias: str, add_members: bool):
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id": guild.id}, {"alias": alias}]})
        if roster_result is not None:
            raise RosterAliasAlreadyExists
        roster_result = await self.bot.rosters.insert_one({
            "clan_name" : clan.name,
            "clan_tag" : clan.tag,
            "clan_badge" : clan.badge.url,
            "members" : [],
            "alias" : alias,
            "server_id" : guild.id,
            "th_restriction" : "1-max"
        })
        inserted_id = roster_result.inserted_id
        roster_result = await self.bot.rosters.find_one({"_id" : inserted_id})
        self.roster_result = roster_result
        if add_members:
            players = await self.bot.get_players(tags=[member.tag for member in clan.members])
            for player in players:
                await self.add_member(player)
            roster_result = await self.bot.rosters.find_one({"_id": inserted_id})
            self.roster_result = roster_result

    async def find_roster(self, guild: disnake.Guild, alias: str):
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id": guild.id}, {"alias": alias}]})
        if roster_result is None:
            raise RosterDoesNotExist
        self.roster_result = roster_result

    async def delete(self):
        await self.bot.rosters.delete_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})

    async def embed(self):
        members = self.roster_result.get("members")
        if not members:
            embed = disnake.Embed(title=f"__{self.roster_result.get('alias')} Roster__", description="No roster members.")
            embed.set_footer(text=f"Linked to {self.roster_result.get('clan_name')}", icon_url=self.roster_result.get("clan_badge"))
            return embed

        roster_text = ""
        longest_tag = 0
        for member in members:
            tag = member.get('tag')
            if len(tag) > longest_tag:
                longest_tag = len(tag)

        thcount = defaultdict(int)
        for member in members:
            name = member.get('name')
            for char in ["`", "*", "_", "~", "ッ"]:
                name = name.replace(char, "", 10)
            name = emoji.replace_emoji(name, "")
            name = name[:12]
            name = name.ljust(12)
            tag = str(member.get('tag')).ljust(longest_tag)
            roster_text += f"{self.bot.fetch_emoji(name=member.get('townhall'))}`{name} {tag}  {member.get('hero_lvs')}`\n"
            thcount[member.get('townhall')] += 1

        tag = str("TAG").ljust(longest_tag)
        roster_text = f"`TH NAME         {tag} HERO`\n" + roster_text

        embed = disnake.Embed(title=f"__{self.roster_result.get('alias')} Roster__", description=roster_text)
        footer_text = "".join(f"Th{index}: {th} " for index, th in sorted(thcount.items(), reverse=True) if th != 0)
        embed.set_footer(text=f"{footer_text}\nLinked to {self.roster_result.get('clan_name')}\nTh{self.th_min}-Th{self.th_max}", icon_url=self.roster_result.get("clan_badge"))
        return embed

    async def missing_embed(self):
        missing = await self.missing_list()
        if not missing:
            embed = disnake.Embed(description=f"**Roster is not missing in any players in {self.roster_result.get('clan_name')}**", color=disnake.Color.red())
            return embed
        longest_tag = 0
        for member in missing:
            tag = member.get('tag')
            if len(tag) > longest_tag:
                longest_tag = len(tag)

        missing_text = ""
        for member in missing:
            name = member.get('name')
            for char in ["`", "*", "_", "~", "ッ"]:
                name = name.replace(char, "", 10)
            name = emoji.replace_emoji(name, "")
            name = name[:12]
            name = name.ljust(12)
            tag = str(member.get('tag')).ljust(longest_tag)
            missing_text += f"{self.bot.fetch_emoji(name=member.get('townhall'))}`{name} {tag}  {member.get('hero_lvs')}`\n"

        tag = str("TAG").ljust(longest_tag)
        missing_text = f"`TH NAME         {tag} HERO`\n" + missing_text

        embed = disnake.Embed(title=f"**{self.roster_result.get('alias')} Roster Missing Members**", description=missing_text)
        embed.set_footer(text=f"Linked to {self.roster_result.get('clan_name')}", icon_url=self.roster_result.get("clan_badge"))
        return embed

    async def refresh(self):
        members = self.players
        if not members:
            return
        tags = [member.get("tag") for member in members]
        players = await self.bot.get_players(tags=tags)
        for player in players:
            player: coc.Player
            await self.remove_member(player)
            await self.add_member(player)

    async def add_member(self, player: coc.Player):
        roster_members = self.roster_result.get("members")
        roster_member_tags = [member.get("tag") for member in roster_members]
        if player.tag in roster_member_tags:
            raise PlayerAlreadyInRoster
        hero_lvs = sum(hero.level for hero in player.heroes)
        await self.bot.rosters.update_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
                                          {"$push" : {"members" : {"name" : player.name, "tag" : player.tag, "townhall" : player.town_hall, "hero_lvs" : hero_lvs}}})
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})
        self.roster_result = roster_result

    async def remove_member(self, player: coc.Player):
        roster_members = self.roster_result.get("members")
        roster_member_tags = [member.get("tag") for member in roster_members]
        if player.tag not in roster_member_tags:
            raise PlayerNotInRoster
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$pull": {"members": {"tag": player.tag}}})
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})
        self.roster_result = roster_result

    async def move_member(self, player: coc.Player, new_roster):
        roster_members = self.roster_result.get("members")
        roster_member_tags = [member.get("tag") for member in roster_members]
        if player.tag not in roster_member_tags:
            raise PlayerNotInRoster
        new_roster_member_tags = [member.get("tag") for member in new_roster.roster_result.get("members")]
        if player.tag in new_roster_member_tags:
            raise PlayerAlreadyInRoster

        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$pull": {"members": {"tag": player.tag}}})
        hero_lvs = sum(hero.level for hero in player.heroes)
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias" : new_roster.roster_result.get("alias")}]},
            {"$push": {"members": {"name": player.name, "tag": player.tag, "townhall": player.town_hall,"hero_lvs": hero_lvs}}})

    async def restrict_th(self, min:int = 0, max="max"):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"th_restriction": f"{min}-{max}"}})

    @property
    def players(self):
        return self.roster_result.get("members")

    @property
    def th_min(self):
        restriction = self.roster_result.get("th_restriction")
        restriction = restriction.split("-")
        return int(restriction[0])

    @property
    def th_max(self):
        restriction = self.roster_result.get("th_restriction")
        restriction = restriction.split("-")
        if restriction[1] == "max":
            max = 15
        else:
            max = int(restriction[1])

        return max

    async def refresh_roster(self):
        pass

    async def missing_list(self):
        roster_members = self.roster_result.get("members")
        roster_member_tags = [member.get("tag") for member in roster_members]
        clan = await self.bot.getClan(self.roster_result.get("clan_tag"))
        clan_members = [member.tag for member in clan.members]
        missing_tags = list(set(roster_member_tags).difference(clan_members))
        return [member for member in roster_members if member.get("tag") in missing_tags]



