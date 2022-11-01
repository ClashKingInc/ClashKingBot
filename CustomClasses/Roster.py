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

    async def clear_roster(self):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"members": []}})

    async def delete(self):
        await self.bot.rosters.delete_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})

    async def embed(self, move_text: str = ""):
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
        for count, member in enumerate(members):
            count = f"{count + 1}".ljust(2)
            name = member.get('name')
            for char in ["`", "*", "_", "~", "ッ"]:
                name = name.replace(char, "", 10)
            name = emoji.replace_emoji(name, "")
            name = name[:12]
            name = name.ljust(12)
            tag = str(member.get('tag')).ljust(longest_tag)
            roster_text += f"`{count}`{self.bot.fetch_emoji(name=member.get('townhall'))}`{name} {tag}  {member.get('hero_lvs')}`\n"
            thcount[member.get('townhall')] += 1

        tag = str("TAG").ljust(longest_tag)
        roster_text = f"`  TH NAME         {tag} HERO`\n" + roster_text

        embed = disnake.Embed(title=f"__{self.roster_result.get('alias')} Roster__", description=roster_text)
        footer_text = "".join(f"Th{index}: {th} " for index, th in sorted(thcount.items(), reverse=True) if th != 0)
        embed.set_footer(text=f"{footer_text}\nLinked to {self.roster_result.get('clan_name')}\nTh{self.th_min}-Th{self.th_max}\n{move_text}", icon_url=self.roster_result.get("clan_badge"))
        return embed

    async def set_missing_text(self, text: str):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"missing_text": text}})
        roster_result = await self.bot.rosters.find_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]})
        self.roster_result = roster_result

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

        tag = "TAG".ljust(longest_tag)
        missing_text = f"{self.missing_text}`TH NAME         {tag} HERO`\n{missing_text}"

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
        current_clan = "No Clan"
        if player.clan is not None:
            current_clan = player.clan.name
        war_pref = player.war_opted_in
        if war_pref is None:
            war_pref = False
        await self.bot.rosters.update_one({"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
                                          {"$push" : {"members" : {"name" : player.name, "tag" : player.tag, "townhall" : player.town_hall, "hero_lvs" : hero_lvs, "current_clan": current_clan, "war_pref" : war_pref}}})
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

    async def rename(self, new_name):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"alias": new_name}})

    async def change_linked_clan(self, new_clan: coc.Clan):
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"clan_name": new_clan.name}})
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"clan_tag": new_clan.tag}})
        await self.bot.rosters.update_one(
            {"$and": [{"server_id": self.roster_result.get("server_id")}, {"alias": self.roster_result.get("alias")}]},
            {"$set": {"clan_badge": new_clan.badge.url}})

    async def other_rosters(self):
        guild = self.roster_result.get("server_id")
        aliases: list = await self.bot.rosters.distinct("alias", filter={"server_id": guild})
        aliases.remove(self.roster_result.get("alias"))
        return aliases

    async def mode_components(self, mode: str, player_page: 0):
        other_rosters = await self.other_rosters()
        roster_options = []
        for roster in other_rosters:
            roster_options.append(disnake.SelectOption(label=f"{roster}", emoji=self.bot.emoji.troop.partial_emoji, value=f"roster_{roster}"))
        roster_select = disnake.ui.Select(
            options=roster_options,
            placeholder="Roster to Edit",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        if mode == "move":
            button_text = "Remove Player Mode"
            mode_text = "mode_remove"
            color = disnake.ButtonStyle.red
        elif mode == "remove":
            button_text = "Move Player Mode"
            mode_text = "mode_move"
            color = disnake.ButtonStyle.green

        mode_buttons = [
            disnake.ui.Button(label=button_text, emoji=self.bot.emoji.gear.partial_emoji,
                              style=color,
                              custom_id=mode_text)
        ]
        buttons = disnake.ui.ActionRow()
        for button in mode_buttons:
            buttons.append_item(button)

        player_options = []
        length = 24
        if player_page >= 1:
            length = length - 1
        players = self.players[(length*player_page):(length*player_page) + length]
        if player_page >= 1:
            player_options.append(disnake.SelectOption(label=f"Previous 25 Players", emoji=self.bot.emoji.back.partial_emoji, value=f"players_{player_page - 1}"))
        for count, player in enumerate(players):
            player_options.append(disnake.SelectOption(label=f"{player.get('name')}",
                                                       emoji=self.bot.partial_emoji_gen(emoji_string=self.bot.fetch_emoji(name=player.get('townhall'))),
                                                       value=f"edit_{player.get('tag')}"))
        if len(players) == length and (len(self.players) > (length * player_page) + length):
            player_options.append(disnake.SelectOption(label=f"Next 25 Players", emoji=self.bot.emoji.forward.partial_emoji, value=f"players_{player_page + 1}"))

        player_select = disnake.ui.Select(
            options=player_options,
            placeholder=f"Select Player(s) to {mode}",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(players),  # the maximum number of options a user can select
        )

        dropdown = [disnake.ui.ActionRow(roster_select), disnake.ui.ActionRow(player_select)]
        if mode == "move":
            roster_options = []
            for roster in other_rosters:
                roster_options.append(disnake.SelectOption(label=f"{roster}", emoji=self.bot.emoji.troop.partial_emoji,
                                                           value=f"rostermove_{roster}"))
            roster_select = disnake.ui.Select(
                options=roster_options,
                placeholder="Select Roster To Move To",  # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=1,  # the maximum number of options a user can select
            )
            dropdown.append(disnake.ui.ActionRow(roster_select))

        dropdown.append(buttons)
        if not self.players:
            dropdown = [dropdown[0], dropdown[-1]]
        return dropdown


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

    @property
    def missing_text(self):
        if self.roster_result.get("missing_text") is None:
            return ""
        return self.roster_result.get("missing_text") + "\n"

    async def refresh_roster(self):
        pass

    async def missing_list(self):
        roster_members = self.roster_result.get("members")
        roster_member_tags = [member.get("tag") for member in roster_members]
        clan = await self.bot.getClan(self.roster_result.get("clan_tag"))
        clan_members = [member.tag for member in clan.members]
        missing_tags = list(set(roster_member_tags).difference(clan_members))
        return [member for member in roster_members if member.get("tag") in missing_tags]



